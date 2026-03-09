from __future__ import annotations

import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from scraper.core.models import EngineType, FetchResult


class BrowserEngine:
    def __init__(self, timeout_ms: int = 30000, headless: bool = True) -> None:
        self.timeout_ms = timeout_ms
        self.headless = headless

    def fetch(self, url: str) -> FetchResult:
        with sync_playwright() as p:
            attempts = [("chromium", p.chromium), ("firefox", p.firefox), ("webkit", p.webkit)]
            last_result: tuple[str, str, int | None] | None = None

            for _, browser_type in attempts:
                html, final_url, status_code = self._fetch_with_browser_type(browser_type, url)
                last_result = (html, final_url, status_code)
                if not self._looks_blocked(html, status_code):
                    return FetchResult(
                        url=url,
                        html=html,
                        status_code=status_code,
                        final_url=final_url,
                        engine_used=EngineType.BROWSER,
                    )

            # If all browser types return blocked content, return the last response.
            if last_result is None:
                raise RuntimeError(f"Browser fetch failed for {url}")
            html, final_url, status_code = last_result

        return FetchResult(
            url=url,
            html=html,
            status_code=status_code,
            final_url=final_url,
            engine_used=EngineType.BROWSER,
        )

    def _fetch_with_browser_type(self, browser_type, url: str) -> tuple[str, str, int | None]:
        browser = browser_type.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        try:
            page = context.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
            page.wait_for_load_state("networkidle", timeout=self.timeout_ms)
            self._wait_through_waf_challenge(page, max_wait_seconds=20)
            self._prime_accordion_panels(page, start_url=url)
            html = page.content()
            final_url = page.url
            status_code = response.status if response else None
            return html, final_url, status_code
        finally:
            context.close()
            browser.close()

    def _prime_accordion_panels(self, page, start_url: str) -> None:
        """Open accordion panels one-by-one based on 'collapsed' class to load panel content."""
        page.wait_for_timeout(800)

        # Click only accordion toggles that target in-page collapse IDs.
        toggles = page.locator(
            "#accordion .panel-title a[data-toggle='collapse'][href^='#'], "
            ".panel-group .panel-title a[data-toggle='collapse'][href^='#']"
        )
        count = toggles.count()
        for i in range(count):
            link = toggles.nth(i)
            try:
                classes = (link.get_attribute("class") or "").strip()
                href = (link.get_attribute("href") or "").strip()
                parent = (link.get_attribute("data-parent") or "").strip()
                controls = (link.get_attribute("aria-controls") or "").strip()

                is_closed = "collapsed" in classes
                valid_toggle = href.startswith("#") and (parent.startswith("#accordion") or controls)
                if is_closed:
                    if not valid_toggle:
                        continue
                    link.click(timeout=1500)
                    page.wait_for_timeout(500)
                    if not self._same_base_url(page.url, start_url):
                        page.goto(start_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                        page.wait_for_timeout(500)
            except Exception:
                continue

        page.wait_for_timeout(800)

    @staticmethod
    def _looks_blocked(html: str, status_code: int | None) -> bool:
        body = html.lower()
        if status_code in {401, 403, 429, 503}:
            return True
        markers = [
            "403 forbidden",
            "access denied",
            "javascript is disabled",
            "attention required",
            "cf-browser-verification",
            "cloudflare",
        ]
        return any(marker in body for marker in markers)

    def _wait_through_waf_challenge(self, page, max_wait_seconds: int = 20) -> None:
        """Allow AWS WAF JS challenge page to set token + reload before capturing DOM."""
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            html = page.content().lower()
            if "token.awswaf.com" in html or "challenge-container" in html:
                page.wait_for_timeout(1500)
                continue
            if "javascript is disabled" in html and "awswafintegration" in html:
                page.wait_for_timeout(1500)
                continue
            return

    @staticmethod
    def _same_base_url(current_url: str, expected_url: str) -> bool:
        current = urlsplit(current_url)
        expected = urlsplit(expected_url)
        return (
            current.scheme == expected.scheme
            and current.netloc == expected.netloc
            and current.path.rstrip("/") == expected.path.rstrip("/")
        )

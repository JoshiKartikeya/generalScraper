from __future__ import annotations

from playwright.sync_api import sync_playwright

from scraper.core.models import EngineType, FetchResult


class BrowserEngine:
    def __init__(self, timeout_ms: int = 30000, headless: bool = True) -> None:
        self.timeout_ms = timeout_ms
        self.headless = headless

    def fetch(self, url: str) -> FetchResult:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=self.timeout_ms)
            html = page.content()
            final_url = page.url
            context.close()
            browser.close()

        return FetchResult(
            url=url,
            html=html,
            status_code=200,
            final_url=final_url,
            engine_used=EngineType.BROWSER,
        )

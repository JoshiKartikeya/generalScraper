from __future__ import annotations

from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class SamacoAboutAdapter(BaseAdapter):
    name = "samaco_about"
    engine_preference = EngineType.AUTO

    allowed_domain = "www.samaco.com.sa"
    allowed_path_prefix = "/en/about-us/"
    ignored_snippets = (
        "Do you have a query or question?",
        "Stay up to date with all the latest news and updates",
    )

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        final_url = fetch_result.final_url or fetch_result.url

        title_node = tree.css_first("h1")
        breadcrumb_nodes = tree.css(".breadcrumb a")
        paragraphs = self._extract_main_paragraphs(tree)

        record = ScrapeRecord(
            source_url=final_url,
            payload={
                "url": final_url,
                "title": title_node.text(strip=True) if title_node else None,
                "breadcrumbs": [
                    node.text(strip=True)
                    for node in breadcrumb_nodes
                    if node.text(strip=True)
                ],
                "body": "\n\n".join(paragraphs) if paragraphs else None,
                "body_paragraphs": paragraphs,
                "engine_used": fetch_result.engine_used.value,
                "status_code": fetch_result.status_code,
            },
        )
        return [record]

    def discover_links(self, fetch_result: FetchResult) -> list[str]:
        tree = HTMLParser(fetch_result.html)
        current_url = fetch_result.final_url or fetch_result.url
        links: set[str] = set()

        for node in tree.css("a[href]"):
            href = node.attributes.get("href")
            if not href:
                continue
            candidate = urljoin(current_url, href.strip())
            if self._is_allowed(candidate):
                links.add(candidate)

        return sorted(links)

    def _is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != self.allowed_domain:
            return False
        return parsed.path.startswith(self.allowed_path_prefix)

    @staticmethod
    def _extract_main_paragraphs(tree: HTMLParser) -> list[str]:
        selectors = [
            ".textInner p",
            ".text.span8 p",
            ".inner .text p",
            ".about-us p",
        ]
        seen: set[str] = set()
        paragraphs: list[str] = []
        for selector in selectors:
            for node in tree.css(selector):
                text = " ".join(node.text(separator=" ", strip=True).split())
                if not text:
                    continue
                if len(text) < 35:
                    continue
                if any(snippet in text for snippet in SamacoAboutAdapter.ignored_snippets):
                    continue
                if text in seen:
                    continue
                seen.add(text)
                paragraphs.append(text)
        return paragraphs

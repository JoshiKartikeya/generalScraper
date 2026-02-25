from __future__ import annotations

from urllib.parse import urlparse

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class SamacoCareersAdapter(BaseAdapter):
    name = "samaco_careers"
    engine_preference = EngineType.AUTO

    allowed_domain = "www.samaco.com.sa"
    allowed_path_prefix = "/en/site/careers/"
    ignored_snippets = (
        "Do you have a query or question?",
        "Stay up to date with all the latest news and updates",
    )

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        final_url = fetch_result.final_url or fetch_result.url

        return [
            ScrapeRecord(
                source_url=final_url,
                payload={
                    "url": final_url,
                    "page_title": self._extract_page_title(tree),
                    "headings_h1": self._extract_texts(tree, "h1", min_len=2),
                    "headings_h2": self._extract_texts(tree, "h2", min_len=2),
                    "headings_h3": self._extract_texts(tree, "h3", min_len=2),
                    "breadcrumbs": self._extract_texts(tree, ".breadcrumb a", min_len=1),
                    "body_paragraphs": self._extract_paragraphs(tree),
                    "engine_used": fetch_result.engine_used.value,
                    "status_code": fetch_result.status_code,
                },
            )
        ]

    def discover_links(self, fetch_result: FetchResult) -> list[str]:
        return []

    @staticmethod
    def _extract_page_title(tree: HTMLParser) -> str | None:
        node = tree.css_first("title")
        if not node:
            return None
        text = " ".join(node.text(separator=" ", strip=True).split())
        return text or None

    @staticmethod
    def _extract_texts(tree: HTMLParser, selector: str, min_len: int = 1) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for node in tree.css(selector):
            text = " ".join(node.text(separator=" ", strip=True).split())
            if len(text) < min_len:
                continue
            if text in seen:
                continue
            seen.add(text)
            values.append(text)
        return values

    @classmethod
    def _extract_paragraphs(cls, tree: HTMLParser) -> list[str]:
        seen: set[str] = set()
        paragraphs: list[str] = []
        for node in tree.css("p"):
            text = " ".join(node.text(separator=" ", strip=True).split())
            if len(text) < 20:
                continue
            if any(snippet in text for snippet in cls.ignored_snippets):
                continue
            if text in seen:
                continue
            seen.add(text)
            paragraphs.append(text)
        return paragraphs

    def _is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if parsed.netloc != self.allowed_domain:
            return False
        return parsed.path.startswith(self.allowed_path_prefix)

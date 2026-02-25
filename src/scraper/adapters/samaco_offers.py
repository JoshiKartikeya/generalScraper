from __future__ import annotations

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class SamacoOffersAdapter(BaseAdapter):
    name = "samaco_offers"
    engine_preference = EngineType.HTTP

    ignored_snippets = (
        "Do you have a query or question?",
        "Stay up to date with all the latest news and updates",
        "Member of Al Nahla Group",
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
                    "page_links": self._extract_links(tree, final_url),
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
            if len(text) < 25:
                continue
            if any(snippet in text for snippet in cls.ignored_snippets):
                continue
            if text in seen:
                continue
            seen.add(text)
            paragraphs.append(text)
        return paragraphs

    @staticmethod
    def _extract_links(tree: HTMLParser, base_url: str) -> list[dict[str, str]]:
        seen: set[str] = set()
        links: list[dict[str, str]] = []
        for node in tree.css("a[href]"):
            href = node.attributes.get("href")
            if not href:
                continue
            label = " ".join(node.text(separator=" ", strip=True).split())
            full_url = urljoin(base_url, href.strip())
            key = f"{label}|{full_url}"
            if key in seen:
                continue
            seen.add(key)
            links.append({"label": label, "url": full_url})
        return links

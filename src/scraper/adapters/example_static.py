from __future__ import annotations

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class ExampleStaticAdapter(BaseAdapter):
    name = "example_static"
    engine_preference = EngineType.AUTO

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        title_node = tree.css_first("h1")
        paragraph_node = tree.css_first("p")

        record = ScrapeRecord(
            source_url=fetch_result.final_url or fetch_result.url,
            payload={
                "title": title_node.text(strip=True) if title_node else None,
                "summary": paragraph_node.text(strip=True) if paragraph_node else None,
                "engine_used": fetch_result.engine_used.value,
                "status_code": fetch_result.status_code,
            },
        )
        return [record]

from __future__ import annotations

from abc import ABC, abstractmethod

from scraper.core.models import EngineType, FetchResult, ScrapeRecord, ScrapeRequest


class BaseAdapter(ABC):
    name: str = "base"
    engine_preference: EngineType = EngineType.AUTO

    def build_request(self, url: str) -> ScrapeRequest:
        return ScrapeRequest(
            url=url,
            adapter_name=self.name,
            engine=self.engine_preference,
        )

    @abstractmethod
    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        """Extract records from fetched page."""

    def discover_links(self, fetch_result: FetchResult) -> list[str]:
        """Return links to crawl next from this page."""
        return []

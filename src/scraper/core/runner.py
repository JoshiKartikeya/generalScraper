from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urldefrag

from scraper.adapters.base import BaseAdapter
from scraper.adapters.registry import get_adapter
from scraper.core.models import EngineType, FetchResult
from scraper.engines.browser_engine import BrowserEngine
from scraper.engines.http_engine import HttpEngine
from scraper.pipeline.dedupe import DedupeStore
from scraper.pipeline.jsonl_sink import JsonlSink


@dataclass(slots=True)
class RunnerConfig:
    output_dir: Path = Path("output")
    retries: int = 2
    retry_backoff_seconds: float = 1.5
    browser_headless: bool = True
    max_pages: int = 50
    persistent_dedupe: bool = True


class ScrapeRunner:
    def __init__(self, config: RunnerConfig | None = None) -> None:
        self.config = config or RunnerConfig()
        self.http_engine = HttpEngine()
        self.browser_engine = BrowserEngine(headless=self.config.browser_headless)
        state_dir = self.config.output_dir / ".state" if self.config.persistent_dedupe else None
        self.dedupe = DedupeStore(state_dir=state_dir)

    def run_single(self, adapter_name: str, url: str) -> tuple[int, Path, EngineType]:
        adapter = get_adapter(adapter_name)
        request = adapter.build_request(url)
        queue: list[str] = [request.url]
        queued: set[str] = {self._normalize_url(request.url)}
        visited: set[str] = set()
        all_records = []
        first_engine_used: EngineType | None = None

        while queue and len(visited) < self.config.max_pages:
            current_url = queue.pop(0)
            normalized_current = self._normalize_url(current_url)
            queued.discard(normalized_current)
            if normalized_current in visited:
                continue

            fetch_result = self._fetch_with_fallback(adapter, current_url, request.engine)
            if first_engine_used is None:
                first_engine_used = fetch_result.engine_used
            visited.add(normalized_current)
            all_records.extend(adapter.extract(fetch_result))

            for next_url in adapter.discover_links(fetch_result):
                normalized_next = self._normalize_url(next_url)
                if normalized_next in visited or normalized_next in queued:
                    continue
                queue.append(next_url)
                queued.add(normalized_next)

        new_records = self.dedupe.filter_new(all_records)

        timestamp = int(time.time())
        out_path = self.config.output_dir / f"scrape-{timestamp}.jsonl"
        sink = JsonlSink(out_path)
        count = sink.write(new_records)
        if self.config.persistent_dedupe:
            self.dedupe.flush()
        return count, out_path, first_engine_used or request.engine

    def close(self) -> None:
        self.http_engine.close()

    def _fetch_with_fallback(
        self, adapter: BaseAdapter, url: str, engine: EngineType
    ) -> FetchResult:
        if engine == EngineType.HTTP:
            return self._retry_fetch(self.http_engine.fetch, url)
        if engine == EngineType.BROWSER:
            return self._retry_fetch(self.browser_engine.fetch, url)

        try:
            http_result = self._retry_fetch(self.http_engine.fetch, url)
            if self._looks_usable(adapter, http_result):
                return http_result
        except Exception:
            # In auto mode, any HTTP failure should escalate to browser fallback.
            pass
        return self._retry_fetch(self.browser_engine.fetch, url)

    def _looks_usable(self, adapter: BaseAdapter, fetch_result: FetchResult) -> bool:
        try:
            extracted = adapter.extract(fetch_result)
            return len(extracted) > 0 and any(r.payload for r in extracted)
        except Exception:
            return False

    def _retry_fetch(self, fetch_fn, url: str) -> FetchResult:
        last_error: Exception | None = None
        for attempt in range(self.config.retries + 1):
            try:
                return fetch_fn(url)
            except Exception as exc:
                last_error = exc
                if attempt >= self.config.retries:
                    raise
                wait = self.config.retry_backoff_seconds * (attempt + 1)
                time.sleep(wait)
        raise RuntimeError(f"Failed to fetch {url}: {last_error}")

    @staticmethod
    def _normalize_url(url: str) -> str:
        clean_url, _ = urldefrag(url)
        return clean_url.rstrip("/")

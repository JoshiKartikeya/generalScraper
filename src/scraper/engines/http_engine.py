from __future__ import annotations

import httpx

from scraper.core.models import EngineType, FetchResult


class HttpEngine:
    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )

    def fetch(self, url: str) -> FetchResult:
        response = self._client.get(url)
        response.raise_for_status()
        return FetchResult(
            url=url,
            html=response.text,
            status_code=response.status_code,
            final_url=str(response.url),
            engine_used=EngineType.HTTP,
        )

    def close(self) -> None:
        self._client.close()

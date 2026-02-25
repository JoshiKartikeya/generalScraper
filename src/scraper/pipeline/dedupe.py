from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scraper.core.models import ScrapeRecord


class DedupeStore:
    def __init__(self, state_dir: Path | None = None) -> None:
        self._seen: set[str] = set()
        self._seen_urls: set[str] = set()
        self._state_dir = state_dir
        self._hash_file = None
        self._url_file = None
        if self._state_dir is not None:
            self._hash_file = self._state_dir / "seen_hashes.txt"
            self._url_file = self._state_dir / "seen_urls.txt"
            self._load_state()

    def filter_new(self, records: list[ScrapeRecord]) -> list[ScrapeRecord]:
        fresh: list[ScrapeRecord] = []
        for record in records:
            digest = self._hash_record(record)
            if digest in self._seen:
                continue
            self._seen.add(digest)
            fresh.append(record)
        return fresh

    def has_seen_url(self, normalized_url: str) -> bool:
        return normalized_url in self._seen_urls

    def mark_url_seen(self, normalized_url: str) -> None:
        self._seen_urls.add(normalized_url)

    def flush(self) -> None:
        if self._state_dir is None:
            return
        self._state_dir.mkdir(parents=True, exist_ok=True)
        if self._hash_file is not None:
            self._hash_file.write_text(
                "\n".join(sorted(self._seen)),
                encoding="utf-8",
            )
        if self._url_file is not None:
            self._url_file.write_text(
                "\n".join(sorted(self._seen_urls)),
                encoding="utf-8",
            )

    def _load_state(self) -> None:
        assert self._state_dir is not None
        self._state_dir.mkdir(parents=True, exist_ok=True)

        if self._hash_file is not None and self._hash_file.exists():
            content = self._hash_file.read_text(encoding="utf-8")
            self._seen.update(line.strip() for line in content.splitlines() if line.strip())
        if self._url_file is not None and self._url_file.exists():
            content = self._url_file.read_text(encoding="utf-8")
            self._seen_urls.update(
                line.strip() for line in content.splitlines() if line.strip()
            )

        # One-time bootstrap from existing outputs when state files are absent.
        if self._hash_file is not None and self._url_file is not None:
            if not self._hash_file.exists() and not self._url_file.exists():
                self._bootstrap_from_output_files()
                self.flush()

    def _bootstrap_from_output_files(self) -> None:
        assert self._state_dir is not None
        output_dir = self._state_dir.parent
        for output_file in output_dir.glob("scrape-*.jsonl"):
            for line in output_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                source_url = obj.get("source_url")
                payload = obj.get("payload")
                if not isinstance(source_url, str) or not isinstance(payload, dict):
                    continue

                normalized_url = source_url.rstrip("/")
                self._seen_urls.add(normalized_url)
                digest = self._hash_from_values(source_url=source_url, payload=payload)
                self._seen.add(digest)

    @staticmethod
    def _hash_record(record: ScrapeRecord) -> str:
        return DedupeStore._hash_from_values(
            source_url=record.source_url,
            payload=record.payload,
        )

    @staticmethod
    def _hash_from_values(source_url: str, payload: dict) -> str:
        raw = f"{source_url}|{sorted(payload.items())}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

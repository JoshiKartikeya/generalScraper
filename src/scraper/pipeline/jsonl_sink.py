from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from scraper.core.models import ScrapeRecord


class JsonlSink:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, records: Iterable[ScrapeRecord]) -> int:
        count = 0
        with self.output_path.open("a", encoding="utf-8") as f:
            for record in records:
                f.write(
                    json.dumps(
                        {
                            "source_url": record.source_url,
                            "payload": record.payload,
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )
                count += 1
        return count

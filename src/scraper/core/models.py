from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EngineType(str, Enum):
    AUTO = "auto"
    HTTP = "http"
    BROWSER = "browser"


@dataclass(slots=True)
class ScrapeRequest:
    url: str
    adapter_name: str
    engine: EngineType = EngineType.AUTO
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    url: str
    html: str
    status_code: int | None = None
    final_url: str | None = None
    engine_used: EngineType = EngineType.HTTP


@dataclass(slots=True)
class ScrapeRecord:
    source_url: str
    payload: dict[str, Any]

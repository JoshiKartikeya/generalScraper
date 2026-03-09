from __future__ import annotations

from scraper.adapters.base import BaseAdapter
from scraper.adapters.example_static import ExampleStaticAdapter
from scraper.adapters.iga_service_info import IgaServiceInfoAdapter
from scraper.adapters.samaco_about import SamacoAboutAdapter


_ADAPTERS: dict[str, type[BaseAdapter]] = {
    ExampleStaticAdapter.name: ExampleStaticAdapter,
    IgaServiceInfoAdapter.name: IgaServiceInfoAdapter,
    SamacoAboutAdapter.name: SamacoAboutAdapter,
}


def get_adapter(name: str) -> BaseAdapter:
    if name not in _ADAPTERS:
        available = ", ".join(sorted(_ADAPTERS.keys()))
        raise ValueError(f"Unknown adapter '{name}'. Available: {available}")
    return _ADAPTERS[name]()


def list_adapters() -> list[str]:
    return sorted(_ADAPTERS.keys())

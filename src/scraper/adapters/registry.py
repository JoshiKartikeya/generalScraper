from __future__ import annotations

from scraper.adapters.base import BaseAdapter
from scraper.adapters.example_static import ExampleStaticAdapter
from scraper.adapters.samaco_about import SamacoAboutAdapter
from scraper.adapters.samaco_car_accessories import SamacoCarAccessoriesAdapter
from scraper.adapters.samaco_car_parts import SamacoCarPartsAdapter
from scraper.adapters.samaco_careers import SamacoCareersAdapter
from scraper.adapters.samaco_contact import SamacoContactAdapter
from scraper.adapters.samaco_lifestyle import SamacoLifestyleAdapter
from scraper.adapters.samaco_offers import SamacoOffersAdapter


_ADAPTERS: dict[str, type[BaseAdapter]] = {
    ExampleStaticAdapter.name: ExampleStaticAdapter,
    SamacoAboutAdapter.name: SamacoAboutAdapter,
    SamacoCarAccessoriesAdapter.name: SamacoCarAccessoriesAdapter,
    SamacoCarPartsAdapter.name: SamacoCarPartsAdapter,
    SamacoCareersAdapter.name: SamacoCareersAdapter,
    SamacoContactAdapter.name: SamacoContactAdapter,
    SamacoLifestyleAdapter.name: SamacoLifestyleAdapter,
    SamacoOffersAdapter.name: SamacoOffersAdapter,
}


def get_adapter(name: str) -> BaseAdapter:
    if name not in _ADAPTERS:
        available = ", ".join(sorted(_ADAPTERS.keys()))
        raise ValueError(f"Unknown adapter '{name}'. Available: {available}")
    return _ADAPTERS[name]()


def list_adapters() -> list[str]:
    return sorted(_ADAPTERS.keys())

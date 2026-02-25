from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class SamacoCarPartsAdapter(BaseAdapter):
    name = "samaco_car_parts"
    engine_preference = EngineType.HTTP

    allowed_domain = "shop.samaco.com.sa"
    allowed_path = "/en/car-parts"

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        final_url = fetch_result.final_url or fetch_result.url
        page_number = self._page_number(final_url)

        records: list[ScrapeRecord] = []
        cards = tree.css("div.part-card")
        for card in cards:
            name_node = card.css_first("p.font-semibold.mb-3.mt-1")
            if not name_node:
                continue

            link_node = card.css_first("a[href]")

            part_name = " ".join(name_node.text(separator=" ", strip=True).split())
            part_url = (
                urljoin(final_url, link_node.attributes.get("href", ""))
                if link_node
                else None
            )

            records.append(
                ScrapeRecord(
                    source_url=final_url,
                    payload={
                        "collection": "car_parts",
                        "page_url": final_url,
                        "page_number": page_number,
                        "part_name": part_name,
                        "product_name": part_name,
                        "part_name_tag": "p.font-semibold.mb-3.mt-1",
                        "product_name_tag": "p.font-semibold.mb-3.mt-1",
                        "part_url": part_url,
                        "product_url": part_url,
                        "engine_used": fetch_result.engine_used.value,
                        "status_code": fetch_result.status_code,
                    },
                )
            )

        return records

    def discover_links(self, fetch_result: FetchResult) -> list[str]:
        # Only paginate this listing; do not crawl part-detail or other links.
        tree = HTMLParser(fetch_result.html)
        cards = tree.css("div.part-card")
        if not cards:
            return []

        final_url = fetch_result.final_url or fetch_result.url
        parsed = urlparse(final_url)
        if parsed.netloc != self.allowed_domain:
            return []
        if parsed.path.rstrip("/") != self.allowed_path:
            return []

        next_page = self._page_number(final_url) + 1
        return [self._build_page_url(final_url, next_page)]

    @staticmethod
    def _page_number(url: str) -> int:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        value = query.get("page", ["1"])[0]
        try:
            page_number = int(value)
            return page_number if page_number > 0 else 1
        except ValueError:
            return 1

    @staticmethod
    def _build_page_url(base_url: str, page_number: int) -> str:
        parsed = urlparse(base_url)
        query = parse_qs(parsed.query)
        query["page"] = [str(page_number)]
        new_query = urlencode(query, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                "",
            )
        )

from __future__ import annotations

import json
from html import unescape
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class SamacoContactAdapter(BaseAdapter):
    name = "samaco_contact"
    engine_preference = EngineType.AUTO

    allowed_domain = "www.samaco.com.sa"
    allowed_path_prefix = "/en/contact-us/"
    excluded_paths = {
        "/en/contact-us/complaints",
        "/en/contact-us/complaints/",
    }

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        final_url = fetch_result.final_url or fetch_result.url
        parsed = urlparse(final_url)
        if parsed.path.rstrip("/") in {p.rstrip("/") for p in self.excluded_paths}:
            return []

        emails = self._extract_contacts(tree, "a[href^='mailto:']", "mailto:")
        phones = self._extract_contacts(tree, "a[href^='tel:']", "tel:")
        records: list[ScrapeRecord] = []

        cards = tree.css("div.list-item.locations.listing")
        for card in cards:
            title_node = card.css_first("h3 a")
            address_node = card.css_first("a.address")
            line1_node = card.css_first(".address-line1")
            city_node = card.css_first(".address-city")
            details_node = card.css_first("a.btn")
            image_node = card.css_first("img")
            distance_node = card.css_first("a[data-latitude][data-longitude]")

            title = title_node.text(strip=True) if title_node else None
            detail_url = (
                urljoin(final_url, details_node.attributes.get("href", ""))
                if details_node
                else None
            )
            location_url = (
                urljoin(final_url, title_node.attributes.get("href", ""))
                if title_node
                else detail_url
            )
            raw_context = card.attributes.get("data-dealer-context", "")
            dealer_context = self._parse_dealer_context(raw_context)

            records.append(
                ScrapeRecord(
                    source_url=final_url,
                    payload={
                        "page_url": final_url,
                        "location_id": card.attributes.get("data-id"),
                        "location_name": title,
                        "location_url": location_url,
                        "location_details_url": detail_url,
                        "address": address_node.text(separator=" ", strip=True)
                        if address_node
                        else None,
                        "address_line1": line1_node.text(strip=True) if line1_node else None,
                        "address_city": city_node.text(strip=True) if city_node else None,
                        "latitude": distance_node.attributes.get("data-latitude")
                        if distance_node
                        else None,
                        "longitude": distance_node.attributes.get("data-longitude")
                        if distance_node
                        else None,
                        "image_url": image_node.attributes.get("src") if image_node else None,
                        "dealer_context": dealer_context,
                        "emails": emails,
                        "phones": phones,
                        "engine_used": fetch_result.engine_used.value,
                        "status_code": fetch_result.status_code,
                    },
                )
            )

        if records:
            return records

        return [
            ScrapeRecord(
                source_url=final_url,
                payload={
                    "page_url": final_url,
                    "location_id": None,
                    "location_name": None,
                    "location_url": None,
                    "location_details_url": None,
                    "address": None,
                    "address_line1": None,
                    "address_city": None,
                    "latitude": None,
                    "longitude": None,
                    "image_url": None,
                    "dealer_context": None,
                    "emails": emails,
                    "phones": phones,
                    "engine_used": fetch_result.engine_used.value,
                    "status_code": fetch_result.status_code,
                },
            )
        ]

    def discover_links(self, fetch_result: FetchResult) -> list[str]:
        return []

    @staticmethod
    def _extract_contacts(tree: HTMLParser, selector: str, prefix: str) -> list[str]:
        values: set[str] = set()
        for node in tree.css(selector):
            href = node.attributes.get("href")
            if not href or not href.startswith(prefix):
                continue
            value = href.replace(prefix, "", 1).strip()
            if value:
                values.add(value)
        return sorted(values)

    @staticmethod
    def _parse_dealer_context(raw_context: str) -> dict | None:
        if not raw_context:
            return None
        try:
            return json.loads(unescape(raw_context))
        except json.JSONDecodeError:
            return None

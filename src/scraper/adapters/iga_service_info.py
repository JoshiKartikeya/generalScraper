from __future__ import annotations

from selectolax.parser import HTMLParser, Node

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class IgaServiceInfoAdapter(BaseAdapter):
    name = "iga_service_info"
    engine_preference = EngineType.BROWSER

    PANEL_SELECTORS = [
        "#accordion .panel.panel-default",
        ".panel-group .panel.panel-default",
    ]
    PANEL_TITLE_SELECTORS = [".panel-heading .panel-title a", ".panel-heading .panel-title", ".panel-title"]
    PANEL_BODY_SELECTORS = [".panel-collapse .panel-body", ".panel-collapse", ".panel-body"]

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        tree = HTMLParser(fetch_result.html)
        final_url = fetch_result.final_url or fetch_result.url
        page_title = self._text_first(tree, ["h1", "h2", "h3", "title"]) or "IGA Service Page"

        panels = self._collect_panels(tree)
        if not panels:
            return []

        records: list[ScrapeRecord] = []
        for panel in panels:
            accordion_title = self._text_first(panel, self.PANEL_TITLE_SELECTORS)
            if not accordion_title:
                continue

            panel_id = self._panel_section_id(panel)
            body = self._first_node(panel, self.PANEL_BODY_SELECTORS) or panel
            full_text = self._clean_text(body.text(separator="\n", strip=True))
            if not full_text:
                continue

            payload = {
                "pageTitle": page_title,
                "accordionTitle": accordion_title,
                "accordionId": panel_id,
                "content": full_text,
            }
            records.append(ScrapeRecord(source_url=final_url, payload=payload))

        return records

    def _collect_panels(self, tree: HTMLParser) -> list[Node]:
        for selector in self.PANEL_SELECTORS:
            nodes = tree.css(selector)
            if nodes:
                return nodes
        return []

    @staticmethod
    def _panel_section_id(panel: Node) -> str | None:
        collapse = panel.css_first(".panel-collapse")
        if collapse:
            collapse_id = collapse.attributes.get("id")
            if collapse_id:
                return collapse_id
        trigger = panel.css_first(".panel-title a[href^='#']")
        if not trigger:
            return None
        href = trigger.attributes.get("href")
        if href and href.startswith("#"):
            return href[1:]
        return None

    @staticmethod
    def _text_first(scope, selectors: list[str]) -> str | None:
        for selector in selectors:
            node = scope.css_first(selector)
            if not node:
                continue
            text = " ".join(node.text(separator=" ", strip=True).split())
            if text:
                return text
        return None

    @staticmethod
    def _first_node(scope, selectors: list[str]) -> Node | None:
        for selector in selectors:
            node = scope.css_first(selector)
            if node:
                return node
        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines)

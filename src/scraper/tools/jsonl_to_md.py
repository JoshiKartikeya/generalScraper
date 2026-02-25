from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert scraper JSONL output into structured Markdown."
    )
    parser.add_argument("--input", required=True, help="Input JSONL path")
    parser.add_argument("--output", required=True, help="Output Markdown path")
    parser.add_argument(
        "--title",
        default="Scrape Report",
        help="Top-level document title",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def group_by_page(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        payload = row.get("payload", {})
        page_key = payload.get("page_url") or payload.get("url") or row.get("source_url")
        if not page_key:
            page_key = "unknown-page"
        grouped[str(page_key)].append(row)
    return dict(grouped)


def render_markdown(title: str, grouped_rows: dict[str, list[dict[str, Any]]]) -> str:
    lines: list[str] = [f"# {title}", ""]
    for page_url in sorted(grouped_rows.keys()):
        rows = grouped_rows[page_url]
        lines.extend(render_page(page_url, rows))
    return "\n".join(lines).rstrip() + "\n"


def render_page(page_url: str, rows: list[dict[str, Any]]) -> list[str]:
    first_payload = rows[0].get("payload", {})
    page_title = pick_page_title(first_payload)

    lines = [f"## {page_title}", "", f"- URL: {page_url}", f"- Records: {len(rows)}", ""]

    if is_location_payload(first_payload):
        lines.extend(render_locations(rows))
        return lines

    lines.extend(render_content(first_payload))
    return lines


def pick_page_title(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("title"),
        payload.get("page_title"),
    ]
    headings_h1 = payload.get("headings_h1")
    if isinstance(headings_h1, list) and headings_h1:
        candidates.append(headings_h1[0])

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Untitled Page"


def is_location_payload(payload: dict[str, Any]) -> bool:
    return "location_name" in payload or "location_id" in payload


def render_locations(rows: list[dict[str, Any]]) -> list[str]:
    lines = ["### Locations", ""]

    sorted_rows = sorted(
        rows,
        key=lambda r: str((r.get("payload", {}).get("location_name") or "")).lower(),
    )
    for idx, row in enumerate(sorted_rows, start=1):
        payload = row.get("payload", {})
        name = payload.get("location_name") or f"Location {idx}"
        lines.append(f"#### {name}")
        lines.extend(
            kv_lines(
                [
                    ("Location ID", payload.get("location_id")),
                    ("Address", payload.get("address")),
                    ("City", payload.get("address_city")),
                    ("Latitude", payload.get("latitude")),
                    ("Longitude", payload.get("longitude")),
                    ("Location URL", payload.get("location_url")),
                    ("Details URL", payload.get("location_details_url")),
                    ("Image URL", payload.get("image_url")),
                    ("Emails", join_list(payload.get("emails"))),
                    ("Phones", join_list(payload.get("phones"))),
                ]
            )
        )
        dealer_context = payload.get("dealer_context")
        if isinstance(dealer_context, dict) and dealer_context:
            lines.append("- Dealer Context:")
            for key in sorted(dealer_context.keys()):
                lines.append(f"  - {key}: {dealer_context[key]}")
        lines.append("")
    return lines


def render_content(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    breadcrumbs = payload.get("breadcrumbs")
    if isinstance(breadcrumbs, list) and breadcrumbs:
        lines.append(f"- Breadcrumbs: {' > '.join(str(x) for x in breadcrumbs)}")
        lines.append("")

    headings_h1 = normalize_str_list(payload.get("headings_h1"))
    headings_h2 = normalize_str_list(payload.get("headings_h2"))
    headings_h3 = normalize_str_list(payload.get("headings_h3"))
    paragraphs = normalize_str_list(payload.get("body_paragraphs"))

    if headings_h1:
        lines.append("### Main Sections")
        lines.append("")
        lines.extend(render_h1_with_paragraphs(headings_h1, paragraphs))
    else:
        title = payload.get("title")
        if isinstance(title, str) and title.strip():
            lines.append(f"### {title.strip()}")
            lines.append("")
        lines.extend(render_paragraph_block(paragraphs))

    if headings_h2:
        lines.append("### H2 Headings")
        lines.append("")
        for text in headings_h2:
            lines.append(f"- {text}")
        lines.append("")

    if headings_h3:
        lines.append("### H3 Headings")
        lines.append("")
        for text in headings_h3:
            lines.append(f"- {text}")
        lines.append("")

    return lines


def render_h1_with_paragraphs(headings_h1: list[str], paragraphs: list[str]) -> list[str]:
    lines: list[str] = []
    if not paragraphs:
        for heading in headings_h1:
            lines.append(f"#### {heading}")
            lines.append("")
        return lines

    chunk_size = max(1, math.ceil(len(paragraphs) / len(headings_h1)))
    cursor = 0
    for idx, heading in enumerate(headings_h1):
        lines.append(f"#### {heading}")
        lines.append("")
        if idx == len(headings_h1) - 1:
            block = paragraphs[cursor:]
        else:
            block = paragraphs[cursor : cursor + chunk_size]
        cursor += chunk_size
        lines.extend(render_paragraph_block(block))
    return lines


def render_paragraph_block(paragraphs: list[str]) -> list[str]:
    lines: list[str] = []
    for p in paragraphs:
        lines.append(p)
        lines.append("")
    return lines


def kv_lines(items: list[tuple[str, Any]]) -> list[str]:
    lines: list[str] = []
    for key, value in items:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        lines.append(f"- {key}: {text}")
    return lines


def normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        text = " ".join(item.split())
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def join_list(value: Any) -> str | None:
    if not isinstance(value, list):
        return None
    cleaned = [str(v).strip() for v in value if str(v).strip()]
    if not cleaned:
        return None
    return ", ".join(cleaned)


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    rows = load_jsonl(input_path)
    grouped = group_by_page(rows)
    md = render_markdown(title=args.title, grouped_rows=grouped)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    print(f"Wrote Markdown: {output_path}")
    print(f"Pages: {len(grouped)}")
    print(f"Records: {len(rows)}")


if __name__ == "__main__":
    main()

# samacoScraper

Reusable Python scraping framework for both:
- non-JS sites (fast HTTP scraping), and
- JS-heavy sites (Playwright browser rendering).

It is built so you do not recreate a new scraper architecture every time.  
You only add a small adapter per site.

## What this project does

- Uses `httpx` first for speed.
- Falls back to Playwright automatically in `auto` mode.
- Extracts data through site adapters.
- Writes records to JSONL output files.
- Deduplicates records in-memory during a run.

## Project structure

- `src/scraper/cli.py`: command line entrypoint
- `src/scraper/core/`: models + runner/orchestration
- `src/scraper/engines/`: HTTP engine and browser engine
- `src/scraper/adapters/`: site-specific extraction logic
- `src/scraper/pipeline/`: dedupe + JSONL sink
- `output/`: generated scrape files

## Requirements

- Python `3.10+` (recommended: 3.11 or 3.12)
- Windows PowerShell (commands below use PowerShell style)
- Internet access for target websites
- Playwright browser binaries installed

## Setup from scratch

1. Clone repo and enter it:

```powershell
git clone <your-repo-url>
cd samacoScraper
```

2. Create and activate virtual environment:

```powershell
python -m venv vevn
.\vevn\Scripts\Activate.ps1
```

3. Install package and dependencies:

```powershell
python -m pip install -e .
```

Or install dependencies via requirements file:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
```

4. Install Playwright browser binaries:

```powershell
playwright install
```

## Prevent venv from being committed

This repo ignores common venv folders (`.venv`, `vevn`, `venv`, `env`, `ENV`) in `.gitignore`.

If a venv was already tracked earlier, untrack it once:

```powershell
git rm -r --cached vevn
git rm -r --cached .venv
git commit -m "Stop tracking virtual environment folders"
```

## How to start the scraper

1. List available adapters:

```powershell
python -m scraper.cli list-adapters
```

2. Run scrape for a URL:

```powershell
python -m scraper.cli run --adapter example_static --url https://example.com
```

3. Output is written to:

`output\scrape-<timestamp>.jsonl`

4. If you want visible browser mode (not headless):

```powershell
python -m scraper.cli run --adapter example_static --url https://example.com --browser-headed
```

## CLI reference

### List adapters

```powershell
python -m scraper.cli list-adapters
```

### Run scrape

```powershell
python -m scraper.cli run --adapter <adapter_name> --url <start_url> [--output-dir output] [--browser-headed]
```

- `--adapter`: adapter registered in `registry.py`
- `--url`: start page URL
- `--output-dir`: output directory (default `output`)
- `--browser-headed`: show browser window while scraping
- `--no-persistent-dedupe`: disable cross-run dedupe and crawl every page again

Persistent dedupe is enabled by default:
- seen page URLs are stored in `output/.state/seen_urls.txt`
- seen record hashes are stored in `output/.state/seen_hashes.txt`
- reruns skip already saved pages and records

## How it works internally

1. CLI loads the selected adapter.
2. Adapter builds a `ScrapeRequest` with preferred engine:
- `http`
- `browser`
- `auto` (recommended default)
3. Runner fetches page content:
- in `auto`, HTTP is attempted first
- if HTTP fails or extraction is unusable, it falls back to browser
4. Adapter extracts `ScrapeRecord` objects from HTML.
5. Pipeline deduplicates and writes JSONL.

## How to scrape your own website sections

Typical pattern:
1. Start from a section/listing URL (example: products page).
2. Extract card fields from listing.
3. Follow each detail link if needed.
4. Handle pagination (`Next` links or page parameters).
5. Save normalized records.

In this project, these rules live in an adapter file.

## Create a new adapter (step-by-step)

1. Copy `src/scraper/adapters/example_static.py` into a new file:

`src/scraper/adapters/<your_site>.py`

2. Update:
- `name`
- `engine_preference`
- extraction selectors and payload fields

3. Register adapter in `src/scraper/adapters/registry.py`.

4. Run:

```powershell
python -m scraper.cli run --adapter <your_site> --url <section_or_start_url>
```

## Real adapter template (pagination + detail traversal)

Use this as a starter in `src/scraper/adapters/<your_site>.py`:

```python
from __future__ import annotations

from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from scraper.adapters.base import BaseAdapter
from scraper.core.models import EngineType, FetchResult, ScrapeRecord


class YourSiteAdapter(BaseAdapter):
    name = "your_site"
    engine_preference = EngineType.AUTO

    def extract(self, fetch_result: FetchResult) -> list[ScrapeRecord]:
        """
        This method handles the current page.
        For multi-page or detail crawling, orchestrate from a custom run flow
        (or extend runner later with queue support).
        """
        tree = HTMLParser(fetch_result.html)
        records: list[ScrapeRecord] = []

        # 1) Extract listing cards from section/search page.
        for card in tree.css("article.product-card"):
            title_node = card.css_first("h2 a")
            price_node = card.css_first(".price")
            href = title_node.attributes.get("href") if title_node else None
            detail_url = urljoin(fetch_result.final_url or fetch_result.url, href) if href else None

            records.append(
                ScrapeRecord(
                    source_url=fetch_result.final_url or fetch_result.url,
                    payload={
                        "title": title_node.text(strip=True) if title_node else None,
                        "price": price_node.text(strip=True) if price_node else None,
                        "detail_url": detail_url,
                    },
                )
            )

        # 2) Capture next page URL for pagination (store it in payload or meta).
        next_node = tree.css_first("a.next, a[rel='next']")
        if next_node:
            next_href = next_node.attributes.get("href")
            if next_href:
                next_url = urljoin(fetch_result.final_url or fetch_result.url, next_href)
                records.append(
                    ScrapeRecord(
                        source_url=fetch_result.final_url or fetch_result.url,
                        payload={"_next_page_url": next_url},
                    )
                )

        return records
```

Detail-page extraction helper pattern:

```python
def extract_detail_fields(detail_html: str) -> dict:
    tree = HTMLParser(detail_html)
    return {
        "sku": tree.css_first(".sku").text(strip=True) if tree.css_first(".sku") else None,
        "description": tree.css_first(".description").text(strip=True) if tree.css_first(".description") else None,
    }
```

How to use this template in practice:
1. Start with a section URL (`/products`, `/jobs`, `/news`, etc.).
2. Extract listing card fields and detail links.
3. Follow detail links and merge detail fields into each record.
4. Follow `_next_page_url` until no next page remains.
5. Save normalized records only (avoid mixed schema lines in final dataset).

Recommended selectors checklist per site:
- listing card selector
- title/link selector
- key summary fields on listing
- detail-page fields
- next-page selector
- any lazy-load trigger (scroll/click for JS-heavy pages)

## Example output format

Each JSONL line contains:

```json
{"source_url":"https://example.com","payload":{"title":"Example Domain","summary":"...","engine_used":"browser","status_code":200}}
```

## Common issues and fixes

### `ModuleNotFoundError: No module named 'scraper'`

Run from repo root and install editable package:

```powershell
python -m pip install -e .
```

### SSL certificate errors in HTTP mode

Current runner already falls back to browser in `auto` mode when HTTP fails.

### Playwright not installed

```powershell
playwright install
```

### No records extracted

- Validate selectors in your adapter.
- Run with `--browser-headed` to inspect rendered content.
- Confirm target data exists in page HTML after render.

## Development notes

- Keep adapters focused on extraction logic only.
- Keep retry/rate-limit/fallback in core runner and engines.
- Reuse this framework for each new site; avoid one-off scripts.

## Legal and ethical scraping

- Respect each site’s Terms of Service.
- Respect robots.txt where applicable.
- Use reasonable request rates.
- Do not scrape private/protected data without permission.

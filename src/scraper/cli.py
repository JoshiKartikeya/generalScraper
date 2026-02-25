from __future__ import annotations

import argparse
from pathlib import Path

from scraper.adapters.registry import list_adapters


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Reusable scraper framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a scrape job")
    run_parser.add_argument("--adapter", required=True, choices=list_adapters())
    run_parser.add_argument("--url", required=True)
    run_parser.add_argument("--output-dir", default="output")
    run_parser.add_argument("--browser-headed", action="store_true")
    run_parser.add_argument("--no-persistent-dedupe", action="store_true")

    subparsers.add_parser("list-adapters", help="List available adapters")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-adapters":
        for name in list_adapters():
            print(name)
        return

    from scraper.core.runner import RunnerConfig, ScrapeRunner

    config = RunnerConfig(
        output_dir=Path(args.output_dir),
        browser_headless=not args.browser_headed,
        persistent_dedupe=not args.no_persistent_dedupe,
    )
    runner = ScrapeRunner(config=config)
    try:
        count, output_file, engine_used = runner.run_single(
            adapter_name=args.adapter,
            url=args.url,
        )
        print(f"Records written: {count}")
        print(f"Output: {output_file}")
        print(f"Engine used: {engine_used.value}")
    finally:
        runner.close()


if __name__ == "__main__":
    main()

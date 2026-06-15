"""Command-line interface for EPS workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH, run_tier1


def main(argv: list[str] | None = None) -> int:
    """Run the ``eps`` CLI."""

    parser = argparse.ArgumentParser(prog="eps")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tier1 = subparsers.add_parser("run-tier1", help="Run the mock Tier-1 screening workflow")
    tier1.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH, help="SQLite cache path")
    tier1.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Ranked CSV output path")

    args = parser.parse_args(argv)
    if args.command == "run-tier1":
        result = run_tier1(cache_path=args.cache, output_path=args.output)
        print(f"Tier 1 total triads: {result.total_triads}")
        print(f"Tier 1 surviving triads: {result.surviving_triads}")
        print(f"Tier 1 retention fraction: {result.retention_fraction:.3f}")
        print(f"Wrote ranked CSV: {result.output_path}")
        print(f"SQLite cache: {result.cache_path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

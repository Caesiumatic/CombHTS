"""Command-line interface for EPS workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from eps.validation.benchmark import (
    DEFAULT_CACHE_PATH as DEFAULT_VALIDATION_CACHE_PATH,
    DEFAULT_REPORT_PATH,
    run_benchmark_validation,
)
from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH, run_tier1
from eps.engines import MockEngine, XTBEngine


def _engine_from_name(name: str):
    if name == "mock":
        return MockEngine(), "mock-gfn2"
    if name == "xtb":
        return XTBEngine(), "gfn2-xtb"
    raise ValueError(f"Unknown engine {name!r}")


def main(argv: list[str] | None = None) -> int:
    """Run the ``eps`` CLI."""

    parser = argparse.ArgumentParser(prog="eps")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tier1 = subparsers.add_parser("run-tier1", help="Run the mock Tier-1 screening workflow")
    tier1.add_argument("--engine", choices=("mock", "xtb"), default="mock", help="Calculation engine")
    tier1.add_argument("--cache", type=Path, default=DEFAULT_CACHE_PATH, help="SQLite cache path")
    tier1.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Ranked CSV output path")

    validate = subparsers.add_parser("validate", help="Run benchmark validation")
    validate.add_argument("--engine", choices=("mock", "xtb"), default="mock", help="Calculation engine")
    validate.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_VALIDATION_CACHE_PATH,
        help="SQLite validation cache path",
    )
    validate.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Validation report CSV path",
    )

    args = parser.parse_args(argv)
    if args.command == "run-tier1":
        engine, method = _engine_from_name(args.engine)
        result = run_tier1(engine=engine, method=method, cache_path=args.cache, output_path=args.output)
        print(f"Tier 1 total triads: {result.total_triads}")
        print(f"Tier 1 surviving triads: {result.surviving_triads}")
        print(f"Tier 1 retention fraction: {result.retention_fraction:.3f}")
        print(f"Wrote ranked CSV: {result.output_path}")
        print(f"SQLite cache: {result.cache_path}")
        return 0

    if args.command == "validate":
        engine, method = _engine_from_name(args.engine)
        result = run_benchmark_validation(
            engine=engine,
            method=method,
            cache_path=args.cache,
            report_path=args.report,
        )
        status = "PASS" if result.tier1_xtb_pass else "FAIL"
        print(f"Benchmark rows: {len(result.rows)}")
        print(f"MAE before calibration: {result.mae_before_V:.3f} V")
        print(f"MAE after calibration: {result.mae_after_V:.3f} V")
        print(
            "Tier-1 xTB target "
            f"({result.tier1_xtb_target_V:.3f} V after calibration): {status}"
        )
        print(
            "Calibration: "
            f"y = {result.calibration.slope:.3f} * x + {result.calibration.intercept:.3f}; "
            f"R^2 = {result.calibration.r2:.3f}"
        )
        print(f"Wrote validation report: {result.report_path}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

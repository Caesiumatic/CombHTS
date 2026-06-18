"""Command-line interface for EPS workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from eps.validation.benchmark import (
    DEFAULT_CACHE_PATH as DEFAULT_VALIDATION_CACHE_PATH,
    DEFAULT_PROFILE_COMPARISON_PATH,
    DEFAULT_REPORT_PATH,
    run_all_calibration_profiles,
    run_calibration_profile,
)
from eps.validation.sanity import (
    DEFAULT_HARVEST_PATH,
    DEFAULT_SOLVENT,
    run_physical_sanity_checks,
)
from eps.validation.memo import DEFAULT_MEMO_DIR, write_validation_memo
from eps.analysis import run_analyze
from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH, run_tier1
from eps.engines import MockEngine, XTBEngine

DEFAULT_ANALYSIS_OUTDIR = DEFAULT_OUTPUT_PATH.parent / "analysis"


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
    tier1.add_argument("--all-output", type=Path, default=None, help="All-triads audit CSV output path")

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
    validate.add_argument(
        "--profile",
        default=None,
        help="Calibration profile name. Defaults to default_screening_profile.",
    )
    validate.add_argument(
        "--all-profiles",
        action="store_true",
        help="Run every configured calibration profile and print the comparison table.",
    )
    validate.add_argument(
        "--profile-comparison",
        type=Path,
        default=DEFAULT_PROFILE_COMPARISON_PATH,
        help="Calibration profile comparison CSV path.",
    )

    sanity = subparsers.add_parser(
        "sanity",
        help="Physical sanity checks on calibrated monomer Eox in the Tier-1 harvest",
    )
    sanity.add_argument(
        "--harvest",
        type=Path,
        default=DEFAULT_HARVEST_PATH,
        help="Tier-1 all-triads harvest CSV path.",
    )
    sanity.add_argument(
        "--solvent",
        default=DEFAULT_SOLVENT,
        help="Solvent within which to compare monomer Eox (default: acetonitrile).",
    )

    memo = subparsers.add_parser(
        "memo",
        help="Write the one-page experimental-validation memo (directive §7)",
    )
    memo.add_argument("--engine", choices=("mock", "xtb"), default="mock", help="Calculation engine")
    memo.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_VALIDATION_CACHE_PATH,
        help="SQLite validation cache path",
    )
    memo.add_argument(
        "--harvest",
        type=Path,
        default=DEFAULT_HARVEST_PATH,
        help="Tier-1 all-triads harvest CSV path for sanity checks.",
    )
    memo.add_argument(
        "--memo-dir",
        type=Path,
        default=DEFAULT_MEMO_DIR,
        help="Directory to write validation_memo_<YYYYMMDD>.md into.",
    )

    analyze = subparsers.add_parser(
        "analyze",
        help="Read-only directive-§8 post-processing of an existing Tier-1 harvest CSV",
    )
    analyze.add_argument(
        "--harvest",
        type=Path,
        default=DEFAULT_HARVEST_PATH,
        help="Tier-1 all-triads harvest CSV path (read-only; never recomputed).",
    )
    analyze.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_ANALYSIS_OUTDIR,
        help="Directory for §8 outputs (summary.csv, PNGs, shortlist.csv).",
    )

    args = parser.parse_args(argv)
    if args.command == "run-tier1":
        engine, method = _engine_from_name(args.engine)
        result = run_tier1(
            engine=engine,
            method=method,
            cache_path=args.cache,
            output_path=args.output,
            all_output_path=args.all_output,
        )
        print(f"Tier 1 total triads: {result.total_triads}")
        print(f"Tier 1 surviving triads: {result.surviving_triads}")
        print(f"Tier 1 retention fraction: {result.retention_fraction:.3f}")
        print(f"Wrote ranked CSV: {result.output_path}")
        print(f"Wrote all-triads audit CSV: {result.all_output_path}")
        print(f"SQLite cache: {result.cache_path}")
        if result.surviving_triads == 0:
            print(f"WARNING: Tier-1 produced zero survivors. See all-triads audit CSV: {result.all_output_path}")
        return 0

    if args.command == "validate":
        engine, method = _engine_from_name(args.engine)
        if args.all_profiles:
            comparison = run_all_calibration_profiles(
                engine=engine,
                method=method,
                cache_path=args.cache,
                report_path=args.report,
                comparison_path=args.profile_comparison,
            )
            print(comparison.to_string(index=False))
            print(f"Wrote calibration profile comparison: {args.profile_comparison}")
            return 0

        result = run_calibration_profile(
            args.profile,
            engine=engine,
            method=method,
            cache_path=args.cache,
            report_path=args.report,
        )
        status = "PASS" if result.tier1_xtb_pass else "FAIL"
        print(f"Calibration profile: {result.profile_name}")
        print(f"Raw benchmark rows: {result.raw_benchmark_rows}")
        print(f"Calibration-eligible rows: {result.calibration_eligible_rows}")
        print(f"Collapsed calibration groups: {result.n_calibration_points}")
        print(f"Counts by label_type: {_format_counts(result.label_type_counts)}")
        print(f"Counts by medium_class: {_format_counts(result.medium_class_counts)}")
        if result.n_calibration_points < 30:
            print(
                "WARNING: active calibration profile has "
                f"{result.n_calibration_points} collapsed groups "
                f"({result.raw_benchmark_rows} raw benchmark rows total); "
                "the >=30 target is not met."
            )
        print(f"MAE before calibration (in-sample): {result.mae_before_V:.3f} V")
        print(f"MAE after calibration (in-sample): {result.mae_after_V:.3f} V")
        print(f"MAE after calibration (LOO-CV, headline): {result.loo_mae_after_V:.3f} V")
        print(
            "Within-(monomer,solvent) experimental spread (noise floor): "
            f"{result.within_group_spread_V:.3f} V"
        )
        print(f"Residual std after calibration: {result.residual_std_after_V:.3f} V")
        print(f"Spearman rank correlation (rho): {result.spearman_rho:.3f} (n={result.n_calibration_points})")
        print(
            "Tier-1 gate "
            f"({result.tier1_xtb_target_V:.3f} V, PROVISIONAL) on LOO-CV: {status}"
        )
        print(f"MAE after by medium: {_mae_after_by_medium(result.rows)}")
        print(f"MAE after by chemical family: {_format_family_mae(result.family_mae)}")
        print("Worst-predicted calibration monomers (calibrated vs experimental):")
        print(_format_worst_predicted(result.worst_predicted))
        print(
            "Calibration: "
            f"y = {result.calibration.slope:.3f} * x + {result.calibration.intercept:.3f}; "
            f"R^2 = {result.calibration.r2:.3f}"
        )
        print(f"Wrote validation report: {result.report_path}")
        return 0

    if args.command == "sanity":
        if not Path(args.harvest).exists():
            print(f"ERROR: harvest CSV not found: {args.harvest}")
            print(
                "Run the Tier-1 harvest first (real numbers come from the cluster xTB run):"
            )
            print("  eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv")
            return 1
        result = run_physical_sanity_checks(args.harvest, solvent_name=args.solvent)
        print(f"Physical sanity checks (solvent: {result.solvent_name})")
        print(f"Harvest: {result.harvest_path}")
        for check in result.checks:
            print(f"  [{check.status}] {check.lower_monomer} < {check.reference_monomer} "
                  f"({check.description}): {check.detail}")
        print(
            f"Summary: {result.n_pass} PASS, {result.n_fail} FAIL, {result.n_skip} SKIP"
        )
        return 0 if result.n_fail == 0 else 1

    if args.command == "memo":
        engine, method = _engine_from_name(args.engine)
        memo_path = write_validation_memo(
            engine=engine,
            method=method,
            cache_path=args.cache,
            harvest_path=args.harvest,
            memo_dir=args.memo_dir,
        )
        print(f"Wrote validation memo: {memo_path}")
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical numbers (T9). Regenerate on the cluster with --engine xtb.")
        return 0

    if args.command == "analyze":
        if not Path(args.harvest).exists():
            print(f"ERROR: harvest CSV not found: {args.harvest}")
            print("Produce it first (real numbers come from the cluster xTB run):")
            print("  eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv")
            return 1
        result = run_analyze(args.harvest, args.outdir)
        print(f"Harvest: {args.harvest}")
        print(f"Total triads: {result.total_triads}; surviving: {result.surviving_triads}; "
              f"retention: {result.retention_fraction:.3f}")
        print(result.summary.to_string(index=False))
        print(f"Wrote summary: {result.summary_path}")
        if result.shortlist_path is not None:
            print(f"Wrote DIAGNOSTIC-ONLY shortlist: {result.shortlist_path}")
        for figure in result.figure_paths:
            print(f"Wrote figure: {figure}")
        for note in result.notes:
            print(f"NOTE: {note}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


def _mae_after_by_medium(rows) -> str:
    if "medium" not in rows.columns:
        return "unavailable"
    parts = []
    for medium, group in rows.groupby("medium", sort=True):
        mae = group["residual_after_V"].abs().mean()
        parts.append(f"{medium}={mae:.3f} V")
    return "; ".join(parts)


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "unavailable"
    return "; ".join(f"{key}={value}" for key, value in counts.items())


def _format_family_mae(family_mae: dict[str, dict[str, float]]) -> str:
    if not family_mae:
        return "unavailable"
    parts = [
        f"{family}={stats['mae_V']:.3f} V (n={stats['n']})"
        for family, stats in sorted(family_mae.items())
    ]
    return "; ".join(parts)


def _format_worst_predicted(worst) -> str:
    if worst is None or worst.empty:
        return "  (none)"
    lines = []
    for _, row in worst.iterrows():
        lines.append(
            f"  {row['monomer_name']} [{row['chemical_family']}]: "
            f"pred={row['calibrated_Eox_V_vs_AgAgCl']:.3f} V, "
            f"exp={row['exp_Eox_V_vs_AgAgCl']:.3f} V, "
            f"signed error={row['residual_after_V']:+.3f} V"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

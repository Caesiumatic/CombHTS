"""Command-line interface for EPS workflows."""

from __future__ import annotations

import argparse
from pathlib import Path

from eps.analysis import run_analyze
from eps.doctor import run_doctor
from eps.engines import GaussianEngine, MockEngine, XTBEngine
from eps.engines.gaussian import GAUSSIAN_METHOD_LABEL, load_tier2_config
from eps.provenance import write_provenance
from eps.validation.benchmark import (
    DEFAULT_CACHE_PATH as DEFAULT_VALIDATION_CACHE_PATH,
)
from eps.validation.benchmark import (
    DEFAULT_PROFILE_COMPARISON_PATH,
    DEFAULT_REPORT_PATH,
    run_all_calibration_profiles,
    run_calibration_profile,
)
from eps.validation.memo import DEFAULT_MEMO_DIR, write_validation_memo
from eps.validation.sanity import (
    DEFAULT_HARVEST_PATH,
    DEFAULT_SOLVENT,
    run_physical_sanity_checks,
)
from eps.validation.solvent_benchmark import compute_solvent_esw_mae
from eps.workflow.dft_calibration import (
    DEFAULT_CACHE_PATH as DEFAULT_DFTCAL_CACHE_PATH,
)
from eps.workflow.dft_calibration import (
    DEFAULT_OUTDIR as DEFAULT_DFTCAL_OUTDIR,
)
from eps.workflow.dft_calibration import (
    MOCK_DFT_METHOD,
    MOCK_XTB_METHOD,
    run_dft_calibration,
)
from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH, run_tier1
from eps.workflow.tier2 import (
    DEFAULT_REFINED_WINDOW_MARGIN_V,
    run_tier2_refined_screen,
    write_tier2_dry_run_inputs,
)
from eps.workflow.tier3 import (
    AIMD_RADICAL_STABILITY,
    EXPLICIT_SOLVATION,
    SLAB_ADSORPTION,
    run_tier3_optional_hook,
    write_tier3_dft_inputs,
)

DEFAULT_ANALYSIS_OUTDIR = DEFAULT_OUTPUT_PATH.parent / "analysis"


def _engine_from_name(name: str):
    if name == "mock":
        return MockEngine(), "mock-gfn2"
    if name == "xtb":
        return XTBEngine(), "gfn2-xtb"
    if name == "gaussian":
        # Tier-2 DFT scaffold (build-only); not wired into any production workflow run.
        return GaussianEngine(), GAUSSIAN_METHOD_LABEL
    raise ValueError(f"Unknown engine {name!r}")


def _dft_calibration_engines(engine_name: str, config_path):
    """Build the (xtb_engine, xtb_method, dft_engine, dft_method, method_label) tuple.

    The xTB descriptor reuses the existing ``monomer_eox_vs_AgAgCl`` path; the DFT Eox comes
    from a separate engine selected by the flag. ``mock`` keeps everything on MockEngine (no
    binaries); ``gaussian`` uses real GFN2-xTB for the descriptor and real Gaussian 16 for DFT.
    """

    if engine_name == "mock":
        return (
            MockEngine(),
            MOCK_XTB_METHOD,
            MockEngine(),
            MOCK_DFT_METHOD,
            "MockEngine (mock-b3lyp), gas phase, opt only",
        )
    if engine_name == "gaussian":
        config = load_tier2_config(config_path)
        return (
            XTBEngine(),
            "gfn2-xtb",
            GaussianEngine(config=config),
            # Config-encoded cache method label (THINK T13): the functional, basis, SMD solvent,
            # and Freq toggle are baked into the cache key, so editing configs/tier2.yaml
            # (gas -> SMD / opt -> freq) forces a recompute instead of reusing a stale value.
            # (Was the STATIC GAUSSIAN_METHOD_LABEL, which made the DFT cache config-blind.)
            config.cache_method_label(),
            config.method_label(),
        )
    raise ValueError(f"Unknown calibrate-dft engine {engine_name!r}")


def _stamp_provenance(output_path, *, engine: str, method: str, extra=None) -> None:
    """Best-effort provenance sidecar: warn on failure, never crash the command."""

    try:
        sidecar = write_provenance(output_path, engine=engine, method=method, extra=extra)
        print(f"Wrote provenance: {sidecar}")
    except Exception as exc:  # noqa: BLE001 - provenance must never break the primary command.
        print(f"WARNING: could not write provenance sidecar for {output_path}: {exc}")


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

    calibrate_dft = subparsers.add_parser(
        "calibrate-dft",
        help="Calibrate xTB->DFT and validate DFT->experiment (mock-first; never changes the pinned default)",
    )
    calibrate_dft.add_argument(
        "--engine",
        choices=("mock", "gaussian"),
        default="mock",
        help="DFT engine for adiabatic_ip: mock (default, no binaries) or gaussian (real g16).",
    )
    calibrate_dft.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Tier-2 config (configs/tier2.yaml) for the gaussian engine; defaults to the shipped file.",
    )
    calibrate_dft.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_DFTCAL_CACHE_PATH,
        help="SQLite cache path for DFT results (per-species, reused on a hit).",
    )
    calibrate_dft.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_DFTCAL_OUTDIR,
        help="Directory for dft_calibration_points.csv, report.md, xtb_to_dft_calibration.json.",
    )
    calibrate_dft.add_argument(
        "--only",
        default=None,
        help="Run on a SINGLE monomer by name (cheap live g16 smoke test before the full batch).",
    )
    calibrate_dft.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run on at most N monomers (after dedup by canonical SMILES).",
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

    tier2 = subparsers.add_parser(
        "tier2",
        help="EXPERIMENTAL: write Tier-2 Gaussian .gjf inputs for survivors (dry-run only; never runs g16)",
    )
    tier2.add_argument("--engine", choices=("gaussian",), default="gaussian", help="Tier-2 engine")
    tier2.add_argument(
        "--dry-run",
        action="store_true",
        help="Required: only writes .gjf inputs for inspection; never submits or runs Gaussian.",
    )
    tier2.add_argument(
        "--survivors",
        type=Path,
        default=DEFAULT_OUTPUT_PATH.parent / "tier1_ranked_xtb.csv",
        help="Tier-1 survivors CSV (must have monomer_canonical_smiles).",
    )
    tier2.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTPUT_PATH.parent / "tier2_inputs",
        help="Directory for the generated .gjf inputs.",
    )

    tier2_screen = subparsers.add_parser(
        "tier2-screen",
        help="Directive §4.2 refined screen: tighter window filter (-0.5 V) on Tier-1 survivors + composite re-rank",
    )
    tier2_screen.add_argument(
        "--survivors",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Tier-1 ranked survivors CSV (the cheap source of the per-triad columns).",
    )
    tier2_screen.add_argument(
        "--dft-results",
        type=Path,
        default=None,
        help="Optional Tier-2 DFT results CSV (per-monomer Eox V vs Ag/AgCl). Absent -> tier2_dft_pending=true.",
    )
    tier2_screen.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH.parent / "tier2_refined.csv",
        help="Output CSV for the refined, re-ranked survivors.",
    )
    tier2_screen.add_argument(
        "--margin",
        type=float,
        default=DEFAULT_REFINED_WINDOW_MARGIN_V,
        help="Refined window margin in V (monomer AIP must be this far below the solvent anodic limit).",
    )

    tier3 = subparsers.add_parser(
        "tier3",
        help="OPTIONAL/not-validated §4.3: range-separated DFT inputs (real) + documented hooks (not run)",
    )
    tier3.add_argument(
        "--method",
        choices=("range-separated-dft", "explicit-solvation", "aimd", "slab"),
        default="range-separated-dft",
        help="range-separated-dft is real (writes .gjf, never runs g16); the others are documented hooks.",
    )
    tier3.add_argument(
        "--survivors",
        type=Path,
        default=DEFAULT_OUTPUT_PATH.parent / "tier2_refined.csv",
        help="Refined-survivors CSV (must have monomer_canonical_smiles) for range-separated-dft inputs.",
    )
    tier3.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTPUT_PATH.parent / "tier3_inputs",
        help="Directory for the generated range-separated-DFT .gjf inputs.",
    )

    subparsers.add_parser(
        "doctor",
        help="No-compute environment readiness check (Python, binaries, imports, configs, data)",
    )

    args = parser.parse_args(argv)
    if args.command == "doctor":
        report = run_doctor()
        for check in report.checks:
            print(f"  [{check.status}] {check.name}: {check.detail}")
        failures = sum(1 for c in report.checks if c.status == "FAIL")
        print(f"Summary: {len(report.checks)} checks, {failures} FAIL, {report.n_warn} WARN")
        return 0 if not report.has_failure else 1

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
        _stamp_provenance(
            result.output_path,
            engine=args.engine,
            method=method,
            extra={"command": "run-tier1", "all_output": str(result.all_output_path),
                   "total_triads": result.total_triads, "surviving_triads": result.surviving_triads},
        )
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
            _stamp_provenance(
                args.profile_comparison, engine=args.engine, method=method,
                extra={"command": "validate", "mode": "all-profiles"},
            )
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
        solvent_esw = compute_solvent_esw_mae(engine=engine, cache_path=args.cache, method=method)
        if solvent_esw.computable:
            print(
                f"Solvent ESW MAE (§7, n={solvent_esw.n_matched}): anodic="
                f"{solvent_esw.anodic_mae_V:.3f} V, cathodic={solvent_esw.cathodic_mae_V:.3f} V "
                "(raw computed vs measured; screening-grade)"
            )
        else:
            print("Solvent ESW MAE (§7): not computable yet (data/solvent_benchmark.csv has no rows)")
        print("Worst-predicted calibration monomers (calibrated vs experimental):")
        print(_format_worst_predicted(result.worst_predicted))
        print(
            "Calibration: "
            f"y = {result.calibration.slope:.3f} * x + {result.calibration.intercept:.3f}; "
            f"R^2 = {result.calibration.r2:.3f}"
        )
        print(f"Wrote validation report: {result.report_path}")
        _stamp_provenance(
            result.report_path, engine=args.engine, method=method,
            extra={"command": "validate", "profile": result.profile_name},
        )
        return 0

    if args.command == "calibrate-dft":
        xtb_engine, xtb_method, dft_engine, dft_method, method_label = _dft_calibration_engines(
            args.engine, args.config
        )
        result = run_dft_calibration(
            xtb_engine=xtb_engine,
            dft_engine=dft_engine,
            xtb_method=xtb_method,
            dft_method=dft_method,
            cache_path=args.cache,
            outdir=args.outdir,
            only=args.only,
            limit=args.limit,
            method_label=method_label,
        )
        print(f"DFT-calibration engine: {args.engine} ({method_label})")
        print(f"Calibration points (ok): {result.n_points}; skipped: {result.n_skipped}")
        if result.xtb_to_dft is not None:
            cal = result.xtb_to_dft
            print(
                "xTB->DFT fit: dft_Eox_eV = "
                f"{cal.slope:.6f} * xtb_descriptor + {cal.intercept:.6f}; "
                f"R^2 = {cal.r2:.4f}; MAE = {cal.mae:.4f} eV"
            )
        else:
            print("xTB->DFT fit: INSUFFICIENT POINTS (< 2)")
        print(
            f"DFT->experiment fit uses PEAK rows only: {result.n_dft_to_exp_peak_points} peak "
            f"monomer(s) fed it; {result.n_nonpeak_excluded} onset monomer(s) excluded."
        )
        if result.dft_to_exp is not None:
            cal = result.dft_to_exp
            print(
                "DFT->experiment fit (units V vs eV; correlation, not equality): "
                f"exp_V = {cal.slope:.6f} * dft_Eox_eV + {cal.intercept:.6f}; "
                f"R^2 = {cal.r2:.4f}; MAE = {cal.mae:.4f} V"
            )
        else:
            print("DFT->experiment fit: INSUFFICIENT PEAK POINTS (< 2)")
        if result.reference_flag_message:
            print(result.reference_flag_message)
        if result.pinned_xtb_to_exp is not None:
            pinned = result.pinned_xtb_to_exp
            print(
                f"Side-by-side: pinned xTB->exp slope={pinned['slope']:.6f}, "
                f"intercept={pinned['intercept']:.6f} (V; UNCHANGED) vs new xTB->DFT above (eV)."
            )
        if result.skipped:
            print(f"Skipped monomers: {', '.join(name for name, _ in result.skipped)}")
        print(f"Wrote points CSV: {result.points_path}")
        print(f"Wrote report: {result.report_path}")
        print(f"Wrote calibration JSON: {result.json_path}")
        print("NOTE: NEW artifact only — configs/tier1.yaml and default_screening_profile are UNCHANGED.")
        _stamp_provenance(
            result.points_path, engine=args.engine, method=dft_method,
            extra={"command": "calibrate-dft", "n_points": result.n_points,
                   "n_skipped": result.n_skipped},
        )
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical numbers (T9). Real numbers come from --engine gaussian on the cluster.")
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
        _stamp_provenance(memo_path, engine=args.engine, method=method, extra={"command": "memo"})
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
        _stamp_provenance(
            result.summary_path, engine="none", method="read-only-analysis",
            extra={"command": "analyze", "harvest": str(args.harvest)},
        )
        return 0

    if args.command == "tier2":
        if not args.dry_run:
            print("ERROR: only --dry-run is supported (this command never runs g16). Pass --dry-run.")
            return 2
        if not Path(args.survivors).exists():
            print(f"ERROR: survivors CSV not found: {args.survivors}")
            print("  eps run-tier1 --engine xtb   # produces the Tier-1 ranked survivors CSV")
            return 1
        result = write_tier2_dry_run_inputs(args.survivors, args.outdir)
        print("EXPERIMENTAL Tier-2 DRY RUN — wrote Gaussian inputs only; g16 was NOT executed.")
        print(f"Survivors read: {result.n_survivors}; unique monomers: {result.n_unique_monomers}")
        print(f"Wrote {len(result.input_paths)} .gjf inputs (neutral + cation per monomer) to {result.outdir}")
        print(f"Rough estimate: ~{result.estimated_cpu_hours:.0f} CPU-hours (very approximate; for planning only)")
        return 0

    if args.command == "tier2-screen":
        if not Path(args.survivors).exists():
            print(f"ERROR: Tier-1 survivors CSV not found: {args.survivors}")
            print("  eps run-tier1   # produces the Tier-1 ranked survivors CSV")
            return 1
        result = run_tier2_refined_screen(
            args.survivors,
            args.output,
            dft_results_path=args.dft_results,
            refined_window_margin_V=args.margin,
        )
        print(f"Tier-2 refined screen (window margin {result.refined_window_margin_V:.2f} V)")
        print(f"Tier-1 survivors in: {result.n_tier1_survivors}; Tier-2 refined survivors: {result.n_tier2_survivors}")
        if result.tier2_dft_pending:
            print("NOTE: tier2_dft_pending=true — used calibrated Tier-1 Eox (no DFT results CSV supplied).")
        print(f"Wrote refined CSV: {result.output_path}")
        _stamp_provenance(
            result.output_path,
            engine="tier2-refined",
            method="composite-rerank",
            extra={"command": "tier2-screen", "refined_window_margin_V": result.refined_window_margin_V,
                   "n_tier2_survivors": result.n_tier2_survivors, "tier2_dft_pending": result.tier2_dft_pending},
        )
        return 0

    if args.command == "tier3":
        print("Tier-3 is OPTIONAL and NOT validated (directive §4.3).")
        if args.method == "range-separated-dft":
            if not Path(args.survivors).exists():
                print(f"ERROR: survivors CSV not found: {args.survivors}")
                print("  eps tier2-screen   # produces the refined survivors CSV")
                return 1
            result = write_tier3_dft_inputs(args.survivors, args.outdir)
            print(f"Method (a) range-separated DFT — REAL config on the Gaussian engine: {result.method_label}")
            print(f"Wrote {len(result.input_paths)} .gjf inputs ({result.n_unique_monomers} unique monomers) to {result.outdir}")
            print("g16 was NOT executed (build-only; a live batch is a PI decision).")
            return 0
        method = {
            "explicit-solvation": EXPLICIT_SOLVATION,
            "aimd": AIMD_RADICAL_STABILITY,
            "slab": SLAB_ADSORPTION,
        }[args.method]
        hook = run_tier3_optional_hook(method)
        print(f"Method {args.method}: [{hook.status}] {hook.note}")
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

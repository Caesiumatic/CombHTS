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
from eps.validation.directive import (
    DEFAULT_DIRECTIVE_CACHE,
    DEFAULT_DIRECTIVE_OUTDIR,
    run_directive_validation,
)
from eps.validation.feasibility import compute_feasibility_metric, format_feasibility_report
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
from eps.workflow.orca_pilots import (
    DEFAULT_CONFIG_PATH as DEFAULT_ORCA_PILOT_CONFIG_PATH,
)
from eps.workflow.orca_pilots import (
    DEFAULT_OPTICAL_OUTDIR,
    DEFAULT_SOLVATION_GRID_CONFIG_PATH,
    DEFAULT_SOLVATION_GRID_OUTDIR,
    DEFAULT_SOLVATION_OUTDIR,
    build_mock_orca_pilot_engines,
    build_real_orca_pilot_engines,
    build_real_orca_solvation_grid_engine,
    run_orca_optical_pilot,
    run_orca_solvation_grid_pilot,
    run_orca_solvation_pilot,
)
from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH, run_tier1
from eps.workflow.tier1_rescore import DEFAULT_OUTDIR as DEFAULT_RESCORE_OUTDIR
from eps.workflow.tier1_rescore import rescore_tier1_harvest
from eps.workflow.tier2 import (
    DEFAULT_REFINED_WINDOW_MARGIN_V,
    DEFAULT_TIER2_HARVEST_OUTPUT,
    DEFAULT_TIER2_HARVEST_REPORT,
    DEFAULT_TIER2_PLAN_OUTDIR,
    DEFAULT_TIER2_TASK_RESULTS_DIR,
    DEFAULT_TIER2_WORK_ROOT,
    harvest_tier2_results,
    plan_tier2_pilot,
    run_tier2_bandgap,
    run_tier2_dimerization,
    run_tier2_refined_screen,
    run_tier2_task,
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
    tier1.add_argument(
        "--allow-large-scale",
        action="store_true",
        help="Authorize a run above the scale_guard ceiling (the freeze-then-scale full-scale switch; "
        "directive §0/§2 — only after per-species methods are frozen and signed off)",
    )

    rescore = subparsers.add_parser(
        "rescore-tier1",
        help="Reapply Tier-1 window policy, filters, and scoring to an existing audit CSV (no engine)",
    )
    rescore.add_argument("--input", type=Path, required=True, help="Existing tier1_all.csv")
    rescore.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESCORE_OUTDIR / "tier1_ranked.csv",
        help="Re-scored ranked CSV output path.",
    )
    rescore.add_argument(
        "--all-output",
        type=Path,
        default=DEFAULT_RESCORE_OUTDIR / "tier1_all.csv",
        help="Re-scored all-triads audit CSV output path.",
    )

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
    validate.add_argument(
        "--harvest",
        type=Path,
        default=None,
        help=(
            "Optional Tier-1 all-triads harvest CSV. When supplied, reports the §7 qualitative "
            "yes/no feasibility DIAGNOSTIC (balanced accuracy + confusion matrix on the matched "
            "in-scope subset; never a single accuracy figure)."
        ),
    )

    validate_directive = subparsers.add_parser(
        "validate-directive",
        help="Write the full directive section-7 validation package (JSON/Markdown/CSVs)",
    )
    validate_directive.add_argument(
        "--engine",
        choices=("mock", "xtb"),
        default="mock",
        help="Calculation engine for per-species validation descriptors.",
    )
    validate_directive.add_argument(
        "--harvest",
        type=Path,
        required=True,
        help="Existing salt-fixed Tier-1 all-triads harvest CSV (read-only).",
    )
    validate_directive.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_DIRECTIVE_CACHE,
        help="Dedicated SQLite validation cache path.",
    )
    validate_directive.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_DIRECTIVE_OUTDIR,
        help="Directory for validation_summary.json, validation_report.md, and CSV artifacts.",
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

    orca_solvation = subparsers.add_parser(
        "orca-pilot-solvation",
        help="Run the mock-first ORCA/openCOSMO-RS solvation-route pilot",
    )
    orca_solvation.add_argument(
        "--engine",
        choices=("mock", "orca"),
        default="mock",
        help="Calculation engine: deterministic mock or real ORCA 6.1.",
    )
    orca_solvation.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_ORCA_PILOT_CONFIG_PATH,
        help="Small ORCA pilot YAML configuration.",
    )
    orca_solvation.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="SQLite cache path; defaults to <outdir>/cache.sqlite.",
    )
    orca_solvation.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_SOLVATION_OUTDIR,
        help="Directory for solvation_points.csv and the default cache.",
    )

    orca_solvation_grid = subparsers.add_parser(
        "orca-pilot-solvation-grid",
        help="Run the stratified monomer x solvent openCOSMO-RS dGsolv expansion pilot",
    )
    orca_solvation_grid.add_argument(
        "--engine",
        choices=("mock", "orca"),
        default="mock",
        help="Calculation engine: deterministic mock or real ORCA 6.1.",
    )
    orca_solvation_grid.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_SOLVATION_GRID_CONFIG_PATH,
        help="Monomer x solvent dGsolv grid YAML configuration.",
    )
    orca_solvation_grid.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="SQLite cache path; defaults to <outdir>/cache.sqlite. Seed it from the pilot cache to reuse points.",
    )
    orca_solvation_grid.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_SOLVATION_GRID_OUTDIR,
        help="Directory for the grid points/plan CSVs and the default cache.",
    )
    orca_solvation_grid.add_argument(
        "--plan-only",
        action="store_true",
        help="Pre-flight only: write the computed-vs-cached-vs-deferred plan and exit (no engine run).",
    )

    orca_optical = subparsers.add_parser(
        "orca-pilot-optical",
        help="Run paired mock-first ORCA sTDA and TDA/TD-DFT optical pilots",
    )
    orca_optical.add_argument(
        "--engine",
        choices=("mock", "orca"),
        default="mock",
        help="Calculation engine: deterministic mock or real ORCA 6.1.",
    )
    orca_optical.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_ORCA_PILOT_CONFIG_PATH,
        help="Small ORCA pilot YAML configuration.",
    )
    orca_optical.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="SQLite cache path; defaults to <outdir>/cache.sqlite.",
    )
    orca_optical.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OPTICAL_OUTDIR,
        help="Directory for paired points, calibration JSON, report, and default cache.",
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

    tier2_plan = subparsers.add_parser(
        "tier2-plan",
        help="Plan the mock-first, array-safe Tier-2 monomer-Eox pilot (no Engine calls)",
    )
    tier2_plan.add_argument(
        "--selection",
        type=Path,
        required=True,
        help="Selection CSV with monomer SMILES and solvent_name columns.",
    )
    tier2_plan.add_argument(
        "--config",
        type=Path,
        default=Path("configs/tier2.yaml"),
        help="Tier-2 method config; defaults to configs/tier2.yaml.",
    )
    tier2_plan.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_TIER2_PLAN_OUTDIR,
        help="Directory for task_manifest.csv, plan_summary.json, plan_report.md, provenance.json.",
    )
    tier2_plan.add_argument(
        "--allow-large-scale",
        action="store_true",
        help="Authorize a Tier-2 plan above the scale_guard ceiling (directive §0 #2 full-survivor "
        "DFT batch; only after freeze + sign-off).",
    )
    tier2_plan.add_argument(
        "--scope",
        choices=("monomer_ip", "full"),
        default="monomer_ip",
        help="monomer_ip (default): monomer oxidation only. full: directive §4.2 complete state set "
        "(monomer IP+EA, solvent anodic+cathodic, electrolyte anion-ox + cation-red).",
    )

    tier2_run_task = subparsers.add_parser(
        "tier2-run-task",
        help="Run exactly one Tier-2 manifest task through mock or Gaussian, array-safe.",
    )
    tier2_run_task.add_argument("--manifest", type=Path, required=True, help="Tier-2 task_manifest.csv")
    tier2_run_task.add_argument("--task-id", required=True, help="Task ID from the manifest")
    tier2_run_task.add_argument(
        "--engine",
        choices=("mock", "gaussian", "orca"),
        default="mock",
        help="Calculation engine for this single task.",
    )
    tier2_run_task.add_argument(
        "--result-dir",
        type=Path,
        default=DEFAULT_TIER2_TASK_RESULTS_DIR,
        help="Root directory for per-task result.json/status.txt and default task-local caches.",
    )
    tier2_run_task.add_argument(
        "--work-root",
        type=Path,
        default=DEFAULT_TIER2_WORK_ROOT,
        help="Persistent per-task Gaussian input/log work root.",
    )
    tier2_run_task.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="Optional per-task SQLite cache. Omit for <result-dir>/task_caches/<task-id>.sqlite.",
    )
    tier2_run_task.add_argument(
        "--config",
        type=Path,
        default=Path("configs/tier2.yaml"),
        help="Tier-2 config used to verify the manifest hash and build Gaussian inputs.",
    )

    tier2_harvest = subparsers.add_parser(
        "tier2-harvest",
        help="No-engine harvest of validated Tier-2 task result.json files.",
    )
    tier2_harvest.add_argument("--manifest", type=Path, required=True, help="Tier-2 task_manifest.csv")
    tier2_harvest.add_argument(
        "--result-dir",
        type=Path,
        default=DEFAULT_TIER2_TASK_RESULTS_DIR,
        help="Root directory containing <task-id>/result.json files.",
    )
    tier2_harvest.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_TIER2_HARVEST_OUTPUT,
        help="Output per-monomer-solvent Eox CSV.",
    )
    tier2_harvest.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_TIER2_HARVEST_REPORT,
        help="Markdown harvest report path.",
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
    tier2_screen.add_argument(
        "--dimerization-dft", type=Path, default=None,
        help="Optional Tier-2 DFT dimerization CSV (overrides the §5 f4 term).",
    )
    tier2_screen.add_argument(
        "--optical-dft", type=Path, default=None,
        help="Optional Tier-2 TD-DFT band-gap CSV (overrides the §5 f5 term).",
    )

    for _name, _help in (
        ("tier2-dimerization", "Directive §4.2 DFT dimerization ΔG per (monomer,solvent) via ORCA (shardable)"),
        ("tier2-bandgap", "Directive §4.2 TD-DFT band-gap convergence per monomer via ORCA (shardable)"),
    ):
        _p = subparsers.add_parser(_name, help=_help)
        _p.add_argument("--survivors", type=Path, required=True, help="Tier-1 survivors CSV.")
        _p.add_argument("--output", type=Path, required=True, help="Output CSV (shard-specific in an array).")
        _p.add_argument("--config", type=Path, default=Path("configs/tier2_orca.yaml"), help="Tier-2 ORCA config.")
        _p.add_argument("--cache", type=Path, default=None, help="SQLite cache (shard-specific in an array).")
        _p.add_argument("--engine", choices=("mock", "orca"), default="orca", help="Calculation engine.")
        _p.add_argument("--n-shards", type=int, default=1, help="Total array shards (parallelism).")
        _p.add_argument("--shard-index", type=int, default=0, help="0-based shard index for this task.")

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
            allow_large_scale=args.allow_large_scale,
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

    if args.command == "rescore-tier1":
        result = rescore_tier1_harvest(
            args.input,
            output_path=args.output,
            all_output_path=args.all_output,
        )
        print("Tier-1 CSV-only re-score: no Engine or SQLite cache opened")
        print(f"Tier 1 total triads: {result.total_triads}")
        print(f"Tier 1 surviving triads: {result.surviving_triads}")
        print(f"Tier 1 retention fraction: {result.retention_fraction:.3f}")
        print(f"Wrote ranked CSV: {result.output_path}")
        print(f"Wrote all-triads audit CSV: {result.all_output_path}")
        _stamp_provenance(
            result.output_path,
            engine="none",
            method="csv-only/measured-first-rescore",
            extra={
                "command": args.command,
                "source": str(result.input_path),
                "total_triads": result.total_triads,
                "surviving_triads": result.surviving_triads,
            },
        )
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
        feasibility = compute_feasibility_metric(harvest_path=args.harvest)
        print(format_feasibility_report(feasibility))
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

    if args.command == "validate-directive":
        engine, method = _engine_from_name(args.engine)
        result = run_directive_validation(
            engine=engine,
            engine_name=args.engine,
            method=method,
            cache_path=args.cache,
            harvest_path=args.harvest,
            outdir=args.outdir,
        )
        print(f"Directive section-7 validation package: {result.outdir}")
        print("metric | target | observed | n | status")
        for row in result.metric_table:
            print(
                f"{row['metric']} | {row['directive target']} | {row['observed value']} | "
                f"{row['n']} | {row['status']}"
            )
        print(f"Wrote validation summary: {result.summary_path}")
        print(f"Wrote validation report: {result.report_path}")
        print(f"Wrote Eox profile summary: {result.eox_profile_summary_path}")
        print(f"Wrote Eox points: {result.eox_points_path}")
        print(f"Wrote ESW descriptor points: {result.esw_descriptor_points_path}")
        print(f"Wrote ESW gate diagnostics: {result.esw_gate_diagnostics_path}")
        print(f"Wrote feasibility matches: {result.feasibility_matches_path}")
        print(f"Wrote provenance: {result.provenance_path}")
        if args.engine == "mock":
            print("NOTE: mock engine -> NON-PHYSICAL workflow smoke only.")
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

    if args.command == "orca-pilot-solvation":
        engines = (
            build_mock_orca_pilot_engines()
            if args.engine == "mock"
            else build_real_orca_pilot_engines(args.config)
        )
        engine, method = engines[0], engines[1]
        result = run_orca_solvation_pilot(
            engine=engine,
            method=method,
            config_path=args.config,
            cache_path=args.cache,
            outdir=args.outdir,
            engine_label=args.engine,
        )
        print(f"ORCA/openCOSMO-RS pilot engine: {args.engine} ({method})")
        print(f"Solvation points: {result.n_ok} ok; {result.n_failed} failed")
        print(f"Wrote points CSV: {result.points_path}")
        _stamp_provenance(
            result.points_path,
            engine=args.engine,
            method=method,
            extra={"command": args.command, "n_ok": result.n_ok, "n_failed": result.n_failed},
        )
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical numbers; use --engine orca on Lop for real values.")
        return 0 if result.n_failed == 0 else 2

    if args.command == "orca-pilot-solvation-grid":
        if args.engine == "mock":
            mock_engines = build_mock_orca_pilot_engines()
            engine, method = mock_engines[0], mock_engines[1]
        else:
            engine, method = build_real_orca_solvation_grid_engine(args.config)
        if args.plan_only:
            from eps.storage import SQLiteCache
            from eps.workflow.orca_pilots import load_solvation_grid_config, plan_solvation_grid

            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)
            cache_file = Path(args.cache) if args.cache is not None else outdir / "cache.sqlite"
            grid = load_solvation_grid_config(args.config)
            plan = plan_solvation_grid(grid, SQLiteCache(cache_file), method)
            plan_path = outdir / "solvation_grid_plan.csv"
            plan.to_csv(plan_path, index=False)
            counts = plan["status"].value_counts().to_dict()
            print(f"ORCA dGsolv grid PRE-FLIGHT plan ({method}); cache: {cache_file}")
            print(f"Points: cached={counts.get('cached', 0)}; compute={counts.get('compute', 0)}; "
                  f"deferred={counts.get('deferred', 0)} (no built-in COSMORS profile)")
            print(f"Wrote plan CSV: {plan_path}")
            return 0
        result = run_orca_solvation_grid_pilot(
            engine=engine,
            method=method,
            config_path=args.config,
            cache_path=args.cache,
            outdir=args.outdir,
            engine_label=args.engine,
        )
        print(f"ORCA/openCOSMO-RS dGsolv grid engine: {args.engine} ({method})")
        print(f"Plan: cached={result.n_cached}; to-compute={result.n_computed}; "
              f"deferred={result.n_deferred} (no built-in COSMORS profile)")
        print(f"Computed points: {result.n_ok} ok; {result.n_failed} failed")
        print(f"Wrote points CSV: {result.points_path}")
        print(f"Wrote plan CSV: {result.plan_path}")
        print(f"SQLite cache: {result.cache_path}")
        print("NOTE: dGsolv is a SOLVATION FREE ENERGY, not solubility. The 20% Tier-1 axis is UNCHANGED. "
              "See docs/lit_curation/solubility_descriptor_status.md")
        _stamp_provenance(
            result.points_path,
            engine=args.engine,
            method=method,
            extra={
                "command": args.command,
                "n_ok": result.n_ok,
                "n_failed": result.n_failed,
                "n_cached": result.n_cached,
                "n_deferred": result.n_deferred,
            },
        )
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical numbers; use --engine orca on Lop for real values.")
        return 0 if result.n_failed == 0 else 2

    if args.command == "orca-pilot-optical":
        engines = (
            build_mock_orca_pilot_engines()
            if args.engine == "mock"
            else build_real_orca_pilot_engines(args.config)
        )
        result = run_orca_optical_pilot(
            stda_engine=engines[2],
            tddft_engine=engines[4],
            stda_method=engines[3],
            tddft_method=engines[5],
            config_path=args.config,
            cache_path=args.cache,
            outdir=args.outdir,
            engine_label=args.engine,
        )
        print(f"ORCA optical pilot engine: {args.engine}")
        print(f"Paired sTDA/TDA points: {result.n_paired}; failed pairs: {result.n_failed}")
        if result.calibration is not None:
            print(
                "Pilot fit: TDDFT_gap_eV = "
                f"{result.calibration.slope:.6f} * sTDA_gap_eV + "
                f"{result.calibration.intercept:.6f}; R^2={result.calibration.r2:.4f}"
            )
        print(f"Wrote points CSV: {result.points_path}")
        print(f"Wrote report: {result.report_path}")
        print(f"Wrote calibration JSON: {result.calibration_path}")
        _stamp_provenance(
            result.points_path,
            engine=args.engine,
            method=f"{engines[3]} + {engines[5]}",
            extra={
                "command": args.command,
                "n_paired": result.n_paired,
                "n_failed": result.n_failed,
            },
        )
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical numbers; use --engine orca on Lop for real values.")
        return 0 if result.n_failed == 0 else 2

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

    if args.command == "tier2-plan":
        result = plan_tier2_pilot(
            args.selection, args.config, args.outdir,
            allow_large_scale=args.allow_large_scale, scope=args.scope,
        )
        print("Tier-2 pilot plan: no Engine calls; no triad-level quantum loop.")
        print(f"Selection rows: {result.n_selection_rows}; unique tasks: {result.n_tasks}")
        print(f"Unique monomers: {result.n_unique_monomers}; monomer-solvent pairs: {result.n_unique_monomer_solvent_pairs}")
        print(f"Method: {result.method_label}")
        print(f"Config hash: {result.config_hash}")
        print(f"Wrote manifest: {result.manifest_path}")
        print(f"Wrote summary: {result.summary_path}")
        print(f"Wrote report: {result.report_path}")
        print(f"Wrote provenance: {result.provenance_path}")
        return 0

    if args.command == "tier2-run-task":
        result = run_tier2_task(
            args.manifest,
            args.task_id,
            engine_name=args.engine,
            result_dir=args.result_dir,
            work_root=args.work_root,
            cache_path=args.cache,
            config_path=args.config,
        )
        print(f"Tier-2 task {result.task_id}: {result.status}")
        print(f"Wrote result: {result.result_path}")
        print(f"Wrote status: {result.status_path}")
        print(f"Task-local cache: {result.cache_path}")
        print(f"Persistent work dir: {result.work_dir}")
        if result.error:
            print(f"ERROR: {result.error}")
        if args.engine == "mock":
            print("NOTE: mock engine -> non-physical smoke result; do not use as science.")
        return 0 if result.status == "success" else 2

    if args.command == "tier2-harvest":
        result = harvest_tier2_results(args.manifest, args.result_dir, args.output, args.report)
        print("Tier-2 harvest: no Engine calls and no SQLite writes.")
        print(f"Manifest tasks: {result.n_manifest_tasks}; validated successes: {result.n_success}")
        print(
            f"Missing={result.n_missing}; failed={result.n_failed}; duplicate={result.n_duplicate}; "
            f"hash_mismatch={result.n_hash_mismatch}; identity_mismatch={result.n_identity_mismatch}"
        )
        print(f"Wrote Eox CSV: {result.output_path}")
        print(f"Wrote report: {result.report_path}")
        if result.partial:
            print("WARNING: partial harvest; failed/missing values were not filled from Tier-1.")
        return 2 if result.partial else 0

    if args.command in ("tier2-dimerization", "tier2-bandgap"):
        engine = MockEngine() if args.engine == "mock" else None  # None -> real OrcaEngine
        common = dict(
            cache_path=args.cache, engine=engine,
            n_shards=args.n_shards, shard_index=args.shard_index,
        )
        if args.command == "tier2-dimerization":
            out = run_tier2_dimerization(args.survivors, args.config, args.output, **common)
        else:
            out = run_tier2_bandgap(args.survivors, args.output, **common)
        print(f"{args.command}: shard {args.shard_index}/{args.n_shards}, {len(out)} items -> {args.output}")
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
            dimerization_dft_path=args.dimerization_dft,
            optical_dft_path=args.optical_dft,
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

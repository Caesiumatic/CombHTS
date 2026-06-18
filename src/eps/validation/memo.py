"""Generate the one-page experimental-validation memo (directive §7).

The memo collects the computable §7 accuracy checks (monomer Eox MAE after calibration,
plus rank correlation, residual spread, worst-predicted monomers, per-family MAE) and the
physical sanity checks, and states plainly the two §7 metrics that are NOT computable yet
(solvent ESW MAE and yes/no feasibility accuracy). It never fabricates numbers for those.

Real numbers come from a real-xTB run on the cluster; with the mock engine the calibration
predictions are non-physical (see THINK T9) and the memo says so in a banner.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.validation.benchmark import (
    BenchmarkValidationResult,
    DEFAULT_BENCHMARK_PATH,
    DEFAULT_CACHE_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_VALIDATION_CONFIG,
    _load_validation_config,
    load_calibration_profiles,
    run_calibration_profile,
)
from eps.validation.sanity import (
    DEFAULT_HARVEST_PATH,
    SanityResult,
    run_physical_sanity_checks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MEMO_DIR = PROJECT_ROOT / "docs"

_INSUFFICIENT_POINTS_MARKER = "requires at least two calibration points"


def write_validation_memo(
    *,
    engine: Engine | None = None,
    method: str = "mock-gfn2",
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    validation_config_path: str | Path = DEFAULT_VALIDATION_CONFIG,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    harvest_path: str | Path = DEFAULT_HARVEST_PATH,
    memo_dir: str | Path = DEFAULT_MEMO_DIR,
    memo_date: date | None = None,
) -> Path:
    """Build the validation memo from a profile sweep + sanity checks; return its path."""

    engine = engine or MockEngine()
    memo_date = memo_date or date.today()
    config = load_calibration_profiles()
    default_profile = str(config["default_screening_profile"])
    target_V = float(_load_validation_config(validation_config_path)["tier1_xtb_mae_target_V"])

    results: dict[str, BenchmarkValidationResult] = {}
    skipped: dict[str, str] = {}
    for profile_name in config["profiles"]:
        try:
            results[profile_name] = run_calibration_profile(
                profile_name,
                engine=engine,
                method=method,
                cache_path=cache_path,
                benchmark_path=benchmark_path,
                validation_config_path=validation_config_path,
                report_path=_profile_report_path(report_path, profile_name),
            )
        except ValueError as exc:
            if _INSUFFICIENT_POINTS_MARKER not in str(exc):
                raise
            skipped[profile_name] = "skipped (fewer than 2 calibration points)"

    detail_profile = default_profile if default_profile in results else next(iter(results), None)
    detail = results.get(detail_profile) if detail_profile else None

    sanity = _maybe_run_sanity(harvest_path)

    is_mock = "mock" in method.lower() or isinstance(engine, MockEngine)
    memo_text = _render_memo(
        memo_date=memo_date,
        method=method,
        is_mock=is_mock,
        target_V=target_V,
        results=results,
        skipped=skipped,
        detail_profile=detail_profile,
        detail=detail,
        sanity=sanity,
        harvest_path=Path(harvest_path),
    )

    if is_mock:
        memo_path = Path(memo_dir) / "validation_memo_MOCK_PREVIEW.md"
    else:
        memo_path = Path(memo_dir) / f"validation_memo_{memo_date:%Y%m%d}.md"
    memo_path.parent.mkdir(parents=True, exist_ok=True)
    memo_path.write_text(memo_text, encoding="utf-8")
    return memo_path


def _maybe_run_sanity(harvest_path: str | Path) -> SanityResult | None:
    if not Path(harvest_path).exists():
        return None
    return run_physical_sanity_checks(harvest_path)


def _profile_report_path(report_path: str | Path, profile_name: str) -> Path:
    path = Path(report_path)
    return path.with_name(f"{path.stem}_{profile_name}{path.suffix}")


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def _render_memo(
    *,
    memo_date: date,
    method: str,
    is_mock: bool,
    target_V: float,
    results: dict[str, BenchmarkValidationResult],
    skipped: dict[str, str],
    detail_profile: str | None,
    detail: BenchmarkValidationResult | None,
    sanity: SanityResult | None,
    harvest_path: Path,
) -> str:
    lines: list[str] = []
    lines.append(f"# Experimental validation memo — {memo_date:%Y-%m-%d}")
    lines.append("")
    if is_mock:
        lines.append(
            "> **ENGINE = MOCK.** The calibration predictions below are NON-PHYSICAL "
            "placeholders (see THINK T9); the table structure is real but the numbers are not. "
            "Regenerate with real xTB on the cluster (command at the bottom) before citing any value."
        )
    else:
        lines.append(f"> Generated from a real run (method: `{method}`).")
    lines.append("")

    lines.append("## 1. Monomer Eox accuracy by calibration profile")
    lines.append("")
    lines.append(
        "| Profile | n | MAE-after (V) | LOO-CV MAE (V) | Residual std (V) | Spearman ρ | R² | "
        f"PASS/FAIL vs {target_V:.2f} V |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |")
    for profile_name in _profile_order(results, skipped):
        if profile_name in results:
            result = results[profile_name]
            passed = np.isfinite(result.loo_mae_after_V) and result.loo_mae_after_V <= target_V
            verdict = "PASS" if passed else "FAIL"
            lines.append(
                f"| {profile_name} | {result.n_calibration_points} | "
                f"{_fmt(result.mae_after_V)} | {_fmt(result.loo_mae_after_V)} | "
                f"{_fmt(result.residual_std_after_V)} | {_fmt(result.spearman_rho)} | "
                f"{_fmt(result.calibration.r2)} | {verdict} |"
            )
        else:
            lines.append(f"| {profile_name} | 0 | — | — | — | — | — | {skipped[profile_name]} |")
    lines.append("")
    lines.append(
        f"The {target_V:.2f} V gate is a PROVISIONAL engineering target, not an established "
        "accuracy (see caveat). LOO-CV MAE is the headline; report it with the residual spread."
    )
    lines.append("")

    lines.append("## 2. Where the model fails")
    lines.append("")
    if detail is not None:
        lines.append(f"Worst-predicted calibration monomers (profile `{detail_profile}`):")
        lines.append("")
        if detail.worst_predicted.empty:
            lines.append("- (none)")
        else:
            lines.append("| Monomer | Family | Predicted Eox (V) | Experimental Eox (V) | Signed error (V) |")
            lines.append("| --- | --- | ---: | ---: | ---: |")
            for _, row in detail.worst_predicted.iterrows():
                lines.append(
                    f"| {row['monomer_name']} | {row['chemical_family']} | "
                    f"{_fmt(row['calibrated_Eox_V_vs_AgAgCl'])} | {_fmt(row['exp_Eox_V_vs_AgAgCl'])} | "
                    f"{row['residual_after_V']:+.3f} |"
                )
        lines.append("")
        lines.append("MAE-after by coarse chemical family (best-effort SMILES substructure bucketing):")
        lines.append("")
        if detail.family_mae:
            lines.append("| Family | MAE-after (V) | n |")
            lines.append("| --- | ---: | ---: |")
            for family, stats in sorted(detail.family_mae.items()):
                lines.append(f"| {family} | {_fmt(stats['mae_V'])} | {int(stats['n'])} |")
        else:
            lines.append("- (no calibration points)")
    else:
        lines.append("No fittable calibration profile produced detail rows.")
    lines.append("")

    lines.append("## 3. Physical sanity checks (directional monomer Eox, within one solvent)")
    lines.append("")
    if sanity is None:
        lines.append(
            f"Harvest CSV not found at `{harvest_path}`, so sanity checks were not run. "
            "Populate it from the cluster Tier-1 xTB harvest (command at the bottom), then run `eps sanity`."
        )
    else:
        lines.append(f"Solvent: `{sanity.solvent_name}`; harvest: `{sanity.harvest_path}`.")
        lines.append("")
        lines.append("| Check | Result | Detail |")
        lines.append("| --- | :---: | --- |")
        for check in sanity.checks:
            lines.append(
                f"| Eox({check.lower_monomer}) < Eox({check.reference_monomer}) "
                f"— {check.description} | {check.status} | {check.detail} |"
            )
        lines.append("")
        lines.append(
            f"Summary: {sanity.n_pass} PASS, {sanity.n_fail} FAIL, {sanity.n_skip} SKIP."
        )
    lines.append("")

    lines.append("## 4. What we CANNOT validate yet")
    lines.append("")
    lines.append(
        "- **Solvent ESW MAE (< 0.30 V)** — not computable yet: there is no solvent "
        "electrochemical-window experimental benchmark in the repo. The computed solvent "
        "anodic/cathodic limits cannot be scored against measured values until such a "
        "benchmark is curated. No number is reported here."
    )
    lines.append(
        "- **Qualitative feasibility yes/no accuracy (> 85%)** — not computable yet: "
        "`data/benchmark.csv` holds continuous Eox values, not binary \"does it polymerize "
        "yes/no\" labels. Computing this first requires DEFINING a label source (a "
        "curation/PI decision), so no accuracy is reported here."
    )
    lines.append("")

    lines.append("## 5. Caveats (THINK T3, T4)")
    lines.append("")
    lines.append(
        "The 0.30 V target is a provisional engineering gate, not an established accuracy. "
        "xTB computes an adiabatic one-electron potential while the benchmark mixes "
        "irreversible Epa/onset values shifted by follow-up chemistry, so a residual spread "
        "on the order of ~0.2 V is an irreducible label/medium noise floor — always report "
        "LOO-CV MAE together with the within-group spread, and do not claim < 0.3 V as "
        "demonstrated. The current fit is an INTERIM xTB→experimental stand-in: the brief's "
        "design calibrates xTB→DFT and then validates the pipeline against experiment, but "
        "the Tier-2 DFT tier is not built yet, so the >=30-group reference-purity burden "
        "currently sits on the calibration set. Treat these numbers as screening-grade."
    )
    lines.append("")

    lines.append("## 6. Regenerate with real numbers (cluster)")
    lines.append("")
    lines.append("```bash")
    lines.append("# On the SCS Lop cluster via qsub (real GFN2-xTB; do NOT run on a head node):")
    lines.append("eps validate --engine xtb --all-profiles")
    lines.append("eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv")
    lines.append("eps sanity --harvest outputs/tier1_all_xtb.csv --solvent acetonitrile")
    lines.append("eps memo --engine xtb --harvest outputs/tier1_all_xtb.csv")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _profile_order(
    results: dict[str, BenchmarkValidationResult],
    skipped: dict[str, str],
) -> list[str]:
    return list(results.keys()) + [name for name in skipped if name not in results]

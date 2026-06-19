"""DFT calibration workflow (directive §7): calibrate xTB -> DFT, then validate DFT -> experiment.

The brief's two-stage design is: (1) calibrate the cheap xTB descriptor against a DFT
"ground truth" (self-generated, no reference-electrode heterogeneity), then (2) validate the
DFT level against experimental CV. This module builds BOTH fits as a NEW artifact. It does NOT
touch the pinned xTB->experiment calibration in ``configs/tier1.yaml`` or
``default_screening_profile`` — the screen's default is unchanged pending live numbers + PI.

Mock-first: with ``--engine mock`` (default) every quantity comes from ``MockEngine`` so the
full plumbing — dedup, per-species caching, both linear fits, the report/json artifacts, and
per-monomer failure-skip — is testable without xtb or g16. With ``--engine gaussian`` the DFT
Eox comes from a real Gaussian 16 ``adiabatic_ip`` (gas-phase ΔSCF in v1, per configs/tier2.yaml)
and the xTB descriptor from real GFN2-xTB.

The xTB DESCRIPTOR is the SAME quantity the existing xTB->experiment calibration uses for its
benchmark monomers: ``monomer_eox_vs_AgAgCl`` (the adiabatic IP projected to V vs Ag/AgCl through
the pinned redox function). Reusing it verbatim makes the new xTB->DFT slope/intercept directly
comparable to the pinned xTB->experiment slope/intercept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from eps.calibration import LinearCalibration, fit_linear_calibration
from eps.chemspace import Solvent, load_solvents
from eps.engines.base import CalcRequest, Engine, SpeciesSpec
from eps.engines.mock import MockEngine
from eps.properties import monomer_eox_vs_AgAgCl
from eps.provenance import git_info
from eps.storage import SQLiteCache, cached_run
from eps.validation.benchmark import (
    DEFAULT_BENCHMARK_PATH,
    _as_bool,
    _benchmark_monomer,
    _load_benchmark,
)
from eps.workflow.tier1 import PROJECT_ROOT, load_tier1_config

DEFAULT_OUTDIR = PROJECT_ROOT / "outputs" / "dft_calibration"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "outputs" / "dft_calibration_cache.sqlite"
DEFAULT_TIER1_CONFIG = PROJECT_ROOT / "configs" / "tier1.yaml"

POINTS_COLUMNS = (
    "monomer_name",
    "canonical_smiles",
    "label_type",
    "xtb_descriptor",
    "dft_Eox_eV",
    "exp_Eox_V_vs_AgAgCl",
    "dft_calc_status",
    "dft_calc_error",
)

# The DFT ΔSCF Eox is a thermodynamic PEAK observable, not the kinetically-defined onset, so the
# DFT->experiment validation (Fit 2) is restricted to peak rows (research review §3.1). Fit 1
# (xTB->DFT) never touches experiment and uses ALL eligible monomers regardless of label_type.
PEAK_LABEL_TYPE = "monomer_oxidation_peak"

# Mock DFT uses a DISTINCT method label from the mock xTB descriptor so the two are not the same
# cached value (different cache key + different MockEngine hash), keeping the fit non-degenerate.
MOCK_XTB_METHOD = "mock-gfn2"
MOCK_DFT_METHOD = "mock-b3lyp"

# High-confidence MeCN/Ag-AgCl core anchors (Eox-benchmark review §"Recommendations"). If the
# DFT->experiment error on THESE is large, suspect the reference-conversion constant, not the DFT.
CORE_MONOMER_NAMES = (
    "thiophene",
    "EDOT",
    "carbazole",
    "pyrrole",
    "dithieno[3,2-b:2',3'-d]pyrrole",
)
CORE_MAE_THRESHOLD_V = 0.15
REFERENCE_FLOOR_NOTE = (
    "Experimental reference carries a ~0.1 V (up to 0.2 V) systematic floor from "
    "liquid-junction / reference-conversion uncertainty (Fc/Fc+ = +0.45 V vs Ag/AgCl in MeCN, "
    "Pavlishchuk & Addison 2000). Do NOT report MAE below ~0.05 V precision or over-tune below ~0.1 V."
)


@dataclass
class DFTCalibrationResult:
    """Outputs of the DFT-calibration workflow (both fits + artifact paths)."""

    points: pd.DataFrame
    xtb_to_dft: LinearCalibration | None
    dft_to_exp: LinearCalibration | None
    n_points: int
    n_skipped: int
    skipped: list[tuple[str, str]]
    method_label: str
    xtb_method: str
    dft_method: str
    points_path: Path
    report_path: Path
    json_path: Path
    pinned_xtb_to_exp: dict[str, float] | None = field(default=None)
    n_dft_to_exp_peak_points: int = 0
    n_nonpeak_excluded: int = 0
    reference_flag_fired: bool = False
    reference_flag_message: str = ""
    composed_xtb_to_agagcl: dict[str, float | int] | None = field(default=None)


def run_dft_calibration(
    *,
    xtb_engine: Engine | None = None,
    dft_engine: Engine | None = None,
    xtb_method: str = MOCK_XTB_METHOD,
    dft_method: str = MOCK_DFT_METHOD,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    outdir: str | Path = DEFAULT_OUTDIR,
    only: str | None = None,
    limit: int | None = None,
    method_label: str = "MockEngine (mock-b3lyp), gas phase, opt only",
    tier1_config_path: str | Path = DEFAULT_TIER1_CONFIG,
    core_monomers: tuple[str, ...] = CORE_MONOMER_NAMES,
) -> DFTCalibrationResult:
    """Run the xTB->DFT calibration and the DFT->experiment validation, mock-first.

    Both engines default to ``MockEngine`` so the workflow is fully exercisable without xtb/g16.
    Each monomer's DFT result is cached per species in SQLite; on a cache hit the engine is not
    invoked, so neither the neutral nor the cation DFT job is recomputed.
    """

    xtb_engine = xtb_engine or MockEngine()
    dft_engine = dft_engine or MockEngine()
    cache = SQLiteCache(cache_path)
    solvents = {solvent.name: solvent for solvent in load_solvents()}

    monomers = _calibration_monomers(benchmark_path, only=only, limit=limit)

    rows: list[dict[str, object]] = []
    skipped: list[tuple[str, str]] = []
    for record in monomers:
        monomer = record["monomer"]
        solvent = _lookup_solvent(solvents, str(record["solvent_name"]))
        exp_eox = record["exp_Eox_V_vs_AgAgCl"]

        xtb_value, xtb_error = _safe(
            lambda: monomer_eox_vs_AgAgCl(monomer, solvent, xtb_engine, cache, method=xtb_method)
        )
        dft_value, dft_error = _safe(
            lambda: _dft_eox_eV(monomer, dft_engine, cache, method=dft_method)
        )

        errors = []
        if xtb_error:
            errors.append(f"xtb_descriptor: {xtb_error}")
        if dft_error:
            errors.append(f"dft: {dft_error}")
        ok = np.isfinite(xtb_value) and np.isfinite(dft_value)
        status = "ok" if ok else "failed"
        error = "; ".join(errors)
        if not ok:
            skipped.append((monomer.name, error or "non-finite value"))

        rows.append(
            {
                "monomer_name": monomer.name,
                "canonical_smiles": monomer.canonical_smiles,
                "label_type": str(record.get("label_type", "")),
                "xtb_descriptor": xtb_value,
                "dft_Eox_eV": dft_value,
                "exp_Eox_V_vs_AgAgCl": exp_eox,
                "dft_calc_status": status,
                "dft_calc_error": error,
            }
        )

    points = pd.DataFrame(rows, columns=list(POINTS_COLUMNS))
    ok_points = points[points["dft_calc_status"] == "ok"].copy()

    # Fit 1 (xTB->DFT) uses ALL eligible monomers — it never touches experiment, so peak/onset
    # is irrelevant to it.
    xtb_to_dft = _maybe_fit(ok_points["xtb_descriptor"], ok_points["dft_Eox_eV"])
    # Fit 2 (DFT->experiment) uses ONLY peak rows: the DFT ΔSCF Eox is a thermodynamic peak
    # observable, and mixing onset rows adds kinetic noise to the validation.
    peak_points = ok_points[ok_points["label_type"] == PEAK_LABEL_TYPE].copy()
    n_nonpeak_excluded = int(len(ok_points) - len(peak_points))
    dft_to_exp = _maybe_fit(peak_points["dft_Eox_eV"], peak_points["exp_Eox_V_vs_AgAgCl"])
    pinned = _load_pinned_xtb_to_exp(tier1_config_path)

    # Screen-ready composed calibration (directive §7): collapse Fit 1 (xTB->DFT) and Fit 2
    # (DFT->exp peak) into one xTB-descriptor -> V vs Ag/AgCl map, a drop-in for tier1.yaml.
    composed = compose_xtb_to_agagcl(
        xtb_to_dft,
        dft_to_exp,
        n_points_xtb_to_dft=int(len(ok_points)),
        n_points_dft_to_exp_peak=int(len(peak_points)),
    )

    # Reference-floor decision flag: a large DFT->exp error on the trusted core anchors points at
    # the reference-conversion constant, not the DFT method.
    reference_residuals = dft_to_exp_residuals(peak_points, dft_to_exp)
    reference_flag_fired, reference_flag_message = core_monomer_reference_flag(
        reference_residuals, core_monomers
    )

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    points_path = out / "dft_calibration_points.csv"
    points.to_csv(points_path, index=False)

    json_path = out / "xtb_to_dft_calibration.json"
    _write_json(
        json_path,
        xtb_to_dft=xtb_to_dft,
        composed=composed,
        n_points=int(len(ok_points)),
        n_skipped=len(skipped),
        xtb_method=xtb_method,
        dft_method=dft_method,
        method_label=method_label,
        benchmark_path=benchmark_path,
    )

    report_path = out / "report.md"
    _write_report(
        report_path,
        points=points,
        ok_points=ok_points,
        peak_points=peak_points,
        n_nonpeak_excluded=n_nonpeak_excluded,
        xtb_to_dft=xtb_to_dft,
        dft_to_exp=dft_to_exp,
        composed=composed,
        pinned=pinned,
        skipped=skipped,
        method_label=method_label,
        xtb_method=xtb_method,
        dft_method=dft_method,
        benchmark_path=benchmark_path,
        reference_flag_message=reference_flag_message,
    )

    return DFTCalibrationResult(
        points=points,
        xtb_to_dft=xtb_to_dft,
        dft_to_exp=dft_to_exp,
        n_points=int(len(ok_points)),
        n_skipped=len(skipped),
        skipped=skipped,
        method_label=method_label,
        xtb_method=xtb_method,
        dft_method=dft_method,
        points_path=points_path,
        report_path=report_path,
        json_path=json_path,
        pinned_xtb_to_exp=pinned,
        n_dft_to_exp_peak_points=int(len(peak_points)),
        n_nonpeak_excluded=n_nonpeak_excluded,
        reference_flag_fired=reference_flag_fired,
        reference_flag_message=reference_flag_message,
        composed_xtb_to_agagcl=composed,
    )


def _calibration_monomers(
    benchmark_path: str | Path,
    *,
    only: str | None,
    limit: int | None,
) -> list[dict[str, object]]:
    """Load calibration-eligible benchmark rows, dedup by canonical SMILES, apply only/limit.

    The first eligible row per canonical SMILES is kept; its solvent feeds the (identical)
    xTB descriptor path, and its converted experimental Eox feeds the DFT->experiment fit.
    """

    frame = _load_benchmark(benchmark_path)
    eligible = frame[frame["calibration_eligible"].map(_as_bool)]
    seen: set[str] = set()
    monomers: list[dict[str, object]] = []
    for row in eligible.to_dict(orient="records"):
        monomer = _benchmark_monomer(row)
        if monomer.canonical_smiles in seen:
            continue
        seen.add(monomer.canonical_smiles)
        if only is not None and monomer.name != only:
            continue
        monomers.append(
            {
                "monomer": monomer,
                "solvent_name": row["solvent_name"],
                "exp_Eox_V_vs_AgAgCl": float(row["exp_Eox_V_vs_AgAgCl"]),
                "label_type": str(row.get("label_type", "")),
            }
        )
    if limit is not None:
        monomers = monomers[:limit]
    return monomers


def _dft_eox_eV(monomer, dft_engine: Engine, cache: SQLiteCache, *, method: str) -> float:
    """DFT adiabatic ionization energy (Eox) in eV, cached per species.

    Routed through the SQLite cache keyed by (canonical_smiles, charge=0, method, solvent,
    adiabatic_ip). For the ``--engine gaussian`` path ``method`` is the config-encoded
    ``Tier2Config.cache_method_label()`` (functional/basis/SMD-solvent/Freq), so changing
    ``configs/tier2.yaml`` changes the key and forces a recompute (THINK T13) — the SMD solvent
    and Freq toggle are carried in ``method`` rather than the ``solvent_name`` slot. On a cache
    hit the engine is NOT called, so the underlying neutral AND cation DFT jobs are both reused
    (never recomputed).
    """

    req = CalcRequest(
        species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=None,
        quantity="adiabatic_ip",
    )
    return cached_run(cache, dft_engine, req, solvent_name=None).value


def _maybe_fit(x: pd.Series, y: pd.Series) -> LinearCalibration | None:
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if len(x_values) < 2:
        return None
    return fit_linear_calibration(x_values, y_values)


def compose_xtb_to_agagcl(
    xtb_to_dft: LinearCalibration | None,
    dft_to_exp: LinearCalibration | None,
    *,
    n_points_xtb_to_dft: int,
    n_points_dft_to_exp_peak: int,
) -> dict[str, float | int] | None:
    """Compose Fit 1 (xTB->DFT) and Fit 2 (DFT->exp) into ONE xTB-descriptor -> V vs Ag/AgCl map.

    The directive's §7 two-stage calibration is two linear maps:
        dft_Eox_eV       = fit1.slope * xtb_descriptor_V + fit1.intercept   (Fit 1, xTB->DFT)
        exp_Eox_V_AgAgCl = fit2.slope * dft_Eox_eV       + fit2.intercept   (Fit 2, DFT->exp peak)
    Substituting Fit 1 into Fit 2 collapses them to a single linear map with the SAME input (the
    xTB descriptor, V vs Ag/AgCl) and output (experimental V vs Ag/AgCl) as the pinned
    ``configs/tier1.yaml`` ``monomer_eox`` calibration, so it is a drop-in replacement:
        composed_slope     = fit2.slope * fit1.slope
        composed_intercept = fit2.slope * fit1.intercept + fit2.intercept
    ``mae_V`` is ``fit2.mae`` — the experimental MAE on the peak set (the only experiment-anchored
    error in the two-stage chain). Returns ``None`` if either fit is missing.
    """

    if xtb_to_dft is None or dft_to_exp is None:
        return None
    return {
        "slope": dft_to_exp.slope * xtb_to_dft.slope,
        "intercept": dft_to_exp.slope * xtb_to_dft.intercept + dft_to_exp.intercept,
        "mae_V": dft_to_exp.mae,
        "n_points_xtb_to_dft": int(n_points_xtb_to_dft),
        "n_points_dft_to_exp_peak": int(n_points_dft_to_exp_peak),
    }


def dft_to_exp_residuals(
    peak_points: pd.DataFrame,
    calibration: LinearCalibration | None,
) -> dict[str, float]:
    """Per-monomer DFT->experiment calibrated residuals (V) over the peak rows used in Fit 2.

    residual = calibration.apply(dft_Eox_eV) - exp_Eox_V_vs_AgAgCl. Empty when there is no fit.
    """

    if calibration is None or peak_points.empty:
        return {}
    residuals: dict[str, float] = {}
    for _, row in peak_points.iterrows():
        predicted = float(calibration.apply(float(row["dft_Eox_eV"])))
        residuals[str(row["monomer_name"])] = predicted - float(row["exp_Eox_V_vs_AgAgCl"])
    return residuals


def core_monomer_reference_flag(
    residuals_by_monomer: dict[str, float],
    core_names: tuple[str, ...] = CORE_MONOMER_NAMES,
) -> tuple[bool, str]:
    """Decision flag on the core-monomer DFT->experiment MAE.

    Over whichever core monomers are PRESENT, if the MAE exceeds ``CORE_MAE_THRESHOLD_V`` the flag
    FIRES (returns True) — a large error on the trusted anchors points at the reference-conversion
    constant, not the DFT method. Returns (fired, human-readable message). If no core monomers are
    present, returns (False, <says so>).
    """

    present = {name: residuals_by_monomer[name] for name in core_names if name in residuals_by_monomer}
    if not present:
        return False, (
            f"No core monomers ({', '.join(core_names)}) present in the peak Fit-2 set; "
            "core-monomer reference check not run."
        )
    mae = float(np.mean([abs(value) for value in present.values()]))
    if mae > CORE_MAE_THRESHOLD_V:
        return True, (
            f"FLAG: core-monomer DFT->exp MAE = {mae:.3f} V > {CORE_MAE_THRESHOLD_V:.2f} V — "
            "re-examine the reference-conversion constant BEFORE re-tuning the DFT method. "
            f"Core monomers present: {', '.join(present)}."
        )
    return False, (
        f"core-monomer DFT->exp MAE = {mae:.3f} V <= {CORE_MAE_THRESHOLD_V:.2f} V "
        f"(within the reference floor; OK). Core monomers present: {', '.join(present)}."
    )


def _load_pinned_xtb_to_exp(tier1_config_path: str | Path) -> dict[str, float] | None:
    """Read the pinned xTB->experiment calibration (slope/intercept) for the side-by-side."""

    try:
        config = load_tier1_config(tier1_config_path)
        monomer_eox = config.get("calibration", {}).get("monomer_eox", {})
        if "slope" not in monomer_eox or "intercept" not in monomer_eox:
            return None
        return {
            "slope": float(monomer_eox["slope"]),
            "intercept": float(monomer_eox["intercept"]),
            "source": str(monomer_eox.get("source", "configs/tier1.yaml")),
        }
    except Exception:  # noqa: BLE001 - the side-by-side is best-effort; never break the workflow.
        return None


def _safe(calculate) -> tuple[float, str]:
    try:
        return float(calculate()), ""
    except Exception as exc:  # noqa: BLE001 - one bad monomer must never abort the batch.
        message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
        return float("nan"), f"{exc.__class__.__name__}: {message}"[:240]


def _lookup_solvent(solvents: dict[str, Solvent], name: str) -> Solvent:
    try:
        return solvents[name]
    except KeyError as exc:
        known = ", ".join(sorted(solvents))
        raise ValueError(f"Unknown benchmark solvent {name!r}; known solvents: {known}") from exc


def _write_json(
    path: Path,
    *,
    xtb_to_dft: LinearCalibration | None,
    composed: dict[str, float | int] | None,
    n_points: int,
    n_skipped: int,
    xtb_method: str,
    dft_method: str,
    method_label: str,
    benchmark_path: str | Path,
) -> None:
    fit = (
        {
            "slope_dft_eV_per_xtb_V": xtb_to_dft.slope,
            "intercept_dft_eV": xtb_to_dft.intercept,
            "r2": xtb_to_dft.r2,
            "mae_eV": xtb_to_dft.mae,
        }
        if xtb_to_dft is not None
        else None
    )
    record = {
        "calibration": "xtb_to_dft",
        "description": "y_DFT_Eox_eV = slope * x_xtb_descriptor_V_vs_AgAgCl + intercept",
        "fit": fit,
        # Screen-ready DFT-anchored map (directive §7): same input/output as the pinned
        # tier1.yaml monomer_eox calibration, so it is a drop-in replacement (review + live
        # gaussian batch required before adopting). null when either stage fit is missing.
        "composed_xtb_to_AgAgCl_V": composed,
        "n_points": n_points,
        "n_skipped": n_skipped,
        "provenance": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "git": git_info(),
            "xtb_method": xtb_method,
            "dft_method": dft_method,
            "dft_method_label": method_label,
            "benchmark": str(benchmark_path),
            "note": (
                "NEW artifact; does NOT replace the pinned xTB->experiment calibration in "
                "configs/tier1.yaml. Default screening calibration is unchanged."
            ),
        },
    }
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")


def _write_report(
    path: Path,
    *,
    points: pd.DataFrame,
    ok_points: pd.DataFrame,
    peak_points: pd.DataFrame,
    n_nonpeak_excluded: int,
    xtb_to_dft: LinearCalibration | None,
    dft_to_exp: LinearCalibration | None,
    composed: dict[str, float | int] | None,
    pinned: dict[str, float] | None,
    skipped: list[tuple[str, str]],
    method_label: str,
    xtb_method: str,
    dft_method: str,
    benchmark_path: str | Path,
    reference_flag_message: str = "",
) -> None:
    lines: list[str] = []
    lines.append("# DFT calibration report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append(
        "Two-stage directive §7: calibrate the cheap xTB descriptor against DFT, then validate "
        "the DFT level against experimental CV. This is a NEW artifact and does NOT change "
        "`configs/tier1.yaml` or `default_screening_profile`."
    )
    lines.append("")
    lines.append("## Method / config")
    lines.append("")
    lines.append(f"- xTB descriptor: `monomer_eox_vs_AgAgCl` (adiabatic IP -> V vs Ag/AgCl), method `{xtb_method}`")
    lines.append(f"- DFT Eox: `engine.run(adiabatic_ip)`, {method_label} (method `{dft_method}`)")
    lines.append(f"- Calibration set: rows of `{Path(benchmark_path).name}` with `calibration_eligible == true`, dedup by canonical SMILES")
    lines.append(f"- Calibration points used (status ok): {len(ok_points)} of {len(points)} candidate monomers")
    lines.append("")
    lines.append("## Fit 1 — xTB -> DFT calibration")
    lines.append("")
    lines.append("`dft_Eox_eV = slope * xtb_descriptor_V + intercept` (both broadly an energy/potential; slope ~ dimensionless eV/V).")
    lines.append(f"Uses ALL {len(ok_points)} eligible monomers (peak + onset): Fit 1 never touches experiment, so label_type is irrelevant to it.")
    lines.append("")
    if xtb_to_dft is not None:
        lines.append(f"- slope = {xtb_to_dft.slope:.6f}")
        lines.append(f"- intercept = {xtb_to_dft.intercept:.6f} eV")
        lines.append(f"- R^2 = {xtb_to_dft.r2:.4f}")
        lines.append(f"- MAE = {xtb_to_dft.mae:.4f} eV")
    else:
        lines.append("- INSUFFICIENT POINTS (< 2): fit not computed.")
    lines.append("")
    lines.append("## Fit 2 — DFT -> experiment validation (PEAK rows only)")
    lines.append("")
    lines.append(
        "`exp_Eox_V_vs_AgAgCl = slope * dft_Eox_eV + intercept`. NOTE: units differ (V vs eV), so "
        "this is a correlation/linear fit, NOT an equality check; the slope carries units of V/eV "
        "and a slope != 1 is expected."
    )
    lines.append(
        f"Fit 2 uses ONLY `{PEAK_LABEL_TYPE}` rows: {len(peak_points)} peak monomers fed the fit; "
        f"{n_nonpeak_excluded} non-peak (onset) monomer(s) were EXCLUDED. The DFT ΔSCF Eox is a "
        "thermodynamic peak observable, so onset rows would add kinetic noise to the validation."
    )
    lines.append("")
    if dft_to_exp is not None:
        lines.append(f"- slope = {dft_to_exp.slope:.6f} V/eV")
        lines.append(f"- intercept = {dft_to_exp.intercept:.6f} V")
        lines.append(f"- R^2 = {dft_to_exp.r2:.4f}")
        lines.append(f"- MAE = {dft_to_exp.mae:.4f} V")
    else:
        lines.append(f"- INSUFFICIENT PEAK POINTS (< 2; {len(peak_points)} peak monomer(s)): fit not computed.")
    lines.append("")
    lines.append("### Reference floor + core-monomer check")
    lines.append("")
    lines.append(REFERENCE_FLOOR_NOTE)
    lines.append("")
    if reference_flag_message:
        lines.append(reference_flag_message)
        lines.append("")
    lines.append("## Side-by-side: pinned xTB->experiment vs new xTB->DFT")
    lines.append("")
    lines.append("Clearly labeled; NO files are overwritten. The pinned values come from `configs/tier1.yaml`.")
    lines.append("")
    lines.append("| calibration | slope | intercept | note |")
    lines.append("| --- | --- | --- | --- |")
    if pinned is not None:
        lines.append(
            f"| pinned xTB->experiment (V) | {pinned['slope']:.6f} | {pinned['intercept']:.6f} | "
            f"PINNED screening default ({pinned.get('source', 'configs/tier1.yaml')}); unchanged |"
        )
    else:
        lines.append("| pinned xTB->experiment (V) | (unavailable) | (unavailable) | not found in configs/tier1.yaml |")
    if xtb_to_dft is not None:
        lines.append(
            f"| new xTB->DFT (eV) | {xtb_to_dft.slope:.6f} | {xtb_to_dft.intercept:.6f} | "
            "NEW artifact; not pinned; for comparison only |"
        )
    else:
        lines.append("| new xTB->DFT (eV) | (insufficient points) | (insufficient points) | NEW artifact |")
    lines.append("")
    lines.append(
        "Both fits use the IDENTICAL xTB descriptor (`monomer_eox_vs_AgAgCl`), so the two "
        "intercepts/slopes are directly comparable. The pinned fit targets experimental V vs "
        "Ag/AgCl; the new fit targets DFT Eox in eV."
    )
    lines.append("")
    lines.append("## Screen-ready calibration (DFT-anchored, directive §7)")
    lines.append("")
    lines.append(
        "Composing Fit 1 (xTB->DFT) and Fit 2 (DFT->exp peak) collapses the two-stage §7 design "
        "into ONE linear map from the xTB descriptor straight to V vs Ag/AgCl:"
    )
    lines.append("")
    lines.append("- `composed_slope     = fit2.slope * fit1.slope`")
    lines.append("- `composed_intercept = fit2.slope * fit1.intercept + fit2.intercept`")
    lines.append("")
    lines.append(
        "This composed map has the SAME input (xTB descriptor) and output (V vs Ag/AgCl) as the "
        "pinned `tier1.yaml` `monomer_eox` calibration, so it is a drop-in replacement."
    )
    lines.append("")
    lines.append("| calibration | slope | intercept | MAE (V) | note |")
    lines.append("| --- | --- | --- | --- | --- |")
    if pinned is not None:
        lines.append(
            f"| pinned xTB->experiment (V) | {pinned['slope']:.6f} | {pinned['intercept']:.6f} | "
            "n/a | PINNED screening default; unchanged |"
        )
    else:
        lines.append("| pinned xTB->experiment (V) | (unavailable) | (unavailable) | n/a | not found |")
    if composed is not None:
        lines.append(
            f"| composed xTB->V (DFT-anchored) | {composed['slope']:.6f} | "
            f"{composed['intercept']:.6f} | {composed['mae_V']:.4f} | "
            f"NEW; xTB->DFT n={composed['n_points_xtb_to_dft']}, "
            f"DFT->exp peak n={composed['n_points_dft_to_exp_peak']} |"
        )
    else:
        lines.append(
            "| composed xTB->V (DFT-anchored) | (insufficient points) | (insufficient points) | "
            "n/a | NEW; needs both stage fits |"
        )
    lines.append("")
    lines.append(
        "To switch the screen to the directive's xTB->DFT calibration, replace the tier1.yaml "
        "monomer_eox slope/intercept with these composed values (with provenance). Requires a real "
        "`--engine gaussian` batch + review first; computed here under whatever engine ran."
    )
    lines.append("")
    lines.append("## Skipped monomers")
    lines.append("")
    if skipped:
        for name, reason in skipped:
            lines.append(f"- {name}: {reason}")
    else:
        lines.append("- (none)")
    lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

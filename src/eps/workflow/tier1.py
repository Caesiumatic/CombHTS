"""Tier-1 mock workflow: per-species calculations, triad join, filters, scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from eps.chemspace import (
    Electrolyte,
    Monomer,
    Solvent,
    load_electrolytes,
    load_monomers,
    load_solvents,
)
from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.properties import (
    anion_oxidation_potential,
    dimerization_dG,
    monomer_eox_vs_AgAgCl,
    monomer_solvation,
    polymer_optical_gap,
    solvent_anodic_limit,
    solvent_anodic_limit_csv,
    solvent_cathodic_limit,
    solvent_cathodic_limit_csv,
)
from eps.scoring import add_composite_score, load_scoring_config
from eps.storage import SQLiteCache

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIER1_CONFIG = PROJECT_ROOT / "configs" / "tier1.yaml"
DEFAULT_SCORING_CONFIG = PROJECT_ROOT / "configs" / "scoring.yaml"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "outputs" / "tier1_cache.sqlite"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "tier1_ranked.csv"


@dataclass(frozen=True)
class Tier1Result:
    """Tier-1 workflow outputs and retention statistics."""

    ranked: pd.DataFrame
    all_triads: pd.DataFrame
    total_triads: int
    surviving_triads: int
    retention_fraction: float
    output_path: Path
    all_output_path: Path
    cache_path: Path


def run_tier1(
    *,
    engine: Engine | None = None,
    method: str = "mock-gfn2",
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    all_output_path: str | Path | None = None,
    tier1_config_path: str | Path = DEFAULT_TIER1_CONFIG,
    scoring_config_path: str | Path = DEFAULT_SCORING_CONFIG,
) -> Tier1Result:
    """Run Tier-1 over seed libraries with per-species cached MockEngine calls."""

    engine = engine or MockEngine()
    cache = SQLiteCache(cache_path)
    monomers = load_monomers()
    solvents = load_solvents()
    electrolytes = load_electrolytes()
    tier1_config = load_tier1_config(tier1_config_path)

    monomer_table = compute_monomer_table(monomers, engine, cache, method=method)
    monomer_solvent_table = compute_monomer_solvent_table(
        monomers,
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=tier1_config.get("calibration", {}),
    )
    solvent_table = compute_solvent_table(
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=tier1_config.get("calibration", {}),
    )
    anion_table = compute_anion_solvent_table(
        electrolytes,
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=tier1_config.get("calibration", {}),
    )

    triads = build_triad_table(
        monomer_table=monomer_table,
        monomer_solvent_table=monomer_solvent_table,
        solvent_table=solvent_table,
        anion_table=anion_table,
        electrolytes=electrolytes,
    )
    all_triads = annotate_tier1_filters(triads, tier1_config)
    filtered = apply_tier1_filters(all_triads, tier1_config)
    ranked = add_composite_score(filtered, load_scoring_config(scoring_config_path))

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output, index=False)

    all_output = Path(all_output_path) if all_output_path is not None else infer_all_output_path(output)
    all_output.parent.mkdir(parents=True, exist_ok=True)
    all_triads.to_csv(all_output, index=False)

    total = len(all_triads)
    survived = len(ranked)
    retention = survived / total if total else 0.0
    return Tier1Result(
        ranked=ranked,
        all_triads=all_triads,
        total_triads=total,
        surviving_triads=survived,
        retention_fraction=retention,
        output_path=output,
        all_output_path=all_output,
        cache_path=Path(cache_path),
    )


def compute_monomer_table(
    monomers: list[Monomer],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
) -> pd.DataFrame:
    """Compute monomer-only properties once per monomer."""

    rows = []
    for monomer in monomers:
        optical_gap = _safe_calculate(lambda: polymer_optical_gap(monomer, engine, cache, method=method))
        dimerization = _safe_calculate(lambda: dimerization_dG(monomer, engine, cache, method=method))
        rows.append(
            {
                "monomer_name": monomer.name,
                "monomer_class": monomer.monomer_class,
                "monomer_smiles": monomer.smiles,
                "monomer_canonical_smiles": monomer.canonical_smiles,
                "optical_gap_eV": optical_gap.value,
                "optical_gap_calc_status": optical_gap.status,
                "optical_gap_calc_error": optical_gap.error,
                "dimerization_dG_kcal_mol": dimerization.value,
                "dimerization_calc_status": dimerization.status,
                "dimerization_calc_error": dimerization.error,
            }
        )
    return pd.DataFrame(rows)


def compute_monomer_solvent_table(
    monomers: list[Monomer],
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
) -> pd.DataFrame:
    """Compute monomer-in-solvent properties over monomer x solvent pairs."""

    eox_calibration = _oxidation_calibration(calibration_config or {})
    rows = []
    for monomer in monomers:
        for solvent in solvents:
            eox = _safe_calculate(
                lambda: monomer_eox_vs_AgAgCl(
                    monomer,
                    solvent,
                    engine,
                    cache,
                    method=method,
                )
            )
            if eox.status == "ok":
                raw_eox = eox.value
                calibrated_eox = _apply_linear_calibration(raw_eox, eox_calibration)
                filter_eox = calibrated_eox if eox_calibration["enabled"] else raw_eox
            else:
                raw_eox = float("nan")
                calibrated_eox = float("nan")
                filter_eox = float("nan")
            solvation = _safe_calculate(
                lambda: monomer_solvation(
                    monomer,
                    solvent,
                    engine,
                    cache,
                    method=method,
                )
            )
            rows.append(
                {
                    "monomer_canonical_smiles": monomer.canonical_smiles,
                    "solvent_name": solvent.name,
                    "solvent_eps_r": solvent.eps_r,
                    "monomer_Eox_raw_V_vs_AgAgCl": raw_eox,
                    "monomer_Eox_calibrated_V_vs_AgAgCl": calibrated_eox,
                    "monomer_Eox_filter_V_vs_AgAgCl": filter_eox,
                    # Deprecated ambiguous alias; prefer the explicit raw/calibrated/filter columns.
                    "monomer_Eox_V": filter_eox,
                    "monomer_Eox_calc_status": eox.status,
                    "monomer_Eox_calc_error": eox.error,
                    "solvation_dG_kcal_mol": solvation.value,
                    "solvation_calc_status": solvation.status,
                    "solvation_calc_error": solvation.error,
                }
            )
    return pd.DataFrame(rows)


def compute_solvent_table(
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
) -> pd.DataFrame:
    """Compute solvent anodic/cathodic limits per spec §3.2 once per solvent.

    The anodic and cathodic limits are computed via the cached engine (adiabatic ΔSCF
    oxidation/reduction of the solvent molecule in its own implicit solvent). If a calc
    fails, the row falls back to the stopgap CSV value so one solvent does not abort the
    screen. ``solvent_anodic_limit_V`` is the value used downstream.

    The shared oxidation calibration (T11) is applied to the ANODIC limit only (an
    oxidation potential); the CATHODIC limit is a reduction potential and stays raw.
    Calibration defaults to disabled when ``calibration_config`` is None, so direct
    callers/tests get raw computed values.
    """

    cal = _oxidation_calibration(calibration_config or {})
    rows = []
    for solvent in solvents:
        anodic = _safe_calculate(
            lambda: solvent_anodic_limit(solvent, engine, cache, method=method)
        )
        cathodic = _safe_calculate(
            lambda: solvent_cathodic_limit(solvent, engine, cache, method=method)
        )
        anodic_csv = solvent_anodic_limit_csv(solvent)
        cathodic_csv = solvent_cathodic_limit_csv(solvent)
        if anodic.status == "ok":
            anodic_calibrated = _apply_linear_calibration(anodic.value, cal)
            anodic_used = anodic_calibrated if cal["enabled"] else anodic.value
            anodic_source = "computed"
        else:
            # CSV stopgap is already in realistic units; do NOT calibrate it.
            anodic_calibrated = float("nan")
            anodic_used = anodic_csv
            anodic_source = "csv_fallback"
        cathodic_used = cathodic.value if cathodic.status == "ok" else cathodic_csv
        rows.append(
            {
                "solvent_name": solvent.name,
                "solvent_smiles": solvent.smiles,
                "solvent_canonical_smiles": solvent.canonical_smiles,
                "solvent_anodic_limit_computed_V": anodic.value,
                "solvent_anodic_limit_calibrated_V": anodic_calibrated,
                "solvent_anodic_limit_csv_V": anodic_csv,
                "solvent_anodic_limit_V": anodic_used,
                "solvent_anodic_limit_source": anodic_source,
                "solvent_anodic_limit_calc_status": anodic.status,
                "solvent_anodic_limit_calc_error": anodic.error,
                "solvent_cathodic_limit_computed_V": cathodic.value,
                "solvent_cathodic_limit_csv_V": cathodic_csv,
                "solvent_cathodic_limit_V": cathodic_used,
                "solvent_cathodic_limit_source": "computed" if cathodic.status == "ok" else "csv_fallback",
                "solvent_cathodic_limit_calc_status": cathodic.status,
                "solvent_cathodic_limit_calc_error": cathodic.error,
            }
        )
    return pd.DataFrame(rows)


def compute_anion_solvent_table(
    electrolytes: list[Electrolyte],
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
) -> pd.DataFrame:
    """Compute anion-in-solvent oxidation potentials once per unique anion x solvent.

    The shared oxidation calibration (T11) is applied to the anion Eox, mirroring the
    monomer raw/calibrated/filter pattern. Calibration defaults to disabled when
    ``calibration_config`` is None. On a failed calc all three value columns are NaN
    (no CSV fallback for anions, mirroring monomer behavior).
    """

    cal = _oxidation_calibration(calibration_config or {})
    unique_by_anion = {electrolyte.canonical_anion_smiles: electrolyte for electrolyte in electrolytes}
    rows = []
    for electrolyte in unique_by_anion.values():
        for solvent in solvents:
            anion_eox = _safe_calculate(
                lambda: anion_oxidation_potential(
                    electrolyte,
                    solvent,
                    engine,
                    cache,
                    method=method,
                )
            )
            if anion_eox.status == "ok":
                raw_anion = anion_eox.value
                calibrated_anion = _apply_linear_calibration(raw_anion, cal)
                filter_anion = calibrated_anion if cal["enabled"] else raw_anion
            else:
                raw_anion = float("nan")
                calibrated_anion = float("nan")
                filter_anion = float("nan")
            rows.append(
                {
                    "anion_canonical_smiles": electrolyte.canonical_anion_smiles,
                    "solvent_name": solvent.name,
                    "anion_Eox_raw_V_vs_AgAgCl": raw_anion,
                    "anion_Eox_calibrated_V_vs_AgAgCl": calibrated_anion,
                    "anion_Eox_filter_V_vs_AgAgCl": filter_anion,
                    # Backward-compat alias; equals the filter value used downstream.
                    "anion_Eox_V": filter_anion,
                    "anion_Eox_calc_status": anion_eox.status,
                    "anion_Eox_calc_error": anion_eox.error,
                }
            )
    return pd.DataFrame(rows)


def build_triad_table(
    *,
    monomer_table: pd.DataFrame,
    monomer_solvent_table: pd.DataFrame,
    solvent_table: pd.DataFrame,
    anion_table: pd.DataFrame,
    electrolytes: list[Electrolyte],
) -> pd.DataFrame:
    """Build all monomer x solvent x electrolyte triads by joining precomputed tables."""

    electrolyte_table = pd.DataFrame(
        [
            {
                "salt": electrolyte.salt,
                "salt_class": electrolyte.salt_class,
                "cation_smiles": electrolyte.cation_smiles,
                "anion_smiles": electrolyte.anion_smiles,
                "anion_canonical_smiles": electrolyte.canonical_anion_smiles,
            }
            for electrolyte in electrolytes
        ]
    )
    electrolyte_props = electrolyte_table.merge(
        anion_table,
        on="anion_canonical_smiles",
        how="left",
        validate="many_to_many",
    )
    triads = (
        monomer_solvent_table.merge(
            monomer_table,
            on="monomer_canonical_smiles",
            how="left",
            validate="many_to_one",
        )
        .merge(solvent_table, on="solvent_name", how="left", validate="many_to_one")
        .merge(electrolyte_props, on="solvent_name", how="left", validate="many_to_many")
    )
    triads["window_margin_V"] = (
        triads["solvent_anodic_limit_V"] - triads["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    # Anion Eox is now on the shared oxidation calibration (T11); the intercept cancels in
    # this margin, so the filter is governed by raw IP differences (extrapolated, screening-grade).
    triads["anion_stability_margin_V"] = (
        triads["anion_Eox_filter_V_vs_AgAgCl"] - triads["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    triads["solubility_score"] = -triads["solvation_dG_kcal_mol"]
    return triads


def annotate_tier1_filters(triads: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Annotate each triad with Tier-1 hard-filter pass/fail booleans and reasons."""

    filters = config["filters"]
    annotated = triads.copy()
    annotated["pass_window_margin"] = annotated["window_margin_V"] > float(filters["min_window_margin_V"])
    annotated["pass_anion_stability"] = annotated["anion_stability_margin_V"] > float(
        filters["min_anion_stability_margin_V"]
    )
    annotated["pass_solvation"] = annotated["solvation_dG_kcal_mol"] < float(
        filters["max_solvation_dG_kcal_mol"]
    )
    annotated["has_calculation_failure"] = annotated.apply(_has_calculation_failure, axis=1)
    annotated["passes_all_tier1_filters"] = (
        annotated["pass_window_margin"]
        & annotated["pass_anion_stability"]
        & annotated["pass_solvation"]
        & ~annotated["has_calculation_failure"]
    )
    annotated["failed_filter_reasons"] = annotated.apply(_failed_filter_reasons, axis=1)
    return annotated


def apply_tier1_filters(triads: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Return only triads passing all hard Tier-1 filters."""

    if "passes_all_tier1_filters" not in triads.columns:
        triads = annotate_tier1_filters(triads, config)
    return triads.loc[triads["passes_all_tier1_filters"]].reset_index(drop=True)


def load_tier1_config(path: str | Path = DEFAULT_TIER1_CONFIG) -> dict:
    """Load Tier-1 hard-filter thresholds from YAML."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def infer_all_output_path(output_path: str | Path) -> Path:
    """Infer the all-triads audit CSV path from the ranked output path."""

    output = Path(output_path)
    if output.name.endswith("_ranked.csv"):
        return output.with_name(output.name.removesuffix("_ranked.csv") + "_all.csv")
    return output.with_name(f"{output.stem}_all{output.suffix or '.csv'}")


def _oxidation_calibration(config: dict) -> dict[str, float | bool]:
    # Single oxidation calibration shared by monomer Eox, solvent anodic limit, and anion Eox (T11).
    monomer_config = config.get("monomer_eox", {})
    return {
        "enabled": bool(monomer_config.get("enabled", False)),
        "slope": float(monomer_config.get("slope", 1.0)),
        "intercept": float(monomer_config.get("intercept", 0.0)),
    }


def _apply_linear_calibration(raw_value: float, calibration: dict[str, float | bool]) -> float:
    return float(calibration["slope"]) * raw_value + float(calibration["intercept"])


def _failed_filter_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    failed_calculations = _failed_calculation_reasons(row)
    if failed_calculations:
        reasons.append("calculation_failed")
        reasons.extend(failed_calculations)
    if not bool(row["pass_window_margin"]):
        reasons.append("window_margin")
    if not bool(row["pass_anion_stability"]):
        reasons.append("anion_stability")
    if not bool(row["pass_solvation"]):
        reasons.append("solvation")
    return ";".join(reasons)


@dataclass(frozen=True)
class _CalcOutcome:
    value: float
    status: str
    error: str


def _safe_calculate(calculate: Callable[[], float]) -> _CalcOutcome:
    try:
        return _CalcOutcome(value=float(calculate()), status="ok", error="")
    except Exception as exc:  # noqa: BLE001 - audit output must preserve per-property failures.
        return _CalcOutcome(value=float("nan"), status="failed", error=_concise_error(exc))


def _concise_error(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:240]


def _has_calculation_failure(row: pd.Series) -> bool:
    return bool(_failed_calculation_reasons(row))


def _failed_calculation_reasons(row: pd.Series) -> list[str]:
    labels = {
        "monomer_Eox_calc_status": "monomer_eox_failed",
        "solvation_calc_status": "solvation_failed",
        "anion_Eox_calc_status": "anion_eox_failed",
        "optical_gap_calc_status": "optical_gap_failed",
        "dimerization_calc_status": "dimerization_failed",
    }
    return [label for column, label in labels.items() if row.get(column, "ok") == "failed"]

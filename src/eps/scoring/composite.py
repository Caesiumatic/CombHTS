"""Composite scoring for surviving Tier-1 triads."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCORING_CONFIG = PROJECT_ROOT / "configs" / "scoring.yaml"

# These are the five physical inputs to the composite. None contains a cation term: window is
# solvent/monomer, anion stability is anion/monomer, and the remaining three are monomer-only.
# Exact duplicates over these columns may therefore be collapsed in presentation views, but the
# full salt rows must remain available for audit. This is deliberately not a cation physics model.
CATION_INDEPENDENT_SCORE_CLASS_COLUMNS = (
    "window_margin_V",
    "anion_stability_margin_V",
    "solvation_dG_kcal_mol",
    "dimerization_dG_kcal_mol",
    "optical_gap_eV",
    "composite_score",
)


def load_scoring_config(path: str | Path = DEFAULT_SCORING_CONFIG) -> dict:
    """Load scoring weights and target optical gap from YAML."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    weights = config["weights"]
    total = sum(float(value) for value in weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
    return config


def add_composite_score(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Add normalized components, Pareto flag, and composite score to triads."""

    scored = frame.copy()
    if scored.empty:
        for column in _component_columns():
            scored[column] = []
        scored["composite_score"] = []
        scored["pareto_front"] = []
        return scored

    target_gap_eV = float(config["target_gap_eV"])
    scored["band_gap_deviation_eV"] = (scored["optical_gap_eV"] - target_gap_eV).abs()

    scored["norm_window_margin"] = _minmax(scored["window_margin_V"])
    scored["norm_anion_stability"] = _minmax(scored["anion_stability_margin_V"])
    scored["norm_solubility"] = _minmax(-scored["solvation_dG_kcal_mol"])
    scored["norm_dimerization"] = _minmax(-scored["dimerization_dG_kcal_mol"])
    scored["norm_band_gap"] = _minmax(-scored["band_gap_deviation_eV"])

    weights = config["weights"]
    scored["composite_score"] = (
        float(weights["window_margin"]) * scored["norm_window_margin"]
        + float(weights["anion_stability"]) * scored["norm_anion_stability"]
        + float(weights["solubility"]) * scored["norm_solubility"]
        + float(weights["dimerization"]) * scored["norm_dimerization"]
        + float(weights["band_gap_deviation"]) * scored["norm_band_gap"]
    )
    scored["pareto_front"] = is_pareto_front(
        scored,
        columns=("window_margin_V", "solubility_score", "band_gap_deviation_eV"),
        maximize=(True, True, False),
    )
    return scored.sort_values("composite_score", ascending=False).reset_index(drop=True)


def collapse_cation_degenerate_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse exact cation-only score permutations for a ranked/presentation view.

    A class must share monomer, solvent, anion, and every available cation-independent scoring
    input exactly. The representative rule is deterministic and intentionally non-physical:
    prefer a row explicitly allowed as a supporting electrolyte, then choose the alphabetically
    first salt. ``salts_tied`` preserves every class member. No score or weight is changed.
    """

    collapsed = frame.copy()
    if collapsed.empty:
        collapsed["salts_tied"] = pd.Series(dtype=str)
        collapsed["n_tied"] = pd.Series(dtype=int)
        return collapsed
    if "salt" not in collapsed.columns:
        collapsed["salts_tied"] = ""
        collapsed["n_tied"] = 1
        return collapsed

    monomer_key = _first_present(collapsed, "monomer_canonical_smiles", "monomer_name")
    anion_key = _first_present(collapsed, "anion_canonical_smiles", "anion_smiles")
    if monomer_key is None or anion_key is None or "solvent_name" not in collapsed.columns:
        collapsed["salts_tied"] = collapsed["salt"].astype(str)
        collapsed["n_tied"] = 1
        return collapsed

    group_columns = [monomer_key, "solvent_name", anion_key]
    group_columns.extend(
        column for column in CATION_INDEPENDENT_SCORE_CLASS_COLUMNS if column in collapsed.columns
    )
    representatives: list[pd.Series] = []
    for _, group in collapsed.groupby(group_columns, sort=False, dropna=False):
        candidates = group
        if "supporting_electrolyte_ok" in group.columns:
            supporting = group.loc[group["supporting_electrolyte_ok"].map(_is_true)]
            if not supporting.empty:
                candidates = supporting
        representative = candidates.sort_values("salt", kind="mergesort").iloc[0].copy()
        salts = sorted({str(salt) for salt in group["salt"]})
        representative["salts_tied"] = ";".join(salts)
        representative["n_tied"] = len(group)
        representatives.append(representative)

    result = pd.DataFrame(representatives)
    sort_columns = [column for column in ("composite_score", monomer_key, "solvent_name", "salt") if column in result]
    ascending = [False if column == "composite_score" else True for column in sort_columns]
    if sort_columns:
        result = result.sort_values(sort_columns, ascending=ascending, kind="mergesort")
    return result.reset_index(drop=True)


def is_pareto_front(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    maximize: tuple[bool, ...],
) -> pd.Series:
    """Return a boolean mask for the Pareto front over mixed optimization directions."""

    if len(columns) != len(maximize):
        raise ValueError("columns and maximize must have the same length")

    values = frame.loc[:, columns].to_numpy(dtype=float)
    adjusted = values.copy()
    for index, should_maximize in enumerate(maximize):
        if not should_maximize:
            adjusted[:, index] *= -1.0

    front = []
    for i, candidate in enumerate(adjusted):
        dominated = False
        for j, challenger in enumerate(adjusted):
            if i == j:
                continue
            if (challenger >= candidate).all() and (challenger > candidate).any():
                dominated = True
                break
        front.append(not dominated)
    return pd.Series(front, index=frame.index, dtype=bool)


def _minmax(series: pd.Series) -> pd.Series:
    low = float(series.min())
    high = float(series.max())
    if high == low:
        return pd.Series(1.0, index=series.index)
    return (series - low) / (high - low)


def _component_columns() -> tuple[str, ...]:
    return (
        "band_gap_deviation_eV",
        "norm_window_margin",
        "norm_anion_stability",
        "norm_solubility",
        "norm_dimerization",
        "norm_band_gap",
    )


def _first_present(frame: pd.DataFrame, *columns: str) -> str | None:
    return next((column for column in columns if column in frame.columns), None)


def _is_true(value: object) -> bool:
    return value is True or str(value).strip().lower() == "true"

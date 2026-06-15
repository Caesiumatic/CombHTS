"""Composite scoring for surviving Tier-1 triads."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCORING_CONFIG = PROJECT_ROOT / "configs" / "scoring.yaml"


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

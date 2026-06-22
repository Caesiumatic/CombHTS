"""No-engine Tier-1 re-scoring from an existing all-triads audit CSV.

This path is for policy/config changes that require only joins and arithmetic. It deliberately
accepts no Engine and never opens the SQLite cache, so failed report-only calculations cannot be
retried accidentally. Expensive per-species results remain exactly those in the source harvest.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from eps.properties.solvent_windows import (
    apply_condition_aware_solvent_windows,
    load_solvent_window_measurements,
)
from eps.scoring import add_composite_score, load_scoring_config
from eps.workflow.tier1 import (
    DEFAULT_SCORING_CONFIG,
    DEFAULT_TIER1_CONFIG,
    PROJECT_ROOT,
    SCORING_CARRY_COLUMNS,
    annotate_tier1_filters,
    apply_tier1_filters,
    attach_scoring_columns,
    load_tier1_config,
)

DEFAULT_OUTDIR = PROJECT_ROOT / "outputs" / "tier1_rescored"

_FILTER_COLUMNS = (
    "pass_window_margin",
    "pass_anion_stability",
    "pass_solvation",
    "has_calculation_failure",
    "passes_all_tier1_filters",
    "failed_filter_reasons",
)
_WINDOW_AUDIT_COLUMNS = (
    "solvent_anodic_limit_prior_V",
    "solvent_anodic_limit_prior_source",
    "solvent_window_gate_policy",
    "solvent_window_condition_match",
    "solvent_window_measurement_salt",
    "solvent_window_measurement_electrolyte",
    "solvent_window_measurement_electrode",
    "solvent_window_measurement_reference",
    "solvent_window_measurement_source",
    "solvent_window_measurement_tier",
    "solvent_window_limit_set_by_electrolyte",
    "solvent_window_candidate_count",
    "solvent_window_measurement_anodic_V",
    "solvent_window_conservative_cap_V",
    "solvent_window_conservative_cap_source",
    "solvent_window_cap_applied",
)


@dataclass(frozen=True)
class Tier1RescoreResult:
    """CSV-only re-score outputs and survivor counts."""

    ranked: pd.DataFrame
    all_triads: pd.DataFrame
    input_path: Path
    output_path: Path
    all_output_path: Path
    total_triads: int
    surviving_triads: int
    retention_fraction: float


def rescore_tier1_harvest(
    input_path: str | Path,
    *,
    output_path: str | Path = DEFAULT_OUTDIR / "tier1_ranked.csv",
    all_output_path: str | Path = DEFAULT_OUTDIR / "tier1_all.csv",
    tier1_config_path: str | Path = DEFAULT_TIER1_CONFIG,
    scoring_config_path: str | Path = DEFAULT_SCORING_CONFIG,
) -> Tier1RescoreResult:
    """Reapply solvent-window policy, hard filters, and scoring without engine calls."""

    source = Path(input_path)
    triads = pd.read_csv(source, low_memory=False)
    triads = _restore_window_prior(triads)
    triads = triads.drop(
        columns=[
            *[column for column in _FILTER_COLUMNS if column in triads.columns],
            *[column for column in SCORING_CARRY_COLUMNS if column in triads.columns],
            *[column for column in _WINDOW_AUDIT_COLUMNS if column in triads.columns],
        ]
    )

    tier1_config = load_tier1_config(tier1_config_path)
    window_config = tier1_config.get("solvent_window_gate", {}) or {}
    if bool(window_config.get("enabled", False)):
        window_path = Path(window_config.get("measurements_path", "data/solvent_windows.csv"))
        if not window_path.is_absolute():
            window_path = PROJECT_ROOT / window_path
        measurements = load_solvent_window_measurements(window_path)
        triads = apply_condition_aware_solvent_windows(
            triads,
            measurements,
            policy=str(window_config.get("policy", "measured_first_conservative")),
            fallback_policy=str(window_config.get("fallback_policy", "min_csv_computed")),
        )

    triads["window_margin_V"] = (
        triads["solvent_anodic_limit_V"] - triads["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    if {"cation_reduction_raw_V_vs_AgAgCl", "solvent_cathodic_limit_V"}.issubset(
        triads.columns
    ):
        triads["cation_reduction_below_solvent_cathodic"] = (
            triads["cation_reduction_raw_V_vs_AgAgCl"] > triads["solvent_cathodic_limit_V"]
        )

    all_triads = annotate_tier1_filters(triads, tier1_config)
    filtered = apply_tier1_filters(all_triads, tier1_config)
    ranked = add_composite_score(filtered, load_scoring_config(scoring_config_path))
    all_triads = attach_scoring_columns(all_triads, ranked)

    output = Path(output_path)
    all_output = Path(all_output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    all_output.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output, index=False)
    all_triads.to_csv(all_output, index=False)

    total = int(len(all_triads))
    survived = int(len(ranked))
    return Tier1RescoreResult(
        ranked=ranked,
        all_triads=all_triads,
        input_path=source,
        output_path=output,
        all_output_path=all_output,
        total_triads=total,
        surviving_triads=survived,
        retention_fraction=survived / total if total else 0.0,
    )


def _restore_window_prior(triads: pd.DataFrame) -> pd.DataFrame:
    """Make repeated re-scores idempotent by restoring the pre-policy window columns."""

    restored = triads.copy()
    if "solvent_anodic_limit_prior_V" in restored.columns:
        restored["solvent_anodic_limit_V"] = restored["solvent_anodic_limit_prior_V"]
    if "solvent_anodic_limit_prior_source" in restored.columns:
        restored["solvent_anodic_limit_source"] = restored[
            "solvent_anodic_limit_prior_source"
        ]
    return restored

"""Condition-aware, measured-first solvent electrochemical-window selection.

The practical anodic limit is not an intrinsic scalar property of an isolated solvent
molecule: it depends on the supporting electrolyte, working electrode, reference scale,
temperature, impurities, and the current cutoff used to declare decomposition.  This module
therefore treats measured windows as versioned condition records and selects the hard-gate
limit only after the cheap solvent/electrolyte join.  No quantum engine is called here.

Selection policy (``measured_first_conservative``):

1. find the lowest exact ``(solvent, salt)`` measurement, or otherwise the lowest eligible
   measurement for the solvent;
2. hard-cap that measured value by ``min(curated CSV, computed descriptor)`` so a wider generic
   formulation can never relax a hard gate relative to the existing conservative evidence;
3. when no measurement exists, use that same conservative fallback directly.

All values are V vs Ag/AgCl.  The selected row carries its experimental conditions and source
into the all-triads audit so a measured formulation limit is never presented as universal.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOLVENT_WINDOWS_PATH = PROJECT_ROOT / "data" / "solvent_windows.csv"

SOLVENT_WINDOW_COLUMNS = (
    "solvent",
    "salt",
    "anodic_limit_V_vs_AgAgCl",
    "cathodic_limit_V_vs_AgAgCl",
    "reference",
    "electrolyte",
    "electrode",
    "temperature_C",
    "cutoff",
    "source",
    "tier",
    "limit_set_by_electrolyte",
    "use_for_gate",
    "notes",
)


def load_solvent_window_measurements(
    path: str | Path = DEFAULT_SOLVENT_WINDOWS_PATH,
) -> pd.DataFrame:
    """Load conditioned solvent-window measurements in V vs Ag/AgCl.

    ``salt`` may be blank when the reported formulation cannot be mapped exactly to a library
    salt.  Such rows remain eligible as conservative solvent-only evidence but can never claim
    an exact salt match.
    """

    frame = pd.read_csv(path, keep_default_na=False)
    missing = set(SOLVENT_WINDOW_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
    frame = frame.loc[:, SOLVENT_WINDOW_COLUMNS].copy()
    frame["anodic_limit_V_vs_AgAgCl"] = pd.to_numeric(
        frame["anodic_limit_V_vs_AgAgCl"], errors="coerce"
    )
    frame["cathodic_limit_V_vs_AgAgCl"] = pd.to_numeric(
        frame["cathodic_limit_V_vs_AgAgCl"], errors="coerce"
    )
    frame["limit_set_by_electrolyte"] = frame["limit_set_by_electrolyte"].map(_as_bool)
    frame["use_for_gate"] = frame["use_for_gate"].map(_as_bool)
    eligible = frame["use_for_gate"] & np.isfinite(frame["anodic_limit_V_vs_AgAgCl"])
    if not (frame.loc[eligible, "reference"] == "Ag/AgCl").all():
        raise ValueError("Every gate-eligible solvent-window row must be converted to Ag/AgCl")
    return frame


def apply_condition_aware_solvent_windows(
    triads: pd.DataFrame,
    measurements: pd.DataFrame,
    *,
    policy: str = "measured_first_conservative",
    fallback_policy: str = "min_csv_computed",
) -> pd.DataFrame:
    """Select a conditioned anodic hard-gate limit for every joined triad.

    Args:
        triads: Joined monomer x solvent x electrolyte table. Required inputs include
            ``solvent_name``, ``salt``, the curated CSV limit, and the computed/calibrated limit.
        measurements: Output of :func:`load_solvent_window_measurements`.
        policy: Currently only ``measured_first_conservative``.
        fallback_policy: Currently only ``min_csv_computed``.

    Returns:
        Copy of ``triads`` whose ``solvent_anodic_limit_V`` is the selected hard-gate value in
        V vs Ag/AgCl, with condition/provenance columns attached.  The original per-solvent value
        is retained as ``solvent_anodic_limit_prior_V``.
    """

    if policy != "measured_first_conservative":
        raise ValueError(f"Unknown solvent-window policy {policy!r}")
    if fallback_policy != "min_csv_computed":
        raise ValueError(f"Unknown solvent-window fallback policy {fallback_policy!r}")

    required = {
        "solvent_name",
        "salt",
        "solvent_anodic_limit_V",
        "solvent_anodic_limit_csv_V",
        "solvent_anodic_limit_calibrated_V",
    }
    missing = required.difference(triads.columns)
    if missing:
        raise ValueError("triad table is missing solvent-window inputs: " + ", ".join(sorted(missing)))

    eligible = measurements.loc[measurements["use_for_gate"]].copy()
    exact: dict[tuple[str, str], pd.Series] = {}
    generic: dict[str, pd.Series] = {}
    exact_counts: dict[tuple[str, str], int] = {}
    generic_counts: dict[str, int] = {}

    for (solvent, salt), group in eligible.loc[eligible["salt"].astype(str) != ""].groupby(
        ["solvent", "salt"], sort=False
    ):
        exact[(str(solvent), str(salt))] = _most_conservative(group)
        exact_counts[(str(solvent), str(salt))] = int(len(group))
    for solvent, group in eligible.groupby("solvent", sort=False):
        generic[str(solvent)] = _most_conservative(group)
        generic_counts[str(solvent)] = int(len(group))

    out = triads.copy()
    out["solvent_anodic_limit_prior_V"] = out["solvent_anodic_limit_V"]
    if "solvent_anodic_limit_source" in out.columns:
        out["solvent_anodic_limit_prior_source"] = out["solvent_anodic_limit_source"]

    selected_values: list[float] = []
    selected_cathodic: list[float] = []
    selected_source: list[str] = []
    condition_match: list[str] = []
    measured_salt: list[str] = []
    measured_electrolyte: list[str] = []
    measured_electrode: list[str] = []
    measured_reference: list[str] = []
    measurement_source: list[str] = []
    measurement_tier: list[str] = []
    measurement_limited: list[bool | str] = []
    candidate_counts: list[int] = []
    measurement_values: list[float] = []
    conservative_caps: list[float] = []
    cap_sources: list[str] = []
    cap_applied: list[bool] = []

    for _, row in out.iterrows():
        key = (str(row["solvent_name"]), str(row["salt"]))
        measured = exact.get(key)
        match = "exact_salt_conservative"
        count = exact_counts.get(key, 0)
        if measured is None:
            measured = generic.get(str(row["solvent_name"]))
            match = "solvent_only_conservative"
            count = generic_counts.get(str(row["solvent_name"]), 0)

        if measured is not None:
            measured_value = float(measured["anodic_limit_V_vs_AgAgCl"])
            conservative_cap, cap_source = _conservative_fallback(row)
            selected_values.append(min(measured_value, conservative_cap))
            cathodic = _finite_or(
                measured["cathodic_limit_V_vs_AgAgCl"], row.get("solvent_cathodic_limit_V", np.nan)
            )
            selected_cathodic.append(cathodic)
            was_capped = conservative_cap < measured_value
            selected_source.append(
                "measured_conditioned_capped_by_fallback"
                if was_capped
                else "measured_conditioned"
            )
            condition_match.append(match)
            measured_salt.append(str(measured["salt"]))
            measured_electrolyte.append(str(measured["electrolyte"]))
            measured_electrode.append(str(measured["electrode"]))
            measured_reference.append(str(measured["reference"]))
            measurement_source.append(str(measured["source"]))
            measurement_tier.append(str(measured["tier"]))
            measurement_limited.append(bool(measured["limit_set_by_electrolyte"]))
            candidate_counts.append(count)
            measurement_values.append(measured_value)
            conservative_caps.append(conservative_cap)
            cap_sources.append(cap_source)
            cap_applied.append(was_capped)
            continue

        fallback, fallback_source = _conservative_fallback(row)
        selected_values.append(fallback)
        selected_cathodic.append(float(row.get("solvent_cathodic_limit_V", np.nan)))
        selected_source.append(fallback_source)
        condition_match.append("no_measurement_fallback")
        measured_salt.append("")
        measured_electrolyte.append("")
        measured_electrode.append("")
        measured_reference.append("")
        measurement_source.append("")
        measurement_tier.append("")
        measurement_limited.append("")
        candidate_counts.append(0)
        measurement_values.append(float("nan"))
        conservative_caps.append(fallback)
        cap_sources.append(fallback_source)
        cap_applied.append(False)

    out["solvent_anodic_limit_V"] = selected_values
    out["solvent_cathodic_limit_V"] = selected_cathodic
    out["solvent_anodic_limit_source"] = selected_source
    out["solvent_window_gate_policy"] = policy
    out["solvent_window_condition_match"] = condition_match
    out["solvent_window_measurement_salt"] = measured_salt
    out["solvent_window_measurement_electrolyte"] = measured_electrolyte
    out["solvent_window_measurement_electrode"] = measured_electrode
    out["solvent_window_measurement_reference"] = measured_reference
    out["solvent_window_measurement_source"] = measurement_source
    out["solvent_window_measurement_tier"] = measurement_tier
    out["solvent_window_limit_set_by_electrolyte"] = measurement_limited
    out["solvent_window_candidate_count"] = candidate_counts
    out["solvent_window_measurement_anodic_V"] = measurement_values
    out["solvent_window_conservative_cap_V"] = conservative_caps
    out["solvent_window_conservative_cap_source"] = cap_sources
    out["solvent_window_cap_applied"] = cap_applied
    return out


def _most_conservative(group: pd.DataFrame) -> pd.Series:
    index = pd.to_numeric(group["anodic_limit_V_vs_AgAgCl"], errors="coerce").idxmin()
    return group.loc[index]


def _conservative_fallback(row: pd.Series) -> tuple[float, str]:
    csv_value = _as_finite(row.get("solvent_anodic_limit_csv_V"))
    computed = _as_finite(row.get("solvent_anodic_limit_calibrated_V"))
    if csv_value is not None and computed is not None:
        return min(csv_value, computed), "fallback_conservative_min_csv_computed"
    if csv_value is not None:
        return csv_value, "curated_csv_fallback"
    if computed is not None:
        return computed, "computed_descriptor_fallback"
    raise ValueError(f"No finite solvent-window fallback for {row.get('solvent_name', '<unknown>')}")


def _as_finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _finite_or(value: object, fallback: object) -> float:
    primary = _as_finite(value)
    if primary is not None:
        return primary
    secondary = _as_finite(fallback)
    return float("nan") if secondary is None else secondary


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}

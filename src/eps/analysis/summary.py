"""Read-only directive-§8 post-processing of an existing Tier-1 harvest CSV.

This module NEVER recomputes or rescores anything: it only reads columns already written by
the Tier-1 workflow and produces summaries, distributions, a Pareto plot, a chemical-space
map, and a diagnostic shortlist. Any output that touches a placeholder axis (``optical_gap``,
``dimerization_dG``, ``band_gap_deviation_eV``, ``composite_score``, or the ``pareto_front``
flag that depends on them) is explicitly labeled placeholder-contaminated / diagnostic-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from eps.analysis import plots
from eps.scoring import collapse_cation_degenerate_rows

SURVIVOR_COLUMN = "passes_all_tier1_filters"
SHORTLIST_REQUIRED_COLUMNS = ("composite_score", "pareto_front")
RETENTION_DIMENSIONS = ("monomer_name", "solvent_name", "salt_class")

DIAGNOSTIC_NOTE = (
    "SCREENING-GRADE -- all five composite axes are now real physics, but optical_gap is the "
    "sTDA-xTB/HOMO-LUMO oligomer gap UNCALIBRATED vs TD-DFT and dimerization_dG is the xTB "
    "coupling free energy whose ABSOLUTE value is set up to a proton constant. The composite is "
    "a usable screening signal, NOT a validated experimental recommendation. See STATUS "
    "scientific caution and THINK T5/T6/T7."
)


@dataclass
class AnalyzeResult:
    """Outputs and provenance of an ``eps analyze`` run."""

    outdir: Path
    total_triads: int
    surviving_triads: int
    retention_fraction: float
    summary: pd.DataFrame
    summary_path: Path
    shortlist_path: Path | None = None
    figure_paths: list[Path] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def run_analyze(harvest_path: str | Path, outdir: str | Path) -> AnalyzeResult:
    """Produce the directive-§8 deliverables from an existing harvest CSV (read-only)."""

    frame = pd.read_csv(harvest_path)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []

    total, surviving, retention = _retention_overall(frame)
    summary = compute_summary(frame)
    summary_path = out / "summary.csv"
    summary.to_csv(summary_path, index=False)

    shortlist_path = _write_shortlist(frame, out, notes)
    pairings = non_obvious_pairings(frame)
    if pairings is None:
        notes.append("non_obvious_pairings.csv SKIPPED: harvest lacks monomer/solvent/score columns.")
    else:
        pairings.to_csv(out / "non_obvious_pairings.csv", index=False)
    figure_paths = _write_figures(frame, out, notes)

    return AnalyzeResult(
        outdir=out,
        total_triads=total,
        surviving_triads=surviving,
        retention_fraction=retention,
        summary=summary,
        summary_path=summary_path,
        shortlist_path=shortlist_path,
        figure_paths=figure_paths,
        notes=notes,
    )


def compute_summary(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a tidy summary table: overall + per-dimension retention + failure counts."""

    rows: list[dict[str, object]] = []
    total, surviving, retention = _retention_overall(frame)
    rows.append(
        {
            "section": "overall",
            "key": "all",
            "total_triads": total,
            "surviving_triads": surviving,
            "retention_fraction": retention,
            "failure_count": "",
        }
    )

    for dimension in RETENTION_DIMENSIONS:
        if dimension not in frame.columns:
            continue
        for key, group in frame.groupby(dimension, sort=True):
            g_total, g_surv, g_ret = _retention_overall(group)
            rows.append(
                {
                    "section": f"by_{dimension}",
                    "key": str(key),
                    "total_triads": g_total,
                    "surviving_triads": g_surv,
                    "retention_fraction": g_ret,
                    "failure_count": "",
                }
            )

    for column in sorted(c for c in frame.columns if c.endswith("_calc_status")):
        failures = int((frame[column].astype(str) == "failed").sum())
        rows.append(
            {
                "section": "failure_count",
                "key": column.removesuffix("_calc_status"),
                "total_triads": "",
                "surviving_triads": "",
                "retention_fraction": "",
                "failure_count": failures,
            }
        )

    return pd.DataFrame(rows)


def build_shortlist(frame: pd.DataFrame, top_n: int = 30) -> pd.DataFrame | None:
    """Top-N Pareto-front triads by composite score, or None if columns are missing."""

    if not all(column in frame.columns for column in SHORTLIST_REQUIRED_COLUMNS):
        return None
    front = frame[frame["pareto_front"].astype(bool)].copy()
    if front.empty:
        return front.assign(diagnostic_note=DIAGNOSTIC_NOTE)
    # ``tier1_all.csv`` intentionally retains every per-salt survivor for audit. The current
    # composite has no cation-dependent axis, so collapse only exact cation-only score classes in
    # this presentation view; do not fabricate a cation contribution to break ties.
    front = collapse_cation_degenerate_rows(front)
    front = front.sort_values("composite_score", ascending=False).head(top_n)
    front["diagnostic_note"] = DIAGNOSTIC_NOTE
    return front.reset_index(drop=True)


# Directive §8 "under-explored monomers" (e.g. selenophenes or furans in ionic liquids): matched
# by substring on monomer_class so naming variants (alkylfuran, oligofuran, ...) are all captured.
_UNDEREXPLORED_CLASS_SUBSTRINGS = ("furan", "selenophen", "donor", "acceptor", "fused")
_OBVIOUS_SOLVENT = "acetonitrile"


def _is_underexplored(monomer_class: object) -> bool:
    cls = str(monomer_class).lower()
    return any(sub in cls for sub in _UNDEREXPLORED_CLASS_SUBSTRINGS)


def non_obvious_pairings(frame: pd.DataFrame, *, top_n: int = 20) -> pd.DataFrame | None:
    """Directive §8: best NON-obvious solvent–electrolyte pairings for under-explored monomers.

    'Obvious' = acetonitrile (the default high-throughput solvent). Per monomer, surface the
    top-scoring SURVIVING pairing in a non-acetonitrile solvent, flagged when it rivals or beats
    that monomer's best acetonitrile pairing. εr is reported as the §3.2 ionic-conductivity proxy.
    Returns None if the needed columns are absent. Read-only; never rescoring.
    """

    needed = {"monomer_name", "solvent_name", "composite_score"}
    if not needed.issubset(frame.columns):
        return None
    df = frame.copy()
    if SURVIVOR_COLUMN in df.columns:
        df = df[df[SURVIVOR_COLUMN].astype(bool)]
    if {"composite_score", "pareto_front"}.issubset(df.columns):
        df = collapse_cation_degenerate_rows(df)
    if df.empty:
        return df

    rows = []
    for monomer, grp in df.groupby("monomer_name"):
        non_obvious = grp[grp["solvent_name"] != _OBVIOUS_SOLVENT]
        if non_obvious.empty:
            continue
        best = non_obvious.loc[non_obvious["composite_score"].idxmax()]
        obvious = grp[grp["solvent_name"] == _OBVIOUS_SOLVENT]
        best_obvious_score = float(obvious["composite_score"].max()) if not obvious.empty else float("nan")
        best_score = float(best["composite_score"])
        rows.append({
            "monomer_name": monomer,
            "monomer_class": best.get("monomer_class", ""),
            "solvent_name": best["solvent_name"],
            "salt": best.get("salt", best.get("salt_class", "")),
            "composite_score": best_score,
            "best_acetonitrile_score": best_obvious_score,
            "beats_acetonitrile": bool(pd.isna(best_obvious_score) or best_score >= best_obvious_score),
            "solvent_eps_r_conductivity_proxy": best.get("solvent_eps_r", float("nan")),
            "under_explored_class": _is_underexplored(best.get("monomer_class", "")),
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    # Surface under-explored + acetonitrile-beating pairings first, then by score.
    result = result.sort_values(
        ["under_explored_class", "beats_acetonitrile", "composite_score"],
        ascending=[False, False, False],
    ).head(top_n).reset_index(drop=True)
    return result


def _write_shortlist(frame: pd.DataFrame, out: Path, notes: list[str]) -> Path | None:
    shortlist = build_shortlist(frame)
    if shortlist is None:
        notes.append(
            "shortlist.csv SKIPPED: harvest lacks composite_score/pareto_front columns "
            "(point analyze at a scored harvest to enable the diagnostic shortlist)."
        )
        return None
    shortlist_path = out / "shortlist.csv"
    # Keep this a standard CSV. A leading ``#`` disclaimer is unsafe because valid SMILES such
    # as acetonitrile (``CC#N``) are truncated by readers using ``comment='#'``. The same caution
    # is already carried losslessly in the ``diagnostic_note`` column on every row.
    shortlist.to_csv(shortlist_path, index=False)
    return shortlist_path


def _write_figures(frame: pd.DataFrame, out: Path, notes: list[str]) -> list[Path]:
    if not plots.matplotlib_available():
        notes.append(
            "Figures SKIPPED: matplotlib is not importable; summary.csv and shortlist.csv "
            "were still produced."
        )
        return []
    figure_paths: list[Path] = []
    figure_paths.extend(plots.plot_distributions(frame, out, notes))
    pareto = plots.plot_pareto(frame, out, notes)
    if pareto is not None:
        figure_paths.append(pareto)
    figure_paths.extend(plots.chemical_space_map(frame, out, notes))
    return figure_paths


def _retention_overall(frame: pd.DataFrame) -> tuple[int, int, float]:
    total = int(len(frame))
    if SURVIVOR_COLUMN in frame.columns:
        surviving = int(frame[SURVIVOR_COLUMN].astype(bool).sum())
    else:
        surviving = 0
    retention = surviving / total if total else 0.0
    return total, surviving, retention

#!/usr/bin/env python3
"""Tabulate openCOSMO-RS dGsolv per (monomer, solvent) for the expansion pilot.

This is a DESCRIPTOR-VALIDATION tabulation, not a solubility calibration and not a scoring
change. dGsolv is a solvation free energy (gas -> dilute solution); it is NOT solubility. See
docs/lit_curation/solubility_descriptor_status.md. The Tier-1 20% "solubility" axis is unchanged.

Ready-to-run, no fabricated results: it reads whatever the cluster run wrote to
outputs/solvation_cosmors_pilot/solvation_grid_points.csv and refuses to present mock numbers.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POINTS = PROJECT_ROOT / "outputs" / "solvation_cosmors_pilot" / "solvation_grid_points.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "outputs" / "solvation_cosmors_pilot"

# The 3-molecule pilot anchors (real ORCA, MeCN), used only as a cache-reuse consistency check.
# Source: docs/runs/2026-06-22_orca-solvation-real-417544.md
PILOT_ANCHORS_MECN = {
    "thiophene": -4.132112,
    "EDOT": -7.908007,
    "pyrrole": -6.982100,
}
PILOT_SOURCE = "docs/runs/2026-06-22_orca-solvation-real-417544.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=Path, default=DEFAULT_POINTS)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args()


def _anchor_check(frame: pd.DataFrame) -> list[dict[str, object]]:
    """Confirm cached MeCN anchors reproduce the published pilot dGsolv values."""

    checks: list[dict[str, object]] = []
    mecn = frame[(frame["solvent_name"] == "acetonitrile") & (frame["calc_status"] == "ok")]
    for monomer, expected in PILOT_ANCHORS_MECN.items():
        row = mecn[mecn["monomer_name"] == monomer]
        if row.empty:
            checks.append({"monomer": monomer, "status": "MISSING", "expected": expected})
            continue
        got = float(row["solvation_dG_kcal_mol"].iloc[0])
        checks.append(
            {
                "monomer": monomer,
                "status": "ok" if abs(got - expected) < 1e-3 else "MISMATCH",
                "expected": expected,
                "got": got,
                "delta": got - expected,
            }
        )
    return checks


def _markdown(payload: dict[str, object], pivot: pd.DataFrame) -> str:
    lines = [
        "# openCOSMO-RS dGsolv expansion pilot — tabulation",
        "",
        "Status: DESCRIPTOR VALIDATION ONLY. dGsolv is a solvation free energy, NOT solubility.",
        "This artifact does NOT change the Tier-1 20% solubility axis "
        "(see docs/lit_curation/solubility_descriptor_status.md).",
        "",
        f"Engine method: `{payload['engine_method']}`",
        f"Points: {payload['n_ok']} ok, {payload['n_failed']} failed, "
        f"{payload['n_deferred']} deferred (no built-in COSMORS profile).",
        "",
        "## dGsolv (kcal/mol) by monomer x solvent",
        "",
        "Lower (more negative) dGsolv = stronger solvation. Blank = not computed (deferred/failed).",
        "",
    ]
    header = "| monomer | class | " + " | ".join(str(c) for c in pivot.columns) + " |"
    sep = "| --- | --- | " + " | ".join("---:" for _ in pivot.columns) + " |"
    lines.append(header)
    lines.append(sep)
    for (monomer, klass), row in pivot.iterrows():
        cells = []
        for col in pivot.columns:
            value = row[col]
            cells.append("" if pd.isna(value) else f"{value:.3f}")
        lines.append(f"| {monomer} | {klass} | " + " | ".join(cells) + " |")

    lines.extend(["", "## Per-solvent summary (computed points only)", "",
                  "| solvent | n | mean dGsolv | min | max |", "| --- | ---: | ---: | ---: | ---: |"])
    for row in payload["per_solvent"]:
        lines.append(
            f"| {row['solvent_name']} | {row['n']} | {row['mean_dG']:.3f} | "
            f"{row['min_dG']:.3f} | {row['max_dG']:.3f} |"
        )

    lines.extend(["", "## Cache-reuse consistency vs the 3-molecule pilot (MeCN)", "",
                  f"Pilot source: {PILOT_SOURCE}", "",
                  "| monomer | expected dGsolv | got | delta | status |",
                  "| --- | ---: | ---: | ---: | --- |"])
    for check in payload["anchor_consistency"]:
        got = check.get("got")
        delta = check.get("delta")
        lines.append(
            f"| {check['monomer']} | {check['expected']:.6f} | "
            f"{'' if got is None else f'{got:.6f}'} | "
            f"{'' if delta is None else f'{delta:+.6f}'} | {check['status']} |"
        )

    if payload["deferred_solvents"]:
        lines.extend(["", "## Deferred solvents (needed for full shortlist, NOT computed)", "",
                      "These shortlist-anchor solvents have no ORCA built-in openCOSMO-RS sigma "
                      "profile and require a custom solvent parametrization (out of pilot scope):", ""])
        for name in payload["deferred_solvents"]:
            lines.append(f"- {name}")

    lines.extend([
        "",
        "## Interpretation guardrail",
        "",
        "dGsolv ranks how favorably a single neutral monomer is solvated. It does NOT predict the",
        "concentration that dissolves: it omits the solute lattice/fusion enthalpy, finite",
        "concentration, aggregation, protonation/charge state, and electrolyte-salt compatibility.",
        "Treat this table as a solvation-affinity descriptor for review, not a solubility ranking.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    points_path = args.points.resolve()
    if not points_path.exists():
        raise SystemExit(
            f"ERROR: points CSV not found: {points_path}\n"
            "Run the pilot on Lop first: qsub scripts/run_solvation_cosmors_pilot.sge"
        )
    frame = pd.read_csv(points_path)
    required = {
        "monomer_name", "monomer_class", "solvent_name", "solvation_dG_kcal_mol",
        "calc_status", "engine_method",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise SystemExit(f"Points CSV lacks required columns: {', '.join(sorted(missing))}")

    methods = set(frame["engine_method"].dropna().unique())
    if any("mock" in str(m).lower() for m in methods):
        raise SystemExit("Refusing to tabulate mock values as a scientific descriptor result")

    computed = frame[frame["calc_status"] == "ok"].copy()
    # Pivot from OK rows only so failed/deferred points render blank, never a stale number.
    pivot = computed.pivot_table(
        index=["monomer_name", "monomer_class"],
        columns="solvent_name",
        values="solvation_dG_kcal_mol",
        aggfunc="first",
    )

    per_solvent = []
    for solvent_name, group in computed.groupby("solvent_name", sort=True):
        per_solvent.append({
            "solvent_name": solvent_name,
            "n": int(len(group)),
            "mean_dG": float(group["solvation_dG_kcal_mol"].mean()),
            "min_dG": float(group["solvation_dG_kcal_mol"].min()),
            "max_dG": float(group["solvation_dG_kcal_mol"].max()),
        })

    deferred = sorted(
        frame.loc[frame["calc_status"] == "deferred", "solvent_name"].astype(str).unique().tolist()
    )

    payload = {
        "status": "descriptor_validation_only_not_solubility_not_scoring",
        "quantity": "openCOSMO-RS dGsolv (kcal/mol)",
        "engine_method": sorted(methods)[0] if methods else "unknown",
        "n_ok": int((frame["calc_status"] == "ok").sum()),
        "n_failed": int((frame["calc_status"] == "failed").sum()),
        "n_deferred": int((frame["calc_status"] == "deferred").sum()),
        "per_solvent": per_solvent,
        "deferred_solvents": deferred,
        "anchor_consistency": _anchor_check(frame),
        "production_scoring_changed": False,
    }

    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    pivot_path = outdir / "solvation_grid_pivot.csv"
    json_path = outdir / "solvation_grid_summary.json"
    md_path = outdir / "solvation_grid_summary.md"
    pivot.to_csv(pivot_path)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(payload, pivot), encoding="utf-8")
    print(f"Wrote pivot CSV: {pivot_path}")
    print(f"Wrote summary JSON: {json_path}")
    print(f"Wrote summary report: {md_path}")
    print("NOTE: dGsolv != solubility; the Tier-1 20% solubility axis is UNCHANGED.")
    for check in payload["anchor_consistency"]:
        if check["status"] not in {"ok"}:
            print(f"WARNING: MeCN anchor {check['monomer']} consistency = {check['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

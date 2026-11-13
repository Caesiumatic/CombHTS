"""Plot the recorded June 22 screen from a compact, verified data extract.

Default: render the committed aggregate JSON without loading calculation artifacts.
To reconstruct that JSON from the archived parent harvest, pass --rebuild-from.
The reconstruction verifies counts, score-class ties, and the entire recorded
Pareto shortlist before writing any aggregate data. It performs no quantum-chemistry
calculations or rescoring; the source composite values and Pareto flags are retained.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/figures/screening_snapshot_20260622.json"
SVG = ROOT / "docs/figures/screening_snapshot_20260622.svg"
SOURCE_SHA256 = "c4eee9ce3b77264b5370e1b2421fbbfd50962259e81e0c450fcb9e38c41d4076"
RESCORE_RECORD = "docs/runs/2026-06-22_tier1-rescore-salt-fixed-417569.md"
SHORTLIST_RECORD = "docs/runs/2026-06-22_analyze-salt-fixed-417571.md"
ROLE_EXCLUSIONS = {"AgClO4": 262, "HClO4": 262, "H2SO4": 255, "pTSA": 16, "CSA": 0}
CLASS_COLUMNS = (
    "monomer_canonical_smiles", "solvent_name", "anion_canonical_smiles",
    "window_margin_V", "anion_stability_margin_V", "solvation_dG_kcal_mol",
    "dimerization_dG_kcal_mol", "optical_gap_eV", "composite_score",
)


def require(condition: bool, detail: str) -> None:
    """Reject a source mismatch before producing a figure-data extract."""
    if not condition:
        raise ValueError(detail)


def rebuild(source: Path) -> dict:
    """Reconstruct the role-filtered screen and export per-solvent summaries."""
    require(hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_SHA256,
            "Source SHA-256 differs from the verified capped-ESW harvest.")
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    capped = [r for r in rows if r["passes_all_tier1_filters"] == "True"]
    removed = Counter(r["salt"] for r in capped if r["salt"] in ROLE_EXCLUSIONS)
    require(removed == Counter({k: v for k, v in ROLE_EXCLUSIONS.items() if v}),
            "Role-exclusion counts differ from run 417569.")
    retained = [r for r in capped if r["salt"] not in ROLE_EXCLUSIONS]
    groups = defaultdict(list)
    for row in retained:
        groups[tuple(row[key] for key in CLASS_COLUMNS)].append(row)
    require((len(rows), len(capped), len(retained), len(groups)) == (7488, 2938, 2143, 1127),
            "Screen or score-class counts differ from run 417569.")
    require(Counter(len(group) for group in groups.values()) == {1: 373, 2: 492, 3: 262},
            "Score-class multiplicities differ from run 417569.")

    classes = []
    for group in groups.values():
        row = dict(sorted(group, key=lambda r: r["salt"])[0])
        row["salts_tied"] = "; ".join(sorted(r["salt"] for r in group))
        row["n_tied"] = len(group)
        classes.append(row)
    classes.sort(key=lambda r: (-float(r["composite_score"]), r["monomer_canonical_smiles"],
                               r["solvent_name"], r["salt"]))
    # The exported top 30 are drawn from the recorded Pareto front, not all scores.
    shortlist = [r for r in classes if r["pareto_front"] == "True"][:30]
    recorded = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in (ROOT / SHORTLIST_RECORD).read_text().splitlines()
        if re.match(r"\| \d+ \|", line)
    ]
    require(len(recorded) == len(shortlist) == 30, "Expected 30 recorded shortlist rows.")
    aliases = {"acetonitrile": "MeCN", "propylene carbonate": "PC"}
    for rank, (expected, row) in enumerate(zip(recorded, shortlist), start=1):
        actual = [row["monomer_name"], aliases.get(row["solvent_name"], row["solvent_name"]),
                  row["salt"], row["salts_tied"], row["n_tied"]]
        target = [expected[1], expected[2], expected[4], expected[5], int(expected[6])]
        require(actual == target, f"Shortlist identity/ties differ at rank {rank}.")
        require(abs(float(expected[7]) - float(row["composite_score"])) <= 0.0000005,
                f"Shortlist score differs at rank {rank}.")

    totals = Counter(r["solvent_name"] for r in rows)
    counts = Counter(r["solvent_name"] for r in retained)
    require(len(totals) == 13 and set(totals.values()) == {576}, "Unexpected solvent coverage.")
    summary = []
    for solvent in sorted(totals, key=lambda s: (-counts[s], s)):
        scores = [float(r["composite_score"]) for r in classes if r["solvent_name"] == solvent]
        summary.append({
            "solvent": solvent, "evaluated_triads": totals[solvent],
            "retained_triads": counts[solvent], "score_classes": len(scores),
            "score_quantiles": dict(zip(("min", "q25", "median", "q75", "max"),
                                        np.quantile(scores, [0, .25, .5, .75, 1]).tolist())) if scores else None,
            "shortlist_scores": [float(r["composite_score"]) for r in shortlist
                                 if r["solvent_name"] == solvent],
        })
    return {
        "snapshot_date": "2026-06-22",
        "source": {
            "artifact": "outputs/tier1_real_7488_capped_esw/tier1_all.csv",
            "sha256": SOURCE_SHA256,
            "lineage": "real GFN2-xTB harvest 417538 → capped-ESW replay 417562 → salt-role replay 417569 → analysis 417571",
            "records": ["docs/runs/2026-06-22_tier1-rescore-capped-esw-417562.md",
                        RESCORE_RECORD, SHORTLIST_RECORD],
            "reconstruction": "The exact salt-fixed CSV is absent locally. Apply the recorded role exclusions to the preserved complete capped-ESW harvest, retain its scores and Pareto flags, then collapse exact cation-only score classes.",
            "verified": {
                "all_rows": 7488, "capped_survivors": 2938, "role_exclusions": ROLE_EXCLUSIONS,
                "retained_rows": 2143, "distinct_score_classes": 1127,
                "classes_by_tie_count": {"1": 373, "2": 492, "3": 262},
                "shortlist": "All 30 ranks match recorded monomer/solvent, representative salt, tied members, tie count, and score within 0.5e-6.",
            },
        },
        "interpretation": {
            "count_unit": "Full per-salt triads; each solvent has 36 monomers × 16 salts.",
            "score_unit": "One value per exact monomer/solvent/anion/scoring-input class; cation duplicates collapsed.",
            "intervals": "Min–max, interquartile range, and median of retained class scores; descriptive intervals, not uncertainty estimates.",
            "shortlist": "30 exported Pareto-front classes ranked by composite score, not the 30 largest scores in the whole pool.",
            "scope": "Screening-grade composite with uncalibrated optical/dimerization/solvation-affinity axes. These are computational candidates, not measured experimental outcomes. Later IPEA and calibration revisions are separate snapshots.",
        },
        "solvents": summary,
    }


def render(data: dict, output: Path, preview: Path | None) -> None:
    """Render coverage and score intervals from the small committed extract."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 11, "axes.labelsize": 11,
        "text.color": "#243447", "axes.labelcolor": "#243447", "xtick.color": "#536274",
        "ytick.color": "#243447", "axes.edgecolor": "#c8d1da", "svg.fonttype": "none",
        "svg.hashsalt": "combhts-june22-screen", "savefig.facecolor": "white",
    })
    rows = data["solvents"]
    teal, pale, ink, orange = "#167e8c", "#e7eef2", "#24485b", "#c66529"
    fig, (left, right) = plt.subplots(1, 2, figsize=(12.3, 7.0), sharey=True,
                                    gridspec_kw={"width_ratios": [1, 1.35], "wspace": .21})
    fig.subplots_adjust(left=.18, right=.97, top=.84, bottom=.20)
    y = np.arange(len(rows))
    labels = [r["solvent"][0].upper() + r["solvent"][1:] for r in rows]
    left.barh(y, [r["evaluated_triads"] for r in rows], height=.55, color=pale, zorder=1)
    left.barh(y, [r["retained_triads"] for r in rows], height=.55, color=teal, zorder=2)
    for i, row in enumerate(rows):
        n = row["retained_triads"]
        left.text(n + 9, i, f"{n:,}", va="center", color=ink, fontsize=10)
        stats = row["score_quantiles"]
        if stats is None:
            right.text(.025, i, "No retained classes", va="center", color="#7b8795", fontsize=10)
            continue
        right.hlines(i, stats["min"], stats["max"], color="#9aafbb", lw=1.3, zorder=2)
        right.vlines([stats["min"], stats["max"]], i-.075, i+.075, color="#9aafbb", lw=1.1)
        right.add_patch(Rectangle((stats["q25"], i-.16), stats["q75"]-stats["q25"], .32,
                                  color="#b9d8df", linewidth=0, zorder=3))
        right.vlines(stats["median"], i-.17, i+.17, color=ink, lw=2, zorder=4)
        selected = row["shortlist_scores"]
        if selected:
            offsets = np.array([-.20, -.10, 0, .10, .20])
            jitter = offsets[np.arange(len(selected)) % len(offsets)]
            right.scatter(selected, i+jitter, s=24, color=orange, edgecolors="white",
                          linewidths=.45, zorder=5)
    left.set_yticks(y, labels)
    left.invert_yaxis()
    left.set_xlim(0, 605)
    left.set_xticks([0, 200, 400, 576])
    left.set_xlabel("Retained triads · 576 evaluated per solvent", labelpad=12)
    right.set_xlim(0, .75)
    right.set_xticks([0, .15, .30, .45, .60, .75])
    right.set_xlabel("Composite score (dimensionless)", labelpad=12)
    for ax in (left, right):
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0, pad=10)
        ax.tick_params(axis="x", length=3)
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#edf1f4", lw=.8)
    right.tick_params(axis="y", labelleft=False)
    left.set_title("A  Retention by solvent", loc="left", fontsize=13, weight="bold", pad=17)
    right.set_title("B  Retained score distributions", loc="left", fontsize=13, weight="bold", pad=17)
    fig.text(.18, .955, "7,488 evaluated  ·  2,143 retained (28.6%)  ·  1,127 distinct score classes",
             fontsize=13, color=ink)
    fig.legend(handles=[
        Line2D([0], [0], color="#9aafbb", lw=1.3, label="Min–max"),
        Patch(facecolor="#b9d8df", label="Middle 50%"),
        Line2D([0], [0], marker="|", color=ink, linestyle="none", markersize=10,
               markeredgewidth=2, label="Median"),
        Line2D([0], [0], marker="o", color=orange, linestyle="none", markersize=5,
               label="30 exported Pareto classes"),
    ], loc="center", bbox_to_anchor=(.58, .045), frameon=False, ncol=4,
       fontsize=10, columnspacing=1.5, handlelength=1.4, handletextpad=.6)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, metadata={"Date": None}, bbox_inches="tight", pad_inches=.15)
    if preview:
        preview.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview, dpi=160, bbox_inches="tight", pad_inches=.15)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-from", type=Path, help="Archived capped-ESW tier1_all.csv")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=SVG)
    parser.add_argument("--preview", type=Path, help="Optional local PNG preview")
    args = parser.parse_args()
    if args.rebuild_from:
        data = rebuild(args.rebuild_from)
        args.data.parent.mkdir(parents=True, exist_ok=True)
        args.data.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    else:
        data = json.loads(args.data.read_text())
    render(data, args.output, args.preview)
    print(args.output)


if __name__ == "__main__":
    main()

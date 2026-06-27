#!/usr/bin/env python3
"""T16 diagnostic: does the computed monomer reorganization energy lambda_ox
(= vertical_IP - adiabatic_IP, GFN2-xTB) separate electropolymerization-FEASIBLE
monomers (YES) from INTRINSICALLY-INFEASIBLE ones (chemical NO)?

Reads lambda_ox from BOTH:
  - outputs/secondary_descriptors.csv            (the 36-row library)
  - outputs/lambda_feasibility/secondary_descriptors_extra.csv  (feasibility-only monomers, Lop)
and feasibility outcomes from data/polymerizability_labels.csv.

Pure stdlib (no scipy/numpy): rank-based Mann-Whitney U + AUC.
Output: outputs/lambda_feasibility/{lambda_feasibility_points.csv, lambda_feasibility_summary.json}
DIAGNOSTIC ONLY — never a filter/score input.
"""
from __future__ import annotations

import csv
import json
import math
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "outputs" / "secondary_descriptors.csv"
# Lop-computed lambda_ox for feasibility monomers off the 36-row library (tracked copy).
EXTRA = ROOT / "data" / "lit_curation" / "lambda_feasibility_extra_results.csv"
LABELS = ROOT / "data" / "polymerizability_labels.csv"
OUTDIR = ROOT / "outputs" / "lambda_feasibility"
POINTS = OUTDIR / "lambda_feasibility_points.csv"
SUMMARY = OUTDIR / "lambda_feasibility_summary.json"


def _norm(name: str) -> str:
    return name.strip().lower()


def _family(name: str) -> str:
    n = name.lower()
    if "carbazole" in n:
        return "carbazole"
    if "amine" in n or "aniline" in n or "toluidine" in n:
        return "arylamine/aniline"
    if "thiophene" in n or n in {"edot", "prodot"}:
        return "thiophene"
    if "pyrrole" in n or n in {"edop"}:
        return "pyrrole"
    if "furan" in n or "benzofuran" in n:
        return "furan"
    if "selenophene" in n or n in {"edos"}:
        return "selenophene"
    if "fluorene" in n:
        return "fluorene"
    return "other"


def load_lambda() -> dict[str, float]:
    """lambda_ox per monomer from both sources, keyed on a FINITE lambda_ox value.

    The extra (Lop) rows carry status='failed' ONLY because the orthogonal cation
    spin-density sub-descriptor hit a cache NOT-NULL error; vertical_IP / adiabatic_IP
    (hence lambda_ox = vertical - adiabatic) were computed successfully. So we accept
    any row with a finite lambda_ox rather than gating on the conflated status flag.
    """
    out: dict[str, float] = {}
    for path in (LIB, EXTRA):
        if not path.exists():
            continue
        with path.open() as fh:
            for r in csv.DictReader(fh):
                try:
                    val = float(r["monomer_lambda_ox_eV"])
                except (ValueError, KeyError, TypeError):
                    continue
                if math.isfinite(val):
                    out[_norm(r["monomer_name"])] = val
    return out


def load_feasibility() -> dict[str, str]:
    raw: dict[str, list[tuple[str, str]]] = {}
    with LABELS.open() as fh:
        for r in csv.DictReader(fh):
            raw.setdefault(_norm(r["monomer_name"]), []).append(
                (r["outcome"], r.get("negative_type", ""))
            )
    out: dict[str, str] = {}
    for k, outs in raw.items():
        if any(o[0] == "YES" for o in outs):
            out[k] = "YES"
        elif any(o[1] == "chemical" for o in outs):
            out[k] = "NO-chem"
        else:
            out[k] = "NO-medium"
    return out


def mannwhitney_auc(a: list[float], b: list[float]) -> tuple[float, float, float]:
    """Return (AUC that a-value > b-value, U statistic for a, normal-approx two-sided p).

    AUC = P(random a > random b) + 0.5 P(tie); ranks handle ties.
    """
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return float("nan"), float("nan"), float("nan")
    combined = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    # average ranks
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[j + 1][0] == combined[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0  # 1-based average rank
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_a = sum(rk for rk, (_, grp) in zip(ranks, combined) if grp == 0)
    u_a = rank_a - na * (na + 1) / 2.0
    auc = u_a / (na * nb)  # P(a > b)
    # normal approximation (no tie correction for simplicity; reported as approx)
    mu = na * nb / 2.0
    sigma = math.sqrt(na * nb * (na + nb + 1) / 12.0)
    z = (u_a - mu) / sigma if sigma > 0 else 0.0
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return auc, u_a, p


def group_stats(vals: list[float]) -> dict[str, float]:
    if not vals:
        return {"n": 0}
    return {
        "n": len(vals),
        "mean": round(st.mean(vals), 4),
        "std": round(st.pstdev(vals), 4) if len(vals) > 1 else 0.0,
        "median": round(st.median(vals), 4),
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
    }


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    lam = load_lambda()
    feas = load_feasibility()

    points = []
    for name in sorted(set(lam) & set(feas)):
        points.append(
            {
                "monomer": name,
                "family": _family(name),
                "feasibility": feas[name],
                "lambda_ox_eV": round(lam[name], 4),
            }
        )

    with POINTS.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["monomer", "family", "feasibility", "lambda_ox_eV"])
        w.writeheader()
        w.writerows(points)

    by = {"YES": [], "NO-chem": [], "NO-medium": []}
    for p in points:
        by[p["feasibility"]].append(p["lambda_ox_eV"])

    auc_chem, u_chem, p_chem = mannwhitney_auc(by["NO-chem"], by["YES"])
    no_all = by["NO-chem"] + by["NO-medium"]
    auc_all, u_all, p_all = mannwhitney_auc(no_all, by["YES"])

    summary = {
        "n_matched": len(points),
        "groups": {g: group_stats(v) for g, v in by.items()},
        "separation_NOchem_vs_YES": {
            "auc_lambda_higher_in_NOchem": round(auc_chem, 4) if auc_chem == auc_chem else None,
            "mannwhitney_U": round(u_chem, 2) if u_chem == u_chem else None,
            "p_two_sided_normal_approx": round(p_chem, 4) if p_chem == p_chem else None,
        },
        "separation_allNO_vs_YES": {
            "auc_lambda_higher_in_NO": round(auc_all, 4) if auc_all == auc_all else None,
            "p_two_sided_normal_approx": round(p_all, 4) if p_all == p_all else None,
        },
        "interpretation_note": (
            "AUC ~0.5 => lambda_ox carries NO feasibility signal (cannot separate YES from NO). "
            "AUC ->1 => higher lambda predicts intrinsic-NO; AUC ->0 => lower lambda predicts NO."
        ),
    }
    with SUMMARY.open("w") as fh:
        json.dump(summary, fh, indent=2)

    # report
    print(f"matched monomers (lambda AND feasibility): {len(points)}")
    print("\nlambda_ox_eV by feasibility group:")
    for g in ("YES", "NO-chem", "NO-medium"):
        s = group_stats(by[g])
        if s["n"]:
            print(f"  {g:10s} n={s['n']:2d}  mean={s['mean']:.3f}  median={s['median']:.3f}  "
                  f"std={s['std']:.3f}  range=[{s['min']:.3f},{s['max']:.3f}]")
        else:
            print(f"  {g:10s} n=0")
    print(f"\nSeparation NO-chem vs YES:  AUC={auc_chem:.3f}  U={u_chem:.1f}  p~{p_chem:.3f}")
    print(f"Separation all-NO  vs YES:  AUC={auc_all:.3f}  p~{p_all:.3f}")
    print("\nAll points (sorted by lambda):")
    for p in sorted(points, key=lambda d: d["lambda_ox_eV"]):
        print(f"  lambda={p['lambda_ox_eV']:.3f}  {p['feasibility']:9s}  {p['family']:18s}  {p['monomer']}")
    print(f"\nWrote {POINTS}\nWrote {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

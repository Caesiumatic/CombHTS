#!/usr/bin/env python3
"""T6: per-class optical calibration of REAL sTDA-xTB hexamer (n=6) gaps to experimental
neutral-polymer optical-gap anchors.

Inputs:
  - data/lit_curation/optical_anchors_selected.csv  (experimental polymer anchors, mapped to library monomers)
  - data/lit_curation/optical_n6_real_stda_36monomers.csv  (real sTDA-xTB n1..n6 gaps from SGE 417866)

This fits  exp_polymer_gap_eV = slope * sTDA_n6_eV + intercept  (global), reports LOO-CV MAE,
the raw hexamer bias (n6 - exp), and per-class mean residual offsets. DIAGNOSTIC ONLY: it does
not change the 15% optical scoring axis or any weights. It answers: can the optical axis graduate
from diagnostic, and where is sTDA-xTB documented-weak?
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from rdkit import Chem

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = ROOT / "data" / "lit_curation" / "optical_anchors_selected.csv"
N6 = ROOT / "data" / "lit_curation" / "optical_n6_real_stda_36monomers.csv"
OUT_CSV = ROOT / "outputs" / "optical_calibration_real_n6" / "optical_real_n6_points.csv"
OUT_JSON = ROOT / "outputs" / "optical_calibration_real_n6" / "optical_real_n6_fit.json"


def canon(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(str(smiles))
    return Chem.MolToSmiles(mol) if mol is not None else None


def fit_linear(x: np.ndarray, y: np.ndarray) -> dict:
    design = np.column_stack([x, np.ones_like(x)])
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    pred = design @ np.array([slope, intercept])
    resid = y - pred
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    loo = []
    for i in range(len(x)):
        keep = np.arange(len(x)) != i
        d = design[keep]
        s, b = np.linalg.lstsq(d, y[keep], rcond=None)[0]
        loo.append(float(s * x[i] + b))
    loo = np.asarray(loo)
    return {
        "slope": float(slope),
        "intercept_eV": float(intercept),
        "r2": r2,
        "in_sample_mae_eV": float(np.mean(np.abs(resid))),
        "loo_cv_mae_eV": float(np.mean(np.abs(loo - y))),
        "pred_eV": pred.tolist(),
        "resid_eV": resid.tolist(),
        "loo_resid_eV": (loo - y).tolist(),
    }


def main() -> int:
    anchors = pd.read_csv(ANCHORS)
    n6 = pd.read_csv(N6)
    n6["canon"] = n6["monomer_smiles"].map(canon)
    n6_by_canon = {row["canon"]: row for _, row in n6.iterrows()}

    rows = []
    unmatched = []
    for _, a in anchors.iterrows():
        c = canon(a["monomer_smiles"])
        m = n6_by_canon.get(c)
        if m is None:
            unmatched.append({"polymer": a["polymer"], "monomer_smiles": a["monomer_smiles"],
                              "monomer_class": a["monomer_class"], "reason": "not in 36-row library"})
            continue
        rows.append({
            "polymer": a["polymer"],
            "monomer_name": m["monomer"],
            "anchor_class": a["monomer_class"],
            "library_class": m["monomer_class"],
            "exp_gap_eV": float(a["optical_gap_eV"]),
            "n6_stda_eV": float(m["optical_gap_n6_eV"]),
            "n6_converged": bool(m["optical_gap_converged"]),
            "raw_bias_n6_minus_exp_eV": float(m["optical_gap_n6_eV"]) - float(a["optical_gap_eV"]),
            "anchor_confidence": a["anchor_confidence"],
            "gap_method": a["gap_method"],
            "source_doi": a["source_doi"],
        })

    pts = pd.DataFrame(rows).sort_values("exp_gap_eV").reset_index(drop=True)
    x = pts["n6_stda_eV"].to_numpy(float)
    y = pts["exp_gap_eV"].to_numpy(float)
    fit = fit_linear(x, y)
    pts["global_pred_eV"] = fit["pred_eV"]
    pts["global_resid_eV"] = fit["resid_eV"]
    pts["loo_resid_eV"] = fit["loo_resid_eV"]

    # High-confidence-only fit (drop medium/Tauc/D-A-CT supporting points)
    hi = pts[pts["anchor_confidence"].str.lower() == "high"].copy()
    fit_hi = fit_linear(hi["n6_stda_eV"].to_numpy(float), hi["exp_gap_eV"].to_numpy(float)) if len(hi) >= 3 else None

    # Per-class offsets after the global fit (mean residual = how far that class sits off the line)
    per_class = []
    for cls, g in pts.groupby("anchor_class"):
        per_class.append({
            "anchor_class": cls,
            "n": int(len(g)),
            "mean_resid_eV": float(g["global_resid_eV"].mean()),
            "mae_eV": float(g["global_resid_eV"].abs().mean()),
            "mean_raw_bias_eV": float(g["raw_bias_n6_minus_exp_eV"].mean()),
            "singleton": len(g) == 1,
        })

    payload = {
        "status": "diagnostic_only_not_production_calibration",
        "relationship": "exp_polymer_gap_eV = slope * sTDA_xTB_n6_eV + intercept_eV",
        "computed_model": "real sTDA-xTB on neutral hexamers (n=6), SGE 417866",
        "n_anchors_matched": int(len(pts)),
        "n_anchors_unmatched": int(len(unmatched)),
        "unmatched": unmatched,
        "global_fit": {k: fit[k] for k in ("slope", "intercept_eV", "r2", "in_sample_mae_eV", "loo_cv_mae_eV")},
        "high_conf_fit": ({k: fit_hi[k] for k in ("slope", "intercept_eV", "r2", "in_sample_mae_eV", "loo_cv_mae_eV")} if fit_hi else None),
        "mean_raw_bias_n6_minus_exp_eV": float(pts["raw_bias_n6_minus_exp_eV"].mean()),
        "std_raw_bias_eV": float(pts["raw_bias_n6_minus_exp_eV"].std(ddof=1)),
        "n6_converged_count": int(pts["n6_converged"].sum()),
        "per_class": per_class,
        "production_scoring_changed": False,
    }

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    pts.to_csv(OUT_CSV, index=False)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print("=== matched anchor points (sorted by experimental gap) ===")
    print(pts[["polymer", "anchor_class", "exp_gap_eV", "n6_stda_eV", "raw_bias_n6_minus_exp_eV",
               "global_resid_eV", "loo_resid_eV", "n6_converged", "anchor_confidence"]].to_string(index=False))
    print("\n=== unmatched ===")
    for u in unmatched:
        print(" ", u)
    print("\n=== GLOBAL fit (all matched) ===")
    print(json.dumps(payload["global_fit"], indent=2))
    print("raw bias (n6-exp) mean/std eV:", round(payload["mean_raw_bias_n6_minus_exp_eV"], 3),
          "/", round(payload["std_raw_bias_eV"], 3))
    print("n6 converged:", payload["n6_converged_count"], "/", len(pts))
    if fit_hi:
        print("\n=== HIGH-confidence-only fit ===")
        print(json.dumps(payload["high_conf_fit"], indent=2))
    print("\n=== per-class offsets (after global fit) ===")
    print(pd.DataFrame(per_class).to_string(index=False))
    print(f"\nWrote {OUT_CSV}\nWrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

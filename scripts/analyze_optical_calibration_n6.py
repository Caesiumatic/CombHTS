#!/usr/bin/env python3
"""Fit diagnostic computed-to-experimental regressions for six optical anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POINTS = PROJECT_ROOT / "outputs" / "optical_calibration_n6" / "optical_n6_points.csv"
DEFAULT_OUTDIR = PROJECT_ROOT / "outputs" / "optical_calibration_n6"
PILOT_REFERENCE = {
    "relationship": "TDA_eV = slope * sTDA_eV + intercept_eV",
    "n": 3,
    "slope": 0.747765,
    "intercept_eV": 0.900030,
    "r2": 0.7701,
    "mae_eV": 0.0973,
    "source": "docs/runs/2026-06-22_orca-optical-corrected-417557.md",
    "note": "method-to-method dimer diagnostic, not experiment",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=Path, default=DEFAULT_POINTS)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args()


def _fit(x: np.ndarray, y: np.ndarray) -> dict[str, object]:
    design = np.column_stack([x, np.ones_like(x)])
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    predicted = design @ np.array([slope, intercept])
    residuals = y - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    leverage = np.diag(design @ np.linalg.inv(design.T @ design) @ design.T)
    loo_predictions: list[float] = []
    for held_out in range(len(x)):
        keep = np.arange(len(x)) != held_out
        loo_design = design[keep]
        loo_slope, loo_intercept = np.linalg.lstsq(loo_design, y[keep], rcond=None)[0]
        loo_predictions.append(float(loo_slope * x[held_out] + loo_intercept))
    loo_residuals = y - np.asarray(loo_predictions)
    leverage_threshold = 2.0 * design.shape[1] / len(x)
    return {
        "slope": float(slope),
        "intercept_eV": float(intercept),
        "r2": r2,
        "in_sample_mae_eV": float(np.mean(np.abs(residuals))),
        "loo_cv_mae_eV": float(np.mean(np.abs(loo_residuals))),
        "predicted_eV": predicted.tolist(),
        "residual_eV": residuals.tolist(),
        "loo_predicted_eV": loo_predictions,
        "loo_residual_eV": loo_residuals.tolist(),
        "leverage": leverage.tolist(),
        "leverage_threshold": leverage_threshold,
        "high_leverage": (leverage > leverage_threshold).tolist(),
    }


def _method_result(frame: pd.DataFrame, column: str) -> dict[str, object]:
    fit = _fit(
        frame[column].to_numpy(dtype=float), frame["experimental_gap_eV"].to_numpy(dtype=float)
    )
    anchors: list[dict[str, object]] = []
    for index, (_, row) in enumerate(frame.iterrows()):
        anchors.append(
            {
                "polymer": row["polymer"],
                "monomer_name": row["monomer_name"],
                "monomer_class": row["monomer_class"],
                "computed_eV": float(row[column]),
                "experimental_eV": float(row["experimental_gap_eV"]),
                "residual_eV": fit["residual_eV"][index],
                "loo_residual_eV": fit["loo_residual_eV"][index],
                "leverage": fit["leverage"][index],
                "high_leverage": fit["high_leverage"][index],
                "source_doi": row["source_doi"],
            }
        )
    detail = pd.DataFrame(anchors)
    class_rows = []
    global_mae = float(fit["in_sample_mae_eV"])
    for monomer_class, group in detail.groupby("monomer_class", sort=True):
        class_mae = float(group["residual_eV"].abs().mean())
        class_rows.append(
            {
                "monomer_class": monomer_class,
                "n": len(group),
                "mean_residual_eV": float(group["residual_eV"].mean()),
                "mae_eV": class_mae,
                "above_global_mae": class_mae > global_mae,
                "single_anchor_class": len(group) == 1,
            }
        )
    fit["anchors"] = anchors
    fit["per_class"] = class_rows
    return fit


def _markdown(payload: dict[str, object]) -> str:
    lines = [
        "# Optical n=6 computed-to-experiment diagnostic fit",
        "",
        "Status: diagnostic only; this artifact does not change the 15% optical score axis.",
        "",
        "The computed models are neutral dimers. This does not satisfy the planned longer-chain/",
        "geometry-sensitivity gate, so the fit must be reviewed before any scoring proposal.",
        "",
        "## Fit summary",
        "",
        "| computed method | n | slope | intercept (eV) | R² | in-sample MAE (eV) | LOO-CV MAE (eV) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method, fit in payload["computed_to_experiment"].items():
        lines.append(
            f"| {method} | 6 | {fit['slope']:.6f} | {fit['intercept_eV']:.6f} | "
            f"{fit['r2']:.4f} | {fit['in_sample_mae_eV']:.4f} | {fit['loo_cv_mae_eV']:.4f} |"
        )
    pilot = payload["pilot_reference"]
    lines.extend(
        [
            "",
            "## n=3 pilot comparison",
            "",
            f"The prior pilot was method-to-method, not computed-to-experiment: "
            f"`TDA = {pilot['slope']:.6f} * sTDA + {pilot['intercept_eV']:.6f} eV`, "
            f"R²={pilot['r2']:.4f}, MAE={pilot['mae_eV']:.4f} eV (n=3).",
            "Its coefficients are not directly interchangeable with either experimental fit.",
        ]
    )
    for method, fit in payload["computed_to_experiment"].items():
        lines.extend(
            [
                "",
                f"## {method}: anchor residual and leverage audit",
                "",
                "| anchor | class | computed (eV) | experiment (eV) | residual (eV) | LOO residual (eV) | leverage | flag |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for anchor in fit["anchors"]:
            flag = "HIGH LEVERAGE — examine before trust" if anchor["high_leverage"] else "—"
            lines.append(
                f"| {anchor['monomer_name']} | {anchor['monomer_class']} | "
                f"{anchor['computed_eV']:.4f} | {anchor['experimental_eV']:.4f} | "
                f"{anchor['residual_eV']:+.4f} | {anchor['loo_residual_eV']:+.4f} | "
                f"{anchor['leverage']:.4f} | {flag} |"
            )
        lines.extend(
            [
                "",
                "Per-class residuals (`above_global_mae` is diagnostic, not an acceptance threshold):",
                "",
                "| class | n | mean residual (eV) | MAE (eV) | above global MAE | singleton |",
                "| --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for row in fit["per_class"]:
            lines.append(
                f"| {row['monomer_class']} | {row['n']} | {row['mean_residual_eV']:+.4f} | "
                f"{row['mae_eV']:.4f} | {row['above_global_mae']} | {row['single_anchor_class']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation guardrail",
            "",
            "A high-leverage anchor or a large LOO residual means the six-point line is sensitive",
            "to that molecule. Investigate its oligomer geometry, class chemistry, and experimental",
            "phase before trusting the global fit. No result here authorizes production scoring.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    frame = pd.read_csv(args.points.resolve())
    required = {
        "polymer",
        "monomer_name",
        "monomer_class",
        "experimental_gap_eV",
        "source_doi",
        "stda_gap_eV",
        "stda_calc_status",
        "tddft_gap_eV",
        "tddft_calc_status",
        "engine",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Points CSV lacks required columns: {', '.join(sorted(missing))}")
    if len(frame) != 6 or not frame["anchor_confidence"].str.lower().eq("high").all():
        raise ValueError("Analysis requires exactly the six HIGH-confidence staging anchors")
    if frame["engine"].eq("mock").any():
        raise ValueError("Refusing to fit mock values as a scientific calibration")
    failed = frame[
        (frame["stda_calc_status"] != "ok") | (frame["tddft_calc_status"] != "ok")
    ]
    if not failed.empty:
        raise ValueError(f"Refusing incomplete fit: {len(failed)} anchors lack a paired result")
    if frame[["stda_gap_eV", "tddft_gap_eV", "experimental_gap_eV"]].isna().any().any():
        raise ValueError("Refusing fit with missing optical energies")

    payload = {
        "status": "diagnostic_only_not_production_calibration",
        "relationship": "experimental_gap_eV = slope * computed_gap_eV + intercept_eV",
        "n_anchors": 6,
        "oligomer_model": "neutral dimer (n=2)",
        "anchor_source_csv": str(
            PROJECT_ROOT / "data" / "lit_curation" / "optical_anchors_selected.csv"
        ),
        "computed_to_experiment": {
            "sTDA": _method_result(frame, "stda_gap_eV"),
            "TDA": _method_result(frame, "tddft_gap_eV"),
        },
        "pilot_reference": PILOT_REFERENCE,
        "production_scoring_changed": False,
    }
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    json_path = outdir / "optical_n6_fit.json"
    md_path = outdir / "optical_n6_fit.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(payload), encoding="utf-8")
    print(f"Wrote computed-to-experiment fit JSON: {json_path}")
    print(f"Wrote computed-to-experiment fit report: {md_path}")
    print("NOTE: diagnostic only; the 15% optical axis remains unchanged pending review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

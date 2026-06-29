#!/usr/bin/env python
"""Harvest the sharded ORCA xTB->DFT calibration (directive §7) into one fit + JSON.

Concatenates every ``outputs/dftcal_orca/shard_*/dft_calibration_points.csv`` written by the
``run_dftcal_orca_array.sge`` array, then fits the screen-ready ``xtb_to_dft_V`` anchor (V vs
Ag/AgCl) and computes the two directive §7 accuracy targets as RAW MAEs against experiment on the
peak rows:

    dft_vs_exp_mae_V          target < 0.15 V   (original B3LYP/SMD DFT vs experiment)
    calibrated_xtb_vs_exp_mae target < 0.30 V   (xTB->DFT anchor applied to the xTB descriptor)

Writes the merged points CSV + ``xtb_to_dft_calibration.json`` to ``outputs/dftcal_orca/``. The
slope/intercept in that JSON are what gets pinned into
``configs/tier1.yaml: calibration.xtb_to_dft.monomer_oxidation`` (then enabled -> re-harvest Tier-1).

Run locally (after pulling the shard CSVs) or on Lop; no engine calls, just pandas + numpy.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from eps.workflow.dft_calibration import _maybe_fit, _peak_mae

ROOT = Path(__file__).resolve().parents[1]
SHARD_GLOB = "outputs/dftcal_orca/shard_*/dft_calibration_points.csv"
OUTDIR = ROOT / "outputs" / "dftcal_orca"
PEAK = "monomer_oxidation_peak"


def main() -> int:
    shard_files = sorted(ROOT.glob(SHARD_GLOB))
    if not shard_files:
        raise SystemExit(f"no shard points CSVs under {ROOT / SHARD_GLOB}")
    frame = pd.concat([pd.read_csv(f) for f in shard_files], ignore_index=True)
    frame = frame.drop_duplicates(subset="canonical_smiles", keep="first")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    merged = OUTDIR / "dft_calibration_points.csv"
    frame.to_csv(merged, index=False)

    ok = frame[frame["dft_calc_status"] == "ok"].copy()
    peak = ok[ok["label_type"] == PEAK].copy()
    fit = _maybe_fit(ok["xtb_descriptor"], ok["dft_Eox_V_vs_AgAgCl"])
    dft_vs_exp = _peak_mae(peak["dft_Eox_V_vs_AgAgCl"], peak["exp_Eox_V_vs_AgAgCl"])
    if fit is not None and not peak.empty:
        cal_xtb = fit.apply(peak["xtb_descriptor"].to_numpy(dtype=float))
        cal_vs_exp = _peak_mae(pd.Series(cal_xtb), peak["exp_Eox_V_vs_AgAgCl"])
    else:
        cal_vs_exp = float("nan")

    def num(v: float) -> float | None:
        return float(v) if np.isfinite(v) else None

    record = {
        "calibration": "xtb_to_dft_V (directive §7, ORCA B3LYP/6-31G(d,p)/SMD/Freq)",
        "n_shards": len(shard_files),
        "n_ok": int(len(ok)),
        "n_peak": int(len(peak)),
        "xtb_to_dft_V": (
            {"slope": fit.slope, "intercept": fit.intercept, "r2": fit.r2, "mae_V": fit.mae}
            if fit is not None
            else None
        ),
        "accuracy_targets": {
            "dft_vs_exp_mae_V": num(dft_vs_exp),
            "dft_vs_exp_target_V": 0.15,
            "calibrated_xtb_vs_exp_mae_V": num(cal_vs_exp),
            "calibrated_xtb_vs_exp_target_V": 0.30,
        },
        "pin_into": "configs/tier1.yaml calibration.xtb_to_dft.monomer_oxidation {slope,intercept}; then enabled:true + re-harvest Tier-1",
    }
    out_json = OUTDIR / "xtb_to_dft_calibration.json"
    out_json.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    print(f"merged {len(shard_files)} shards -> {merged}  ({len(ok)} ok, {len(peak)} peak)")
    print(json.dumps(record["xtb_to_dft_V"], indent=2))
    print(json.dumps(record["accuracy_targets"], indent=2))
    print(f"wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

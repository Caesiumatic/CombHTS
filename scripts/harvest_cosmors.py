#!/usr/bin/env python3
"""Harvest decoupled openCOSMO-RS ΔGsolv for the CURRENT library (directive §4.1 COSMO-RS).

Decoupled: one ORCA σ-profile per species (monomers + solvents), cached, then a cheap pairwise
combine for every (monomer, solvent) pair. Writes data/solvation_cosmors.csv, which the Tier-1
screen reads cosmors-first (ALPB ΔGsolv proxy stays only as the fallback when a pair is absent).

REAL ORCA — run on Lop via SGE (scripts/run_cosmors_harvest.sge). See
docs/research/opencosmors_decoupling_20260628.md.
"""
from __future__ import annotations

import csv
from pathlib import Path

from eps.chemspace.loaders import load_monomers, load_solvents
from eps.engines.cosmors import dgsolv_kcal_mol, generate_sigma_profile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = PROJECT_ROOT / "outputs" / "cosmors_sigma_cache"
OUT_CSV = PROJECT_ROOT / "data" / "solvation_cosmors.csv"
METHOD = "orca6.1/opencosmors24a/bp86/def2-tzvpd"


def main() -> int:
    monomers = load_monomers()
    solvents = load_solvents()
    print(f"library: {len(monomers)} monomers x {len(solvents)} solvents", flush=True)

    # 1) one σ-profile per species (cached, reused across all pairings)
    solvent_profiles = {}
    for s in solvents:
        print(f"[σ solvent] {s.name}", flush=True)
        solvent_profiles[s.name] = generate_sigma_profile(s.canonical_smiles, cache_dir=CACHE_DIR)

    rows = []
    for i, m in enumerate(monomers, 1):
        print(f"[σ monomer {i}/{len(monomers)}] {m.name}", flush=True)
        try:
            mp = generate_sigma_profile(m.canonical_smiles, cache_dir=CACHE_DIR)
        except Exception as exc:  # noqa: BLE001 — record the failure, keep harvesting
            print(f"   FAILED σ-profile {m.name}: {exc}", flush=True)
            continue
        # 2) cheap pairwise combine for every solvent
        for s in solvents:
            try:
                dg = dgsolv_kcal_mol(mp, solvent_profiles[s.name])
                rows.append({
                    "monomer_name": m.name,
                    "monomer_canonical_smiles": mp.canonical_smiles,
                    "solvent_name": s.name,
                    "dGsolv_kcal_mol": f"{dg:.6f}",
                    "method": METHOD,
                })
            except Exception as exc:  # noqa: BLE001
                print(f"   FAILED combine {m.name}/{s.name}: {exc}", flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["monomer_name", "monomer_canonical_smiles", "solvent_name", "dGsolv_kcal_mol", "method"],
        )
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} (monomer,solvent) ΔGsolv rows -> {OUT_CSV}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

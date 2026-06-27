#!/usr/bin/env python3
"""Compute per-monomer secondary descriptors (lambda_ox + frontier/IP) for the
feasibility-set monomers that are NOT in the 36-row optical/secondary-descriptor
library, so the lambda-vs-feasibility diagnostic (THINK T16) has a balanced
YES / intrinsic-NO sample.

REAL GFN2-xTB — must run through SGE on Lop (head-node compute forbidden).
Reuses the exact production path: eps.properties.monomer_secondary_descriptors
with XTBEngine + SQLiteCache, method='gfn2-xtb', so lambda_ox = vertical_IP -
adiabatic_IP is computed identically to data/.../secondary_descriptors.csv.

Input : data/lit_curation/lambda_feasibility_extra_monomers.csv
        (monomer_name, feasibility_label, monomer_smiles)
Output: outputs/lambda_feasibility/secondary_descriptors_extra.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from rdkit import Chem

from eps.chemspace.models import Monomer
from eps.engines import XTBEngine
from eps.properties import monomer_secondary_descriptors
from eps.storage.cache import SQLiteCache

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT = PROJECT_ROOT / "data" / "lit_curation" / "lambda_feasibility_extra_monomers.csv"
OUTDIR = PROJECT_ROOT / "outputs" / "lambda_feasibility"
OUTPUT = OUTDIR / "secondary_descriptors_extra.csv"
CACHE = OUTDIR / "lambda_extra_cache.sqlite"
METHOD = "gfn2-xtb"

COLUMNS = [
    "monomer_name",
    "feasibility_label",
    "monomer_canonical_smiles",
    "monomer_HOMO_eV",
    "monomer_LUMO_eV",
    "monomer_HL_gap_eV",
    "monomer_vertical_IP_eV",
    "monomer_adiabatic_IP_eV",
    "monomer_lambda_ox_eV",
    "monomer_cation_max_spin",
    "monomer_cation_max_spin_atom_idx",
    "monomer_cation_max_spin_is_alpha",
    "monomer_cation_alpha_spin_sum",
    "secondary_monomer_calc_status",
    "secondary_monomer_calc_error",
]


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    engine = XTBEngine()
    cache = SQLiteCache(CACHE)

    rows: list[dict[str, object]] = []
    with INPUT.open() as fh:
        records = list(csv.DictReader(fh))

    for i, rec in enumerate(records, 1):
        name = rec["monomer_name"].strip()
        label = rec["feasibility_label"].strip()
        smiles = rec["monomer_smiles"].strip()
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None:
            print(f"[{i}/{len(records)}] {name}: INVALID SMILES {smiles!r} — skipped", flush=True)
            continue
        canonical = Chem.MolToSmiles(mol, canonical=True)
        monomer = Monomer(
            name=name,
            monomer_class="feasibility-extra",
            smiles=smiles,
            canonical_smiles=canonical,
        )
        print(f"[{i}/{len(records)}] {name} ({label})  {canonical}", flush=True)
        desc = monomer_secondary_descriptors(monomer, engine, cache, method=METHOD)
        out = {
            "monomer_name": name,
            "feasibility_label": label,
            "monomer_canonical_smiles": canonical,
            **desc,
        }
        rows.append(out)
        print(
            f"      lambda_ox={desc.get('monomer_lambda_ox_eV')}  "
            f"vIP={desc.get('monomer_vertical_IP_eV')}  aIP={desc.get('monomer_adiabatic_IP_eV')}  "
            f"status={desc.get('secondary_monomer_calc_status')}",
            flush=True,
        )

    with OUTPUT.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} rows -> {OUTPUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Reusable n-mer oligomer assembly for Tier-1 band-gap and dimerization physics.

The directive (§4.1) names ``stk`` for oligomer assembly; ``stk`` is not available in this
environment, so this module implements the equivalent capability with RDKit (a documented
substitution — see STATUS / the overnight report). Coupling regiochemistry is DATA-DRIVEN:
each monomer's ditopic building block (two ``[*]`` dummies marking the coupling atoms, isotope
1 = head, 2 = tail) lives in ``data/polymerization.csv`` and is human-reviewable. For the
clean 5-membered heteroaromatics the two α-coupling carbons can also be auto-derived
(``detect_alpha_carbons``); the CSV building block stays authoritative.

Assembly links building blocks head-to-tail into a linear n-mer and caps the ends with H.
Pure RDKit; no engine, no network — fully unit-testable without xtb.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rdkit import Chem

from eps.structures.geometry import smiles_to_xyz

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLYMERIZATION_PATH = PROJECT_ROOT / "data" / "polymerization.csv"
DEFAULT_OLIGOMER_N = 6
DIMER_N = 2

# Aromatic ring heteroatoms whose neighboring C–H carbons are α-coupling sites.
_AROMATIC_HETEROATOMS = {7, 8, 16, 34}  # N, O, S, Se


@dataclass(frozen=True)
class PolymerizationSpec:
    """Per-monomer coupling chemistry for oligomer assembly."""

    monomer_name: str
    coupling_mode: str
    building_block_smiles: str
    approximate: bool
    notes: str


def load_polymerization_specs(
    path: str | Path = DEFAULT_POLYMERIZATION_PATH,
) -> dict[str, PolymerizationSpec]:
    """Load the per-monomer polymerization specs keyed by monomer name."""

    frame = pd.read_csv(path, keep_default_na=False)
    required = {"monomer_name", "coupling_mode", "building_block_smiles", "approximate", "notes"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    specs: dict[str, PolymerizationSpec] = {}
    for row in frame.to_dict(orient="records"):
        specs[str(row["monomer_name"])] = PolymerizationSpec(
            monomer_name=str(row["monomer_name"]),
            coupling_mode=str(row["coupling_mode"]),
            building_block_smiles=str(row["building_block_smiles"]),
            approximate=str(row["approximate"]).strip().lower() in {"true", "1", "yes"},
            notes=str(row["notes"]),
        )
    return specs


def detect_alpha_carbons(mol: Chem.Mol) -> list[int]:
    """Return aromatic α-carbon indices: ring-heteroatom neighbors bearing an H.

    For a clean 5-membered heteroaromatic this is exactly the two α-positions; for fused or
    substituted rings it may return a different count, in which case an explicit building
    block must be supplied in the CSV rather than auto-deriving.
    """

    sites: set[int] = set()
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() in _AROMATIC_HETEROATOMS and atom.GetIsAromatic():
            for neighbor in atom.GetNeighbors():
                if (
                    neighbor.GetAtomicNum() == 6
                    and neighbor.GetIsAromatic()
                    and neighbor.GetTotalNumHs() >= 1
                ):
                    sites.add(neighbor.GetIdx())
    return sorted(sites)


def alpha_building_block_smiles(monomer_smiles: str) -> str:
    """Build a ditopic [1*]/[2*]-marked building block from auto-detected α-carbons.

    Raises ValueError unless exactly two α-carbons are found (use an explicit building block
    in ``data/polymerization.csv`` otherwise).
    """

    mol = Chem.MolFromSmiles(monomer_smiles)
    if mol is None:
        raise ValueError(f"Invalid monomer SMILES: {monomer_smiles}")
    alpha = detect_alpha_carbons(mol)
    if len(alpha) != 2:
        raise ValueError(
            f"auto α-coupling needs exactly 2 α-carbons, found {len(alpha)} for {monomer_smiles}; "
            "supply an explicit building_block_smiles instead"
        )
    rw = Chem.RWMol(mol)
    for isotope, carbon_idx in zip((1, 2), alpha):
        dummy = rw.AddAtom(Chem.Atom(0))
        rw.GetAtomWithIdx(dummy).SetIsotope(isotope)
        rw.AddBond(carbon_idx, dummy, Chem.BondType.SINGLE)
    built = rw.GetMol()
    Chem.SanitizeMol(built)
    return Chem.MolToSmiles(built)


def assemble_oligomer(building_block_smiles: str, n: int) -> Chem.Mol:
    """Assemble a linear n-mer from a ditopic [1*]/[2*] building block; caps ends with H."""

    if n < 1:
        raise ValueError("oligomer length n must be >= 1")
    building_block = Chem.MolFromSmiles(building_block_smiles)
    if building_block is None:
        raise ValueError(f"Invalid building-block SMILES: {building_block_smiles}")
    dummies = [a for a in building_block.GetAtoms() if a.GetAtomicNum() == 0]
    if len(dummies) != 2 or {d.GetIsotope() for d in dummies} != {1, 2}:
        raise ValueError(
            f"building block must have exactly two dummies isotope-labeled 1 and 2: {building_block_smiles}"
        )

    chain = Chem.Mol(building_block)
    for _ in range(n - 1):
        chain = _grow(chain, Chem.Mol(building_block))
    return _cap(chain)


def oligomer_smiles(monomer_smiles: str, spec: PolymerizationSpec, n: int) -> str:
    """Return the canonical SMILES of the assembled n-mer for one monomer."""

    building_block = spec.building_block_smiles or alpha_building_block_smiles(monomer_smiles)
    return Chem.MolToSmiles(assemble_oligomer(building_block, n))


def oligomer_xyz(monomer_smiles: str, spec: PolymerizationSpec, n: int, charge: int = 0) -> str:
    """Return a 3D XYZ geometry for the assembled n-mer (via the shared ETKDG path)."""

    return smiles_to_xyz(oligomer_smiles(monomer_smiles, spec, n), charge=charge)


def write_building_block_artifact(
    monomers,
    specs: dict[str, PolymerizationSpec],
    n: int,
    output_path: str | Path,
) -> Path:
    """Write a human-reviewable CSV of building blocks + assembled SMILES per monomer."""

    rows = []
    for monomer in monomers:
        spec = specs.get(monomer.name)
        row: dict[str, object] = {
            "monomer_name": monomer.name,
            "monomer_canonical_smiles": monomer.canonical_smiles,
            "coupling_mode": spec.coupling_mode if spec else "MISSING",
            "approximate": spec.approximate if spec else "",
            "building_block_smiles": spec.building_block_smiles if spec else "",
            "notes": spec.notes if spec else "no polymerization spec for this monomer",
        }
        try:
            row["alpha_autodetect_n"] = len(detect_alpha_carbons(Chem.MolFromSmiles(monomer.canonical_smiles)))
        except Exception:  # noqa: BLE001 - artifact must never crash the run.
            row["alpha_autodetect_n"] = "error"
        for label, length in (("dimer_smiles", DIMER_N), (f"oligomer_n{n}_smiles", n)):
            try:
                row[label] = oligomer_smiles(monomer.canonical_smiles, spec, length) if spec else ""
            except Exception as exc:  # noqa: BLE001
                row[label] = f"ASSEMBLY_ERROR: {type(exc).__name__}: {exc}"
        rows.append(row)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


def _grow(chain: Chem.Mol, unit: Chem.Mol) -> Chem.Mol:
    n_chain = chain.GetNumAtoms()
    combo = Chem.RWMol(Chem.CombineMols(chain, unit))
    tail_dummy = _find_isotope(combo, isotope=2, lo=0, hi=n_chain)
    head_dummy = _find_isotope(combo, isotope=1, lo=n_chain, hi=combo.GetNumAtoms())
    if tail_dummy is None or head_dummy is None:
        raise ValueError("could not locate coupling dummies during oligomer growth")
    carbon_tail = next(nb.GetIdx() for nb in combo.GetAtomWithIdx(tail_dummy).GetNeighbors())
    carbon_head = next(nb.GetIdx() for nb in combo.GetAtomWithIdx(head_dummy).GetNeighbors())
    combo.AddBond(carbon_tail, carbon_head, Chem.BondType.SINGLE)
    for idx in sorted((tail_dummy, head_dummy), reverse=True):
        combo.RemoveAtom(idx)
    grown = combo.GetMol()
    Chem.SanitizeMol(grown)
    return grown


def _cap(mol: Chem.Mol) -> Chem.Mol:
    rw = Chem.RWMol(mol)
    for idx in sorted((a.GetIdx() for a in rw.GetAtoms() if a.GetAtomicNum() == 0), reverse=True):
        rw.RemoveAtom(idx)
    capped = rw.GetMol()
    Chem.SanitizeMol(capped)
    return capped


def _find_isotope(mol: Chem.Mol, *, isotope: int, lo: int, hi: int) -> int | None:
    for idx in range(lo, hi):
        atom = mol.GetAtomWithIdx(idx)
        if atom.GetAtomicNum() == 0 and atom.GetIsotope() == isotope:
            return idx
    return None

from __future__ import annotations

import itertools
import math

import pytest

from eps.structures import smiles_to_xyz
from eps.structures.oligomer import load_polymerization_specs, oligomer_smiles


def test_smiles_to_xyz_embeds_large_dioctylfluorene_hexamer() -> None:
    # The 416-atom dioctylfluorene n=6 oligomer fails the deterministic embed; the hardened
    # random-coordinate retries must still produce a geometry (regression for the harvest bug
    # where the whole fluorene column dropped out with optical_gap = NaN).
    spec = load_polymerization_specs()["fluorene 9,9-dioctyl"]
    monomer = next(m for m in __import__("eps.chemspace", fromlist=["load_monomers"]).load_monomers()
                   if m.name == "fluorene 9,9-dioctyl")
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, 6)

    xyz = smiles_to_xyz(hexamer)
    atom_count = int(xyz.strip().splitlines()[0])
    assert atom_count == 416
    assert atom_count == len(xyz.strip().splitlines()) - 2


def test_smiles_to_xyz_raises_clear_error_on_unembeddable_input() -> None:
    with pytest.raises(ValueError, match="Invalid SMILES|failed to embed"):
        smiles_to_xyz("not a smiles at all !!!")


def _parse_xyz_coords(xyz: str) -> list[tuple[float, float, float]]:
    lines = xyz.strip().splitlines()
    return [
        (float(parts[1]), float(parts[2]), float(parts[3]))
        for line in lines[2:]
        for parts in [line.split()]
    ]


def test_smiles_to_xyz_edos_has_no_atom_clash() -> None:
    # EDOS (3,4-ethylenedioxyselenophene): Se cannot be typed by MMFF or UFF, so the old
    # UFF pre-optimization collapsed the geometry to a ~0.26 A clash. The fix skips FF
    # optimization here and hands the clean ETKDG embedding (~1.0 A min distance) to xTB.
    xyz = smiles_to_xyz("C1COc2cc[se]c2O1", charge=0)
    lines = xyz.strip().splitlines()
    atom_count = int(lines[0])

    assert atom_count == 15
    assert atom_count == len(lines) - 2

    coords = _parse_xyz_coords(xyz)
    min_distance = min(
        math.dist(a, b) for a, b in itertools.combinations(coords, 2)
    )
    assert min_distance > 0.7


def test_smiles_to_xyz_produces_valid_thiophene_xyz() -> None:
    xyz = smiles_to_xyz("c1ccsc1", charge=0)
    lines = xyz.strip().splitlines()
    atom_count = int(lines[0])

    assert atom_count == len(lines) - 2
    assert atom_count > 5
    assert any(line.startswith("S ") for line in lines[2:])
    for line in lines[2:]:
        parts = line.split()
        assert len(parts) == 4
        float(parts[1])
        float(parts[2])
        float(parts[3])

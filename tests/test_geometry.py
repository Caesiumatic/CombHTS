from __future__ import annotations

from eps.structures import smiles_to_xyz


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

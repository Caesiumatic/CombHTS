from __future__ import annotations

from pathlib import Path

import pytest
from rdkit import Chem

from eps.chemspace import load_monomers
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    alpha_building_block_smiles,
    assemble_oligomer,
    detect_alpha_carbons,
    load_polymerization_specs,
    oligomer_smiles,
    write_building_block_artifact,
)


def _idx_to_symbol(smiles: str, idxs: list[int]) -> list[str]:
    mol = Chem.MolFromSmiles(smiles)
    return [mol.GetAtomWithIdx(i).GetSymbol() for i in idxs]


@pytest.mark.parametrize(
    "smiles",
    ["c1ccsc1", "c1cc[nH]c1", "c1ccoc1", "c1cc[se]c1", "CCCCCCc1ccsc1"],
)
def test_alpha_detection_finds_two_alpha_carbons_on_clean_heteroaromatics(smiles: str) -> None:
    mol = Chem.MolFromSmiles(smiles)
    alpha = detect_alpha_carbons(mol)

    assert len(alpha) == 2
    # Every detected site is a carbon directly bonded to the ring heteroatom.
    assert all(sym == "C" for sym in _idx_to_symbol(smiles, alpha))
    hetero = {7, 8, 16, 34}
    for idx in alpha:
        neighbors = {nb.GetAtomicNum() for nb in mol.GetAtomWithIdx(idx).GetNeighbors()}
        assert neighbors & hetero


def test_alpha_building_block_has_two_isotope_dummies() -> None:
    bb = alpha_building_block_smiles("c1ccsc1")
    mol = Chem.MolFromSmiles(bb)
    dummies = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
    assert len(dummies) == 2
    assert {d.GetIsotope() for d in dummies} == {1, 2}


def test_alpha_building_block_rejects_non_clean_ring() -> None:
    # A 2,3-dioxythiophene has one α-carbon blocked, so auto-derivation must refuse it
    # (this is the WRONG isomer; the library now stores the 3,4-dioxy form, see
    # test_alkylenedioxy_monomers_have_two_free_alpha_carbons).
    with pytest.raises(ValueError, match="exactly 2 α-carbons"):
        alpha_building_block_smiles("c1cc2c(s1)OCCO2")


def test_alkylenedioxy_monomers_have_two_free_alpha_carbons() -> None:
    """Regression: EDOT/ProDOT/EDOP/EDOS must be the 3,4-dioxy isomer with BOTH α-carbons
    (adjacent to the ring heteroatom) free (bearing an H) for clean 2,5 coupling. Guards
    against silently regressing to the 2,3-dioxy isomer (one α blocked)."""

    library = {m.name: m for m in load_monomers()}
    for name in ("EDOT", "ProDOT", "EDOP", "EDOS"):
        mol = Chem.MolFromSmiles(library[name].canonical_smiles)
        assert mol is not None
        alpha = detect_alpha_carbons(mol)
        assert len(alpha) == 2, f"{name}: expected 2 α-carbons, got {len(alpha)}"
        for idx in alpha:
            atom = mol.GetAtomWithIdx(idx)
            assert atom.GetTotalNumHs() >= 1, f"{name}: α-carbon {idx} is blocked (no H)"
            assert any(nb.GetAtomicNum() in {7, 8, 16, 34} for nb in atom.GetNeighbors())
        # And the spec is now clean α-coupling, not an approximate explicit block.
        spec = load_polymerization_specs()[name]
        assert spec.coupling_mode == "alpha"
        assert spec.approximate is False


def test_assemble_thiophene_hexamer_atom_count_and_connectivity() -> None:
    hexamer = assemble_oligomer("[1*]c1ccc([2*])s1", 6)
    # Single connected fragment (no leftover dummies, no disconnected pieces).
    assert len(Chem.GetMolFrags(hexamer)) == 1
    assert not any(a.GetAtomicNum() == 0 for a in hexamer.GetAtoms())
    assert hexamer.GetNumAtoms() == 30  # 6 thiophenes x 5 heavy atoms, α,α'-coupled
    assert Chem.AddHs(hexamer).GetNumAtoms() == 44


def test_assemble_dimer_of_thiophene_is_bithiophene() -> None:
    dimer = assemble_oligomer("[1*]c1ccc([2*])s1", 2)
    assert Chem.MolToSmiles(dimer) == Chem.MolToSmiles(Chem.MolFromSmiles("c1ccc(-c2cccs2)s1"))


def test_every_library_monomer_has_a_spec_that_assembles() -> None:
    specs = load_polymerization_specs()
    monomers = load_monomers()
    assert set(specs) >= {m.name for m in monomers}

    for monomer in monomers:
        spec = specs[monomer.name]
        for n in (2, DEFAULT_OLIGOMER_N):
            smiles = oligomer_smiles(monomer.canonical_smiles, spec, n)
            mol = Chem.MolFromSmiles(smiles)
            assert mol is not None
            assert len(Chem.GetMolFrags(mol)) == 1  # connected
            assert not any(a.GetAtomicNum() == 0 for a in mol.GetAtoms())  # no dummies


def test_polymer_optical_gap_is_computed_on_the_oligomer_not_the_monomer(tmp_path: Path) -> None:
    from eps.engines import CalcRequest, MockEngine, SpeciesSpec
    from eps.properties.calculators import polymer_optical_gap, polymer_optical_gap_method
    from eps.storage import SQLiteCache

    specs = load_polymerization_specs()
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = specs["thiophene"]
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()

    gap = polymer_optical_gap(monomer, engine, cache, spec=spec, n=DEFAULT_OLIGOMER_N)

    # The value matches the engine's optical_gap of the assembled hexamer SMILES, not the monomer.
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, DEFAULT_OLIGOMER_N)
    expected = MockEngine().run(
        CalcRequest(SpeciesSpec(hexamer, 0, 1), "mock-gfn2", None, "optical_gap")
    ).value
    monomer_value = MockEngine().run(
        CalcRequest(SpeciesSpec(monomer.canonical_smiles, 0, 1), "mock-gfn2", None, "optical_gap")
    ).value
    assert gap == pytest.approx(expected)
    assert gap != pytest.approx(monomer_value)
    assert polymer_optical_gap_method(monomer, engine, cache, spec=spec) == "mock-deterministic"


def test_building_block_artifact_is_written_with_review_columns(tmp_path: Path) -> None:
    specs = load_polymerization_specs()
    monomers = load_monomers()
    artifact = write_building_block_artifact(monomers, specs, DEFAULT_OLIGOMER_N, tmp_path / "bb.csv")

    assert artifact.exists()
    import pandas as pd

    frame = pd.read_csv(artifact)
    assert {"monomer_name", "building_block_smiles", "coupling_mode", "approximate",
            "dimer_smiles", "oligomer_n6_smiles", "notes"}.issubset(frame.columns)
    assert len(frame) == len(monomers)
    # No assembly errors leaked into the artifact.
    assert not frame["oligomer_n6_smiles"].astype(str).str.contains("ASSEMBLY_ERROR").any()

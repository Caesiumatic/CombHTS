from __future__ import annotations

from rdkit import Chem

from eps.chemspace import load_electrolytes, load_monomers, load_solvents


def test_seed_monomers_parse_and_canonicalize() -> None:
    monomers = load_monomers()

    assert len(monomers) == 15
    for monomer in monomers:
        mol = Chem.MolFromSmiles(monomer.smiles, sanitize=True)
        assert mol is not None
        assert Chem.MolToSmiles(Chem.MolFromSmiles(monomer.canonical_smiles), canonical=True) == (
            monomer.canonical_smiles
        )


def test_seed_solvents_parse_and_have_valid_windows() -> None:
    solvents = load_solvents()

    assert len(solvents) == 11
    for solvent in solvents:
        mol = Chem.MolFromSmiles(solvent.smiles, sanitize=True)
        assert mol is not None
        assert solvent.eps_r > 0
        assert solvent.esw_anodic_V > solvent.esw_cathodic_V
        assert Chem.MolToSmiles(Chem.MolFromSmiles(solvent.canonical_smiles), canonical=True) == (
            solvent.canonical_smiles
        )


def test_seed_electrolytes_parse_and_canonicalize() -> None:
    electrolytes = load_electrolytes()

    assert len(electrolytes) == 10
    for electrolyte in electrolytes:
        cation = Chem.MolFromSmiles(electrolyte.cation_smiles, sanitize=True)
        anion = Chem.MolFromSmiles(electrolyte.anion_smiles, sanitize=True)
        assert cation is not None
        assert anion is not None
        assert Chem.MolToSmiles(
            Chem.MolFromSmiles(electrolyte.canonical_cation_smiles),
            canonical=True,
        ) == electrolyte.canonical_cation_smiles
        assert Chem.MolToSmiles(
            Chem.MolFromSmiles(electrolyte.canonical_anion_smiles),
            canonical=True,
        ) == electrolyte.canonical_anion_smiles

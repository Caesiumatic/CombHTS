from __future__ import annotations

from pathlib import Path

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
        assert solvent.potential_reference == "Ag/AgCl"
        assert solvent.eps_r > 0
        assert solvent.esw_anodic_V > solvent.esw_cathodic_V
        assert solvent.esw_anodic_V <= 4.0 or (
            "TODO replace with measured anodic limit vs Ag/AgCl" in solvent.notes
        )
        assert Chem.MolToSmiles(Chem.MolFromSmiles(solvent.canonical_smiles), canonical=True) == (
            solvent.canonical_smiles
        )

    water = next(solvent for solvent in solvents if solvent.name == "water")
    assert water.eps_r == 80.1


def test_seed_solvent_esw_values_are_pinned() -> None:
    expected = {
        "acetonitrile": (3.3, -2.7),
        "DCM": (2.7, -1.8),
        "propylene carbonate": (4.0, -2.5),
        "DMF": (2.0, -2.5),
        "DMSO": (1.6, -2.4),
        "THF": (2.9, -2.4),
        "nitromethane": (3.8, -1.2),
        "water": (0.77, -0.83),
        "GBL": (3.0, -2.5),
        "sulfolane": (2.5, -3.0),
        "NMP": (2.1, -2.4),
    }

    solvents = {solvent.name: solvent for solvent in load_solvents()}

    assert set(solvents) == set(expected)
    for name, (anodic, cathodic) in expected.items():
        solvent = solvents[name]
        assert solvent.esw_anodic_V == anodic
        assert solvent.esw_cathodic_V == cathodic
        assert "stopgap = cathodic + spec ESW width from CombHTS table 2.2" in solvent.notes


def test_solvent_xtb_gbsa_names_are_loaded() -> None:
    solvents = {solvent.name: solvent for solvent in load_solvents()}

    assert solvents["acetonitrile"].xtb_gbsa_name == "acetonitrile"
    assert solvents["water"].xtb_gbsa_name == "water"
    assert solvents["DMSO"].xtb_gbsa_name == "dmso"
    assert solvents["DMF"].xtb_gbsa_name == "dmf"
    assert solvents["THF"].xtb_gbsa_name == "thf"
    assert solvents["DCM"].xtb_gbsa_name == "CH2Cl2"
    assert solvents["propylene carbonate"].xtb_gbsa_name is None
    assert solvents["GBL"].xtb_gbsa_name is None
    assert solvents["sulfolane"].xtb_gbsa_name is None
    assert solvents["NMP"].xtb_gbsa_name is None
    assert solvents["nitromethane"].xtb_gbsa_name is None


def test_solvent_loader_warns_on_implausible_anodic_limit(tmp_path: Path, recwarn) -> None:
    csv_path = tmp_path / "solvents.csv"
    csv_path.write_text(
        "\n".join(
            [
                (
                    "name,smiles,eps_r,esw_anodic_V,esw_cathodic_V,"
                    "potential_reference,xtb_gbsa_name,notes"
                ),
                "bad-solvent,CC#N,37.5,6.0,-2.7,Ag/AgCl,acetonitrile,looks like width",
            ]
        ),
        encoding="utf-8",
    )

    solvents = load_solvents(csv_path)

    assert len(solvents) == 1
    warning = recwarn.pop(UserWarning)
    assert "may be an ESW width" in str(warning.message)


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

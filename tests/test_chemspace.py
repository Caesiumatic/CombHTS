from __future__ import annotations

from pathlib import Path

from rdkit import Chem

from eps.chemspace import load_electrolytes, load_monomers, load_solvents

# The validated seed library (directive §2 scale-up appends to it; these rows must stay present
# and byte-identical — see data/needs_review.md for what was deferred). Counts are pinned so an
# accidental drop is caught; bump them deliberately when the library grows.
SEED_MONOMER_NAMES = {
    "thiophene", "EDOT", "ProDOT", "3-hexylthiophene", "bithiophene", "pyrrole", "EDOP",
    "furan", "selenophene", "EDOS", "aniline", "carbazole", "fluorene 9,9-dioctyl", "CPDT",
    "benzothiadiazole-thiophene D-A",
}
SEED_SALT_NAMES = {
    "TBAPF6", "TBABF4", "TBAClO4", "TBAOTf", "TBATFSI", "LiClO4", "LiTFSI", "NaClO4",
    "H2SO4", "pTSA",
}
LIBRARY_MONOMER_COUNT = 36
LIBRARY_SOLVENT_COUNT = 13
LIBRARY_SALT_COUNT = 16


def test_seed_monomers_parse_and_canonicalize() -> None:
    monomers = load_monomers()

    assert len(monomers) == LIBRARY_MONOMER_COUNT
    names = {monomer.name for monomer in monomers}
    # The 15 validated seed monomers are all still present (rows unchanged).
    assert SEED_MONOMER_NAMES.issubset(names)
    for monomer in monomers:
        mol = Chem.MolFromSmiles(monomer.smiles, sanitize=True)
        assert mol is not None
        assert Chem.MolToSmiles(Chem.MolFromSmiles(monomer.canonical_smiles), canonical=True) == (
            monomer.canonical_smiles
        )


def test_seed_solvents_parse_and_have_valid_windows() -> None:
    solvents = load_solvents()

    assert len(solvents) == LIBRARY_SOLVENT_COUNT
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

    # The 11 validated seed solvents stay present with byte-identical ESW values (subset, because
    # the directive §2.2 scale-up appends nitrobenzene/benzonitrile).
    assert set(expected).issubset(set(solvents))
    for name, (anodic, cathodic) in expected.items():
        solvent = solvents[name]
        assert solvent.esw_anodic_V == anodic
        assert solvent.esw_cathodic_V == cathodic
        assert "stopgap = cathodic + spec ESW width from CombHTS table 2.2" in solvent.notes


def test_directive_2_2_solvent_additions_present_and_parse() -> None:
    solvents = {solvent.name: solvent for solvent in load_solvents()}

    for name in ("nitrobenzene", "benzonitrile"):
        assert name in solvents
        solvent = solvents[name]
        assert Chem.MolFromSmiles(solvent.smiles) is not None
        assert solvent.esw_anodic_V > solvent.esw_cathodic_V
        # The added windows are explicitly flagged as a FALLBACK (computed anodic limit is
        # primary), never sold as the authoritative/measured value used by the screen.
        notes = solvent.notes.lower()
        assert "fallback" in notes and "primary" in notes
        assert solvent.xtb_gbsa_name is not None  # uses a documented ALPB proxy keyword


def test_solvent_xtb_gbsa_names_are_loaded() -> None:
    solvents = {solvent.name: solvent for solvent in load_solvents()}

    assert solvents["acetonitrile"].xtb_gbsa_name == "acetonitrile"
    assert solvents["water"].xtb_gbsa_name == "water"
    assert solvents["DMSO"].xtb_gbsa_name == "dmso"
    assert solvents["DMF"].xtb_gbsa_name == "dmf"
    assert solvents["THF"].xtb_gbsa_name == "thf"
    assert solvents["DCM"].xtb_gbsa_name == "ch2cl2"
    assert solvents["nitromethane"].xtb_gbsa_name == "nitromethane"
    assert solvents["propylene carbonate"].xtb_gbsa_name == "dmso"
    assert solvents["GBL"].xtb_gbsa_name == "acetonitrile"
    assert solvents["sulfolane"].xtb_gbsa_name == "dmso"
    assert solvents["NMP"].xtb_gbsa_name == "dmf"
    for proxy_name in ("propylene carbonate", "GBL", "sulfolane", "NMP"):
        assert "ALPB proxy (no native xtb param); nearest dielectric" in solvents[proxy_name].notes


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

    assert len(electrolytes) == LIBRARY_SALT_COUNT
    # The 10 validated seed salts are all still present (rows unchanged).
    assert SEED_SALT_NAMES.issubset({electrolyte.salt for electrolyte in electrolytes})
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


def test_directive_2_3_salt_additions_present_and_parse() -> None:
    electrolytes = {electrolyte.salt: electrolyte for electrolyte in load_electrolytes()}

    for salt in ("TEAPF6", "LiBF4", "KCl", "CSA", "HClO4"):
        assert salt in electrolytes
        electrolyte = electrolytes[salt]
        assert Chem.MolFromSmiles(electrolyte.cation_smiles) is not None
        assert Chem.MolFromSmiles(electrolyte.anion_smiles) is not None

    # Polymeric / surfactant salts the per-ion model cannot handle stayed OUT of the live CSV.
    assert "NaPSS" not in electrolytes
    assert "NaDBSA" not in electrolytes


def test_electrolyte_roles_exclude_reference_salt_and_all_acids() -> None:
    electrolytes = {electrolyte.salt: electrolyte for electrolyte in load_electrolytes()}

    assert electrolytes["AgClO4"].electrolyte_role == "reference_only"
    assert electrolytes["AgClO4"].supporting_electrolyte_ok is False
    for salt in ("H2SO4", "pTSA", "CSA", "HClO4"):
        assert electrolytes[salt].electrolyte_role == "acid"
        assert electrolytes[salt].supporting_electrolyte_ok is False
    for salt in ("TBAPF6", "TBABF4", "TBAClO4", "LiClO4", "KCl"):
        assert electrolytes[salt].electrolyte_role == "supporting"
        assert electrolytes[salt].supporting_electrolyte_ok is True

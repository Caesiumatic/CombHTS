from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
from rdkit import Chem


def test_canonicalize_smiles_handles_valid_and_invalid_inputs() -> None:
    audit = _load_audit_module()

    canonical, error = audit.canonicalize_smiles("C1=CC=CS1")
    assert canonical == "c1ccsc1"
    assert error == ""

    canonical, error = audit.canonicalize_smiles("not-a-smiles")
    assert canonical == ""
    assert "could not parse" in error


def test_audit_real_staging_writes_summary_and_issues(tmp_path: Path) -> None:
    audit = _load_audit_module()
    summary_path = tmp_path / "summary.csv"
    issues_path = tmp_path / "issues.csv"

    summary, issues = audit.audit_staging(Path("."), summary_path, issues_path)

    assert summary_path.exists()
    assert issues_path.exists()
    assert len(summary) == 5
    assert set(summary["file"]) == {
        "data/lit_curation/solvent_esw_staging.csv",
        "data/lit_curation/polymerization_outcomes_staging.csv",
        "data/lit_curation/optical_anchors_selected.csv",
        "data/lit_curation/solubility_staging.csv",
        "data/lit_curation/optical_doping_staging.csv",
    }
    assert summary["columns_ok"].all()
    assert set(issues["classification"]).issubset(set(audit.CLASSIFICATIONS))
    assert (issues["file"] == "data/lit_curation/solvent_esw_staging.csv").any()

    written_summary = pd.read_csv(summary_path)
    written_issues = pd.read_csv(issues_path)
    assert len(written_summary) == len(summary)
    assert len(written_issues) == len(issues)


def test_section7_review_tables_are_parseable_and_smiles_are_valid() -> None:
    tables = [
        Path("data/lit_curation/eox_gapfill_candidates.csv"),
        Path("data/lit_curation/esw_promotion_candidates.csv"),
        Path("data/lit_curation/esw_remaining_gap_matrix.csv"),
        Path("data/lit_curation/polymerizability_promotion_candidates.csv"),
        Path("data/lit_curation/library_waveA_readiness_candidates.csv"),
    ]

    for table in tables:
        assert not pd.read_csv(table).empty

    for table, column in (
        (Path("data/lit_curation/eox_gapfill_candidates.csv"), "monomer_smiles"),
        (Path("data/lit_curation/polymerizability_promotion_candidates.csv"), "monomer_smiles"),
    ):
        df = pd.read_csv(table, keep_default_na=False)
        for smiles in df[column]:
            if smiles:
                assert Chem.MolFromSmiles(smiles, sanitize=True) is not None

    wave = pd.read_csv(
        Path("data/lit_curation/library_waveA_readiness_candidates.csv"),
        keep_default_na=False,
    )
    for smiles_or_pair in wave["smiles_or_ion_smiles"]:
        for smiles in smiles_or_pair.split("|"):
            assert Chem.MolFromSmiles(smiles.strip(), sanitize=True) is not None


def _load_audit_module() -> ModuleType:
    path = Path("scripts/audit_lit_curation_staging.py")
    spec = importlib.util.spec_from_file_location("audit_lit_curation_staging", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

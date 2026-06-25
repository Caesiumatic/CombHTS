"""Schema/SMILES audit coverage for the 2026-06-25 research-ingest staging files.

These tests exercise ONLY the newly registered ``RESEARCH_INGEST_20260625_SPECS`` schema set.
They do not touch production data and do not change the established Section-7 audit surface
(``STAGING_SPECS``), which is covered separately by ``test_lit_curation_audit.py``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from rdkit import Chem

from eps.curation import staging_audit

NEW_FILES = {
    "data/lit_curation/esw_windows_staging_20260625.csv",
    "data/lit_curation/eox_calibration_staging_20260625.csv",
    "data/lit_curation/feasibility_labels_staging_20260625.csv",
    "data/lit_curation/optical_anchors_staging_20260625.csv",
}


def test_research_ingest_specs_audit_clean(tmp_path: Path) -> None:
    summary, issues = staging_audit.audit_staging(
        Path("."),
        tmp_path / "summary.csv",
        tmp_path / "issues.csv",
        specs=staging_audit.RESEARCH_INGEST_20260625_SPECS,
    )

    assert len(summary) == 4
    assert set(summary["file"]) == NEW_FILES
    # every clean staging file matches its registered schema
    assert summary["columns_ok"].all()
    # no SMILES in any CLEAN staging file may fail RDKit (failures are quarantined separately)
    assert int(summary["rdkit_invalid_smiles"].sum()) == 0
    # the audit must not invent production duplicates for these review-only dated files
    assert int(summary["production_duplicate_rows"].sum()) == 0
    assert set(issues["classification"]).issubset(set(staging_audit.CLASSIFICATIONS))


def test_default_audit_surface_is_unchanged() -> None:
    """Registering the new specs must not alter the default STAGING_SPECS audit surface."""
    assert len(staging_audit.STAGING_SPECS) == 5
    assert len(staging_audit.RESEARCH_INGEST_20260625_SPECS) == 4
    new_paths = {spec.path for spec in staging_audit.RESEARCH_INGEST_20260625_SPECS}
    default_paths = {spec.path for spec in staging_audit.STAGING_SPECS}
    assert new_paths.isdisjoint(default_paths)


def test_clean_staging_smiles_canonical_and_quarantine_routing() -> None:
    # Every SMILES in the clean Eox / feasibility staging files parses and is canonical.
    for rel, column in (
        ("data/lit_curation/eox_calibration_staging_20260625.csv", "smiles"),
        ("data/lit_curation/feasibility_labels_staging_20260625.csv", "smiles"),
    ):
        df = pd.read_csv(rel, keep_default_na=False)
        for smiles in df[column]:
            if smiles:
                assert Chem.MolFromSmiles(smiles, sanitize=True) is not None

    # No '[se]' or '*'-attachment or hand-constructed SMILES leaked into a clean file.
    for rel in (
        "data/lit_curation/eox_calibration_staging_20260625.csv",
        "data/lit_curation/feasibility_labels_staging_20260625.csv",
        "data/lit_curation/optical_anchors_staging_20260625.csv",
    ):
        df = pd.read_csv(rel, keep_default_na=False)
        smiles_col = "repeat_unit_smiles" if "repeat_unit_smiles" in df.columns else "smiles"
        for smiles in df[smiles_col]:
            assert "[se]" not in smiles.lower()
            assert "*" not in smiles

    # Quarantine files carry an explicit reason for every routed row.
    for rel in (
        "data/lit_curation/eox_calibration_quarantine_20260625.csv",
        "data/lit_curation/feasibility_quarantine_20260625.csv",
        "data/lit_curation/optical_anchors_quarantine_20260625.csv",
    ):
        df = pd.read_csv(rel, keep_default_na=False)
        assert not df.empty
        assert (df["quarantine_reason"].str.len() > 0).all()


def test_feasibility_dedup_review_has_expected_status_vocabulary() -> None:
    df = pd.read_csv(
        "data/lit_curation/feasibility_dedup_review_20260625.csv", keep_default_na=False
    )
    assert not df.empty
    assert set(df["match_status"]).issubset({"NEW", "DUPLICATE", "CONFLICT"})

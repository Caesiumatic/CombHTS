from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

from eps.curation import eox_rescue, staging_audit


def test_canonicalize_smiles_handles_valid_and_invalid_inputs() -> None:
    canonical, error = staging_audit.canonicalize_smiles("C1=CC=CS1")
    assert canonical == "c1ccsc1"
    assert error == ""

    canonical, error = staging_audit.canonicalize_smiles("not-a-smiles")
    assert canonical == ""
    assert "could not parse" in error


def test_audit_real_staging_writes_summary_and_issues(tmp_path: Path) -> None:
    summary_path = tmp_path / "summary.csv"
    issues_path = tmp_path / "issues.csv"

    summary, issues = staging_audit.audit_staging(Path("."), summary_path, issues_path)

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
    assert set(issues["classification"]).issubset(set(staging_audit.CLASSIFICATIONS))
    assert (issues["file"] == "data/lit_curation/solvent_esw_staging.csv").any()

    written_summary = pd.read_csv(summary_path)
    written_issues = pd.read_csv(issues_path)
    assert len(written_summary) == len(summary)
    assert len(written_issues) == len(issues)


def test_audit_script_entrypoint_writes_expected_outputs(tmp_path: Path) -> None:
    summary_path = tmp_path / "script_summary.csv"
    issues_path = tmp_path / "script_issues.csv"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_lit_curation_staging.py",
            "--repo-root",
            ".",
            "--summary",
            str(summary_path),
            "--issues",
            str(issues_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == ""
    assert completed.stderr == ""
    summary = pd.read_csv(summary_path)
    issues = pd.read_csv(issues_path)
    assert len(summary) == 5
    assert set(issues["classification"]).issubset(set(staging_audit.CLASSIFICATIONS))
    assert (issues["issue_type"] == "production_duplicate").any()


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


def test_eox_r11_r21_rescue_package_is_review_only_and_deterministic(tmp_path: Path) -> None:
    review_path = tmp_path / "review.csv"
    report_path = tmp_path / "report.md"

    result = eox_rescue.build_eox_r11_r21_review_package(
        repo_root=Path("."),
        review_path=review_path,
        report_path=report_path,
    )

    assert review_path.exists()
    assert report_path.exists()
    assert list(result.review.columns) == list(eox_rescue.REVIEW_COLUMNS)
    assert list(result.review["record_id"]) == [f"R{index}" for index in range(11, 22)]
    assert result.review["rdkit_parse_ok"].all()
    assert result.review["conversion_check_pass"].all()
    assert not result.review["duplicate_internal"].any()
    assert not result.review["duplicate_production_benchmark"].any()
    assert set(result.review["review_classification"]) == {"PROMOTE_NOW_CANDIDATE"}

    formula_by_record = dict(zip(result.review["record_id"], result.review["formula_match"], strict=True))
    assert all(formula_by_record[record_id] == "TRUE" for record_id in ["R14", "R15", "R16", "R17"])
    assert all(
        formula_by_record[record_id] == "NOT_PROVIDED"
        for record_id in ["R11", "R12", "R13", "R18", "R19", "R20", "R21"]
    )
    assert result.summary["promotable_rescue_onset_groups"] == 11
    assert result.summary["projected_union_onset_groups"] == 27
    assert result.summary["combined_experimental_combination_inventory"] == 50
    assert result.summary["no_candidate_promoted_to_benchmark"] is True
    assert "No candidate was promoted into `data/benchmark.csv`" in report_path.read_text(
        encoding="utf-8"
    )


def test_eox_r11_r21_rescue_refuses_production_csv_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="production CSV"):
        eox_rescue.build_eox_r11_r21_review_package(
            repo_root=Path("."),
            review_path=Path("data/benchmark.csv"),
            report_path=tmp_path / "report.md",
        )


def test_eox_r11_r21_rescue_flags_bad_conversion(tmp_path: Path) -> None:
    source = pd.read_csv(eox_rescue.DEFAULT_SOURCE_CANDIDATES_PATH, keep_default_na=False)
    source.loc[source["record_id"] == "R11", "potential_vs_AgAgCl_V"] = 1.006
    source_path = tmp_path / "bad_conversion.csv"
    source.to_csv(source_path, index=False)

    result = eox_rescue.build_eox_r11_r21_review_package(
        repo_root=Path("."),
        source_candidates_path=source_path,
        review_path=tmp_path / "review.csv",
        report_path=tmp_path / "report.md",
    )

    r11 = result.review.loc[result.review["record_id"] == "R11"].iloc[0]
    assert not bool(r11["conversion_check_pass"])
    assert r11["review_classification"] == "NEEDS_REFERENCE_CHECK"
    assert "expected E_AgAgCl" in r11["blocking_issue"]

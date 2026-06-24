from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from eps.curation import eox_master_audit

REPO_ROOT = Path(".")
BENCHMARK_PATH = Path("data/benchmark.csv")
R11_REVIEW_PATH = Path("data/lit_curation/eox_r11_r21_rescue_review.csv")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _external_manifest_fixture(tmp_path: Path) -> Path:
    rows = [
        ("camarada_2011_thiophene_oligomers.pdf", "10.1002/polb.22360", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("zhu_2017_thienothiophene_edot.pdf", "10.1007/s11426-016-0305-9", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("zhen_2014_oligofuran.pdf", "10.1039/C4RA00437J", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("yadav_2020_edos.pdf", "10.1039/D0RA01436B", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("bandera_2022_alkyne_dtp.pdf", "10.1039/D2RA03265A", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("liu_2016_thiadiazolopyridine.pdf", "10.1039/C6RA08528H", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        ("zhang_2016_pyridopyrazine_main.pdf", "10.3390/polym8100377", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        (
            "zhang_2016_pyridopyrazine_si.pdf",
            "10.3390/polym8100377",
            "supporting_information",
            "FOUND_LOCAL_EXTRACTED",
        ),
        ("kong_2017_quinoxaline_main.pdf", "10.3390/polym9120656", "primary_article", "FOUND_LOCAL_EXTRACTED"),
        (
            "kong_2017_quinoxaline_si.pdf",
            "10.3390/polym9120656",
            "supporting_information",
            "FOUND_LOCAL_EXTRACTED",
        ),
        ("molecules_2025_n_furfuryl_pyrrole.pdf", "10.3390/molecules30010042", "primary_article", "DOWNLOADED_OFFICIAL_EXTRACTED"),
        ("membranes_2021_electropolymerization.pdf", "10.3390/membranes11020125", "primary_article", "DOWNLOADED_OFFICIAL_EXTRACTED"),
        ("nano_2025_edot_candidate.pdf", "10.3390/nano15211643", "primary_article", "DOWNLOADED_OFFICIAL_EXTRACTED"),
        ("ijms_2023_candidate.pdf", "10.3390/ijms24032219", "primary_article", "DOWNLOADED_OFFICIAL_EXTRACTED"),
        ("nano_2024_candidate.pdf", "10.3390/nano14020180", "primary_article", "DOWNLOADED_OFFICIAL_EXTRACTED"),
        ("jelechem_2015_candidate.pdf", "10.1016/j.jelechem.2015.04.041", "primary_article", "MISSING_PAYWALLED"),
        ("thin_solid_films_2012_candidate.pdf", "10.1016/j.thinsolidfilms.2012.10.050", "primary_article", "MISSING_PAYWALLED"),
    ]
    frame = pd.DataFrame(
        [
            {
                "canonical_filename": filename,
                "sha256": hashlib.sha256(filename.encode()).hexdigest(),
                "size_bytes": "100",
                "identified_title": filename.removesuffix(".pdf"),
                "doi": doi,
                "source_type": source_type,
                "original_local_path": f"/redacted/{filename}",
                "acquisition_method": "TEST_FIXTURE",
                "status": status,
                "notes": "fixture",
            }
            for filename, doi, source_type, status in rows
        ],
        columns=eox_master_audit.EXTERNAL_MANIFEST_COLUMNS,
    )
    path = tmp_path / "MANIFEST.tsv"
    frame.to_csv(path, sep="\t", index=False)
    return path


def _build(tmp_path: Path, **overrides: object) -> eox_master_audit.EoxMasterAuditResult:
    defaults: dict[str, object] = {
        "repo_root": REPO_ROOT,
        "external_manifest_path": _external_manifest_fixture(tmp_path),
        "benchmark_path": BENCHMARK_PATH,
        "r11_r21_review_path": R11_REVIEW_PATH,
        "source_manifest_out": tmp_path / "source_manifest.csv",
        "master_evidence_out": tmp_path / "master_evidence.csv",
        "combination_summary_out": tmp_path / "combination_summary.csv",
        "production_change_proposal_out": tmp_path / "proposal.csv",
        "report_out": tmp_path / "report.md",
    }
    defaults.update(overrides)
    return eox_master_audit.build_eox_g1_2_master_audit(**defaults)


def _row(frame: pd.DataFrame, record_id: str) -> pd.Series:
    selected = frame.loc[frame["record_id"] == record_id]
    assert len(selected) == 1
    return selected.iloc[0]


def test_required_master_schema_rejects_missing_columns(tmp_path: Path) -> None:
    result = _build(tmp_path)
    broken = result.master_evidence.drop(columns=["source_id"])

    with pytest.raises(ValueError, match="missing required columns: source_id"):
        eox_master_audit.validate_master_evidence_schema(broken)


def test_master_enum_validation_rejects_unknown_class(tmp_path: Path) -> None:
    result = _build(tmp_path)
    broken = result.master_evidence.copy()
    broken.loc[0, "master_label_class"] = "HAND_WAVY"

    with pytest.raises(ValueError, match="master_label_class has invalid values"):
        eox_master_audit.validate_master_enums(broken)


def test_master_boolean_validation_is_strict(tmp_path: Path) -> None:
    result = _build(tmp_path)
    broken = result.master_evidence.copy()
    broken["rdkit_parse_ok"] = broken["rdkit_parse_ok"].astype(object)
    broken.loc[0, "rdkit_parse_ok"] = "yes"

    with pytest.raises(ValueError, match="rdkit_parse_ok must be a strict boolean"):
        eox_master_audit.validate_master_evidence_schema(broken)


def test_rdkit_canonicalization_is_deterministic() -> None:
    first = eox_master_audit.canonicalize_smiles("c1csc(-c2cccs2)c1")
    second = eox_master_audit.canonicalize_smiles(first["canonical_smiles"])

    assert first["rdkit_parse_ok"]
    assert first["canonical_smiles"] == second["canonical_smiles"]
    assert first["inchikey"] == second["inchikey"]


def test_experimental_measurement_id_is_deterministic() -> None:
    row = {
        "canonical_smiles": "c1ccsc1",
        "label_type": "monomer_oxidation_onset",
        "potential_original_V": "1.5",
        "reference_electrode_original": "Ag/AgCl",
        "solvent_system": "acetonitrile",
        "supporting_electrolyte": "0.1 M TBAPF6",
        "electrolyte_concentration_M": "0.1",
        "source_id": "SRC001",
        "source_locator": "Table 1",
        "measurement_method": "cyclic voltammetry",
    }

    assert eox_master_audit.experimental_measurement_id(row) == eox_master_audit.experimental_measurement_id(
        row
    )


def test_directive_combination_id_excludes_label_type() -> None:
    base = {
        "canonical_smiles": "c1ccsc1",
        "solvent_name": "acetonitrile",
        "supporting_electrolyte": "0.1 M TBAPF6",
    }

    onset = {**base, "label_type": "monomer_oxidation_onset"}
    peak = {**base, "label_type": "monomer_oxidation_peak"}
    assert eox_master_audit.directive_combination_id(onset) == eox_master_audit.directive_combination_id(
        peak
    )


def test_onset_and_peak_same_formulation_count_once_in_combination_summary(tmp_path: Path) -> None:
    result = _build(tmp_path)
    ftpf = result.master_evidence[result.master_evidence["exact_monomer_name"].str.startswith("FTPF")]

    assert len(ftpf) == 2
    assert ftpf["directive_combination_id"].nunique() == 1
    summary = result.combination_summary[
        result.combination_summary["directive_combination_id"] == ftpf.iloc[0]["directive_combination_id"]
    ].iloc[0]
    assert summary["measurement_count"] == 2
    assert summary["clean_cv_agagcl_onset_count"] == 1
    assert summary["clean_cv_agagcl_peak_count"] == 1


def test_onset_and_peak_keep_separate_model_groups(tmp_path: Path) -> None:
    result = _build(tmp_path)
    ftpf = result.master_evidence[result.master_evidence["exact_monomer_name"].str.startswith("FTPF")]

    assert ftpf["current_model_group_id"].nunique() == 2


def test_different_salts_create_different_directive_combinations(tmp_path: Path) -> None:
    result = _build(tmp_path)
    pf6 = _row(result.master_evidence, "EXT_EDOS_ACN_TBAPF6")
    bf4 = _row(result.master_evidence, "EXT_EDOS_ACN_TBABF4")

    assert pf6["directive_combination_id"] != bf4["directive_combination_id"]


def test_different_solvents_create_different_directive_combinations(tmp_path: Path) -> None:
    result = _build(tmp_path)
    acn = _row(result.master_evidence, "EXT_EDOS_ACN_TBAPF6")
    pc = _row(result.master_evidence, "EXT_EDOS_PC_TBAPF6")

    assert acn["directive_combination_id"] != pc["directive_combination_id"]


def test_concentration_alone_does_not_create_new_directive_combination() -> None:
    base = {
        "canonical_smiles": "c1ccsc1",
        "solvent_name": "acetonitrile",
        "supporting_electrolyte": "TBAPF6",
        "electrolyte_concentration_M": "0.1",
    }
    changed = {**base, "electrolyte_concentration_M": "0.2"}

    assert eox_master_audit.directive_combination_id(base) == eox_master_audit.directive_combination_id(
        changed
    )


def test_duplicate_source_reporting_does_not_double_count_measurements(tmp_path: Path) -> None:
    result = _build(tmp_path)
    master = result.master_evidence.copy()
    duplicate = master.iloc[[0]].copy()
    duplicate.loc[:, "record_id"] = "DUPLICATE_SOURCE_ROW"
    expanded = pd.concat([master, duplicate], ignore_index=True)

    summary = eox_master_audit.build_combination_summary(expanded)
    combo_id = master.iloc[0]["directive_combination_id"]
    original = result.combination_summary[
        result.combination_summary["directive_combination_id"] == combo_id
    ].iloc[0]
    expanded_row = summary[summary["directive_combination_id"] == combo_id].iloc[0]
    assert expanded_row["measurement_count"] == original["measurement_count"]


def test_mixed_solvent_rows_are_not_current_pipeline_comparable(tmp_path: Path) -> None:
    result = _build(tmp_path)
    r11 = _row(result.master_evidence, "R11")

    assert r11["master_label_class"] == "MIXED_SOLVENT_PARKED"
    assert not bool(r11["current_pipeline_comparable"])
    assert not bool(r11["directive_quantity_eligible"])


def test_unresolved_reference_rows_are_not_current_pipeline_comparable(tmp_path: Path) -> None:
    result = _build(tmp_path)
    edos = _row(result.master_evidence, "EXT_EDOS_ACN_TBAPF6")

    assert edos["master_label_class"] == "UNRESOLVED_REFERENCE"
    assert edos["reference_frame"] == "native_ag_plus"
    assert not bool(edos["current_pipeline_comparable"])


def test_source_conflicts_block_profile_eligibility(tmp_path: Path) -> None:
    result = _build(tmp_path)
    r14 = _row(result.master_evidence, "R14")

    assert r14["master_label_class"] == "SOURCE_CONFLICT"
    assert r14["disposition"] == "PARK"
    assert not bool(r14["onset_profile_eligible"])


def test_native_fc_rows_stay_separate_without_agagcl_conversion(tmp_path: Path) -> None:
    result = _build(tmp_path)
    native = _row(result.master_evidence, "EXT_ZHU_M4")

    assert native["reference_frame"] == "native_fc"
    assert native["master_label_class"] == "CLEAN_CV_ONSET_NATIVE_FC"
    assert native["potential_vs_AgAgCl_V"] == ""
    assert not bool(native["current_pipeline_comparable"])


def test_camarada_rows_are_classified_as_non_cv_steady_state(tmp_path: Path) -> None:
    result = _build(tmp_path)
    camarada = result.master_evidence[result.master_evidence["source_doi"] == "10.1002/polb.22360"]

    assert len(camarada) == 10
    assert set(camarada["master_label_class"]) == {"NON_CV_STEADY_STATE"}


def test_camarada_rows_are_not_directive_or_onset_profile_eligible(tmp_path: Path) -> None:
    result = _build(tmp_path)
    camarada = result.master_evidence[result.master_evidence["source_doi"] == "10.1002/polb.22360"]

    assert not camarada["directive_quantity_eligible"].any()
    assert not camarada["onset_profile_eligible"].any()
    assert camarada["production_correction_required"].all()


def test_zhang_and_kong_source_conflict_rows_remain_parked(tmp_path: Path) -> None:
    result = _build(tmp_path)
    conflicted = result.master_evidence[result.master_evidence["record_id"].isin([f"R{i}" for i in range(14, 22)])]

    assert len(conflicted) == 8
    assert set(conflicted["master_label_class"]) == {"SOURCE_CONFLICT"}
    assert set(conflicted["disposition"]) == {"PARK"}


def test_master_audit_refuses_production_csv_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="production CSV"):
        _build(
            tmp_path,
            source_manifest_out=None,
            master_evidence_out=Path("data/benchmark.csv"),
            combination_summary_out=None,
            production_change_proposal_out=None,
            report_out=None,
        )


def test_master_build_does_not_mutate_production_benchmark(tmp_path: Path) -> None:
    before = _sha256(BENCHMARK_PATH)

    _build(tmp_path)

    assert _sha256(BENCHMARK_PATH) == before


def test_master_build_is_byte_stable(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = _build(first_dir)
    second = _build(second_dir)

    for first_path, second_path in zip(first.written_paths, second.written_paths, strict=True):
        assert first_path.name == second_path.name
        assert first_path.read_bytes() == second_path.read_bytes()


def test_report_counts_match_generated_csv_counts(tmp_path: Path) -> None:
    result = _build(tmp_path)
    summary = pd.read_csv(tmp_path / "combination_summary.csv", keep_default_na=False)
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    eligible_count = int(summary["directive_quantity_eligible"].map(lambda value: str(value) == "True").sum())

    assert eligible_count == result.summary["directive_quantity_eligible_combinations"]
    assert f"Directive-eligible combinations: {eligible_count}" in report

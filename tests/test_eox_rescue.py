from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

from eps.curation import eox_rescue
from eps.validation import benchmark as benchmark_validation

REPO_ROOT = Path(".")
SOURCE_PATH = Path("data/lit_curation/eox_r11_r21_source_candidates.csv")
BENCHMARK_PATH = Path("data/benchmark.csv")


def _source_fixture() -> pd.DataFrame:
    return pd.read_csv(SOURCE_PATH, keep_default_na=False)


def _benchmark_fixture() -> pd.DataFrame:
    return pd.read_csv(BENCHMARK_PATH, keep_default_na=False)


def _write_source(source: pd.DataFrame, path: Path) -> Path:
    source.to_csv(path, index=False)
    return path


def _build_from_source(source: pd.DataFrame, tmp_path: Path) -> eox_rescue.EoxRescueResult:
    source_path = _write_source(source, tmp_path / "source.csv")
    return eox_rescue.build_eox_r11_r21_review_package(
        repo_root=REPO_ROOT,
        source_candidates_path=source_path,
        review_path=tmp_path / "review.csv",
        report_path=tmp_path / "report.md",
    )


def _row_by_record(review: pd.DataFrame, record_id: str) -> pd.Series:
    return review.loc[review["record_id"] == record_id].iloc[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_required_source_schema_rejects_missing_columns(tmp_path: Path) -> None:
    source = _source_fixture().drop(columns=["publisher_url"])
    source_path = _write_source(source, tmp_path / "missing_column.csv")

    with pytest.raises(ValueError, match="missing required columns: publisher_url"):
        eox_rescue.load_source_candidates(source_path)


@pytest.mark.parametrize(
    ("mutation", "observed_fragment"),
    [
        ("missing", "R11, R12, R13"),
        ("additional", "R99"),
        ("duplicate", "R11, R11"),
    ],
)
def test_source_scope_must_be_exactly_r11_through_r21(
    tmp_path: Path,
    mutation: str,
    observed_fragment: str,
) -> None:
    source = _source_fixture()
    if mutation == "missing":
        source = source.loc[source["record_id"] != "R21"].copy()
    elif mutation == "additional":
        extra = source.iloc[[0]].copy()
        extra.loc[:, "record_id"] = "R99"
        source = pd.concat([source, extra], ignore_index=True)
    elif mutation == "duplicate":
        source.loc[source["record_id"] == "R12", "record_id"] = "R11"
    source_path = _write_source(source, tmp_path / f"{mutation}.csv")

    with pytest.raises(ValueError, match="must contain exactly the expected records") as excinfo:
        eox_rescue.load_source_candidates(source_path)

    assert observed_fragment in str(excinfo.value)


def test_committed_candidate_smiles_parse_and_canonicalize_deterministically() -> None:
    source = _source_fixture()

    for row in source.to_dict(orient="records"):
        mol = Chem.MolFromSmiles(row["input_smiles"], sanitize=True)
        assert mol is not None, row["record_id"]
        first = Chem.MolToSmiles(mol, canonical=True)
        second = Chem.MolToSmiles(Chem.MolFromSmiles(first, sanitize=True), canonical=True)
        assert first == second


@pytest.mark.parametrize(
    ("smiles", "error_fragment"),
    [
        ("", "blank SMILES"),
        ("not-a-smiles", "RDKit could not parse SMILES"),
    ],
)
def test_blank_or_invalid_smiles_need_structure_check(
    tmp_path: Path,
    smiles: str,
    error_fragment: str,
) -> None:
    source = _source_fixture()
    source.loc[source["record_id"] == "R11", "input_smiles"] = smiles

    result = _build_from_source(source, tmp_path)

    r11 = _row_by_record(result.review, "R11")
    assert not bool(r11["rdkit_parse_ok"])
    assert r11["review_classification"] == "NEEDS_STRUCTURE_CHECK"
    assert r11["review_classification"] != "PROMOTE_NOW_CANDIDATE"
    assert error_fragment in r11["blocking_issue"]


def test_formula_mismatch_needs_structure_check(tmp_path: Path) -> None:
    source = _source_fixture()
    source.loc[source["record_id"] == "R14", "source_formula"] = "C1H1"

    result = _build_from_source(source, tmp_path)

    r14 = _row_by_record(result.review, "R14")
    assert r14["formula_match"] == "FALSE"
    assert r14["review_classification"] == "NEEDS_STRUCTURE_CHECK"
    assert "does not match source formula" in r14["blocking_issue"]


def test_r11_r13_conversion_is_original_plus_0065_v() -> None:
    source = _source_fixture()
    early = source[source["record_id"].isin(["R11", "R12", "R13"])]

    for row in early.to_dict(orient="records"):
        expected = float(row["potential_original_V"]) + 0.065
        assert float(row["potential_vs_AgAgCl_V"]) == pytest.approx(expected)
        assert eox_rescue._conversion_check(row) == (True, "")


def test_r14_r21_conversion_is_original_plus_0075_v() -> None:
    source = _source_fixture()
    later = source[source["record_id"].isin([f"R{index}" for index in range(14, 22)])]

    for row in later.to_dict(orient="records"):
        expected = float(row["potential_original_V"]) + 0.075
        assert float(row["potential_vs_AgAgCl_V"]) == pytest.approx(expected)
        assert eox_rescue._conversion_check(row) == (True, "")


def test_bad_conversion_needs_reference_check(tmp_path: Path) -> None:
    source = _source_fixture()
    source.loc[source["record_id"] == "R11", "potential_vs_AgAgCl_V"] = 1.006

    result = _build_from_source(source, tmp_path)

    r11 = _row_by_record(result.review, "R11")
    assert not bool(r11["conversion_check_pass"])
    assert r11["review_classification"] == "NEEDS_REFERENCE_CHECK"
    assert "expected E_AgAgCl" in r11["blocking_issue"]


def test_missing_durable_provenance_needs_provenance_check(tmp_path: Path) -> None:
    source = _source_fixture()
    source.loc[source["record_id"] == "R14", ["source_doi", "publisher_url"]] = ""

    result = _build_from_source(source, tmp_path)

    r14 = _row_by_record(result.review, "R14")
    assert r14["full_citation"]
    assert r14["review_classification"] == "NEEDS_PROVENANCE_CHECK"
    assert "source DOI or durable publisher URL" in r14["blocking_issue"]


def test_no_doi_with_durable_url_remains_eligible(tmp_path: Path) -> None:
    source = _source_fixture()
    r11_source = source.loc[source["record_id"] == "R11"].iloc[0]
    assert r11_source["source_doi"] == ""
    assert r11_source["publisher_url"]

    result = _build_from_source(source, tmp_path)

    r11 = _row_by_record(result.review, "R11")
    assert r11["review_classification"] == "PROMOTE_NOW_CANDIDATE"
    assert "No DOI found" in r11["review_notes"]


def test_internal_duplicate_is_flagged_and_rejected(tmp_path: Path) -> None:
    source = _source_fixture()
    r11 = source.loc[source["record_id"] == "R11"].iloc[0]
    duplicate_fields = [
        "input_smiles",
        "label_type",
        "full_citation",
        "electrochemistry_source_locator",
        "solvent",
        "supporting_electrolyte",
        "electrolyte_concentration_M",
    ]
    for field in duplicate_fields:
        source.loc[source["record_id"] == "R12", field] = r11[field]

    result = _build_from_source(source, tmp_path)

    duplicated = result.review[result.review["record_id"].isin(["R11", "R12"])]
    assert duplicated["duplicate_internal"].all()
    assert set(duplicated["review_classification"]) == {"REJECT"}


def test_onset_peak_rows_do_not_collapse_into_one_independent_group(tmp_path: Path) -> None:
    source = _source_fixture()
    r11 = source.loc[source["record_id"] == "R11"].iloc[0]
    matching_fields = [
        "input_smiles",
        "source_doi",
        "full_citation",
        "electrochemistry_source_locator",
        "solvent",
        "supporting_electrolyte",
        "electrolyte_concentration_M",
    ]
    for field in matching_fields:
        source.loc[source["record_id"] == "R12", field] = r11[field]
    source.loc[source["record_id"] == "R12", "label_type"] = "monomer_oxidation_peak"

    result = _build_from_source(source, tmp_path)

    r11_review = _row_by_record(result.review, "R11")
    r12_review = _row_by_record(result.review, "R12")
    assert r11_review["independent_group_id"] != r12_review["independent_group_id"]
    assert not bool(r11_review["duplicate_internal"])
    assert not bool(r12_review["duplicate_internal"])


def test_production_duplicate_uses_actual_benchmark_collapse_key(tmp_path: Path) -> None:
    source = _source_fixture()
    benchmark = _benchmark_fixture()
    production_row = benchmark.iloc[0]
    source.loc[
        source["record_id"] == "R11",
        ["input_smiles", "solvent", "label_type"],
    ] = [
        production_row["monomer_smiles"],
        production_row["solvent_name"],
        production_row["label_type"],
    ]

    result = _build_from_source(source, tmp_path)

    r11 = _row_by_record(result.review, "R11")
    monomer = benchmark_validation._benchmark_monomer(production_row.to_dict())
    benchmark_key = benchmark_validation._benchmark_group_id(production_row.to_dict(), monomer)
    rescue_key = eox_rescue._validation_group_key(
        canonical_smiles=r11["canonical_smiles"],
        solvent=r11["solvent"],
        label_type=r11["label_type"],
    )
    assert rescue_key == benchmark_key.lower()
    assert bool(r11["duplicate_production_benchmark"])
    assert r11["review_classification"] == "DUPLICATE_PRODUCTION"


def test_counting_semantics_preserve_benchmark_onset_peak_separation(tmp_path: Path) -> None:
    benchmark = _benchmark_fixture()
    benchmark_group_ids = set()
    for row in benchmark.to_dict(orient="records"):
        monomer = benchmark_validation._benchmark_monomer(row)
        benchmark_group_ids.add(benchmark_validation._benchmark_group_id(row, monomer).lower())

    assert eox_rescue._production_validation_groups(benchmark) == benchmark_group_ids

    result = _build_from_source(_source_fixture(), tmp_path)

    assert result.summary["existing_production_onset_groups"] == 16
    assert result.summary["existing_production_peak_groups"] == 23
    assert result.summary["promotable_rescue_onset_groups"] == 11
    assert result.summary["promotable_rescue_peak_groups"] == 0
    assert result.summary["projected_union_onset_groups"] == 27
    assert result.summary["projected_union_peak_groups"] == 23


def test_review_package_is_review_only_and_deterministic(tmp_path: Path) -> None:
    source_path = _write_source(_source_fixture(), tmp_path / "source.csv")
    review_path_a = tmp_path / "review_a.csv"
    report_path_a = tmp_path / "report_a.md"
    review_path_b = tmp_path / "review_b.csv"
    report_path_b = tmp_path / "report_b.md"

    result = eox_rescue.build_eox_r11_r21_review_package(
        repo_root=REPO_ROOT,
        source_candidates_path=source_path,
        review_path=review_path_a,
        report_path=report_path_a,
    )
    eox_rescue.build_eox_r11_r21_review_package(
        repo_root=REPO_ROOT,
        source_candidates_path=source_path,
        review_path=review_path_b,
        report_path=report_path_b,
    )

    assert review_path_a.read_bytes() == review_path_b.read_bytes()
    assert report_path_a.read_bytes() == report_path_b.read_bytes()
    assert list(result.review.columns) == list(eox_rescue.REVIEW_COLUMNS)
    assert list(result.review["record_id"]) == [f"R{index}" for index in range(11, 22)]
    assert result.review["rdkit_parse_ok"].all()
    assert result.review["conversion_check_pass"].all()
    assert not result.review["duplicate_internal"].any()
    assert not result.review["duplicate_production_benchmark"].any()
    assert set(result.review["review_classification"]) == {"PROMOTE_NOW_CANDIDATE"}

    formula_by_record = dict(
        zip(result.review["record_id"], result.review["formula_match"], strict=True)
    )
    assert all(formula_by_record[record_id] == "TRUE" for record_id in ["R14", "R15", "R16", "R17"])
    assert all(
        formula_by_record[record_id] == "NOT_PROVIDED"
        for record_id in ["R11", "R12", "R13", "R18", "R19", "R20", "R21"]
    )
    assert result.summary["combined_experimental_combination_inventory"] == 50
    assert result.summary["no_candidate_promoted_to_benchmark"] is True
    assert "No candidate was promoted into `data/benchmark.csv`" in report_path_a.read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("production_path", [Path("data/benchmark.csv"), Path("data/monomers.csv")])
def test_review_package_refuses_production_csv_output(
    tmp_path: Path,
    production_path: Path,
) -> None:
    with pytest.raises(ValueError, match="production CSV"):
        eox_rescue.build_eox_r11_r21_review_package(
            repo_root=REPO_ROOT,
            review_path=production_path,
            report_path=tmp_path / "report.md",
        )


def test_review_build_does_not_mutate_production_benchmark(tmp_path: Path) -> None:
    before = _sha256(BENCHMARK_PATH)

    eox_rescue.build_eox_r11_r21_review_package(
        repo_root=REPO_ROOT,
        review_path=tmp_path / "review.csv",
        report_path=tmp_path / "report.md",
    )

    assert _sha256(BENCHMARK_PATH) == before

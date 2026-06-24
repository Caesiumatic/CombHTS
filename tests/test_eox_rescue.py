from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from eps.curation import eox_rescue
from eps.validation import benchmark as benchmark_validation

REPO_ROOT = Path(".")
SOURCE_PATH = Path("data/lit_curation/eox_r11_r21_source_candidates.csv")
BENCHMARK_PATH = Path("data/benchmark.csv")

CORRECTED_SMILES = {
    "R12": "Cc1csc(-c2cnc(-c3cc(C)cs3)c3nsnc23)c1",
    "R13": "CCCCc1csc(-c2cnc(-c3cc(CCCC)cs3)c3nsnc23)c1",
    "R14": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4cccs4)cnc(-c4cccs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R15": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(CCCC)cs4)cnc(-c4cc(CCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R16": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(OCCCCCC)cs4)cnc(-c4cc(OCCCCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R21": "COc1ccc(-c2nc3c(-c4cccs4)ccc(-c4cccs4)c3nc2-c2ccc(OC)cc2)cc1",
}
CORRECTED_CANONICAL_SMILES = {
    record_id: Chem.MolToSmiles(Chem.MolFromSmiles(smiles), canonical=True)
    for record_id, smiles in CORRECTED_SMILES.items()
}
CORRECTED_FORMULAE = {
    "R12": "C15H11N3S3",
    "R13": "C21H23N3S3",
    "R14": "C47H57N3O2S2",
    "R15": "C55H73N3O2S2",
    "R16": "C59H81N3O4S2",
    "R21": "C30H22N2O2S2",
}
OLD_INCORRECT_SMILES = {
    "R12": "Cc1cc(-c2cnc(-c3csc(C)c3)c3nsnc23)cs1",
    "R13": "CCCCc1cc(-c2cnc(-c3csc(CCCC)c3)c3nsnc23)cs1",
    "R14": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4ccsc4)cnc(-c4ccsc4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R15": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(CCCC)c4)cnc(-c4csc(CCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R16": "CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(OCCCCCC)c4)cnc(-c4csc(OCCCCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1",
    "R21": "COc1ccc(-c2nc3c(-c4ccsc4)ccc(-c4ccsc4)c3nc2-c2ccc(OC)cc2)cc1",
}


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


def _terminal_thiophene_profiles(smiles: str) -> list[dict[str, list[str] | list[int]]]:
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None
    profiles: list[dict[str, list[str] | list[int]]] = []
    for raw_ring in Chem.GetSymmSSSR(mol):
        ring = tuple(int(index) for index in raw_ring)
        atoms = [mol.GetAtomWithIdx(index) for index in ring]
        symbols = [atom.GetSymbol() for atom in atoms]
        if len(ring) != 5 or symbols.count("S") != 1 or symbols.count("C") != 4:
            continue
        sulfur_index = next(index for index in ring if mol.GetAtomWithIdx(index).GetSymbol() == "S")
        core_distances: list[int] = []
        sidechain_distances: list[int] = []
        sidechain_symbols: list[str] = []
        for atom_index in ring:
            atom = mol.GetAtomWithIdx(atom_index)
            if atom.GetSymbol() != "C":
                continue
            for neighbor in atom.GetNeighbors():
                if neighbor.GetIdx() in ring:
                    continue
                distance_to_sulfur = len(Chem.GetShortestPath(mol, atom_index, sulfur_index)) - 1
                if neighbor.GetIsAromatic():
                    core_distances.append(distance_to_sulfur)
                else:
                    sidechain_distances.append(distance_to_sulfur)
                    sidechain_symbols.append(neighbor.GetSymbol())
        if core_distances:
            profiles.append(
                {
                    "core_distances": core_distances,
                    "sidechain_distances": sidechain_distances,
                    "sidechain_symbols": sidechain_symbols,
                }
            )
    return profiles


def test_required_source_schema_rejects_missing_columns(tmp_path: Path) -> None:
    source = _source_fixture().drop(columns=["publisher_url"])
    source_path = _write_source(source, tmp_path / "missing_column.csv")

    with pytest.raises(ValueError, match="missing required columns: publisher_url"):
        eox_rescue.load_source_candidates(source_path)


def test_source_conflict_schema_rejects_missing_columns(tmp_path: Path) -> None:
    source = _source_fixture().drop(columns=["source_conflict_details"])
    source_path = _write_source(source, tmp_path / "missing_conflict_column.csv")

    with pytest.raises(ValueError, match="missing required columns: source_conflict_details"):
        eox_rescue.load_source_candidates(source_path)


def test_source_conflict_schema_rejects_invalid_boolean_values(tmp_path: Path) -> None:
    source = _source_fixture()
    source["reference_source_conflict"] = source["reference_source_conflict"].astype(object)
    source.loc[source["record_id"] == "R14", "reference_source_conflict"] = "yes"
    source_path = _write_source(source, tmp_path / "invalid_bool.csv")

    with pytest.raises(ValueError, match="reference_source_conflict must be a strict boolean"):
        eox_rescue.load_source_candidates(source_path)


def test_source_conflict_schema_rejects_true_flag_with_blank_details(tmp_path: Path) -> None:
    source = _source_fixture()
    source.loc[source["record_id"] == "R14", "source_conflict_details"] = ""
    source_path = _write_source(source, tmp_path / "blank_conflict_details.csv")

    with pytest.raises(ValueError, match="source conflict flag set but blank source_conflict_details"):
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


@pytest.mark.parametrize("record_id", sorted(CORRECTED_SMILES))
def test_corrected_candidate_smiles_and_canonical_connectivity(record_id: str) -> None:
    source = _source_fixture()
    row = source.loc[source["record_id"] == record_id].iloc[0]

    assert row["input_smiles"] == CORRECTED_SMILES[record_id]
    mol = Chem.MolFromSmiles(row["input_smiles"], sanitize=True)
    assert mol is not None
    assert Chem.MolToSmiles(mol, canonical=True) == CORRECTED_CANONICAL_SMILES[record_id]


def test_old_incorrect_smiles_are_absent_from_source_candidates() -> None:
    source_text = SOURCE_PATH.read_text(encoding="utf-8")

    for record_id, smiles in OLD_INCORRECT_SMILES.items():
        assert smiles not in source_text, record_id


@pytest.mark.parametrize("record_id", sorted(CORRECTED_FORMULAE))
def test_corrected_candidate_formulae(record_id: str) -> None:
    mol = Chem.MolFromSmiles(CORRECTED_SMILES[record_id], sanitize=True)
    assert mol is not None
    assert rdMolDescriptors.CalcMolFormula(mol) == CORRECTED_FORMULAE[record_id]


@pytest.mark.parametrize("record_id", sorted(CORRECTED_SMILES))
def test_corrected_thiophene_core_attachment_is_alpha_to_sulfur(record_id: str) -> None:
    profiles = _terminal_thiophene_profiles(CORRECTED_SMILES[record_id])

    assert len(profiles) == 2
    for profile in profiles:
        assert profile["core_distances"] == [1]


@pytest.mark.parametrize("record_id", ["R12", "R13"])
def test_r12_r13_are_4_alkylthiophen_2_yl_not_2_alkylthiophen_4_yl(record_id: str) -> None:
    profiles = _terminal_thiophene_profiles(CORRECTED_SMILES[record_id])

    assert len(profiles) == 2
    for profile in profiles:
        assert profile["sidechain_symbols"] == ["C"]
        assert profile["sidechain_distances"] == [2]


@pytest.mark.parametrize("record_id", ["R14", "R21"])
def test_r14_r21_donors_are_unsubstituted_thiophen_2_yl(record_id: str) -> None:
    profiles = _terminal_thiophene_profiles(CORRECTED_SMILES[record_id])

    assert len(profiles) == 2
    for profile in profiles:
        assert profile["sidechain_symbols"] == []
        assert profile["sidechain_distances"] == []


def test_r15_donor_is_4_butylthiophen_2_yl() -> None:
    profiles = _terminal_thiophene_profiles(CORRECTED_SMILES["R15"])

    assert len(profiles) == 2
    for profile in profiles:
        assert profile["sidechain_symbols"] == ["C"]
        assert profile["sidechain_distances"] == [2]


def test_r16_donor_is_4_hexyloxythiophen_2_yl() -> None:
    profiles = _terminal_thiophene_profiles(CORRECTED_SMILES["R16"])

    assert len(profiles) == 2
    for profile in profiles:
        assert profile["sidechain_symbols"] == ["O"]
        assert profile["sidechain_distances"] == [2]


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
    assert result.summary["promotable_rescue_onset_groups"] == 3
    assert result.summary["promotable_rescue_peak_groups"] == 0
    assert result.summary["projected_union_onset_groups"] == 19
    assert result.summary["projected_union_peak_groups"] == 23
    assert result.summary["combined_experimental_combination_inventory"] == 42
    assert result.summary["reference_source_conflict_rows"] == 8
    assert result.summary["condition_source_conflict_rows"] == 4


def test_source_conflicts_are_fail_closed_by_record_group(tmp_path: Path) -> None:
    result = _build_from_source(_source_fixture(), tmp_path)

    for record_id in ["R11", "R12", "R13"]:
        row = _row_by_record(result.review, record_id)
        assert row["research_status"] == "RESEARCH_READY_FOR_RDKIT_AUDIT"
        assert not bool(row["reference_source_conflict"])
        assert not bool(row["condition_source_conflict"])
        assert row["source_conflict_details"] == ""
        assert row["review_classification"] == "PROMOTE_NOW_CANDIDATE"

    for record_id in ["R14", "R15", "R16", "R17"]:
        row = _row_by_record(result.review, record_id)
        assert row["research_status"] == "SOURCE_VALUE_CONFLICT"
        assert bool(row["reference_source_conflict"])
        assert not bool(row["condition_source_conflict"])
        assert row["review_classification"] == "NEEDS_REFERENCE_CHECK"
        assert "Section 2.3 reports Ag wire = 0.03 V vs SCE" in row["source_conflict_details"]
        assert "source reference conflict unresolved" in row["blocking_issue"]

    for record_id in ["R18", "R19", "R20", "R21"]:
        row = _row_by_record(result.review, record_id)
        assert row["research_status"] == "SOURCE_VALUE_CONFLICT"
        assert bool(row["reference_source_conflict"])
        assert bool(row["condition_source_conflict"])
        assert row["review_classification"] == "NEEDS_REFERENCE_CHECK"
        assert "Table 1 footnote (b) uses +0.02 V" in row["source_conflict_details"]
        assert "Section 3.1 reports 0.1 M TBAPF6" in row["source_conflict_details"]
        assert "source reference conflict unresolved" in row["blocking_issue"]
        assert "source condition conflict unresolved" in row["blocking_issue"]


def test_passing_conversion_does_not_override_reference_source_conflict(tmp_path: Path) -> None:
    result = _build_from_source(_source_fixture(), tmp_path)
    r14 = _row_by_record(result.review, "R14")

    assert bool(r14["conversion_check_pass"])
    assert r14["review_classification"] == "NEEDS_REFERENCE_CHECK"
    assert r14["review_classification"] != "PROMOTE_NOW_CANDIDATE"
    assert "Source-internal conflict is unresolved" in r14["review_notes"]


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
    assert result.summary["reference_source_conflict_rows"] == 8
    assert result.summary["condition_source_conflict_rows"] == 4
    assert result.review["review_classification"].value_counts().to_dict() == {
        "NEEDS_REFERENCE_CHECK": 8,
        "PROMOTE_NOW_CANDIDATE": 3,
    }

    formula_by_record = dict(
        zip(result.review["record_id"], result.review["formula_match"], strict=True)
    )
    assert all(formula_by_record[record_id] == "TRUE" for record_id in ["R14", "R15", "R16", "R17"])
    assert all(
        formula_by_record[record_id] == "NOT_PROVIDED"
        for record_id in ["R11", "R12", "R13", "R18", "R19", "R20", "R21"]
    )
    assert result.summary["promotable_rescue_onset_groups"] == 3
    assert result.summary["projected_union_onset_groups"] == 19
    assert result.summary["projected_union_peak_groups"] == 23
    assert result.summary["combined_experimental_combination_inventory"] == 42
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

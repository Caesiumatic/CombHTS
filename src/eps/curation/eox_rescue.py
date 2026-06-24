"""Review-only Eox staging rescue for R11-R21 literature candidates."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_CANDIDATES_PATH = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_r11_r21_source_candidates.csv"
)
DEFAULT_REVIEW_PATH = PROJECT_ROOT / "data" / "lit_curation" / "eox_r11_r21_rescue_review.csv"
DEFAULT_REPORT_PATH = (
    PROJECT_ROOT / "docs" / "research" / "eox_r11_r21_staging_rescue_20260624.md"
)
DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "benchmark.csv"
DEFAULT_MONOMERS_PATH = PROJECT_ROOT / "data" / "monomers.csv"

SCE_TO_AGAGCL_V = 0.045
"""Source-approved SCE to Ag/AgCl additive shift in V for this review audit."""

CONVERSION_TOLERANCE_V = 1e-6
"""Strict numeric tolerance in V for the source-transcribed Ag/AgCl conversion."""

EXPECTED_RECORD_IDS = tuple(f"R{index}" for index in range(11, 22))

REVIEW_CLASSIFICATIONS = (
    "PROMOTE_NOW_CANDIDATE",
    "NEEDS_STRUCTURE_CHECK",
    "NEEDS_PROVENANCE_CHECK",
    "NEEDS_REFERENCE_CHECK",
    "NEEDS_CONDITION_CHECK",
    "DUPLICATE_PRODUCTION",
    "REJECT",
)

SOURCE_COLUMNS = (
    "record_id",
    "source_compound_label",
    "exact_monomer_name",
    "input_smiles",
    "monomer_class",
    "structure_source_locator",
    "source_formula",
    "source_hrms_or_ms",
    "analytical_evidence_locator",
    "structure_transcription_confidence",
    "label_type",
    "source_label_type_text",
    "potential_original_V",
    "reference_electrode_original",
    "reference_calibration_text",
    "reference_offset_vs_SCE_V",
    "conversion_equation",
    "potential_vs_AgAgCl_V",
    "solvent",
    "solvent_composition",
    "supporting_electrolyte",
    "electrolyte_concentration_M",
    "monomer_concentration_M",
    "working_electrode",
    "scan_rate_mV_s",
    "source_doi",
    "doi_status",
    "publisher_url",
    "full_citation",
    "electrochemistry_source_locator",
    "research_status",
    "research_notes",
    "reference_source_conflict",
    "condition_source_conflict",
    "source_conflict_details",
)

REVIEW_COLUMNS = (
    "record_id",
    "source_compound_label",
    "exact_monomer_name",
    "input_smiles",
    "canonical_smiles",
    "inchikey",
    "calculated_formula",
    "source_formula",
    "formula_match",
    "monomer_class",
    "label_type",
    "potential_original_V",
    "reference_electrode_original",
    "reference_calibration_text",
    "conversion_equation",
    "potential_vs_AgAgCl_V",
    "conversion_check_pass",
    "solvent",
    "solvent_composition",
    "supporting_electrolyte",
    "electrolyte_concentration_M",
    "monomer_concentration_M",
    "working_electrode",
    "scan_rate_mV_s",
    "source_doi",
    "doi_status",
    "full_citation",
    "structure_source_locator",
    "electrochemistry_source_locator",
    "structure_transcription_confidence",
    "rdkit_parse_ok",
    "duplicate_internal",
    "duplicate_production_benchmark",
    "independent_group_id",
    "research_status",
    "reference_source_conflict",
    "condition_source_conflict",
    "source_conflict_details",
    "review_classification",
    "blocking_issue",
    "review_notes",
)

SOURCE_CONFLICT_BOOLEAN_COLUMNS = ("reference_source_conflict", "condition_source_conflict")

_FORMULA_RE = re.compile(r"([A-Z][a-z]?)(\d*)")


@dataclass(frozen=True)
class EoxRescueResult:
    """In-memory and on-disk result for the R11-R21 review-only rescue package."""

    review: pd.DataFrame
    summary: dict[str, Any]
    source_candidates_path: Path
    review_path: Path | None
    report_path: Path | None


def build_eox_r11_r21_review_package(
    *,
    repo_root: str | Path = PROJECT_ROOT,
    source_candidates_path: str | Path = DEFAULT_SOURCE_CANDIDATES_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    monomers_path: str | Path = DEFAULT_MONOMERS_PATH,
    review_path: str | Path | None = DEFAULT_REVIEW_PATH,
    report_path: str | Path | None = DEFAULT_REPORT_PATH,
    external_inputs: Iterable[str | Path] = (),
) -> EoxRescueResult:
    """Build deterministic review-only R11-R21 staging outputs.

    Args:
        repo_root: Repository root used for production-output guardrails and git SHA lookup.
        source_candidates_path: Normalized CSV transcribed from the targeted research packet.
        benchmark_path: Production benchmark CSV used only for duplicate/group counting.
        monomers_path: Production monomer library used only for current-library counts.
        review_path: Optional review CSV destination under ``data/lit_curation``.
        report_path: Optional Markdown report destination under ``docs/research``.
        external_inputs: Optional external evidence files to hash in the report.

    Returns:
        Review dataframe, summary metrics, and written artifact paths.
    """

    root = Path(repo_root).resolve()
    source_path = Path(source_candidates_path)
    source = load_source_candidates(source_path)
    benchmark = pd.read_csv(benchmark_path, keep_default_na=False)
    monomers = pd.read_csv(monomers_path, keep_default_na=False)

    review = build_rescue_review(source, benchmark)
    summary = summarize_rescue_review(
        review=review,
        benchmark=benchmark,
        monomers=monomers,
        repo_root=root,
        source_candidates_path=source_path,
        external_inputs=tuple(Path(path) for path in external_inputs),
    )

    written_review: Path | None = None
    if review_path is not None:
        written_review = Path(review_path)
        _refuse_production_csv_output(written_review, root)
        written_review.parent.mkdir(parents=True, exist_ok=True)
        review.to_csv(written_review, index=False)

    written_report: Path | None = None
    if report_path is not None:
        written_report = Path(report_path)
        written_report.parent.mkdir(parents=True, exist_ok=True)
        written_report.write_text(_render_report(review, summary), encoding="utf-8")

    return EoxRescueResult(
        review=review,
        summary=summary,
        source_candidates_path=source_path,
        review_path=written_review,
        report_path=written_report,
    )


def load_source_candidates(path: str | Path) -> pd.DataFrame:
    """Load and validate the normalized R11-R21 source-candidate CSV."""

    frame = pd.read_csv(path, keep_default_na=False)
    missing = [column for column in SOURCE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
    record_ids = tuple(str(value).strip() for value in frame["record_id"])
    if set(record_ids) != set(EXPECTED_RECORD_IDS) or len(record_ids) != len(EXPECTED_RECORD_IDS):
        expected = ", ".join(EXPECTED_RECORD_IDS)
        observed = ", ".join(record_ids)
        raise ValueError(
            "R11-R21 source candidates must contain exactly the expected records; "
            f"expected {expected}; observed {observed}"
        )
    _validate_source_conflict_fields(frame, path)
    return frame.loc[:, SOURCE_COLUMNS].copy()


def build_rescue_review(source: pd.DataFrame, benchmark: pd.DataFrame) -> pd.DataFrame:
    """Canonicalize, classify, and duplicate-check normalized source candidates."""

    production_groups = _production_validation_groups(benchmark)
    base_rows: list[dict[str, Any]] = []
    for row in source.to_dict(orient="records"):
        rdkit = _rdkit_audit(_clean(row["input_smiles"]))
        conversion_ok, conversion_note = _conversion_check(row)
        formula_match = _formula_match(rdkit["formula"], _clean(row["source_formula"]))
        independent_group_id = _independent_group_id(row, rdkit["canonical_smiles"])
        production_key = _validation_group_key(
            canonical_smiles=rdkit["canonical_smiles"],
            solvent=_clean(row["solvent"]),
            label_type=_clean(row["label_type"]),
        )
        base_rows.append(
            {
                "record_id": _clean(row["record_id"]),
                "source_compound_label": _clean(row["source_compound_label"]),
                "exact_monomer_name": _clean(row["exact_monomer_name"]),
                "input_smiles": _clean(row["input_smiles"]),
                "canonical_smiles": rdkit["canonical_smiles"],
                "inchikey": rdkit["inchikey"],
                "calculated_formula": rdkit["formula"],
                "source_formula": _clean(row["source_formula"]),
                "formula_match": formula_match,
                "monomer_class": _clean(row["monomer_class"]),
                "label_type": _clean(row["label_type"]),
                "potential_original_V": _as_number_or_blank(row["potential_original_V"]),
                "reference_electrode_original": _clean(row["reference_electrode_original"]),
                "reference_calibration_text": _clean(row["reference_calibration_text"]),
                "conversion_equation": _clean(row["conversion_equation"]),
                "potential_vs_AgAgCl_V": _as_number_or_blank(row["potential_vs_AgAgCl_V"]),
                "conversion_check_pass": conversion_ok,
                "solvent": _clean(row["solvent"]),
                "solvent_composition": _clean(row["solvent_composition"]),
                "supporting_electrolyte": _clean(row["supporting_electrolyte"]),
                "electrolyte_concentration_M": _as_number_or_blank(
                    row["electrolyte_concentration_M"]
                ),
                "monomer_concentration_M": _as_number_or_blank(row["monomer_concentration_M"]),
                "working_electrode": _clean(row["working_electrode"]),
                "scan_rate_mV_s": _as_number_or_blank(row["scan_rate_mV_s"]),
                "source_doi": _clean(row["source_doi"]),
                "doi_status": _clean(row["doi_status"]),
                "full_citation": _clean(row["full_citation"]),
                "structure_source_locator": _clean(row["structure_source_locator"]),
                "electrochemistry_source_locator": _clean(row["electrochemistry_source_locator"]),
                "structure_transcription_confidence": _clean(
                    row["structure_transcription_confidence"]
                ),
                "rdkit_parse_ok": bool(rdkit["parse_ok"]),
                "duplicate_internal": False,
                "duplicate_production_benchmark": production_key in production_groups,
                "independent_group_id": independent_group_id,
                "research_status": _clean(row["research_status"]),
                "reference_source_conflict": bool(row["reference_source_conflict"]),
                "condition_source_conflict": bool(row["condition_source_conflict"]),
                "source_conflict_details": _clean(row["source_conflict_details"]),
                "_rdkit_error": rdkit["error"],
                "_conversion_note": conversion_note,
                "_analytical_evidence_locator": _clean(row["analytical_evidence_locator"]),
                "_source_hrms_or_ms": _clean(row["source_hrms_or_ms"]),
                "_publisher_url": _clean(row["publisher_url"]),
            }
        )

    group_counts = pd.Series([row["independent_group_id"] for row in base_rows]).value_counts()
    review_rows: list[dict[str, Any]] = []
    for row in base_rows:
        row["duplicate_internal"] = bool(
            row["independent_group_id"] and group_counts[row["independent_group_id"]] > 1
        )
        classification, blocker, notes = _classify_review_row(row)
        public = {column: row[column] for column in REVIEW_COLUMNS if column not in {"review_classification", "blocking_issue", "review_notes"}}
        public["review_classification"] = classification
        public["blocking_issue"] = blocker
        public["review_notes"] = notes
        review_rows.append(public)

    review = pd.DataFrame(review_rows, columns=REVIEW_COLUMNS)
    return review.sort_values(
        by="record_id",
        key=lambda values: values.map(_record_sort_key),
        kind="mergesort",
    ).reset_index(drop=True)


def summarize_rescue_review(
    *,
    review: pd.DataFrame,
    benchmark: pd.DataFrame,
    monomers: pd.DataFrame,
    repo_root: Path,
    source_candidates_path: Path,
    external_inputs: tuple[Path, ...],
) -> dict[str, Any]:
    """Compute deterministic reporting counts for the review package."""

    benchmark_records = _benchmark_records(benchmark)
    rescue_records = _review_records(review)
    production_onset = {
        record["independent_key"] for record in benchmark_records if record["label_bucket"] == "onset"
    }
    production_peak = {
        record["independent_key"] for record in benchmark_records if record["label_bucket"] == "peak"
    }
    promotable = [
        record for record in rescue_records if record["review_classification"] == "PROMOTE_NOW_CANDIDATE"
    ]
    rescue_onset = {
        record["independent_key"] for record in promotable if record["label_bucket"] == "onset"
    }
    rescue_peak = {
        record["independent_key"] for record in promotable if record["label_bucket"] == "peak"
    }
    rescue_canonicals = {
        str(value) for value in review["canonical_smiles"] if _clean(value)
    }
    benchmark_canonicals = {record["canonical_smiles"] for record in benchmark_records}
    library_canonicals = _library_canonical_smiles(monomers)

    input_hashes = {
        str(path): _sha256_or_missing(path)
        for path in (source_candidates_path, *external_inputs)
    }
    classification_counts = {
        classification: int(count)
        for classification, count in review["review_classification"].value_counts().sort_index().items()
    }
    label_counts = {
        bucket: int(count)
        for bucket, count in pd.Series([_label_bucket(value) for value in review["label_type"]])
        .value_counts()
        .sort_index()
        .items()
    }

    return {
        "repo_sha": _git_sha(repo_root),
        "input_sha256": input_hashes,
        "source_candidate_rows": int(len(review)),
        "review_rows": int(len(review)),
        "rdkit_parse_ok_rows": int(review["rdkit_parse_ok"].sum()),
        "conversion_check_pass_rows": int(review["conversion_check_pass"].sum()),
        "classification_counts": classification_counts,
        "label_counts_all_rows": label_counts,
        "duplicate_internal_rows": int(review["duplicate_internal"].sum()),
        "duplicate_production_benchmark_rows": int(review["duplicate_production_benchmark"].sum()),
        "reference_source_conflict_rows": int(review["reference_source_conflict"].sum()),
        "condition_source_conflict_rows": int(review["condition_source_conflict"].sum()),
        "canonical_collapse": {
            "raw_rows": int(len(review)),
            "unique_canonical_structures": int(len(rescue_canonicals)),
            "canonical_duplicate_rows": int(len(review) - len(rescue_canonicals)),
        },
        "existing_production_onset_groups": int(len(production_onset)),
        "existing_production_peak_groups": int(len(production_peak)),
        "promotable_rescue_onset_groups": int(len(rescue_onset)),
        "promotable_rescue_peak_groups": int(len(rescue_peak)),
        "projected_union_onset_groups": int(len(production_onset | rescue_onset)),
        "projected_union_peak_groups": int(len(production_peak | rescue_peak)),
        "combined_experimental_combination_inventory": int(
            len(
                {record["independent_key"] for record in benchmark_records}
                | {record["independent_key"] for record in promotable}
            )
        ),
        "production_unique_structures": int(len(benchmark_canonicals)),
        "production_current_library_structures": int(len(benchmark_canonicals & library_canonicals)),
        "production_benchmark_only_structures": int(len(benchmark_canonicals - library_canonicals)),
        "rescue_unique_structures": int(len(rescue_canonicals)),
        "rescue_current_library_structures": int(len(rescue_canonicals & library_canonicals)),
        "rescue_benchmark_only_structures": int(len(rescue_canonicals - library_canonicals)),
        "no_candidate_promoted_to_benchmark": True,
    }


def _classify_review_row(row: dict[str, Any]) -> tuple[str, str, str]:
    structure_issues: list[str] = []
    provenance_issues: list[str] = []
    reference_issues: list[str] = []
    condition_issues: list[str] = []

    if not row["input_smiles"]:
        structure_issues.append("candidate SMILES is blank")
    if not row["rdkit_parse_ok"]:
        structure_issues.append(row["_rdkit_error"] or "RDKit parse failed")
    if not row["canonical_smiles"]:
        structure_issues.append("canonical SMILES was not generated")
    if not row["inchikey"]:
        structure_issues.append("InChIKey was not generated")
    if not row["source_compound_label"] or not row["exact_monomer_name"]:
        structure_issues.append("source compound label or exact monomer name is blank")
    if not row["structure_source_locator"]:
        structure_issues.append("structure source locator is blank")
    if row["formula_match"] == "FALSE":
        structure_issues.append(
            f"calculated formula {row['calculated_formula']} does not match source formula {row['source_formula']}"
        )
    if row["formula_match"] == "NOT_PROVIDED" and not row["_analytical_evidence_locator"]:
        structure_issues.append("no source formula or analytical-evidence locator is present")

    if row["duplicate_internal"]:
        return "REJECT", "Duplicate independent group inside R11-R21 rescue set.", _review_note(row)
    if row["duplicate_production_benchmark"]:
        return (
            "DUPLICATE_PRODUCTION",
            "Canonical validation group already exists in data/benchmark.csv.",
            _review_note(row),
        )

    if not row["full_citation"] or (not row["source_doi"] and not row["_publisher_url"]):
        provenance_issues.append("source DOI or durable publisher URL plus full citation is missing")
    if not row["electrochemistry_source_locator"]:
        provenance_issues.append("electrochemistry source locator is blank")

    if _label_bucket(row["label_type"]) != "onset":
        condition_issues.append(f"label type is not explicit onset: {row['label_type']}")
    for field in (
        "potential_original_V",
        "reference_electrode_original",
        "reference_calibration_text",
        "conversion_equation",
        "potential_vs_AgAgCl_V",
    ):
        if _clean(row[field]) == "":
            reference_issues.append(f"{field} is blank")
    if not row["conversion_check_pass"]:
        reference_issues.append(row["_conversion_note"] or "approved conversion check failed")
    if row["reference_source_conflict"]:
        reference_issues.append(
            f"source reference conflict unresolved: {row['source_conflict_details']}"
        )
    for field in ("solvent", "supporting_electrolyte"):
        if not row[field]:
            condition_issues.append(f"{field} is blank")
    if row["condition_source_conflict"]:
        condition_issues.append(
            f"source condition conflict unresolved: {row['source_conflict_details']}"
        )

    all_blockers = _blocking_issue(
        structure_issues,
        provenance_issues,
        reference_issues,
        condition_issues,
    )
    if structure_issues:
        return "NEEDS_STRUCTURE_CHECK", all_blockers, _review_note(row)
    if provenance_issues:
        return "NEEDS_PROVENANCE_CHECK", all_blockers, _review_note(row)
    if reference_issues:
        return "NEEDS_REFERENCE_CHECK", all_blockers, _review_note(row)
    if condition_issues:
        return "NEEDS_CONDITION_CHECK", all_blockers, _review_note(row)
    return "PROMOTE_NOW_CANDIDATE", "", _review_note(row)


def _blocking_issue(*groups: list[str]) -> str:
    return "; ".join(issue for group in groups for issue in group)


def _review_note(row: dict[str, Any]) -> str:
    parts: list[str] = []
    if row["formula_match"] == "TRUE":
        parts.append("Source formula/HRMS formula agrees with RDKit formula.")
    elif row["formula_match"] == "NOT_PROVIDED":
        parts.append("No source formula was provided; retained analytical locator for human review.")
    if row["_source_hrms_or_ms"]:
        parts.append(row["_source_hrms_or_ms"])
    if row["_analytical_evidence_locator"] and row["formula_match"] == "NOT_PROVIDED":
        parts.append(f"Analytical locator: {row['_analytical_evidence_locator']}.")
    if row["doi_status"] == "NO_DOI_FOUND_AFTER_TARGETED_SEARCH":
        parts.append("No DOI found, but durable article/PDF provenance is recorded.")
    if row["_conversion_note"] == "":
        parts.append("Approved reference conversion reproduced exactly.")
    if row["reference_source_conflict"] or row["condition_source_conflict"]:
        parts.append(
            "Source-internal conflict is unresolved; numeric values are retained as working "
            "transcriptions for audit only."
        )
    return " ".join(parts)


def _validate_source_conflict_fields(frame: pd.DataFrame, path: str | Path) -> None:
    for index, row in frame.iterrows():
        record_id = _clean(row["record_id"])
        parsed_flags: dict[str, bool] = {}
        for column in SOURCE_CONFLICT_BOOLEAN_COLUMNS:
            parsed = _strict_source_bool(row[column], column=column, record_id=record_id, path=path)
            frame.at[index, column] = parsed
            parsed_flags[column] = parsed
        details = _clean(row["source_conflict_details"])
        if (parsed_flags["reference_source_conflict"] or parsed_flags["condition_source_conflict"]) and not details:
            raise ValueError(
                f"{path} row {record_id} has a source conflict flag set but blank "
                "source_conflict_details"
            )


def _strict_source_bool(value: object, *, column: str, record_id: str, path: str | Path) -> bool:
    if pd.api.types.is_bool(value):
        return bool(value)
    text = _clean(value)
    if text == "true":
        return True
    if text == "false":
        return False
    raise ValueError(
        f"{path} row {record_id} column {column} must be a strict boolean true/false; "
        f"observed {text!r}"
    )


def _conversion_check(row: dict[str, Any]) -> tuple[bool, str]:
    record_id = _clean(row["record_id"])
    try:
        number = int(record_id.removeprefix("R"))
    except ValueError:
        return False, f"unexpected record id {record_id!r}"
    expected_reference_offset = 0.020 if 11 <= number <= 13 else 0.030
    expected_addition = expected_reference_offset + SCE_TO_AGAGCL_V

    original = _as_float(row["potential_original_V"])
    reported = _as_float(row["potential_vs_AgAgCl_V"])
    reference_offset = _as_float(row["reference_offset_vs_SCE_V"])
    equation = _clean(row["conversion_equation"])
    calibration_text = _clean(row["reference_calibration_text"])
    if original is None or reported is None or reference_offset is None:
        return False, "native potential, converted potential, or reference offset is not numeric"
    expected = original + expected_addition
    numeric_ok = abs(expected - reported) <= CONVERSION_TOLERANCE_V
    offset_ok = abs(reference_offset - expected_reference_offset) <= CONVERSION_TOLERANCE_V
    equation_ok = f"{expected_addition:.3f}" in equation
    text_ok = f"{expected_reference_offset:.2f}" in calibration_text or f"{expected_reference_offset:.3f}" in calibration_text
    if numeric_ok and offset_ok and equation_ok and text_ok:
        return True, ""
    details = (
        f"expected E_AgAgCl={expected:.6f} V from +{expected_addition:.3f} V; "
        f"reported {reported:.6f} V; offset_ok={offset_ok}; "
        f"equation_ok={equation_ok}; calibration_text_ok={text_ok}"
    )
    return False, details


def _rdkit_audit(smiles: str) -> dict[str, Any]:
    if not smiles:
        return {"parse_ok": False, "canonical_smiles": "", "inchikey": "", "formula": "", "error": "blank SMILES"}
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        return {
            "parse_ok": False,
            "canonical_smiles": "",
            "inchikey": "",
            "formula": "",
            "error": f"RDKit could not parse SMILES: {smiles}",
        }
    canonical = Chem.MolToSmiles(mol, canonical=True)
    try:
        inchikey = Chem.MolToInchiKey(mol)
    except Exception as exc:  # noqa: BLE001 - report the structure issue without aborting the audit
        inchikey = ""
        error = f"InChIKey generation failed: {exc}"
    else:
        error = ""
    return {
        "parse_ok": True,
        "canonical_smiles": canonical,
        "inchikey": inchikey,
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "error": error,
    }


def _formula_match(calculated: str, source_formula: str) -> str:
    if not source_formula:
        return "NOT_PROVIDED"
    if not calculated:
        return "NOT_COMPUTABLE"
    return "TRUE" if _parse_formula(calculated) == _parse_formula(source_formula) else "FALSE"


def _parse_formula(formula: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element, raw_count in _FORMULA_RE.findall(formula):
        counts[element] = counts.get(element, 0) + (int(raw_count) if raw_count else 1)
    return counts


def _production_validation_groups(benchmark: pd.DataFrame) -> set[str]:
    groups: set[str] = set()
    for _, row in benchmark.iterrows():
        canonical = _canonical_smiles(_clean(row.get("monomer_smiles", "")))
        if not canonical:
            continue
        groups.add(
            _validation_group_key(
                canonical_smiles=canonical,
                solvent=_clean(row.get("solvent_name", "")),
                label_type=_clean(row.get("label_type", "")),
            )
        )
    return groups


def _benchmark_records(benchmark: pd.DataFrame) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _, row in benchmark.iterrows():
        canonical = _canonical_smiles(_clean(row.get("monomer_smiles", "")))
        if not canonical:
            continue
        label_type = _clean(row.get("label_type", ""))
        independent_key = _pipe_key(
            canonical,
            label_type,
            _clean(row.get("source_doi", "")) or _clean(row.get("source_doi_or_ref", "")),
            _clean(row.get("source_locator", "")),
            _clean(row.get("solvent_name", "")),
            _clean(row.get("electrolyte", "")),
        )
        rows.append(
            {
                "canonical_smiles": canonical,
                "label_bucket": _label_bucket(label_type),
                "independent_key": independent_key,
            }
        )
    return rows


def _review_records(review: pd.DataFrame) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for _, row in review.iterrows():
        records.append(
            {
                "canonical_smiles": _clean(row["canonical_smiles"]),
                "label_bucket": _label_bucket(row["label_type"]),
                "independent_key": _clean(row["independent_group_id"]),
                "review_classification": _clean(row["review_classification"]),
            }
        )
    return records


def _library_canonical_smiles(monomers: pd.DataFrame) -> set[str]:
    canonicals: set[str] = set()
    for smiles in monomers["smiles"]:
        canonical = _canonical_smiles(_clean(smiles))
        if canonical:
            canonicals.add(canonical)
    return canonicals


def _canonical_smiles(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles, sanitize=True) if smiles else None
    return Chem.MolToSmiles(mol, canonical=True) if mol is not None else ""


def _independent_group_id(row: dict[str, Any], canonical_smiles: str) -> str:
    key = _pipe_key(
        canonical_smiles,
        _clean(row["label_type"]),
        _clean(row["source_doi"]) or _clean(row["full_citation"]),
        _clean(row["electrochemistry_source_locator"]),
        _clean(row["solvent"]),
        _clean(row["supporting_electrolyte"]),
        _clean(row["electrolyte_concentration_M"]),
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"eox-r11-r21-{digest}"


def _validation_group_key(*, canonical_smiles: str, solvent: str, label_type: str) -> str:
    return _pipe_key(canonical_smiles, solvent, label_type)


def _pipe_key(*parts: object) -> str:
    return "|".join(_clean(part).lower() for part in parts)


def _label_bucket(label_type: object) -> str:
    text = _clean(label_type).lower()
    if "onset" in text:
        return "onset"
    if "peak" in text or "epa" in text:
        return "peak"
    return "other"


def _record_sort_key(value: object) -> int:
    text = _clean(value)
    try:
        return int(text.removeprefix("R"))
    except ValueError:
        return 9999


def _render_report(review: pd.DataFrame, summary: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# R11-R21 Eox staging-rescue review")
    lines.append("")
    lines.append("This is a review-only curation package. No candidate was promoted into `data/benchmark.csv`.")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- Repo SHA used: `{summary['repo_sha']}`")
    lines.append("- Normalized source and optional external evidence inputs:")
    for path, digest in sorted(summary["input_sha256"].items()):
        lines.append(f"  - `{Path(path).name}`: `{digest}` (`{path}`)")
    lines.append("")
    lines.append(
        "Optional external reports are evidence/context inputs only; the normalized "
        "source-candidate CSV is the only machine-loaded candidate source."
    )
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- Source rows: {summary['source_candidate_rows']}")
    lines.append(f"- RDKit parsed rows: {summary['rdkit_parse_ok_rows']}")
    lines.append(f"- Internal duplicates: {summary['duplicate_internal_rows']}")
    lines.append(
        f"- Production benchmark duplicates: {summary['duplicate_production_benchmark_rows']}"
    )
    lines.append(f"- Reference-source conflicts: {summary['reference_source_conflict_rows']}")
    lines.append(f"- Condition-source conflicts: {summary['condition_source_conflict_rows']}")
    lines.append(f"- Conversion checks passed: {summary['conversion_check_pass_rows']}")
    lines.append(
        "- Canonical duplicate collapse: "
        f"{summary['canonical_collapse']['raw_rows']} raw rows -> "
        f"{summary['canonical_collapse']['unique_canonical_structures']} unique canonical structures "
        f"({summary['canonical_collapse']['canonical_duplicate_rows']} duplicate rows)."
    )
    lines.append(
        "- Existing production groups: "
        f"{summary['existing_production_onset_groups']} onset; "
        f"{summary['existing_production_peak_groups']} peak."
    )
    lines.append(
        "- Promotable rescue groups: "
        f"{summary['promotable_rescue_onset_groups']} onset; "
        f"{summary['promotable_rescue_peak_groups']} peak."
    )
    lines.append(
        "- Projected union groups: "
        f"{summary['projected_union_onset_groups']} onset; "
        f"{summary['projected_union_peak_groups']} peak; "
        f"{summary['combined_experimental_combination_inventory']} combined experimental combinations."
    )
    lines.append(
        "- Production benchmark structures: "
        f"{summary['production_unique_structures']} unique; "
        f"{summary['production_current_library_structures']} current-library; "
        f"{summary['production_benchmark_only_structures']} benchmark-only."
    )
    lines.append(
        "- Rescue structures: "
        f"{summary['rescue_unique_structures']} unique; "
        f"{summary['rescue_current_library_structures']} current-library; "
        f"{summary['rescue_benchmark_only_structures']} benchmark-only."
    )
    lines.append("")
    lines.append(
        "The combined experimental-combination inventory exceeds 30 only when peak and onset "
        "benchmarks are counted together. The onset-only projected union remains below 30, and "
        "the peak track is unchanged by this rescue package. Therefore this package does not close "
        "the Directive >=30 benchmark question by raw row count."
    )
    lines.append(
        "Numerically reproducible conversions are retained as audit transcriptions only; a "
        "source-internal reference or condition conflict keeps the affected row out of "
        "PROMOTE_NOW_CANDIDATE."
    )
    lines.append("")
    lines.append("## Disposition")
    lines.append("")
    lines.append(
        "| record | class | RDKit | canonical SMILES | formula | conversion | reference conflict | condition conflict | production duplicate | blocker |"
    )
    lines.append("| --- | --- | :---: | --- | --- | :---: | :---: | :---: | :---: | --- |")
    for _, row in review.iterrows():
        blocker = _clean(row["blocking_issue"]) or "-"
        lines.append(
            f"| {row['record_id']} | {row['review_classification']} | "
            f"{bool(row['rdkit_parse_ok'])} | `{row['canonical_smiles']}` | "
            f"{row['formula_match']} | {bool(row['conversion_check_pass'])} | "
            f"{bool(row['reference_source_conflict'])} | "
            f"{bool(row['condition_source_conflict'])} | "
            f"{bool(row['duplicate_production_benchmark'])} | {blocker} |"
        )
    lines.append("")
    lines.append("## Classification Counts")
    lines.append("")
    for classification in REVIEW_CLASSIFICATIONS:
        count = summary["classification_counts"].get(classification, 0)
        lines.append(f"- {classification}: {count}")
    lines.append("")
    lines.append("## Human Review Recommendation")
    lines.append("")
    lines.append(
        "Review only the PROMOTE_NOW_CANDIDATE rows against the primary figures/schemes before "
        "any production ingest. Keep source-conflicted rows in staging until a later scientific "
        "decision resolves or excludes their internal reference/condition contradictions. If "
        "approved, ingest through a separate benchmark-promotion task that preserves onset labels "
        "and keeps peak/onset counts separate."
    )
    lines.append("")
    return "\n".join(lines)


def _refuse_production_csv_output(path: Path, repo_root: Path) -> None:
    resolved = path.resolve()
    data_root = (repo_root / "data").resolve()
    lit_root = (repo_root / "data" / "lit_curation").resolve()
    if resolved.suffix.lower() == ".csv" and _is_relative_to(resolved, data_root) and not _is_relative_to(
        resolved, lit_root
    ):
        raise ValueError(f"Refusing to write review-only Eox rescue output to production CSV: {path}")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _git_sha(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


def _sha256_or_missing(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def _as_float(value: object) -> float | None:
    try:
        text = _clean(value)
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _as_number_or_blank(value: object) -> float | str:
    number = _as_float(value)
    return "" if number is None else number


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--source-candidates", type=Path, default=DEFAULT_SOURCE_CANDIDATES_PATH)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--monomers", type=Path, default=DEFAULT_MONOMERS_PATH)
    parser.add_argument("--review-out", type=Path, default=DEFAULT_REVIEW_PATH)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--external-input",
        action="append",
        default=[],
        help="External research/evidence input to hash in the report. May be repeated.",
    )
    args = parser.parse_args()
    result = build_eox_r11_r21_review_package(
        repo_root=args.repo_root,
        source_candidates_path=args.source_candidates,
        benchmark_path=args.benchmark,
        monomers_path=args.monomers,
        review_path=args.review_out,
        report_path=args.report_out,
        external_inputs=args.external_input,
    )
    print(f"Wrote {len(result.review)} review rows to {result.review_path}")
    print(f"Wrote report to {result.report_path}")


if __name__ == "__main__":
    main()

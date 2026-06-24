"""Review-only G1.2 Eox master-closure audit.

The audit consolidates current production benchmark rows, manually normalized
R11-R21 staging rows, and a bounded external-evidence queue into deterministic
review tables. It never promotes rows into production data.
"""

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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXTERNAL_MANIFEST_PATH = Path.home() / "CombHTS_evidence" / "G1_2" / "MANIFEST.tsv"
DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "benchmark.csv"
DEFAULT_R11_R21_REVIEW_PATH = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_r11_r21_rescue_review.csv"
)
DEFAULT_SOURCE_MANIFEST_OUT = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_g1_2_source_manifest.csv"
)
DEFAULT_MASTER_EVIDENCE_OUT = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_g1_2_master_evidence.csv"
)
DEFAULT_COMBINATION_SUMMARY_OUT = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_g1_2_combination_summary.csv"
)
DEFAULT_PRODUCTION_CHANGE_PROPOSAL_OUT = (
    PROJECT_ROOT / "data" / "lit_curation" / "eox_g1_2_production_change_proposal.csv"
)
DEFAULT_REPORT_OUT = (
    PROJECT_ROOT / "docs" / "research" / "eox_g1_2_master_closure_audit_20260624.md"
)

MASTER_LABEL_CLASSES = (
    "CLEAN_CV_ONSET_AGAGCL",
    "CLEAN_CV_PEAK_AGAGCL",
    "CLEAN_CV_ONSET_NATIVE_FC",
    "CLEAN_CV_PEAK_NATIVE_FC",
    "NON_CV_STEADY_STATE",
    "NON_CV_POLARIZATION_ONSET",
    "MIXED_SOLVENT_PARKED",
    "SOURCE_CONFLICT",
    "UNRESOLVED_REFERENCE",
    "STRUCTURE_BLOCKED",
    "PROVENANCE_BLOCKED",
    "DUPLICATE",
    "REJECT",
)

DISPOSITIONS = (
    "KEEP",
    "ADD_NEW_BENCHMARK_ROW",
    "RELABEL_ONTOLOGY",
    "MARK_CALIBRATION_INELIGIBLE",
    "CORRECT_STRUCTURE",
    "CORRECT_METADATA",
    "PARK",
    "REJECT",
    "NO_ACTION",
)

SOURCE_MANIFEST_COLUMNS = (
    "source_id",
    "canonical_filename",
    "sha256",
    "size_bytes",
    "identified_title",
    "doi",
    "source_type",
    "main_or_si",
    "acquisition_method",
    "acquisition_status",
    "used_in_audit",
    "evidence_role",
    "notes",
)

MASTER_EVIDENCE_COLUMNS = (
    "record_id",
    "source_id",
    "source_record_label",
    "exact_monomer_name",
    "input_smiles",
    "canonical_smiles",
    "inchikey",
    "rdkit_parse_ok",
    "monomer_class",
    "label_type",
    "master_label_class",
    "potential_original_V",
    "potential_original_units",
    "reference_electrode_original",
    "reference_frame",
    "reference_calibration_text",
    "conversion_equation",
    "conversion_to_AgAgCl_V",
    "potential_vs_AgAgCl_V",
    "solvent_system",
    "solvent_name",
    "solvent_composition",
    "supporting_electrolyte",
    "electrolyte_concentration_M",
    "monomer_concentration_M",
    "working_electrode",
    "counter_electrode",
    "scan_rate_mV_s",
    "measurement_method",
    "first_cycle_or_scan",
    "source_doi",
    "source_citation",
    "source_locator",
    "structure_locator",
    "evidence_quote_short",
    "experimental_measurement_id",
    "directive_combination_id",
    "current_model_group_id",
    "duplicate_of_record_id",
    "literature_cv_clean",
    "current_pipeline_comparable",
    "directive_quantity_eligible",
    "onset_profile_eligible",
    "peak_profile_eligible",
    "native_fc_profile_eligible",
    "production_current_status",
    "production_ingest_recommended",
    "production_correction_required",
    "disposition",
    "blocking_issue",
    "review_notes",
)

COMBINATION_SUMMARY_COLUMNS = (
    "directive_combination_id",
    "representative_record_id",
    "canonical_smiles",
    "exact_monomer_name",
    "solvent_name",
    "solvent_system",
    "supporting_electrolyte",
    "measurement_count",
    "clean_cv_agagcl_onset_count",
    "clean_cv_agagcl_peak_count",
    "native_fc_count",
    "production_current_count",
    "production_correction_required_count",
    "staging_or_external_count",
    "directive_quantity_eligible",
    "has_current_pipeline_comparable",
    "onset_profile_eligible",
    "peak_profile_eligible",
    "native_fc_profile_eligible",
    "best_record_id",
    "best_master_label_class",
    "coverage_status",
    "blocking_issue",
)

PRODUCTION_CHANGE_PROPOSAL_COLUMNS = (
    "proposal_id",
    "record_id",
    "directive_combination_id",
    "action",
    "target_file",
    "production_current_status",
    "proposed_status",
    "requires_branch_pr",
    "source_id",
    "reason",
    "blocked_by",
    "notes",
)

EXTERNAL_MANIFEST_COLUMNS = (
    "canonical_filename",
    "sha256",
    "size_bytes",
    "identified_title",
    "doi",
    "source_type",
    "original_local_path",
    "acquisition_method",
    "status",
    "notes",
)


@dataclass(frozen=True)
class EoxMasterAuditResult:
    """In-memory and on-disk result for the review-only G1.2 master audit."""

    source_manifest: pd.DataFrame
    master_evidence: pd.DataFrame
    combination_summary: pd.DataFrame
    production_change_proposal: pd.DataFrame
    summary: dict[str, Any]
    written_paths: tuple[Path, ...]


def build_eox_g1_2_master_audit(
    *,
    repo_root: str | Path = PROJECT_ROOT,
    external_manifest_path: str | Path = DEFAULT_EXTERNAL_MANIFEST_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    r11_r21_review_path: str | Path = DEFAULT_R11_R21_REVIEW_PATH,
    source_manifest_out: str | Path | None = DEFAULT_SOURCE_MANIFEST_OUT,
    master_evidence_out: str | Path | None = DEFAULT_MASTER_EVIDENCE_OUT,
    combination_summary_out: str | Path | None = DEFAULT_COMBINATION_SUMMARY_OUT,
    production_change_proposal_out: str | Path | None = DEFAULT_PRODUCTION_CHANGE_PROPOSAL_OUT,
    report_out: str | Path | None = DEFAULT_REPORT_OUT,
) -> EoxMasterAuditResult:
    """Build deterministic review-only G1.2 Eox audit artifacts.

    All output CSVs are review artifacts. Production CSVs under ``data/`` and
    configuration files are refused as destinations.
    """

    root = Path(repo_root).resolve()
    benchmark = pd.read_csv(benchmark_path, keep_default_na=False)
    r11_review = pd.read_csv(r11_r21_review_path, keep_default_na=False)
    external_manifest = load_external_manifest(external_manifest_path)
    source_manifest = build_source_manifest(
        external_manifest=external_manifest,
        benchmark_path=Path(benchmark_path),
        r11_review_path=Path(r11_r21_review_path),
    )
    source_lookup = _source_lookup(source_manifest)
    master = build_master_evidence(
        benchmark=benchmark,
        r11_review=r11_review,
        source_lookup=source_lookup,
    )
    validate_master_evidence_schema(master)
    validate_master_enums(master)
    combination_summary = build_combination_summary(master)
    production_change_proposal = build_production_change_proposal(master)
    summary = summarize_master_audit(
        source_manifest=source_manifest,
        master=master,
        combination_summary=combination_summary,
        proposal=production_change_proposal,
        repo_root=root,
        external_manifest_path=Path(external_manifest_path),
        benchmark_path=Path(benchmark_path),
        r11_review_path=Path(r11_r21_review_path),
    )

    written: list[Path] = []
    for path, frame in (
        (source_manifest_out, source_manifest),
        (master_evidence_out, master),
        (combination_summary_out, combination_summary),
        (production_change_proposal_out, production_change_proposal),
    ):
        if path is None:
            continue
        output_path = Path(path)
        _refuse_forbidden_output(output_path, root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output_path, index=False, lineterminator="\n")
        written.append(output_path)

    if report_out is not None:
        report_path = Path(report_out)
        _refuse_forbidden_output(report_path, root)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_closure_report(summary, master, combination_summary), encoding="utf-8")
        written.append(report_path)

    return EoxMasterAuditResult(
        source_manifest=source_manifest,
        master_evidence=master,
        combination_summary=combination_summary,
        production_change_proposal=production_change_proposal,
        summary=summary,
        written_paths=tuple(written),
    )


def load_external_manifest(path: str | Path) -> pd.DataFrame:
    """Load the local external-evidence manifest without absolute-path leakage."""

    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"External G1.2 evidence manifest not found: {manifest_path}. "
            "Prepare $HOME/CombHTS_evidence/G1_2/MANIFEST.tsv first."
        )
    frame = pd.read_csv(manifest_path, sep="\t", keep_default_na=False)
    missing = [column for column in EXTERNAL_MANIFEST_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{manifest_path} is missing required columns: {', '.join(missing)}")
    return frame.loc[:, EXTERNAL_MANIFEST_COLUMNS].copy()


def build_source_manifest(
    *,
    external_manifest: pd.DataFrame,
    benchmark_path: Path,
    r11_review_path: Path,
) -> pd.DataFrame:
    """Build the committed source manifest with canonical filenames only."""

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(
        external_manifest.sort_values(
            by=["source_type", "canonical_filename"],
            kind="mergesort",
        ).to_dict(orient="records"),
        start=1,
    ):
        filename = _clean(row["canonical_filename"])
        source_type = _clean(row["source_type"])
        rows.append(
            {
                "source_id": f"SRC{index:03d}",
                "canonical_filename": filename,
                "sha256": _clean(row["sha256"]),
                "size_bytes": _clean(row["size_bytes"]),
                "identified_title": _clean(row["identified_title"]),
                "doi": _clean(row["doi"]),
                "source_type": source_type,
                "main_or_si": _main_or_si(filename, source_type),
                "acquisition_method": _clean(row["acquisition_method"]),
                "acquisition_status": _clean(row["status"]),
                "used_in_audit": True,
                "evidence_role": _evidence_role(filename, source_type, _clean(row["status"])),
                "notes": _manifest_notes(row),
            }
        )

    rows.extend(
        [
            {
                "source_id": "SRC_REPO_BENCHMARK",
                "canonical_filename": "data/benchmark.csv",
                "sha256": _sha256_or_missing(benchmark_path),
                "size_bytes": str(benchmark_path.stat().st_size) if benchmark_path.exists() else "",
                "identified_title": "Current production Eox benchmark table",
                "doi": "",
                "source_type": "repository_table",
                "main_or_si": "repo",
                "acquisition_method": "REPOSITORY_READ",
                "acquisition_status": "FOUND_REPO_TRACKED",
                "used_in_audit": True,
                "evidence_role": "current_production_state",
                "notes": "Repository table hashed for review-only comparison; not modified.",
            },
            {
                "source_id": "SRC_REPO_R11_R21_REVIEW",
                "canonical_filename": "data/lit_curation/eox_r11_r21_rescue_review.csv",
                "sha256": _sha256_or_missing(r11_review_path),
                "size_bytes": str(r11_review_path.stat().st_size) if r11_review_path.exists() else "",
                "identified_title": "R11-R21 review-only Eox rescue table",
                "doi": "",
                "source_type": "repository_table",
                "main_or_si": "repo",
                "acquisition_method": "REPOSITORY_READ",
                "acquisition_status": "FOUND_REPO_TRACKED",
                "used_in_audit": True,
                "evidence_role": "staging_review_state",
                "notes": "Repository staging table hashed for review-only comparison; not modified.",
            },
        ]
    )
    frame = pd.DataFrame(rows, columns=SOURCE_MANIFEST_COLUMNS)
    return frame.sort_values(by="source_id", kind="mergesort").reset_index(drop=True)


def build_master_evidence(
    *,
    benchmark: pd.DataFrame,
    r11_review: pd.DataFrame,
    source_lookup: dict[str, str],
) -> pd.DataFrame:
    """Build one review row per production, staging, or external measurement."""

    rows: list[dict[str, Any]] = []
    for index, row in enumerate(benchmark.to_dict(orient="records"), start=1):
        rows.append(_production_row(index, row, source_lookup))
    for row in r11_review.to_dict(orient="records"):
        rows.append(_r11_r21_row(row, source_lookup))
    rows.extend(_external_rows(source_lookup))

    materialized = [_materialize_master_row(row) for row in rows]
    by_measurement: dict[str, str] = {}
    for row in materialized:
        measurement_id = row["experimental_measurement_id"]
        row["duplicate_of_record_id"] = by_measurement.get(measurement_id, "")
        by_measurement.setdefault(measurement_id, row["record_id"])

    frame = pd.DataFrame(materialized, columns=MASTER_EVIDENCE_COLUMNS)
    return frame.sort_values(by="record_id", key=lambda values: values.map(_record_sort_key), kind="mergesort").reset_index(
        drop=True
    )


def validate_master_evidence_schema(frame: pd.DataFrame) -> None:
    """Validate the committed master evidence schema and strict booleans."""

    missing = [column for column in MASTER_EVIDENCE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"master evidence is missing required columns: {', '.join(missing)}")
    for index, row in frame.iterrows():
        record_id = _clean(row["record_id"]) or f"row-{index + 1}"
        for column in (
            "rdkit_parse_ok",
            "literature_cv_clean",
            "current_pipeline_comparable",
            "directive_quantity_eligible",
            "onset_profile_eligible",
            "peak_profile_eligible",
            "native_fc_profile_eligible",
            "production_ingest_recommended",
            "production_correction_required",
        ):
            strict_bool(row[column], column=column, record_id=record_id)


def validate_master_enums(frame: pd.DataFrame) -> None:
    """Validate master label classes and disposition enums."""

    _validate_enum(frame, "master_label_class", MASTER_LABEL_CLASSES)
    _validate_enum(frame, "disposition", DISPOSITIONS)


def strict_bool(value: object, *, column: str, record_id: str) -> bool:
    """Parse a strict boolean field from a normalized CSV row."""

    if pd.api.types.is_bool(value):
        return bool(value)
    text = _clean(value)
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "True":
        return True
    if text == "False":
        return False
    raise ValueError(f"row {record_id} column {column} must be a strict boolean true/false")


def canonicalize_smiles(smiles: str) -> dict[str, Any]:
    """Return canonical SMILES and InChIKey for a monomer candidate."""

    text = _clean(smiles)
    if not text:
        return {"canonical_smiles": "", "inchikey": "", "rdkit_parse_ok": False}
    mol = Chem.MolFromSmiles(text, sanitize=True)
    if mol is None:
        return {"canonical_smiles": "", "inchikey": "", "rdkit_parse_ok": False}
    try:
        inchikey = Chem.MolToInchiKey(mol)
    except Exception:  # noqa: BLE001 - structure remains usable for canonical grouping
        inchikey = ""
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "inchikey": inchikey,
        "rdkit_parse_ok": True,
    }


def experimental_measurement_id(row: dict[str, Any]) -> str:
    """Stable ID for one source-level measurement, including label and condition."""

    key = _pipe_key(
        row.get("canonical_smiles") or row.get("input_smiles") or row.get("exact_monomer_name"),
        row.get("label_type"),
        row.get("potential_original_V"),
        row.get("reference_electrode_original"),
        row.get("solvent_system") or row.get("solvent_name"),
        row.get("supporting_electrolyte"),
        row.get("electrolyte_concentration_M"),
        row.get("source_id"),
        row.get("source_locator"),
        row.get("measurement_method"),
    )
    return f"meas-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def directive_combination_id(row: dict[str, Any]) -> str:
    """Stable ID for directive combination counts.

    The ID intentionally excludes label type and electrolyte concentration so
    onset/peak reports and concentration-only variants do not inflate the count.
    """

    key = _pipe_key(
        row.get("canonical_smiles") or row.get("input_smiles") or row.get("exact_monomer_name"),
        row.get("solvent_name") or row.get("solvent_system"),
        row.get("supporting_electrolyte"),
    )
    return f"combo-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def current_model_group_id(row: dict[str, Any]) -> str:
    """Stable ID for current model profiles, keeping onset and peak separate."""

    key = _pipe_key(
        row.get("canonical_smiles") or row.get("input_smiles") or row.get("exact_monomer_name"),
        row.get("solvent_name") or row.get("solvent_system"),
        _label_bucket(row.get("label_type")),
        row.get("reference_frame"),
    )
    return f"model-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"


def build_combination_summary(master: pd.DataFrame) -> pd.DataFrame:
    """Collapse master evidence to directive-level formulation groups."""

    rows: list[dict[str, Any]] = []
    for combo_id, group in master.groupby("directive_combination_id", sort=True):
        unique_measurements = sorted(set(group["experimental_measurement_id"]))
        best = _best_row(group)
        blockers = sorted({_clean(value) for value in group["blocking_issue"] if _clean(value)})
        rows.append(
            {
                "directive_combination_id": combo_id,
                "representative_record_id": _clean(group.iloc[0]["record_id"]),
                "canonical_smiles": _clean(best["canonical_smiles"]),
                "exact_monomer_name": _clean(best["exact_monomer_name"]),
                "solvent_name": _clean(best["solvent_name"]),
                "solvent_system": _clean(best["solvent_system"]),
                "supporting_electrolyte": _clean(best["supporting_electrolyte"]),
                "measurement_count": len(unique_measurements),
                "clean_cv_agagcl_onset_count": int(
                    (group["master_label_class"] == "CLEAN_CV_ONSET_AGAGCL").sum()
                ),
                "clean_cv_agagcl_peak_count": int(
                    (group["master_label_class"] == "CLEAN_CV_PEAK_AGAGCL").sum()
                ),
                "native_fc_count": int(group["master_label_class"].str.contains("NATIVE_FC").sum()),
                "production_current_count": int(
                    (group["production_current_status"] == "CURRENT_PRODUCTION_OK").sum()
                ),
                "production_correction_required_count": int(
                    group["production_correction_required"].map(_bool_value).sum()
                ),
                "staging_or_external_count": int(
                    (
                        group["production_current_status"].isin(
                            ["STAGING_REVIEW_ONLY", "EXTERNAL_EVIDENCE_READY", "EXTERNAL_EVIDENCE_BLOCKED"]
                        )
                    ).sum()
                ),
                "directive_quantity_eligible": bool(group["directive_quantity_eligible"].any()),
                "has_current_pipeline_comparable": bool(group["current_pipeline_comparable"].any()),
                "onset_profile_eligible": bool(group["onset_profile_eligible"].any()),
                "peak_profile_eligible": bool(group["peak_profile_eligible"].any()),
                "native_fc_profile_eligible": bool(group["native_fc_profile_eligible"].any()),
                "best_record_id": _clean(best["record_id"]),
                "best_master_label_class": _clean(best["master_label_class"]),
                "coverage_status": _coverage_status(group),
                "blocking_issue": "; ".join(blockers),
            }
        )
    return pd.DataFrame(rows, columns=COMBINATION_SUMMARY_COLUMNS).sort_values(
        by="directive_combination_id", kind="mergesort"
    ).reset_index(drop=True)


def build_production_change_proposal(master: pd.DataFrame) -> pd.DataFrame:
    """Build a proposal-only table; it is not an ingest plan."""

    rows: list[dict[str, Any]] = []
    eligible_new = master[
        (master["disposition"] == "ADD_NEW_BENCHMARK_ROW")
        | (master["production_correction_required"].map(_bool_value))
        | (master["disposition"].isin(["PARK", "REJECT"]))
    ].copy()
    for index, row in enumerate(eligible_new.to_dict(orient="records"), start=1):
        action = _proposal_action(row)
        rows.append(
            {
                "proposal_id": f"G12-P{index:03d}",
                "record_id": row["record_id"],
                "directive_combination_id": row["directive_combination_id"],
                "action": action,
                "target_file": "data/benchmark.csv"
                if action in {"ADD_NEW_BENCHMARK_ROW", "RELABEL_ONTOLOGY", "MARK_CALIBRATION_INELIGIBLE"}
                else "data/lit_curation/eox_g1_2_master_evidence.csv",
                "production_current_status": row["production_current_status"],
                "proposed_status": "PROPOSED_ONLY",
                "requires_branch_pr": action in {
                    "ADD_NEW_BENCHMARK_ROW",
                    "RELABEL_ONTOLOGY",
                    "MARK_CALIBRATION_INELIGIBLE",
                },
                "source_id": row["source_id"],
                "reason": _proposal_reason(row, action),
                "blocked_by": row["blocking_issue"],
                "notes": row["review_notes"],
            }
        )
    frame = pd.DataFrame(rows, columns=PRODUCTION_CHANGE_PROPOSAL_COLUMNS)
    return frame.sort_values(by="proposal_id", kind="mergesort").reset_index(drop=True)


def summarize_master_audit(
    *,
    source_manifest: pd.DataFrame,
    master: pd.DataFrame,
    combination_summary: pd.DataFrame,
    proposal: pd.DataFrame,
    repo_root: Path,
    external_manifest_path: Path,
    benchmark_path: Path,
    r11_review_path: Path,
) -> dict[str, Any]:
    """Compute all report counts directly from CSV-ready frames."""

    eligible_combos = combination_summary[
        combination_summary["directive_quantity_eligible"].map(_bool_value)
    ]
    onset_combos = combination_summary[combination_summary["onset_profile_eligible"].map(_bool_value)]
    peak_combos = combination_summary[combination_summary["peak_profile_eligible"].map(_bool_value)]
    native_fc_combos = combination_summary[
        combination_summary["native_fc_profile_eligible"].map(_bool_value)
    ]
    class_counts = _value_counts(master["master_label_class"])
    disposition_counts = _value_counts(master["disposition"])
    production_status_counts = _value_counts(master["production_current_status"])
    proposal_counts = _value_counts(proposal["action"]) if len(proposal) else {}
    return {
        "repo_sha": _git_sha(repo_root),
        "input_sha256": {
            "external_manifest": _sha256_or_missing(external_manifest_path),
            "benchmark": _sha256_or_missing(benchmark_path),
            "r11_r21_review": _sha256_or_missing(r11_review_path),
        },
        "source_manifest_rows": int(len(source_manifest)),
        "external_source_rows": int((source_manifest["source_type"] != "repository_table").sum()),
        "master_rows": int(len(master)),
        "rdkit_parse_ok_rows": int(master["rdkit_parse_ok"].map(_bool_value).sum()),
        "production_benchmark_rows": int((master["production_current_status"].str.startswith("CURRENT_")).sum()),
        "r11_r21_rows": int(master["record_id"].str.startswith("R").sum()),
        "external_measurement_rows": int(master["record_id"].str.startswith("EXT").sum()),
        "class_counts": class_counts,
        "disposition_counts": disposition_counts,
        "production_status_counts": production_status_counts,
        "proposal_counts": proposal_counts,
        "production_correction_required_rows": int(
            master["production_correction_required"].map(_bool_value).sum()
        ),
        "camarada_non_cv_rows": int((master["master_label_class"] == "NON_CV_STEADY_STATE").sum()),
        "directive_quantity_eligible_rows": int(
            master["directive_quantity_eligible"].map(_bool_value).sum()
        ),
        "directive_quantity_eligible_combinations": int(len(eligible_combos)),
        "onset_profile_eligible_combinations": int(len(onset_combos)),
        "peak_profile_eligible_combinations": int(len(peak_combos)),
        "native_fc_profile_eligible_combinations": int(len(native_fc_combos)),
        "directive_gte_30_status": "PASS" if len(eligible_combos) >= 30 else "FAIL",
        "paywalled_sources": int((source_manifest["acquisition_status"] == "MISSING_PAYWALLED").sum()),
        "forbidden_production_files_modified": False,
        "engine": "none (no-engine curation)",
    }


def render_closure_report(
    summary: dict[str, Any],
    master: pd.DataFrame,
    combination_summary: pd.DataFrame,
) -> str:
    """Render the human-readable closure audit report."""

    lines: list[str] = [
        "# G1.2 Eox master closure audit",
        "",
        "This is a review-only, no-engine curation audit. It does not modify production benchmark,",
        "library, config, redox, scoring, Tier-1, Tier-2, validation, cache, or output-schema files.",
        "",
        "## Provenance",
        "",
        f"- Repo SHA: `{summary['repo_sha']}`",
        f"- Engine: {summary['engine']}",
        "- Input hashes:",
    ]
    for label, digest in sorted(summary["input_sha256"].items()):
        lines.append(f"  - {label}: `{digest}`")
    lines.extend(
        [
            "",
            "The external source manifest records canonical filenames, SHA-256 hashes, DOI/status,",
            "and extraction status only. PDFs, zips, and raw extracted text remain outside the repo.",
            "",
            "## Closure Counts",
            "",
            f"- Source-manifest rows: {summary['source_manifest_rows']}",
            f"- External evidence rows: {summary['external_source_rows']}",
            f"- Master evidence rows: {summary['master_rows']}",
            f"- Production benchmark rows reviewed: {summary['production_benchmark_rows']}",
            f"- R11-R21 staging rows reviewed: {summary['r11_r21_rows']}",
            f"- External measurement/provenance rows reviewed: {summary['external_measurement_rows']}",
            f"- RDKit parse-ok rows: {summary['rdkit_parse_ok_rows']}",
            f"- Directive-eligible combinations: {summary['directive_quantity_eligible_combinations']} "
            f"({summary['directive_gte_30_status']} vs >=30)",
            f"- Onset-profile eligible combinations: {summary['onset_profile_eligible_combinations']}",
            f"- Peak-profile eligible combinations: {summary['peak_profile_eligible_combinations']}",
            f"- Native-Fc eligible combinations: {summary['native_fc_profile_eligible_combinations']}",
            f"- Production corrections proposed: {summary['production_correction_required_rows']}",
            f"- Camarada non-CV steady-state rows found in production: {summary['camarada_non_cv_rows']}",
            f"- Paywalled DOI rows with no lawful PDF downloaded: {summary['paywalled_sources']}",
            "",
            "## Master Class Counts",
            "",
        ]
    )
    for key, count in summary["class_counts"].items():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Disposition Counts", ""])
    for key, count in summary["disposition_counts"].items():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Production Proposal Counts", ""])
    for key, count in summary["proposal_counts"].items():
        lines.append(f"- {key}: {count}")

    lines.extend(
        [
            "",
            "## Scientific Findings",
            "",
            "- The 10 Camarada thiophene-oligomer rows in current production are not ordinary CV",
            "  onset rows. The source uses slow steady-state polarization curves, so this audit",
            "  marks them non-CV and proposes a future production correction rather than treating",
            "  them as calibration/onset-profile evidence.",
            "- R11-R13 remain staging-only because they are mixed ACN/DCM pseudo-reference rows.",
            "  R14-R21 remain parked because source-internal reference and condition conflicts",
            "  are unresolved.",
            "- Direct Ag/AgCl clean-CV external rows from the prepared official evidence packet",
            "  are proposal-only additions. Native-Fc, mixed-solvent, unresolved-reference,",
            "  polarization, structure-blocked, and paywalled rows remain separate or parked.",
            "",
            "## Count Semantics",
            "",
            "Directive combinations collapse onset and peak reports for the same canonical",
            "monomer/solvent/electrolyte formulation and ignore concentration-only variants.",
            "Current model groups keep onset and peak separate. All counts above are recomputed",
            "from the generated CSV rows, not copied from prior reports.",
            "",
            "## Review Tables",
            "",
            "- `data/lit_curation/eox_g1_2_source_manifest.csv`",
            "- `data/lit_curation/eox_g1_2_master_evidence.csv`",
            "- `data/lit_curation/eox_g1_2_combination_summary.csv`",
            "- `data/lit_curation/eox_g1_2_production_change_proposal.csv`",
            "",
            "## Combination Snapshot",
            "",
            "| status | count |",
            "| --- | ---: |",
        ]
    )
    for status, count in _value_counts(combination_summary["coverage_status"]).items():
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No production ingest was performed.",
            "- No branch was created or switched for this work unit.",
            "- No Lop, xTB, Gaussian, ORCA, or other quantum engine was run.",
            "- Production CSVs and configs are only read for hashing/counting.",
            "",
        ]
    )
    return "\n".join(lines)


def _production_row(index: int, row: dict[str, Any], source_lookup: dict[str, str]) -> dict[str, Any]:
    doi = _clean(row.get("source_doi")) or _clean(row.get("source_doi_or_ref"))
    label = _clean(row.get("label_type"))
    is_camarada = doi == "10.1002/polb.22360"
    if is_camarada:
        master_class = "NON_CV_STEADY_STATE"
        status = "CURRENT_PRODUCTION_ONTOLOGY_ERROR"
        disposition = "RELABEL_ONTOLOGY"
        blocker = "Camarada Table 5 values come from slow steady-state polarization curves, not ordinary CV onset."
        correction_required = True
    else:
        master_class = "CLEAN_CV_ONSET_AGAGCL" if _label_bucket(label) == "onset" else "CLEAN_CV_PEAK_AGAGCL"
        status = "CURRENT_PRODUCTION_OK"
        disposition = "KEEP"
        blocker = ""
        correction_required = False
    source_id = _source_id_for(doi=doi, filename_hint="", source_lookup=source_lookup) or "SRC_REPO_BENCHMARK"
    return {
        "record_id": f"PROD{index:03d}",
        "source_id": source_id,
        "source_record_label": f"data/benchmark.csv row {index}",
        "exact_monomer_name": row.get("monomer_name", ""),
        "input_smiles": row.get("monomer_smiles", ""),
        "monomer_class": "",
        "label_type": label,
        "master_label_class": master_class,
        "potential_original_V": row.get("native_potential_V", ""),
        "potential_original_units": "V",
        "reference_electrode_original": row.get("native_reference", ""),
        "reference_frame": row.get("reference_frame", "agagcl") or "agagcl",
        "reference_calibration_text": row.get("conversion_source", ""),
        "conversion_equation": row.get("conversion_method", ""),
        "conversion_to_AgAgCl_V": row.get("conversion_to_AgAgCl_V", ""),
        "potential_vs_AgAgCl_V": row.get("exp_Eox_V_vs_AgAgCl", ""),
        "solvent_system": row.get("medium", "") or row.get("solvent_name", ""),
        "solvent_name": row.get("solvent_name", ""),
        "solvent_composition": "",
        "supporting_electrolyte": row.get("electrolyte", ""),
        "electrolyte_concentration_M": _electrolyte_concentration(row.get("electrolyte", "")),
        "monomer_concentration_M": "",
        "working_electrode": row.get("working_electrode", ""),
        "counter_electrode": "",
        "scan_rate_mV_s": row.get("scan_rate_mV_s", ""),
        "measurement_method": "steady-state polarization" if is_camarada else "cyclic voltammetry",
        "first_cycle_or_scan": "source reported",
        "source_doi": doi,
        "source_citation": row.get("source_citation", ""),
        "source_locator": row.get("source_locator", ""),
        "structure_locator": "data/benchmark.csv monomer_smiles",
        "evidence_quote_short": "Production row audited against source class.",
        "production_current_status": status,
        "production_ingest_recommended": False,
        "production_correction_required": correction_required,
        "disposition": disposition,
        "blocking_issue": blocker,
        "review_notes": row.get("notes", ""),
    }


def _r11_r21_row(row: dict[str, Any], source_lookup: dict[str, str]) -> dict[str, Any]:
    record_id = _clean(row["record_id"])
    source_doi = _clean(row["source_doi"])
    full_citation = _clean(row["full_citation"])
    if record_id in {"R11", "R12", "R13"}:
        master_class = "MIXED_SOLVENT_PARKED"
        blocker = "Mixed ACN/DCM pseudo-reference row remains staging-only for master closure."
    else:
        master_class = "SOURCE_CONFLICT"
        blocker = _clean(row["blocking_issue"]) or "Source-internal reference or condition conflict unresolved."
    source_id = _source_id_for(doi=source_doi, filename_hint=_source_hint_from_citation(full_citation), source_lookup=source_lookup)
    return {
        "record_id": record_id,
        "source_id": source_id or "SRC_REPO_R11_R21_REVIEW",
        "source_record_label": row["source_compound_label"],
        "exact_monomer_name": row["exact_monomer_name"],
        "input_smiles": row["input_smiles"],
        "monomer_class": row["monomer_class"],
        "label_type": row["label_type"],
        "master_label_class": master_class,
        "potential_original_V": row["potential_original_V"],
        "potential_original_units": "V",
        "reference_electrode_original": row["reference_electrode_original"],
        "reference_frame": "pseudo_sce_to_agagcl",
        "reference_calibration_text": row["reference_calibration_text"],
        "conversion_equation": row["conversion_equation"],
        "conversion_to_AgAgCl_V": _as_float(row["potential_vs_AgAgCl_V"]) - _as_float(row["potential_original_V"])
        if _as_float(row["potential_vs_AgAgCl_V"]) is not None and _as_float(row["potential_original_V"]) is not None
        else "",
        "potential_vs_AgAgCl_V": row["potential_vs_AgAgCl_V"],
        "solvent_system": row["solvent"],
        "solvent_name": row["solvent"],
        "solvent_composition": row["solvent_composition"],
        "supporting_electrolyte": row["supporting_electrolyte"],
        "electrolyte_concentration_M": row["electrolyte_concentration_M"],
        "monomer_concentration_M": row["monomer_concentration_M"],
        "working_electrode": row["working_electrode"],
        "counter_electrode": "",
        "scan_rate_mV_s": row["scan_rate_mV_s"],
        "measurement_method": "cyclic voltammetry",
        "first_cycle_or_scan": "first scan",
        "source_doi": source_doi,
        "source_citation": full_citation,
        "source_locator": row["electrochemistry_source_locator"],
        "structure_locator": row["structure_source_locator"],
        "evidence_quote_short": row["source_conflict_details"] or row["review_notes"],
        "production_current_status": "STAGING_REVIEW_ONLY",
        "production_ingest_recommended": False,
        "production_correction_required": False,
        "disposition": "PARK",
        "blocking_issue": blocker,
        "review_notes": row["review_notes"],
    }


def _external_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        _ext(
            "EXT_FUPY_ONSET",
            source_lookup,
            "molecules_2025_n_furfuryl_pyrrole.pdf",
            "FuPy",
            "N-furfuryl pyrrole",
            "c1ccoc1CN2C=CC=C2",
            "pyrrole",
            "monomer_oxidation_onset",
            "CLEAN_CV_ONSET_AGAGCL",
            1.32,
            "Ag wire calibrated to SCE",
            "agagcl",
            "Ag wire calibrated 0.004 V vs SCE; SCE to Ag/AgCl +0.045 V.",
            "E_AgAgCl = E_original + 0.049 V",
            0.049,
            1.369,
            "acetonitrile",
            "acetonitrile",
            "",
            "0.1 M Bu4NClO4",
            0.1,
            0.005,
            "Pt wire",
            "Pt wire",
            100,
            "cyclic voltammetry",
            "first scan",
            "10.3390/molecules30010042",
            "Molecules 2025 FuPy/EDOT electrochromic copolymers",
            "Figure 1 and experimental electrochemical section",
            "Synthesis/compound section and SI",
            "Eonset of FuPy reported as 1.32 V; Ag wire calibrated 0.004 V vs SCE.",
            "ADD_NEW_BENCHMARK_ROW",
            "",
            "Clean first-scan monomer onset with same-experiment reference calibration.",
        ),
        _ext(
            "EXT_DTC_ONSET",
            source_lookup,
            "membranes_2021_electropolymerization.pdf",
            "DTC",
            "3,6-di(2-thienyl)carbazole",
            "c1ccc(s1)-c1ccc2[nH]c3ccc(-c4cccs4)cc3c2c1",
            "carbazole",
            "monomer_oxidation_onset",
            "CLEAN_CV_ONSET_AGAGCL",
            0.88,
            "Ag/AgCl",
            "agagcl",
            "Direct Ag/AgCl reference.",
            "",
            0,
            0.88,
            "acetonitrile",
            "acetonitrile",
            "",
            "0.2 M LiClO4",
            0.2,
            0.002,
            "ITO",
            "Pt",
            100,
            "cyclic voltammetry",
            "first scan",
            "10.3390/membranes11020125",
            "Membranes 2021 electrochromic polymer membranes",
            "Figure 2; electrooxidation curve text",
            "Monomer list in experimental/synthesis section",
            "Eonset values for DTC/BTP/TF reported vs Ag/AgCl.",
            "ADD_NEW_BENCHMARK_ROW",
            "",
            "Clean direct-Ag/AgCl monomer onset.",
        ),
        _ext(
            "EXT_BTP_ONSET",
            source_lookup,
            "membranes_2021_electropolymerization.pdf",
            "BTP",
            "2,2'-bithiophene",
            "c1csc(-c2cccs2)c1",
            "thiophene_oligomer",
            "monomer_oxidation_onset",
            "CLEAN_CV_ONSET_AGAGCL",
            1.22,
            "Ag/AgCl",
            "agagcl",
            "Direct Ag/AgCl reference.",
            "",
            0,
            1.22,
            "acetonitrile",
            "acetonitrile",
            "",
            "0.2 M LiClO4",
            0.2,
            0.002,
            "ITO",
            "Pt",
            100,
            "cyclic voltammetry",
            "first scan",
            "10.3390/membranes11020125",
            "Membranes 2021 electrochromic polymer membranes",
            "Figure 2; electrooxidation curve text",
            "Commercial monomer label",
            "BTP Eonset reported as 1.22 V vs Ag/AgCl.",
            "ADD_NEW_BENCHMARK_ROW",
            "",
            "Direct-Ag/AgCl onset is separate from Camarada steady-state BTP row.",
        ),
        _ext(
            "EXT_TF_ONSET",
            source_lookup,
            "membranes_2021_electropolymerization.pdf",
            "TF",
            "2-(2-thienyl)furan",
            "c1oc(cc1)c2cccs2",
            "furan_thiophene",
            "monomer_oxidation_onset",
            "CLEAN_CV_ONSET_AGAGCL",
            1.19,
            "Ag/AgCl",
            "agagcl",
            "Direct Ag/AgCl reference.",
            "",
            0,
            1.19,
            "acetonitrile",
            "acetonitrile",
            "",
            "0.2 M LiClO4",
            0.2,
            0.002,
            "ITO",
            "Pt",
            100,
            "cyclic voltammetry",
            "first scan",
            "10.3390/membranes11020125",
            "Membranes 2021 electrochromic polymer membranes",
            "Figure 2; electrooxidation curve text",
            "Monomer list in experimental/synthesis section",
            "TF Eonset reported as 1.19 V vs Ag/AgCl.",
            "ADD_NEW_BENCHMARK_ROW",
            "",
            "Clean direct-Ag/AgCl monomer onset.",
        ),
        _ext(
            "EXT_ALKYNEDTP_ONSET",
            source_lookup,
            "bandera_2022_alkyne_dtp.pdf",
            "AlkyneDTP",
            "N-but-3-ynyl dithieno[3,2-b:2',3'-d]pyrrole",
            "C#CCCCN1c2sccc2c2ccsc21",
            "dithienopyrrole",
            "monomer_oxidation_onset",
            "CLEAN_CV_ONSET_AGAGCL",
            0.77,
            "Ag/AgCl",
            "agagcl",
            "Direct Ag/AgCl reference.",
            "",
            0,
            0.77,
            "acetonitrile",
            "acetonitrile",
            "",
            "0.1 M TBAPF6",
            0.1,
            0.0025,
            "Pt button",
            "Pt wire",
            100,
            "cyclic voltammetry",
            "first cycle",
            "10.1039/D2RA03265A",
            "Bandera et al. 2022 alkyne-DTP electropolymerization",
            "Experimental electrochemistry; Figure 2; onset discussion",
            "Scheme 1",
            "First-cycle irreversible monomer peak onset reported as 770 mV.",
            "ADD_NEW_BENCHMARK_ROW",
            "",
            "Exact structure, first-cycle onset, MeCN/TBAPF6, and Ag/AgCl are all supported.",
        ),
        _ext_blocked(
            "EXT_DTPNAP_ONSET",
            source_lookup,
            "bandera_2022_alkyne_dtp.pdf",
            "DTPNap",
            "naphthalimide dithienopyrrole derivative",
            "",
            "dithienopyrrole",
            0.20,
            "Ag/AgCl",
            "agagcl",
            "DCM",
            "DCM",
            "0.1 M TBAPF6",
            "10.1039/D2RA03265A",
            "Bandera et al. 2022",
            "Scheme 4; Figure 2a",
            "STRUCTURE_BLOCKED",
            "Exact machine-auditable DTPNap structure not normalized in this review-only audit.",
        ),
    ]
    rows.extend(_edos_rows(source_lookup))
    rows.extend(_zhen_rows(source_lookup))
    rows.extend(_zhu_rows(source_lookup))
    rows.extend(_nano2025_rows(source_lookup))
    rows.extend(_nano2024_rows(source_lookup))
    rows.extend(_ijms2023_rows(source_lookup))
    rows.extend(_paywalled_rows(source_lookup))
    return rows


def _edos_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    specs = [
        ("EXT_EDOS_ACN_TBAPF6", "acetonitrile", "acetonitrile", "0.1 M TBAPF6", 0.1, 1.10),
        ("EXT_EDOS_ACN_TBABF4", "acetonitrile", "acetonitrile", "0.1 M TBABF4", 0.1, 1.13),
        ("EXT_EDOS_ACN_TBACLO4", "acetonitrile", "acetonitrile", "0.1 M TBAClO4", 0.1, 1.09),
        ("EXT_EDOS_PC_TBAPF6", "propylene carbonate", "propylene carbonate", "0.1 M TBAPF6", 0.1, 1.11),
        ("EXT_EDOS_PC_TBABF4", "propylene carbonate", "propylene carbonate", "0.1 M TBABF4", 0.1, 1.07),
        ("EXT_EDOS_PC_TBACLO4", "propylene carbonate", "propylene carbonate", "0.1 M TBAClO4", 0.1, 1.06),
    ]
    rows: list[dict[str, Any]] = []
    for record_id, solvent_system, solvent_name, electrolyte, concentration, potential in specs:
        rows.append(
            _ext(
                record_id,
                source_lookup,
                "yadav_2020_edos.pdf",
                "EDOS",
                "3,4-ethylenedioxyselenophene",
                "C1COc2c(O1)[se]cc2",
                "selenophene",
                "monomer_oxidation_onset",
                "UNRESOLVED_REFERENCE",
                potential,
                "Ag/Ag+",
                "native_ag_plus",
                "Native Ag/Ag+ reference; no same-experiment Ag/AgCl conversion retained.",
                "",
                "",
                "",
                solvent_system,
                solvent_name,
                "",
                electrolyte,
                concentration,
                "",
                "Pt",
                "Pt",
                "",
                "anodic oxidation curve",
                "first anodic scan",
                "10.1039/D0RA01436B",
                "Yadav et al. 2020 EDOS electropolymerization",
                "Table 1 and electrochemical discussion",
                "Monomer structure in article scheme",
                "EDOS Eox values reported in six media vs Ag/Ag+.",
                "PARK",
                "Ag/Ag+ reference is unresolved for current Ag/AgCl profile.",
                "Preserve native values; do not force-convert.",
            )
        )
    return rows


def _zhen_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    specs = [
        ("EXT_FURAN_POLARIZATION", "Fu", "furan", "c1ccoc1", 1.25),
        ("EXT_BIFURAN_POLARIZATION", "2Fu", "2,2'-bifuran", "c1cc(oc1)-c2ccoc2", 0.80),
        (
            "EXT_TERFURAN_POLARIZATION",
            "3Fu",
            "2,2':5',2''-terfuran",
            "c1cc(oc1)-c2cc(oc2)-c3ccoc3",
            0.70,
        ),
    ]
    rows: list[dict[str, Any]] = []
    for record_id, label, name, smiles, potential in specs:
        rows.append(
            _ext(
                record_id,
                source_lookup,
                "zhen_2014_oligofuran.pdf",
                label,
                name,
                smiles,
                "furan_oligomer",
                "monomer_oxidation_onset",
                "NON_CV_POLARIZATION_ONSET",
                potential,
                "Ag/AgCl",
                "agagcl",
                "Direct Ag/AgCl reference.",
                "",
                0,
                potential,
                "CH2Cl2",
                "DCM",
                "",
                "0.1 M Bu4NPF6",
                0.1,
                0.01,
                "Pt",
                "Pt",
                "",
                "anodic polarization",
                "source reported",
                "10.1039/C4RA00437J",
                "Zhen et al. 2014 furan-based monomers",
                "Section 3.2.1 anodic polarization curves",
                "Article structures",
                "Onset oxidation potentials reported from anodic polarization curves.",
                "PARK",
                "Method is anodic polarization, not clean CV.",
                "Classified by actual method despite onset wording.",
            )
        )
    return rows


def _zhu_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    specs = [
        ("M1", -0.05, "DCM/ACN", "4:1 v/v", "MIXED_SOLVENT_PARKED"),
        ("M2", 0.10, "DCM/ACN", "3:1 v/v", "MIXED_SOLVENT_PARKED"),
        ("M3", 0.13, "DCM/ACN", "3:1 v/v", "MIXED_SOLVENT_PARKED"),
        ("M4", 0.27, "DCM", "", "STRUCTURE_BLOCKED"),
        ("M5", 0.06, "DCM", "", "STRUCTURE_BLOCKED"),
        ("M6", 0.12, "DCM", "", "STRUCTURE_BLOCKED"),
        ("M7", 0.39, "CHCl3/ACN", "4:1 v/v", "MIXED_SOLVENT_PARKED"),
        ("M8", 0.34, "DCM/THF", "3:2 v/v", "MIXED_SOLVENT_PARKED"),
        ("M9", 0.26, "DCM", "", "STRUCTURE_BLOCKED"),
        ("M10", 0.59, "DCM", "", "REJECT"),
    ]
    rows: list[dict[str, Any]] = []
    for label, potential, solvent, composition, master_class in specs:
        blocker = "Exact machine-auditable structure not normalized; retain native Fc track only."
        disposition = "PARK"
        if master_class == "MIXED_SOLVENT_PARKED":
            blocker = "Mixed-solvent native-Fc row stays parked; no MeCN Fc conversion applied."
        if master_class == "REJECT":
            blocker = "Source states M10 was not easily electropolymerized; reject for benchmark ingest."
            disposition = "REJECT"
        rows.append(
            _ext(
                f"EXT_ZHU_{label}",
                source_lookup,
                "zhu_2017_thienothiophene_edot.pdf",
                label,
                f"Zhu 2017 monomer {label}",
                "",
                "thienothiophene_edot",
                "monomer_oxidation_onset",
                master_class if master_class != "STRUCTURE_BLOCKED" else "CLEAN_CV_ONSET_NATIVE_FC",
                potential,
                "Fc/Fc+",
                "native_fc",
                "Native Fc/Fc+ values retained; no DCM/mixed-solvent Ag/AgCl conversion.",
                "",
                "",
                "",
                solvent,
                solvent,
                composition,
                "0.1 M TBAPF6",
                0.1,
                "",
                "Pt",
                "Pt",
                100,
                "cyclic voltammetry",
                "first scan",
                "10.1007/s11426-016-0305-9",
                "Zhu et al. 2017 thienothiophene/EDOT monomers",
                "Table 1 footnote and Figure 1 discussion",
                "Scheme/table structures; not machine-normalized here",
                "Onset oxidation potentials reported vs Fc/Fc+.",
                disposition,
                blocker,
                "Native-Fc track remains separate from current Ag/AgCl pipeline.",
            )
        )
    return rows


def _nano2025_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, potential in (("4BD-EDOT", 0.85), ("3BD-EDOT", 0.95)):
        rows.append(
            _ext(
                f"EXT_NANO2025_{label.replace('-', '_')}",
                source_lookup,
                "nano_2025_edot_candidate.pdf",
                label,
                label,
                "",
                "biphenyl_edot",
                "monomer_oxidation_onset",
                "NON_CV_POLARIZATION_ONSET",
                potential,
                "Ag/AgCl",
                "agagcl",
                "Direct Ag/AgCl reference.",
                "",
                0,
                potential,
                "CH2Cl2",
                "DCM",
                "",
                "0.1 M Bu4NPF6",
                0.1,
                "",
                "Pt",
                "Pt",
                "",
                "anodic polarization",
                "source reported",
                "10.3390/nano15211643",
                "Nanomaterials 2025 biphenyl-EDOT polymers",
                "Figure 1 anodic polarization curves",
                "Article/SI structures; not machine-normalized here",
                "Polymerization potentials reported from anodic polarization curves.",
                "PARK",
                "Method is anodic polarization and structures are not normalized here.",
                "Do not treat as clean CV onset.",
            )
        )
    return rows


def _nano2024_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, potential in (("CBP", 0.86), ("TCB", 1.00), ("TPTCzSiOH", 0.85)):
        rows.append(
            _ext(
                f"EXT_NANO2024_{label}",
                source_lookup,
                "nano_2024_candidate.pdf",
                label,
                label,
                "",
                "carbazole",
                "monomer_oxidation_onset",
                "UNRESOLVED_REFERENCE",
                potential,
                "Ag/AgNO3",
                "native_ag_agno3",
                "Native Ag/AgNO3 reference; no Ag/AgCl conversion retained.",
                "",
                "",
                "",
                "acetonitrile",
                "acetonitrile",
                "",
                "0.1 M TBAP",
                0.1,
                0.0001,
                "glassy carbon",
                "Pt",
                "",
                "cyclic voltammetry",
                "source reported",
                "10.3390/nano14020180",
                "Nanomaterials 2024 microporous polymer-modified electrodes",
                "SI Table S3; electropolymerization section",
                "SI structures; not machine-normalized here",
                "Eonset rows reported vs Ag/AgNO3.",
                "PARK",
                "Ag/AgNO3 reference unresolved for current Ag/AgCl profile.",
                "Retain as provenance only.",
            )
        )
    return rows


def _ijms2023_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in ("IDOH-Th", "IDOD-Th", "IDOH-3HT", "IDOD-3HT"):
        rows.append(
            _ext_blocked(
                f"EXT_IJMS2023_{label.replace('-', '_')}",
                source_lookup,
                "ijms_2023_candidate.pdf",
                label,
                label,
                "",
                "isoindigo_thiophene",
                "",
                "Ag/AgCl",
                "agagcl",
                "CH2Cl2",
                "DCM",
                "0.1 M Bu4NPF6",
                "10.3390/ijms24032219",
                "IJMS 2023 isoindigo-thiophene electrosynthesis",
                "CV/anodic oxidation section; table text not reliably machine-extracted",
                "PROVENANCE_BLOCKED",
                "Exact per-monomer Eonset values and structures require manual table normalization.",
            )
        )
    return rows


def _paywalled_rows(source_lookup: dict[str, str]) -> list[dict[str, Any]]:
    specs = [
        (
            "EXT_JELECHEM2015_PAYWALLED",
            "jelechem_2015_candidate.pdf",
            "10.1016/j.jelechem.2015.04.041",
            "Electrochemical synthesis of new conjugated polymers based on carbazole and furan units",
        ),
        (
            "EXT_THINSOLID2012_PAYWALLED",
            "thin_solid_films_2012_candidate.pdf",
            "10.1016/j.thinsolidfilms.2012.10.050",
            "Thin Solid Films 2012 candidate",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for record_id, filename, doi, title in specs:
        rows.append(
            _ext_blocked(
                record_id,
                source_lookup,
                filename,
                title,
                title,
                "",
                "",
                "",
                "",
                "agagcl",
                "",
                "",
                "",
                doi,
                title,
                "DOI resolver/publisher landing only; no lawful open PDF downloaded",
                "PROVENANCE_BLOCKED",
                "No lawful open PDF was retrieved; do not use for production ingest.",
            )
        )
    return rows


def _ext(
    record_id: str,
    source_lookup: dict[str, str],
    filename_hint: str,
    source_record_label: str,
    exact_monomer_name: str,
    input_smiles: str,
    monomer_class: str,
    label_type: str,
    master_label_class: str,
    potential_original_v: object,
    reference_electrode_original: str,
    reference_frame: str,
    reference_calibration_text: str,
    conversion_equation: str,
    conversion_to_agagcl_v: object,
    potential_vs_agagcl_v: object,
    solvent_system: str,
    solvent_name: str,
    solvent_composition: str,
    supporting_electrolyte: str,
    electrolyte_concentration_m: object,
    monomer_concentration_m: object,
    working_electrode: str,
    counter_electrode: str,
    scan_rate_m_v_s: object,
    measurement_method: str,
    first_cycle_or_scan: str,
    source_doi: str,
    source_citation: str,
    source_locator: str,
    structure_locator: str,
    evidence_quote_short: str,
    disposition: str,
    blocking_issue: str,
    review_notes: str,
) -> dict[str, Any]:
    return {
        "record_id": record_id,
        "source_id": _source_id_for(doi=source_doi, filename_hint=filename_hint, source_lookup=source_lookup),
        "source_record_label": source_record_label,
        "exact_monomer_name": exact_monomer_name,
        "input_smiles": input_smiles,
        "monomer_class": monomer_class,
        "label_type": label_type,
        "master_label_class": master_label_class,
        "potential_original_V": potential_original_v,
        "potential_original_units": "V",
        "reference_electrode_original": reference_electrode_original,
        "reference_frame": reference_frame,
        "reference_calibration_text": reference_calibration_text,
        "conversion_equation": conversion_equation,
        "conversion_to_AgAgCl_V": conversion_to_agagcl_v,
        "potential_vs_AgAgCl_V": potential_vs_agagcl_v,
        "solvent_system": solvent_system,
        "solvent_name": solvent_name,
        "solvent_composition": solvent_composition,
        "supporting_electrolyte": supporting_electrolyte,
        "electrolyte_concentration_M": electrolyte_concentration_m,
        "monomer_concentration_M": monomer_concentration_m,
        "working_electrode": working_electrode,
        "counter_electrode": counter_electrode,
        "scan_rate_mV_s": scan_rate_m_v_s,
        "measurement_method": measurement_method,
        "first_cycle_or_scan": first_cycle_or_scan,
        "source_doi": source_doi,
        "source_citation": source_citation,
        "source_locator": source_locator,
        "structure_locator": structure_locator,
        "evidence_quote_short": evidence_quote_short,
        "production_current_status": "EXTERNAL_EVIDENCE_READY"
        if disposition == "ADD_NEW_BENCHMARK_ROW"
        else "EXTERNAL_EVIDENCE_BLOCKED",
        "production_ingest_recommended": disposition == "ADD_NEW_BENCHMARK_ROW",
        "production_correction_required": False,
        "disposition": disposition,
        "blocking_issue": blocking_issue,
        "review_notes": review_notes,
    }


def _ext_blocked(
    record_id: str,
    source_lookup: dict[str, str],
    filename_hint: str,
    source_record_label: str,
    exact_monomer_name: str,
    input_smiles: str,
    monomer_class: str,
    potential_original_v: object,
    reference_electrode_original: str,
    reference_frame: str,
    solvent_system: str,
    solvent_name: str,
    supporting_electrolyte: str,
    source_doi: str,
    source_citation: str,
    source_locator: str,
    master_label_class: str,
    blocking_issue: str,
) -> dict[str, Any]:
    return _ext(
        record_id,
        source_lookup,
        filename_hint,
        source_record_label,
        exact_monomer_name,
        input_smiles,
        monomer_class,
        "monomer_oxidation_onset",
        master_label_class,
        potential_original_v,
        reference_electrode_original,
        reference_frame,
        "",
        "",
        "",
        "",
        solvent_system,
        solvent_name,
        "",
        supporting_electrolyte,
        _electrolyte_concentration(supporting_electrolyte),
        "",
        "",
        "",
        "",
        "cyclic voltammetry",
        "source reported",
        source_doi,
        source_citation,
        source_locator,
        "not normalized",
        blocking_issue,
        "PARK" if master_label_class != "REJECT" else "REJECT",
        blocking_issue,
        "Provenance retained for later manual normalization.",
    )


def _materialize_master_row(row: dict[str, Any]) -> dict[str, Any]:
    rdkit = canonicalize_smiles(_clean(row.get("input_smiles", "")))
    materialized = {column: "" for column in MASTER_EVIDENCE_COLUMNS}
    materialized.update({key: _clean(value) for key, value in row.items() if key in MASTER_EVIDENCE_COLUMNS})
    materialized["canonical_smiles"] = rdkit["canonical_smiles"]
    materialized["inchikey"] = rdkit["inchikey"]
    materialized["rdkit_parse_ok"] = bool(rdkit["rdkit_parse_ok"])
    materialized["literature_cv_clean"] = _is_literature_clean(row)
    materialized["current_pipeline_comparable"] = _is_current_pipeline_comparable(row, rdkit)
    materialized["directive_quantity_eligible"] = materialized["current_pipeline_comparable"]
    materialized["onset_profile_eligible"] = (
        materialized["current_pipeline_comparable"]
        and materialized["master_label_class"] == "CLEAN_CV_ONSET_AGAGCL"
    )
    materialized["peak_profile_eligible"] = (
        materialized["current_pipeline_comparable"]
        and materialized["master_label_class"] == "CLEAN_CV_PEAK_AGAGCL"
    )
    materialized["native_fc_profile_eligible"] = (
        materialized["literature_cv_clean"]
        and rdkit["rdkit_parse_ok"]
        and materialized["master_label_class"] in {"CLEAN_CV_ONSET_NATIVE_FC", "CLEAN_CV_PEAK_NATIVE_FC"}
    )
    materialized["production_ingest_recommended"] = _bool_value(
        row.get("production_ingest_recommended", False)
    )
    materialized["production_correction_required"] = _bool_value(
        row.get("production_correction_required", False)
    )
    materialized["experimental_measurement_id"] = experimental_measurement_id(materialized)
    materialized["directive_combination_id"] = directive_combination_id(materialized)
    materialized["current_model_group_id"] = current_model_group_id(materialized)
    materialized["duplicate_of_record_id"] = ""
    if materialized["disposition"] not in DISPOSITIONS:
        materialized["disposition"] = "PARK"
    return materialized


def _is_literature_clean(row: dict[str, Any]) -> bool:
    return _clean(row.get("master_label_class")) in {
        "CLEAN_CV_ONSET_AGAGCL",
        "CLEAN_CV_PEAK_AGAGCL",
        "CLEAN_CV_ONSET_NATIVE_FC",
        "CLEAN_CV_PEAK_NATIVE_FC",
    }


def _is_current_pipeline_comparable(row: dict[str, Any], rdkit: dict[str, Any]) -> bool:
    return (
        bool(rdkit["rdkit_parse_ok"])
        and _clean(row.get("master_label_class")) in {"CLEAN_CV_ONSET_AGAGCL", "CLEAN_CV_PEAK_AGAGCL"}
        and not _clean(row.get("blocking_issue"))
        and _clean(row.get("reference_frame")) == "agagcl"
        and _clean(row.get("potential_vs_AgAgCl_V")) != ""
    )


def _best_row(group: pd.DataFrame) -> pd.Series:
    priority = {
        "CLEAN_CV_ONSET_AGAGCL": 0,
        "CLEAN_CV_PEAK_AGAGCL": 1,
        "CLEAN_CV_ONSET_NATIVE_FC": 2,
        "CLEAN_CV_PEAK_NATIVE_FC": 3,
        "NON_CV_STEADY_STATE": 4,
        "NON_CV_POLARIZATION_ONSET": 5,
        "MIXED_SOLVENT_PARKED": 6,
        "SOURCE_CONFLICT": 7,
        "UNRESOLVED_REFERENCE": 8,
        "STRUCTURE_BLOCKED": 9,
        "PROVENANCE_BLOCKED": 10,
        "REJECT": 11,
    }
    sortable = group.assign(_priority=group["master_label_class"].map(priority).fillna(99))
    return sortable.sort_values(by=["_priority", "record_id"], kind="mergesort").iloc[0]


def _coverage_status(group: pd.DataFrame) -> str:
    if bool(group["directive_quantity_eligible"].map(_bool_value).any()):
        if (group["production_current_status"] == "CURRENT_PRODUCTION_OK").any():
            return "CURRENT_PRODUCTION_ELIGIBLE"
        return "NEW_ELIGIBLE_PROPOSAL"
    if bool(group["production_correction_required"].map(_bool_value).any()):
        return "CURRENT_PRODUCTION_CORRECTION_REQUIRED"
    classes = set(group["master_label_class"])
    if "SOURCE_CONFLICT" in classes:
        return "SOURCE_CONFLICT_BLOCKED"
    if "MIXED_SOLVENT_PARKED" in classes:
        return "MIXED_SOLVENT_PARKED"
    if "UNRESOLVED_REFERENCE" in classes:
        return "REFERENCE_BLOCKED"
    if "STRUCTURE_BLOCKED" in classes:
        return "STRUCTURE_BLOCKED"
    if "PROVENANCE_BLOCKED" in classes:
        return "PROVENANCE_BLOCKED"
    if "NON_CV_POLARIZATION_ONSET" in classes:
        return "NON_CV_METHOD_PARKED"
    if "REJECT" in classes:
        return "REJECTED"
    return "PARKED"


def _proposal_action(row: dict[str, Any]) -> str:
    if _bool_value(row["production_correction_required"]):
        return "MARK_CALIBRATION_INELIGIBLE"
    if row["disposition"] == "ADD_NEW_BENCHMARK_ROW":
        return "ADD_NEW_BENCHMARK_ROW"
    if row["disposition"] == "REJECT":
        return "REJECT"
    return "PARK"


def _proposal_reason(row: dict[str, Any], action: str) -> str:
    if action == "MARK_CALIBRATION_INELIGIBLE":
        return "Current production row is non-CV steady-state evidence and should not feed CV/onset profiles."
    if action == "ADD_NEW_BENCHMARK_ROW":
        return "Clean direct-Ag/AgCl CV onset evidence is ready for a separate production-ingest review."
    if action == "REJECT":
        return "Source or method explicitly blocks benchmark use."
    return "Evidence is retained but blocked by method, reference, structure, mixed solvent, or provenance."


def _source_lookup(source_manifest: pd.DataFrame) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for row in source_manifest.to_dict(orient="records"):
        source_id = _clean(row["source_id"])
        filename = _clean(row["canonical_filename"])
        doi = _clean(row["doi"])
        if filename:
            lookup[f"filename:{filename}"] = source_id
        if doi:
            lookup.setdefault(f"doi:{doi}", source_id)
    return lookup


def _source_id_for(*, doi: str, filename_hint: str, source_lookup: dict[str, str]) -> str:
    doi_key = f"doi:{_clean(doi)}"
    if _clean(doi) and doi_key in source_lookup:
        return source_lookup[doi_key]
    filename = _clean(filename_hint)
    if filename:
        direct_key = f"filename:{filename}"
        if direct_key in source_lookup:
            return source_lookup[direct_key]
        for key, source_id in source_lookup.items():
            if key.startswith("filename:") and filename in key:
                return source_id
    return ""


def _source_hint_from_citation(citation: str) -> str:
    text = citation.lower()
    if "novel donor-acceptor" in text or "liu" in text:
        return "liu_2016_thiadiazolopyridine.pdf"
    if "pyrido[4,3-b]pyrazine" in text or "polym8100377" in text:
        return "zhang_2016_pyridopyrazine_main.pdf"
    if "neutral cyan" in text or "polym9120656" in text:
        return "kong_2017_quinoxaline_main.pdf"
    return ""


def _main_or_si(filename: str, source_type: str) -> str:
    if source_type == "repository_table":
        return "repo"
    if source_type == "supporting_information" or "_si" in filename or filename.endswith(".zip"):
        return "supporting_information"
    if source_type in {"research_report", "research_audit"}:
        return "research_context"
    return "main_article"


def _evidence_role(filename: str, source_type: str, status: str) -> str:
    if status == "MISSING_PAYWALLED":
        return "provenance_blocked"
    if source_type in {"research_report", "research_audit"}:
        return "research_context"
    if "camarada" in filename:
        return "production_ontology_check"
    if any(token in filename for token in ("zhang_2016", "kong_2017", "liu_2016")):
        return "r11_r21_staging_check"
    return "external_candidate_check"


def _manifest_notes(row: dict[str, Any]) -> str:
    notes = _clean(row["notes"])
    original = _clean(row["original_local_path"])
    notes = re.sub(r"; same-sha duplicates: [^;]+", "; same-sha duplicates redacted", notes)
    if original:
        notes = f"{notes}; original_path_redacted"
    return notes.replace(str(Path.home()), "$HOME")


def _validate_enum(frame: pd.DataFrame, column: str, allowed: Iterable[str]) -> None:
    allowed_set = set(allowed)
    invalid = sorted({_clean(value) for value in frame[column] if _clean(value) not in allowed_set})
    if invalid:
        raise ValueError(f"{column} has invalid values: {', '.join(invalid)}")


def _refuse_forbidden_output(path: Path, repo_root: Path) -> None:
    resolved = path.resolve()
    root = repo_root.resolve()
    data_root = (root / "data").resolve()
    lit_root = (root / "data" / "lit_curation").resolve()
    forbidden_roots = (
        (root / "configs").resolve(),
        (root / "src" / "eps" / "scoring").resolve(),
        (root / "src" / "eps" / "redox").resolve(),
        (root / "src" / "eps" / "validation").resolve(),
    )
    production_csvs = {
        (root / "data" / "benchmark.csv").resolve(),
        (root / "data" / "benchmark_candidates.csv").resolve(),
        (root / "data" / "monomers.csv").resolve(),
        (root / "data" / "solvents.csv").resolve(),
        (root / "data" / "electrolytes.csv").resolve(),
    }
    if resolved.suffix.lower() == ".csv" and resolved in production_csvs:
        raise ValueError(f"Refusing to write review-only G1.2 Eox output to production CSV: {path}")
    if resolved.suffix.lower() == ".csv" and _is_relative_to(resolved, data_root) and not _is_relative_to(
        resolved, lit_root
    ):
        raise ValueError(f"Refusing to write review-only G1.2 Eox output outside data/lit_curation: {path}")
    for forbidden in forbidden_roots:
        if _is_relative_to(resolved, forbidden):
            raise ValueError(f"Refusing to write review-only G1.2 Eox output to forbidden surface: {path}")


def _electrolyte_concentration(electrolyte: object) -> str:
    text = _clean(electrolyte)
    for token in text.split():
        try:
            float(token)
        except ValueError:
            continue
        return token
    return ""


def _value_counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().sort_index().items()}


def _label_bucket(label_type: object) -> str:
    text = _clean(label_type).lower()
    if "onset" in text:
        return "onset"
    if "peak" in text or "epa" in text:
        return "peak"
    return "other"


def _record_sort_key(value: object) -> tuple[int, int, str]:
    text = _clean(value)
    prefix_order = 3
    numeric = 9999
    if text.startswith("PROD"):
        prefix_order = 0
        numeric = _safe_int(text.removeprefix("PROD"))
    elif text.startswith("R"):
        prefix_order = 1
        numeric = _safe_int(text.removeprefix("R"))
    elif text.startswith("EXT"):
        prefix_order = 2
    return (prefix_order, numeric, text)


def _safe_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 9999


def _pipe_key(*parts: object) -> str:
    return "|".join(_clean(part).lower() for part in parts)


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _bool_value(value: object) -> bool:
    if pd.api.types.is_bool(value):
        return bool(value)
    text = _clean(value)
    if text in {"true", "True", "1"}:
        return True
    if text in {"false", "False", "0", ""}:
        return False
    return bool(value)


def _as_float(value: object) -> float | None:
    try:
        text = _clean(value)
        return float(text) if text else None
    except (TypeError, ValueError):
        return None


def _sha256_or_missing(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def _git_sha(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--external-manifest", type=Path, default=DEFAULT_EXTERNAL_MANIFEST_PATH)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK_PATH)
    parser.add_argument("--r11-r21-review", type=Path, default=DEFAULT_R11_R21_REVIEW_PATH)
    parser.add_argument("--source-manifest-out", type=Path, default=DEFAULT_SOURCE_MANIFEST_OUT)
    parser.add_argument("--master-evidence-out", type=Path, default=DEFAULT_MASTER_EVIDENCE_OUT)
    parser.add_argument("--combination-summary-out", type=Path, default=DEFAULT_COMBINATION_SUMMARY_OUT)
    parser.add_argument(
        "--production-change-proposal-out",
        type=Path,
        default=DEFAULT_PRODUCTION_CHANGE_PROPOSAL_OUT,
    )
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    args = parser.parse_args()

    result = build_eox_g1_2_master_audit(
        repo_root=args.repo_root,
        external_manifest_path=args.external_manifest,
        benchmark_path=args.benchmark,
        r11_r21_review_path=args.r11_r21_review,
        source_manifest_out=args.source_manifest_out,
        master_evidence_out=args.master_evidence_out,
        combination_summary_out=args.combination_summary_out,
        production_change_proposal_out=args.production_change_proposal_out,
        report_out=args.report_out,
    )
    print(
        "Built G1.2 Eox master audit: "
        f"{result.summary['master_rows']} rows, "
        f"{result.summary['directive_quantity_eligible_combinations']} eligible combinations, "
        f"{result.summary['directive_gte_30_status']}."
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from rdkit import Chem


CLASSIFICATIONS = (
    "PROMOTE_NOW_CANDIDATE",
    "NEEDS_SOURCE_CHECK",
    "NEEDS_REFERENCE_CONVERSION_CHECK",
    "NEEDS_STRUCTURE_CHECK",
    "NEEDS_CONDITION_MATCH_CHECK",
    "PARK",
    "REJECT",
)


@dataclass(frozen=True)
class StagingSpec:
    path: str
    required_columns: tuple[str, ...]
    smiles_fields: tuple[str, ...] = ()
    key_fields: tuple[str, ...] = ()


STAGING_SPECS = (
    StagingSpec(
        path="data/lit_curation/solvent_esw_staging.csv",
        required_columns=(
            "solvent",
            "anodic_limit_orig_V",
            "cathodic_limit_orig_V",
            "reference_electrode",
            "supporting_electrolyte",
            "working_electrode",
            "cutoff_criterion",
            "anodic_limit_vs_AgAgCl_V",
            "cathodic_limit_vs_AgAgCl_V",
            "conversion",
            "source_doi",
            "citation",
            "confidence",
            "flags",
            "needs_review",
        ),
        key_fields=(
            "solvent",
            "supporting_electrolyte",
            "working_electrode",
            "reference_electrode",
            "anodic_limit_orig_V",
            "cathodic_limit_orig_V",
            "source_doi",
        ),
    ),
    StagingSpec(
        path="data/lit_curation/polymerization_outcomes_staging.csv",
        required_columns=(
            "monomer",
            "smiles",
            "outcome",
            "conditions",
            "source_doi",
            "citation",
            "confidence",
            "name_in_library",
            "needs_review",
        ),
        smiles_fields=("smiles",),
        key_fields=("canonical_smiles", "outcome", "source_doi"),
    ),
    StagingSpec(
        path="data/lit_curation/optical_anchors_selected.csv",
        required_columns=(
            "polymer",
            "monomer_smiles",
            "optical_gap_eV",
            "gap_method",
            "doping_onset_orig_V",
            "reference_electrode",
            "doping_onset_vs_AgAgCl_V",
            "conversion",
            "source_doi",
            "citation",
            "flags",
            "needs_review",
            "monomer_class",
            "selected_reason",
            "anchor_confidence",
        ),
        smiles_fields=("monomer_smiles",),
        key_fields=("canonical_smiles", "optical_gap_eV", "source_doi"),
    ),
    StagingSpec(
        path="data/lit_curation/solubility_staging.csv",
        required_columns=(
            "monomer",
            "solvent",
            "solubility_value",
            "units",
            "temperature_C",
            "value_type",
            "source_doi",
            "citation",
            "needs_review",
        ),
        key_fields=("monomer", "solvent", "solubility_value", "units", "source_doi"),
    ),
    StagingSpec(
        path="data/lit_curation/optical_doping_staging.csv",
        required_columns=(
            "polymer",
            "monomer_smiles",
            "optical_gap_eV",
            "gap_method",
            "doping_onset_orig_V",
            "reference_electrode",
            "doping_onset_vs_AgAgCl_V",
            "conversion",
            "source_doi",
            "citation",
            "flags",
            "needs_review",
        ),
        smiles_fields=("monomer_smiles",),
        key_fields=("canonical_smiles", "optical_gap_eV", "doping_onset_orig_V", "source_doi"),
    ),
)


def canonicalize_smiles(smiles: Any) -> tuple[str, str]:
    """Return a canonical RDKit SMILES string for a neutral or charged species, or an error message."""

    text = _clean(smiles)
    if not text:
        return "", ""
    mol = Chem.MolFromSmiles(text, sanitize=True)
    if mol is None:
        return "", f"RDKit could not parse SMILES: {text}"
    return Chem.MolToSmiles(mol, canonical=True), ""


def audit_staging(
    repo_root: Path,
    summary_path: Path | None = None,
    issues_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Audit literature-curation staging CSVs without modifying production inputs."""

    repo_root = repo_root.resolve()
    production = _load_production_indexes(repo_root)
    issue_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for spec in STAGING_SPECS:
        path = repo_root / spec.path
        if not path.exists():
            issue_rows.append(
                {
                    "file": spec.path,
                    "row_number": "",
                    "source_key": "",
                    "classification": "NEEDS_SOURCE_CHECK",
                    "canonical_smiles": "",
                    "duplicate_internal": False,
                    "duplicate_production": False,
                    "issue_type": "missing_file",
                    "message": "Expected staging file is missing.",
                }
            )
            summary_rows.append(_summary_for_missing_file(spec))
            continue

        df = pd.read_csv(path, keep_default_na=False)
        missing_columns = tuple(column for column in spec.required_columns if column not in df.columns)
        df = _add_canonical_smiles(df, spec)
        semantic_keys = [_semantic_key(row, spec) for _, row in df.iterrows()]
        duplicate_keys = {
            key for key in semantic_keys if key and semantic_keys.count(key) > 1
        }

        per_file_rows: list[dict[str, Any]] = []
        for index, row in df.iterrows():
            canonical_smiles = _clean(row.get("canonical_smiles", ""))
            invalid_smiles = _clean(row.get("_smiles_error", ""))
            duplicate_internal = semantic_keys[index] in duplicate_keys
            duplicate_production, production_message = _production_duplicate(spec, row, production)
            classification, issue_type, message = _classify_row(
                spec=spec,
                row=row,
                missing_columns=missing_columns,
                invalid_smiles=invalid_smiles,
                duplicate_internal=duplicate_internal,
                duplicate_production=duplicate_production,
                production_message=production_message,
            )
            per_file_rows.append(
                {
                    "file": spec.path,
                    "row_number": index + 2,
                    "source_key": _source_key(row),
                    "classification": classification,
                    "canonical_smiles": canonical_smiles,
                    "duplicate_internal": duplicate_internal,
                    "duplicate_production": duplicate_production,
                    "issue_type": issue_type,
                    "message": message,
                }
            )

        issue_rows.extend(per_file_rows)
        summary_rows.append(_summary_for_file(spec, df, per_file_rows, missing_columns))

    summary = pd.DataFrame(summary_rows)
    issues = pd.DataFrame(issue_rows)
    if summary_path is not None:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary.to_csv(summary_path, index=False)
    if issues_path is not None:
        issues_path.parent.mkdir(parents=True, exist_ok=True)
        issues.to_csv(issues_path, index=False)
    return summary, issues


def _add_canonical_smiles(df: pd.DataFrame, spec: StagingSpec) -> pd.DataFrame:
    df = df.copy()
    canonical_values: list[str] = []
    errors: list[str] = []
    for _, row in df.iterrows():
        row_canonicals: list[str] = []
        row_errors: list[str] = []
        for field in spec.smiles_fields:
            canonical, error = canonicalize_smiles(row.get(field, ""))
            if canonical:
                row_canonicals.append(canonical)
            if error:
                row_errors.append(f"{field}: {error}")
        canonical_values.append(";".join(row_canonicals))
        errors.append("; ".join(row_errors))
    df["canonical_smiles"] = canonical_values
    df["_smiles_error"] = errors
    return df


def _classify_row(
    *,
    spec: StagingSpec,
    row: pd.Series,
    missing_columns: tuple[str, ...],
    invalid_smiles: str,
    duplicate_internal: bool,
    duplicate_production: bool,
    production_message: str,
) -> tuple[str, str, str]:
    if missing_columns:
        return (
            "NEEDS_STRUCTURE_CHECK",
            "schema",
            f"Missing required columns: {', '.join(missing_columns)}",
        )
    if invalid_smiles:
        return "NEEDS_STRUCTURE_CHECK", "smiles_parse", invalid_smiles
    if duplicate_internal:
        return "NEEDS_SOURCE_CHECK", "internal_duplicate", "Semantic duplicate inside staging file."

    if spec.path.endswith("solvent_esw_staging.csv"):
        return _classify_solvent_esw(row, duplicate_production, production_message)
    if spec.path.endswith("polymerization_outcomes_staging.csv"):
        return _classify_polymerization(row, duplicate_production, production_message)
    if spec.path.endswith("optical_anchors_selected.csv"):
        if _has_unconverted_reference(row):
            return (
                "NEEDS_REFERENCE_CONVERSION_CHECK",
                "reference_conversion",
                "Doping onset reference is not pinned to Ag/AgCl; optical gap itself remains usable only as a staging anchor.",
            )
        return "PARK", "diagnostic_optical", "Selected optical anchor; 417587 remains diagnostic only."
    if spec.path.endswith("solubility_staging.csv"):
        solvent = _clean(row.get("solvent", "")).lower()
        if solvent not in {"acetonitrile", "propylene carbonate", "nitromethane", "nmp", "dmf", "dcm", "gbl"}:
            return (
                "NEEDS_CONDITION_MATCH_CHECK",
                "condition_match",
                "Solubility row is not in a current priority organic process solvent.",
            )
        return "NEEDS_SOURCE_CHECK", "source_check", "Solubility staging row needs human source check."
    if spec.path.endswith("optical_doping_staging.csv"):
        if _has_unconverted_reference(row):
            return (
                "NEEDS_REFERENCE_CONVERSION_CHECK",
                "reference_conversion",
                "Doping onset is not convertible under pinned reference conventions.",
            )
        return "PARK", "diagnostic_optical", "Optical/doping staging is not part of this production ingest."
    return "PARK", "not_targeted", "No targeted promotion rule for this staging file."


def _classify_solvent_esw(
    row: pd.Series,
    duplicate_production: bool,
    production_message: str,
) -> tuple[str, str, str]:
    flags = _clean(row.get("flags", "")).lower()
    reference = _clean(row.get("reference_electrode", "")).lower()
    conversion = _clean(row.get("conversion", "")).lower()
    confidence = _clean(row.get("confidence", "")).lower()
    converted = _is_number(row.get("anodic_limit_vs_AgAgCl_V", "")) and _is_number(
        row.get("cathodic_limit_vs_AgAgCl_V", "")
    )
    if "likely swapped" in flags:
        return "REJECT", "known_extraction_error", "Anodic/cathodic assignment is flagged as likely swapped."
    if not converted:
        return (
            "NEEDS_REFERENCE_CONVERSION_CHECK",
            "reference_conversion",
            "No pinned Ag/AgCl conversion is available for this reference/solvent.",
        )
    if any(token in flags or token in reference or token in conversion for token in ("dmfc", "li/li", "ag/ag+")):
        return (
            "NEEDS_REFERENCE_CONVERSION_CHECK",
            "reference_conversion",
            "Reference scale requires a source-specific conversion check.",
        )
    if duplicate_production:
        return "PARK", "production_duplicate", production_message
    if confidence in {"high", "med", "medium"} and _clean(row.get("source_doi", "")):
        return "PROMOTE_NOW_CANDIDATE", "promotion_candidate", "Converted conditioned ESW row is review-ready."
    return "NEEDS_SOURCE_CHECK", "source_check", "Low-confidence ESW row needs primary-source check."


def _classify_polymerization(
    row: pd.Series,
    duplicate_production: bool,
    production_message: str,
) -> tuple[str, str, str]:
    if duplicate_production:
        return "PARK", "production_duplicate", production_message
    confidence = _clean(row.get("confidence", "")).lower()
    outcome = _clean(row.get("outcome", "")).lower()
    text = " ".join(
        [
            outcome,
            _clean(row.get("conditions", "")).lower(),
            _clean(row.get("citation", "")).lower(),
        ]
    )
    if not _clean(row.get("source_doi", "")):
        return "NEEDS_SOURCE_CHECK", "source_check", "No DOI or stable source identifier is recorded."
    if outcome == "conditional":
        if any(
            token in text
            for token in (
                "does not",
                "no film",
                "failed",
                "degradation",
                "over-oxidation",
                "poorly conducting",
                "soluble",
            )
        ):
            return (
                "NEEDS_CONDITION_MATCH_CHECK",
                "condition_match",
                "Conditional row contains possible negative evidence but must be mapped to an explicit triad condition.",
            )
        return "NEEDS_CONDITION_MATCH_CHECK", "condition_match", "Conditional outcome needs binary mapping."
    if outcome == "yes" and confidence in {"high", "med", "medium"}:
        return "PROMOTE_NOW_CANDIDATE", "promotion_candidate", "Positive film-growth evidence is review-ready."
    return "NEEDS_SOURCE_CHECK", "source_check", "Outcome needs source-confidence review."


def _has_unconverted_reference(row: pd.Series) -> bool:
    native = _clean(row.get("doping_onset_orig_V", ""))
    converted = _clean(row.get("doping_onset_vs_AgAgCl_V", ""))
    flags = _clean(row.get("flags", "")).lower()
    conversion = _clean(row.get("conversion", "")).lower()
    return bool(native) and (not converted or "omitted" in flags or "pinned only" in conversion)


def _summary_for_file(
    spec: StagingSpec,
    df: pd.DataFrame,
    rows: list[dict[str, Any]],
    missing_columns: tuple[str, ...],
) -> dict[str, Any]:
    classifications = {classification: 0 for classification in CLASSIFICATIONS}
    for row in rows:
        classifications[row["classification"]] += 1
    parsed_smiles = sum(1 for value in df["canonical_smiles"] if _clean(value))
    invalid_smiles = sum(1 for value in df["_smiles_error"] if _clean(value))
    summary = {
        "file": spec.path,
        "rows": len(df),
        "columns_ok": not missing_columns,
        "missing_columns": ";".join(missing_columns),
        "smiles_fields": ";".join(spec.smiles_fields),
        "rdkit_valid_smiles": parsed_smiles,
        "rdkit_invalid_smiles": invalid_smiles,
        "internal_duplicate_rows": sum(bool(row["duplicate_internal"]) for row in rows),
        "production_duplicate_rows": sum(bool(row["duplicate_production"]) for row in rows),
    }
    summary.update(classifications)
    return summary


def _summary_for_missing_file(spec: StagingSpec) -> dict[str, Any]:
    summary = {
        "file": spec.path,
        "rows": 0,
        "columns_ok": False,
        "missing_columns": "FILE_MISSING",
        "smiles_fields": ";".join(spec.smiles_fields),
        "rdkit_valid_smiles": 0,
        "rdkit_invalid_smiles": 0,
        "internal_duplicate_rows": 0,
        "production_duplicate_rows": 0,
    }
    summary.update({classification: 0 for classification in CLASSIFICATIONS})
    summary["NEEDS_SOURCE_CHECK"] = 1
    return summary


def _semantic_key(row: pd.Series, spec: StagingSpec) -> str:
    parts = [_clean(row.get(field, "")).lower() for field in spec.key_fields]
    return "|".join(parts)


def _production_duplicate(
    spec: StagingSpec,
    row: pd.Series,
    production: dict[str, set[tuple[Any, ...]]],
) -> tuple[bool, str]:
    if spec.path.endswith("solvent_esw_staging.csv"):
        if not (
            _is_number(row.get("anodic_limit_vs_AgAgCl_V", ""))
            and _is_number(row.get("cathodic_limit_vs_AgAgCl_V", ""))
        ):
            return False, ""
        key = (
            _clean(row.get("solvent", "")).lower(),
            round(float(row.get("anodic_limit_vs_AgAgCl_V")), 3),
            round(float(row.get("cathodic_limit_vs_AgAgCl_V")), 3),
        )
        if key in production["solvent_window_limits"]:
            return True, "Same solvent and Ag/AgCl limits already exist in production ESW/benchmark data."
    if spec.path.endswith("polymerization_outcomes_staging.csv"):
        canonical = _clean(row.get("canonical_smiles", ""))
        solvent = _clean(row.get("conditions", "")).lower()
        outcome = _clean(row.get("outcome", "")).upper()
        if canonical and any(key[0] == canonical and key[2] == outcome for key in production["polymer_labels"]):
            if not solvent or any(key[1] in solvent for key in production["polymer_labels"] if key[0] == canonical):
                return True, "Same molecule/outcome is already represented in production polymerizability labels."
    return False, ""


def _load_production_indexes(repo_root: Path) -> dict[str, set[tuple[Any, ...]]]:
    solvent_window_limits: set[tuple[Any, ...]] = set()
    for rel_path, anodic_col, cathodic_col in (
        (
            "data/solvent_windows.csv",
            "anodic_limit_V_vs_AgAgCl",
            "cathodic_limit_V_vs_AgAgCl",
        ),
        ("data/solvent_benchmark.csv", "exp_anodic_V_vs_AgAgCl", "exp_cathodic_V_vs_AgAgCl"),
    ):
        path = repo_root / rel_path
        if path.exists():
            df = pd.read_csv(path, keep_default_na=False)
            for _, row in df.iterrows():
                if _is_number(row.get(anodic_col, "")) and _is_number(row.get(cathodic_col, "")):
                    solvent_window_limits.add(
                        (
                            _clean(row.get("solvent", "")).lower(),
                            round(float(row.get(anodic_col)), 3),
                            round(float(row.get(cathodic_col)), 3),
                        )
                    )

    polymer_labels: set[tuple[Any, ...]] = set()
    path = repo_root / "data/polymerizability_labels.csv"
    if path.exists():
        df = pd.read_csv(path, keep_default_na=False)
        for _, row in df.iterrows():
            canonical, _ = canonicalize_smiles(row.get("monomer_smiles", ""))
            if canonical:
                polymer_labels.add(
                    (
                        canonical,
                        _clean(row.get("solvent", "")).lower(),
                        _clean(row.get("outcome", "")).upper(),
                    )
                )
    return {
        "solvent_window_limits": solvent_window_limits,
        "polymer_labels": polymer_labels,
    }


def _source_key(row: pd.Series) -> str:
    for field in ("monomer", "polymer", "solvent"):
        value = _clean(row.get(field, ""))
        if value:
            return value
    return _clean(row.get("source_doi", ""))


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _is_number(value: Any) -> bool:
    try:
        if not _clean(value):
            return False
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("data/lit_curation/staging_audit_summary.csv"),
    )
    parser.add_argument(
        "--issues",
        type=Path,
        default=Path("data/lit_curation/staging_audit_issues.csv"),
    )
    args = parser.parse_args()
    audit_staging(args.repo_root, args.summary, args.issues)


if __name__ == "__main__":
    main()

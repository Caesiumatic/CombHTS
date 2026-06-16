"""Benchmark validation of predicted monomer oxidation potentials."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from rdkit import Chem

from eps.calibration import LinearCalibration, fit_linear_calibration
from eps.chemspace import Solvent, load_monomers, load_solvents
from eps.chemspace.models import Monomer
from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.properties import monomer_eox_vs_AgAgCl
from eps.storage import SQLiteCache

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "benchmark.csv"
DEFAULT_VALIDATION_CONFIG = PROJECT_ROOT / "configs" / "validation.yaml"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "outputs" / "validation_cache.sqlite"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "outputs" / "validation_report.csv"

ALLOWED_LABEL_TYPES = {
    "monomer_oxidation_peak",
    "monomer_oxidation_onset",
    "electropolymerization_onset",
    "electropolymerization_growth_setpoint",
    "polymer_doping_onset",
    "unknown_or_mixed",
}
CALIBRATION_LABEL_TYPES = {"monomer_oxidation_peak", "monomer_oxidation_onset"}
ALLOWED_REPORTED_POTENTIAL_TYPES = {"Epa", "Eonset", "E1/2", "setpoint", "not_reported"}
ALLOWED_REPORTED_POTENTIAL_TYPES |= {
    "first anodic oxidation value",
    "irreversible oxidation peak",
    "irreversible oxidation peak during first anodic scan",
    "experimental oxidation potential",
}
ALLOWED_SOURCE_CONFIDENCE = {"high", "medium", "low", "provisional"}
ALLOWED_MEDIUM_CLASSES = {"aqueous", "nonaqueous", "mixed"}


@dataclass(frozen=True)
class BenchmarkValidationResult:
    """Validation report for benchmark oxidation potentials."""

    rows: pd.DataFrame
    raw_benchmark_rows: int
    calibration_eligible_rows: int
    label_type_counts: dict[str, int]
    medium_class_counts: dict[str, int]
    mae_before_V: float
    mae_after_V: float
    loo_mae_after_V: float
    calibration: LinearCalibration
    tier1_xtb_target_V: float
    tier1_xtb_pass: bool
    n_calibration_points: int
    within_group_spread_V: float
    report_path: Path


def run_benchmark_validation(
    *,
    engine: Engine | None = None,
    method: str = "mock-gfn2",
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    validation_config_path: str | Path = DEFAULT_VALIDATION_CONFIG,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    media: tuple[str, ...] | None = ("nonaqueous",),
    allowed_tiers: tuple[str, ...] | None = ("A", "B"),
    collapse_duplicates: bool = True,
) -> BenchmarkValidationResult:
    """Validate predicted Eox values against benchmark CV data using MockEngine by default."""

    engine = engine or MockEngine()
    cache = SQLiteCache(cache_path)
    benchmark = _load_benchmark(benchmark_path)
    solvents = {solvent.name: solvent for solvent in load_solvents()}

    rows = []
    for row in benchmark.to_dict(orient="records"):
        solvent = _lookup_solvent(solvents, str(row["solvent_name"]))
        monomer = _benchmark_monomer(row)
        predicted = monomer_eox_vs_AgAgCl(monomer, solvent, engine, cache, method=method)
        experimental = float(row["exp_Eox_V_vs_AgAgCl"])
        group_id = _benchmark_group_id(row, monomer)
        rows.append(
            {
                **row,
                "canonical_smiles": monomer.canonical_smiles,
                "pred_Eox_V_vs_AgAgCl": predicted,
                "residual_before_V": predicted - experimental,
                "group_id": group_id,
            }
        )

    report = pd.DataFrame(rows)
    report["in_calibration_set"] = _calibration_mask(
        report,
        media=media,
        allowed_tiers=allowed_tiers,
    )
    report["calibration_exclusion_reason"] = _calibration_exclusion_reasons(
        report,
        media=media,
        allowed_tiers=allowed_tiers,
    )
    raw_benchmark_rows = int(len(report))
    calibration_eligible_rows = _calibration_eligible_count(report)
    label_type_counts = _value_counts(report, "label_type")
    medium_class_counts = _value_counts(report, "medium_class")
    calibration_rows = report[report["in_calibration_set"]].copy()
    points = _calibration_points(calibration_rows, collapse_duplicates=collapse_duplicates)
    if len(points) < 2:
        raise ValueError(
            "benchmark calibration requires at least two calibration points after "
            f"medium/tier filtering and duplicate collapsing; found {len(points)}"
        )

    calibration = fit_linear_calibration(
        points["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float),
        points["exp_Eox_V_vs_AgAgCl"].to_numpy(dtype=float),
    )
    corrected = calibration.apply(report["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float))
    report["calibrated_Eox_V_vs_AgAgCl"] = corrected
    report["residual_after_V"] = report["calibrated_Eox_V_vs_AgAgCl"] - report["exp_Eox_V_vs_AgAgCl"]

    point_pred = points["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float)
    point_exp = points["exp_Eox_V_vs_AgAgCl"].to_numpy(dtype=float)
    mae_before = _mae(point_pred - point_exp)
    mae_after = _mae(calibration.apply(point_pred) - point_exp)
    loo_mae_after = _loo_mae(point_pred, point_exp)
    within_group_spread = _within_group_spread(calibration_rows)

    config = _load_validation_config(validation_config_path)
    tier1_target = float(config["tier1_xtb_mae_target_V"])
    tier1_pass = bool(np.isfinite(loo_mae_after) and loo_mae_after <= tier1_target)
    report["tier1_xtb_mae_target_V"] = tier1_target
    report["tier1_xtb_pass_after_calibration"] = tier1_pass

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output, index=False)

    return BenchmarkValidationResult(
        rows=report,
        raw_benchmark_rows=raw_benchmark_rows,
        calibration_eligible_rows=calibration_eligible_rows,
        label_type_counts=label_type_counts,
        medium_class_counts=medium_class_counts,
        mae_before_V=mae_before,
        mae_after_V=mae_after,
        loo_mae_after_V=loo_mae_after,
        calibration=calibration,
        tier1_xtb_target_V=tier1_target,
        tier1_xtb_pass=tier1_pass,
        n_calibration_points=len(points),
        within_group_spread_V=within_group_spread,
        report_path=output,
    )


def _load_benchmark(path: str | Path) -> pd.DataFrame:
    required = {
        "monomer_name",
        "monomer_smiles",
        "solvent_name",
        "electrolyte",
        "exp_Eox_V_vs_AgAgCl",
        "source_doi_or_ref",
    }
    frame = pd.read_csv(path, keep_default_na=False)
    missing = required.difference(frame.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required columns: {missing_list}")
    if len(frame) < 2:
        raise ValueError("benchmark validation requires at least two rows")
    _validate_benchmark_integrity(frame, path)
    _validate_benchmark_ontology(frame, path)
    return frame


def _validate_benchmark_integrity(frame: pd.DataFrame, path: str | Path) -> None:
    failures: list[str] = []
    canonical_by_index: dict[int, str] = {}

    for index, row in frame.iterrows():
        smiles = str(row["monomer_smiles"])
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None:
            failures.append(_row_label(row, index, f"invalid SMILES {smiles!r}"))
        else:
            canonical_by_index[index] = Chem.MolToSmiles(mol, canonical=True)

    if failures:
        details = "\n".join(f"  - {failure}" for failure in failures)
        raise ValueError(f"{path} contains invalid benchmark SMILES:\n{details}")

    library_by_name = {monomer.name: monomer for monomer in load_monomers()}
    for index, row in frame.iterrows():
        name = str(row["monomer_name"])
        if name not in library_by_name:
            continue
        benchmark_canonical = canonical_by_index[index]
        library_canonical = library_by_name[name].canonical_smiles
        if benchmark_canonical != library_canonical:
            raise ValueError(
                _row_label(
                    row,
                    index,
                    (
                        f"library SMILES mismatch for {name}: benchmark canonical "
                        f"{benchmark_canonical!r} != library canonical {library_canonical!r}"
                    ),
                )
            )

    if {"native_potential_V", "conversion_to_AgAgCl_V"}.issubset(frame.columns):
        native = pd.to_numeric(frame["native_potential_V"], errors="coerce")
        conversion = pd.to_numeric(frame["conversion_to_AgAgCl_V"], errors="coerce")
        experimental = pd.to_numeric(frame["exp_Eox_V_vs_AgAgCl"], errors="coerce")
        checked = native.notna() & conversion.notna() & experimental.notna()
        for index in frame[checked].index:
            expected = float(native.loc[index] + conversion.loc[index])
            observed = float(experimental.loc[index])
            if abs(expected - observed) > 0.005:
                raise ValueError(
                    _row_label(
                        frame.loc[index],
                        int(index),
                        (
                            "conversion mismatch: native_potential_V + "
                            f"conversion_to_AgAgCl_V = {expected:.3f}, but "
                            f"exp_Eox_V_vs_AgAgCl = {observed:.3f}"
                        ),
                    )
                )


def _validate_benchmark_ontology(frame: pd.DataFrame, path: str | Path) -> None:
    if not _has_ontology_schema(frame):
        return

    failures: list[str] = []
    for index, row in frame.iterrows():
        label_type = str(row["label_type"])
        if label_type not in ALLOWED_LABEL_TYPES:
            failures.append(_row_label(row, int(index), f"invalid label_type {label_type!r}"))

        reported_type = str(row["reported_potential_type"])
        if reported_type not in ALLOWED_REPORTED_POTENTIAL_TYPES:
            failures.append(
                _row_label(row, int(index), f"invalid reported_potential_type {reported_type!r}")
            )

        confidence = str(row["source_confidence"])
        if confidence not in ALLOWED_SOURCE_CONFIDENCE:
            failures.append(_row_label(row, int(index), f"invalid source_confidence {confidence!r}"))

        medium_class = str(row["medium_class"])
        if medium_class not in ALLOWED_MEDIUM_CLASSES:
            failures.append(_row_label(row, int(index), f"invalid medium_class {medium_class!r}"))

        eligible = _as_bool(row["calibration_eligible"])
        if not eligible and _is_blank(row["exclusion_reason"]):
            failures.append(
                _row_label(
                    row,
                    int(index),
                    "calibration_eligible is false but exclusion_reason is blank",
                )
            )

        if eligible and label_type not in CALIBRATION_LABEL_TYPES:
            failures.append(
                _row_label(
                    row,
                    int(index),
                    f"calibration_eligible is true but label_type {label_type!r} is not a monomer oxidation label",
                )
            )

        if not _is_low_or_provisional(row) and not _has_source_reference(row):
            failures.append(
                _row_label(
                    row,
                    int(index),
                    (
                        "source_doi is required unless source_doi_or_ref and source_locator "
                        "are populated, or source_confidence is low/provisional"
                    ),
                )
            )
        if not _is_low_or_provisional(row) and _is_blank(row["source_locator"]):
            failures.append(
                _row_label(
                    row,
                    int(index),
                    "source_locator is required unless source_confidence is low/provisional",
                )
            )

    if failures:
        details = "\n".join(f"  - {failure}" for failure in failures)
        raise ValueError(f"{path} has invalid benchmark ontology metadata:\n{details}")


def _row_label(row: pd.Series, zero_based_index: int, message: str) -> str:
    return (
        f"row {zero_based_index + 2} "
        f"({row.get('monomer_name', '<unknown>')}, {row.get('solvent_name', '<unknown>')}): "
        f"{message}"
    )


def _benchmark_monomer(row: dict[str, object]) -> Monomer:
    smiles = str(row["monomer_smiles"])
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid benchmark monomer SMILES: {smiles}")
    canonical = Chem.MolToSmiles(mol, canonical=True)
    return Monomer(
        name=str(row["monomer_name"]),
        monomer_class="benchmark",
        smiles=smiles,
        canonical_smiles=canonical,
        notes=str(row.get("notes", "")),
    )


def _benchmark_group_id(row: dict[str, object], monomer: Monomer) -> str:
    """Return the duplicate-collapse key for experimental labels.

    Strict benchmark v1 keeps peak-like and onset-like monomer oxidation labels
    separate, so ontology-enabled rows collapse by raw benchmark SMILES, solvent,
    and label type. Legacy synthetic fixtures without ontology keep the older
    canonical-smiles/solvent behavior.
    """

    label_type = str(row.get("label_type", "")).strip()
    if label_type:
        return f"{row['monomer_smiles']}|{row['solvent_name']}|{label_type}"
    return f"{monomer.canonical_smiles}|{row['solvent_name']}"


def _lookup_solvent(solvents: dict[str, Solvent], name: str) -> Solvent:
    try:
        return solvents[name]
    except KeyError as exc:
        known = ", ".join(sorted(solvents))
        raise ValueError(f"Unknown benchmark solvent {name!r}; known solvents: {known}") from exc


def _load_validation_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _mae(residuals: np.ndarray) -> float:
    return float(np.mean(np.abs(residuals)))


def _calibration_mask(
    report: pd.DataFrame,
    *,
    media: tuple[str, ...] | None,
    allowed_tiers: tuple[str, ...] | None,
) -> pd.Series:
    mask = pd.Series(True, index=report.index, dtype=bool)
    medium_column = _medium_filter_column(report)
    if media is not None and medium_column is not None:
        mask &= report[medium_column].isin(media)
    if allowed_tiers is not None and "reliability_tier" in report.columns:
        mask &= report["reliability_tier"].isin(allowed_tiers)
    if _has_ontology_schema(report):
        mask &= report["calibration_eligible"].map(_as_bool)
        mask &= report["label_type"].isin(CALIBRATION_LABEL_TYPES)
        mask &= pd.to_numeric(report["exp_Eox_V_vs_AgAgCl"], errors="coerce").notna()
        for column in _required_calibration_metadata_columns():
            mask &= ~report[column].map(_is_blank)
        mask &= ~report["source_locator"].map(_is_blank)
        mask &= report.apply(_has_source_reference, axis=1)
    return mask


def _calibration_exclusion_reasons(
    report: pd.DataFrame,
    *,
    media: tuple[str, ...] | None,
    allowed_tiers: tuple[str, ...] | None,
) -> pd.Series:
    if not _has_ontology_schema(report):
        return pd.Series("", index=report.index, dtype=object)

    reasons: list[str] = []
    medium_column = _medium_filter_column(report)
    for _, row in report.iterrows():
        row_reasons: list[str] = []
        if media is not None and medium_column is not None and row[medium_column] not in media:
            row_reasons.append("medium_filter")
        if (
            allowed_tiers is not None
            and "reliability_tier" in report.columns
            and row["reliability_tier"] not in allowed_tiers
        ):
            row_reasons.append("reliability_tier_filter")
        if not _as_bool(row["calibration_eligible"]):
            row_reasons.append("calibration_ineligible")
            if not _is_blank(row["exclusion_reason"]):
                row_reasons.append(str(row["exclusion_reason"]))
        if row["label_type"] not in CALIBRATION_LABEL_TYPES:
            row_reasons.append(f"disallowed_label_type:{row['label_type']}")
        if pd.isna(pd.to_numeric(row["exp_Eox_V_vs_AgAgCl"], errors="coerce")):
            row_reasons.append("missing_converted_potential")
        missing_metadata = [
            column for column in _required_calibration_metadata_columns() if _is_blank(row[column])
        ]
        if missing_metadata:
            row_reasons.append("missing_conversion_metadata:" + ",".join(missing_metadata))
        if _is_blank(row["source_locator"]):
            row_reasons.append("missing_source_locator")
        if not _has_source_reference(row):
            row_reasons.append("missing_source_reference")
        reasons.append(";".join(row_reasons))
    return pd.Series(reasons, index=report.index, dtype=object)


def _has_ontology_schema(frame: pd.DataFrame) -> bool:
    return _ontology_columns().issubset(frame.columns)


def _medium_filter_column(report: pd.DataFrame) -> str | None:
    if _has_ontology_schema(report) and "medium_class" in report.columns:
        return "medium_class"
    if "medium" in report.columns:
        return "medium"
    return None


def _ontology_columns() -> set[str]:
    return {
        "label_type",
        "calibration_eligible",
        "exclusion_reason",
        "reported_potential_type",
        "reported_reference_electrode",
        "converted_reference_electrode",
        "conversion_method",
        "source_doi",
        "source_locator",
        "source_confidence",
        "medium_class",
    }


def _required_calibration_metadata_columns() -> tuple[str, ...]:
    return (
        "reported_reference_electrode",
        "converted_reference_electrode",
        "conversion_method",
    )


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _is_blank(value: object) -> bool:
    return str(value).strip() == ""


def _is_low_or_provisional(row: pd.Series) -> bool:
    return str(row["source_confidence"]).strip().lower() in {"low", "provisional"}


def _has_source_reference(row: pd.Series) -> bool:
    return not _is_blank(row["source_doi"]) or (
        not _is_blank(row.get("source_doi_or_ref", ""))
        and not _is_blank(row.get("source_locator", ""))
    )


def _calibration_eligible_count(report: pd.DataFrame) -> int:
    if _has_ontology_schema(report):
        return int(report["calibration_eligible"].map(_as_bool).sum())
    return int(len(report))


def _value_counts(report: pd.DataFrame, column: str) -> dict[str, int]:
    if column not in report.columns:
        return {}
    return {str(key): int(value) for key, value in report[column].value_counts(dropna=False).sort_index().items()}


def _calibration_points(calibration_rows: pd.DataFrame, *, collapse_duplicates: bool) -> pd.DataFrame:
    columns = ["group_id", "pred_Eox_V_vs_AgAgCl", "exp_Eox_V_vs_AgAgCl"]
    if not collapse_duplicates:
        return calibration_rows.loc[:, columns].reset_index(drop=True)
    return (
        calibration_rows.groupby("group_id", as_index=False)
        .agg(
            pred_Eox_V_vs_AgAgCl=("pred_Eox_V_vs_AgAgCl", "first"),
            exp_Eox_V_vs_AgAgCl=("exp_Eox_V_vs_AgAgCl", "mean"),
        )
        .loc[:, columns]
    )


def _loo_mae(predicted: np.ndarray, experimental: np.ndarray) -> float:
    if len(predicted) < 3:
        return float("nan")
    residuals: list[float] = []
    for held_out in range(len(predicted)):
        train_mask = np.ones(len(predicted), dtype=bool)
        train_mask[held_out] = False
        calibration = fit_linear_calibration(predicted[train_mask], experimental[train_mask])
        held_pred = calibration.apply(np.array([predicted[held_out]], dtype=float))[0]
        residuals.append(float(held_pred - experimental[held_out]))
    return _mae(np.array(residuals, dtype=float))


def _within_group_spread(calibration_rows: pd.DataFrame) -> float:
    spreads = [
        float(np.std(group["exp_Eox_V_vs_AgAgCl"].to_numpy(dtype=float)))
        for _, group in calibration_rows.groupby("group_id")
        if len(group) > 1
    ]
    if not spreads:
        return 0.0
    return float(np.mean(spreads))

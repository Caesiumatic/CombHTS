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


@dataclass(frozen=True)
class BenchmarkValidationResult:
    """Validation report for benchmark oxidation potentials."""

    rows: pd.DataFrame
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
        group_id = f"{monomer.canonical_smiles}|{row['solvent_name']}"
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
    if media is not None and "medium" in report.columns:
        mask &= report["medium"].isin(media)
    if allowed_tiers is not None and "reliability_tier" in report.columns:
        mask &= report["reliability_tier"].isin(allowed_tiers)
    return mask


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

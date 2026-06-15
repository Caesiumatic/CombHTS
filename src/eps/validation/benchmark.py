"""Benchmark validation of predicted monomer oxidation potentials."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from rdkit import Chem

from eps.calibration import LinearCalibration, fit_linear_calibration
from eps.chemspace import Solvent, load_solvents
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
    calibration: LinearCalibration
    tier1_xtb_target_V: float
    tier1_xtb_pass: bool
    report_path: Path


def run_benchmark_validation(
    *,
    engine: Engine | None = None,
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    validation_config_path: str | Path = DEFAULT_VALIDATION_CONFIG,
    report_path: str | Path = DEFAULT_REPORT_PATH,
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
        predicted = monomer_eox_vs_AgAgCl(monomer, solvent, engine, cache)
        experimental = float(row["exp_Eox_V_vs_AgAgCl"])
        rows.append(
            {
                **row,
                "canonical_smiles": monomer.canonical_smiles,
                "pred_Eox_V_vs_AgAgCl": predicted,
                "residual_before_V": predicted - experimental,
            }
        )

    report = pd.DataFrame(rows)
    calibration = fit_linear_calibration(
        report["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float),
        report["exp_Eox_V_vs_AgAgCl"].to_numpy(dtype=float),
    )
    corrected = calibration.apply(report["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float))
    report["calibrated_Eox_V_vs_AgAgCl"] = corrected
    report["residual_after_V"] = report["calibrated_Eox_V_vs_AgAgCl"] - report["exp_Eox_V_vs_AgAgCl"]

    mae_before = _mae(report["residual_before_V"].to_numpy(dtype=float))
    mae_after = _mae(report["residual_after_V"].to_numpy(dtype=float))
    config = _load_validation_config(validation_config_path)
    tier1_target = float(config["tier1_xtb_mae_target_V"])
    report["tier1_xtb_mae_target_V"] = tier1_target
    report["tier1_xtb_pass_after_calibration"] = mae_after <= tier1_target

    output = Path(report_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output, index=False)

    return BenchmarkValidationResult(
        rows=report,
        mae_before_V=mae_before,
        mae_after_V=mae_after,
        calibration=calibration,
        tier1_xtb_target_V=tier1_target,
        tier1_xtb_pass=mae_after <= tier1_target,
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
    return frame


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

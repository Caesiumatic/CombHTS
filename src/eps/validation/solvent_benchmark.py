"""Directive §7 solvent-ESW MAE: score the computed solvent anodic/cathodic limits against a
measured electrochemical-window benchmark.

The benchmark (``data/solvent_benchmark.csv``) is seeded header-only — its rows are curated later
from the solvent-ESW research. With ZERO rows the metric is NOT computable and is reported as such
(never fabricated); as soon as measured rows land it becomes a real MAE = mean |computed anodic
limit − measured anodic| (and the cathodic analog), computed through the SAME cached per-species
engine path the screen uses. RAW computed limits (uncalibrated adiabatic ΔSCF) are compared, so the
metric reflects the underlying physics rather than the monomer-fit oxidation calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from eps.chemspace import Solvent, load_solvents
from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.storage import SQLiteCache

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOLVENT_BENCHMARK_PATH = PROJECT_ROOT / "data" / "solvent_benchmark.csv"

SOLVENT_BENCHMARK_COLUMNS = (
    "solvent",
    "smiles",
    "exp_anodic_V_vs_AgAgCl",
    "exp_cathodic_V_vs_AgAgCl",
    "reference",
    "electrolyte",
    "electrode",
    "source",
    "tier",
)


@dataclass
class SolventEswMaeResult:
    """Directive §7 solvent-ESW MAE outcome (computable only when benchmark rows exist)."""

    n_benchmark_rows: int
    n_matched: int
    computable: bool
    anodic_mae_V: float
    cathodic_mae_V: float
    per_solvent: list[dict[str, object]] = field(default_factory=list)
    note: str = ""


def load_solvent_benchmark(
    path: str | Path = DEFAULT_SOLVENT_BENCHMARK_PATH,
) -> pd.DataFrame:
    """Load the solvent ESW benchmark, validating the schema. A header-only file yields 0 rows."""

    frame = pd.read_csv(path, keep_default_na=False)
    missing = set(SOLVENT_BENCHMARK_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(
            f"{path} is missing required columns: {', '.join(sorted(missing))}"
        )
    return frame


def compute_solvent_esw_mae(
    *,
    engine: Engine | None = None,
    cache_path: str | Path,
    method: str = "mock-gfn2",
    benchmark_path: str | Path = DEFAULT_SOLVENT_BENCHMARK_PATH,
    solvents: list[Solvent] | None = None,
) -> SolventEswMaeResult:
    """Compute the §7 solvent-ESW MAE over whatever benchmark rows exist (0 rows -> not computable).

    Compares the RAW computed adiabatic ΔSCF anodic/cathodic limits (``solvent_anodic_limit_computed_V``
    / ``solvent_cathodic_limit_computed_V``) to the measured values, joined by solvent name over the
    solvents present in BOTH the benchmark and the library. With no rows it short-circuits (no engine
    calls) and returns ``computable=False``.
    """

    benchmark = load_solvent_benchmark(benchmark_path)
    if benchmark.empty:
        return SolventEswMaeResult(
            n_benchmark_rows=0,
            n_matched=0,
            computable=False,
            anodic_mae_V=float("nan"),
            cathodic_mae_V=float("nan"),
            note="no solvent-ESW benchmark rows yet (header-only); not computable",
        )

    # Local import keeps the validation package importable without pulling the whole workflow at module load.
    from eps.workflow.tier1 import compute_solvent_table

    engine = engine or MockEngine()
    cache = SQLiteCache(cache_path)
    library = solvents if solvents is not None else load_solvents()
    by_name = {solvent.name: solvent for solvent in library}

    bench_names = {str(name) for name in benchmark["solvent"]}
    matched = [by_name[name] for name in bench_names if name in by_name]
    if not matched:
        return SolventEswMaeResult(
            n_benchmark_rows=int(len(benchmark)),
            n_matched=0,
            computable=False,
            anodic_mae_V=float("nan"),
            cathodic_mae_V=float("nan"),
            note="benchmark solvents are not in the screen library; not computable",
        )

    table = compute_solvent_table(matched, engine, cache, method=method)
    merged = benchmark.merge(table, left_on="solvent", right_on="solvent_name", how="inner")

    anodic_abs: list[float] = []
    cathodic_abs: list[float] = []
    per_solvent: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        entry: dict[str, object] = {"solvent": row["solvent"]}
        exp_anodic = _as_float(row["exp_anodic_V_vs_AgAgCl"])
        exp_cathodic = _as_float(row["exp_cathodic_V_vs_AgAgCl"])
        comp_anodic = float(row["solvent_anodic_limit_computed_V"])
        comp_cathodic = float(row["solvent_cathodic_limit_computed_V"])
        anodic_ok = row.get("solvent_anodic_limit_calc_status") == "ok"
        cathodic_ok = row.get("solvent_cathodic_limit_calc_status") == "ok"
        if anodic_ok and np.isfinite(exp_anodic) and np.isfinite(comp_anodic):
            anodic_abs.append(abs(comp_anodic - exp_anodic))
            entry["anodic_abs_error_V"] = abs(comp_anodic - exp_anodic)
        if cathodic_ok and np.isfinite(exp_cathodic) and np.isfinite(comp_cathodic):
            cathodic_abs.append(abs(comp_cathodic - exp_cathodic))
            entry["cathodic_abs_error_V"] = abs(comp_cathodic - exp_cathodic)
        per_solvent.append(entry)

    anodic_mae = float(np.mean(anodic_abs)) if anodic_abs else float("nan")
    cathodic_mae = float(np.mean(cathodic_abs)) if cathodic_abs else float("nan")
    computable = len(anodic_abs) > 0
    return SolventEswMaeResult(
        n_benchmark_rows=int(len(benchmark)),
        n_matched=len(per_solvent),
        computable=computable,
        anodic_mae_V=anodic_mae,
        cathodic_mae_V=cathodic_mae,
        per_solvent=per_solvent,
        note="raw computed adiabatic ΔSCF limits vs measured (uncalibrated, screening-grade)",
    )


def _as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")

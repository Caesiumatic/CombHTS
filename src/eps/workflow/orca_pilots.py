"""Mock-first ORCA 6.1 route pilots for solvation and optical-gap calibration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

from eps.calibration import LinearCalibration, fit_linear_calibration
from eps.chemspace import load_monomers, load_solvents
from eps.engines import CalcRequest, Engine, MockEngine, OrcaConfig, OrcaEngine, SpeciesSpec
from eps.storage import SQLiteCache
from eps.storage.cache import CacheKey, cached_run
from eps.structures.oligomer import load_polymerization_specs, oligomer_smiles

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "orca_pilots.yaml"
DEFAULT_SOLVATION_OUTDIR = PROJECT_ROOT / "outputs" / "orca_solvation_pilot"
DEFAULT_OPTICAL_OUTDIR = PROJECT_ROOT / "outputs" / "orca_optical_pilot"
DEFAULT_SOLVATION_GRID_CONFIG_PATH = PROJECT_ROOT / "configs" / "solvation_cosmors_pilot.yaml"
DEFAULT_SOLVATION_GRID_OUTDIR = PROJECT_ROOT / "outputs" / "solvation_cosmors_pilot"


@dataclass(frozen=True)
class OrcaSolvationPilotResult:
    """ORCA/openCOSMO-RS pilot results; values are dGsolv in kcal/mol."""

    points: pd.DataFrame
    points_path: Path
    cache_path: Path
    n_ok: int
    n_failed: int
    engine_label: str


@dataclass(frozen=True)
class OrcaSolvationGridResult:
    """Monomer x solvent openCOSMO-RS dGsolv grid (descriptor validation, not solubility)."""

    points: pd.DataFrame
    plan: pd.DataFrame
    points_path: Path
    plan_path: Path
    cache_path: Path
    n_ok: int
    n_failed: int
    n_cached: int
    n_computed: int
    n_deferred: int
    engine_label: str


@dataclass(frozen=True)
class OrcaOpticalPilotResult:
    """Paired ORCA sTDA and TDA/TD-DFT pilot with an optional linear fit."""

    points: pd.DataFrame
    points_path: Path
    report_path: Path
    calibration_path: Path
    cache_path: Path
    calibration: LinearCalibration | None
    n_paired: int
    n_failed: int
    engine_label: str


def load_orca_pilot_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load the small-pilot YAML configuration."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if not isinstance(config, dict) or not {"solvation", "optical"}.issubset(config):
        raise ValueError(f"{path} must contain solvation and optical mappings")
    return config


def run_orca_solvation_pilot(
    *,
    engine: Engine,
    method: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    cache_path: str | Path | None = None,
    outdir: str | Path = DEFAULT_SOLVATION_OUTDIR,
    engine_label: str,
) -> OrcaSolvationPilotResult:
    """Run the configured neutral-monomer dGsolv pilot through the Engine/cache path."""

    config = load_orca_pilot_config(config_path)["solvation"]
    monomers = {monomer.name: monomer for monomer in load_monomers()}
    solvents = {solvent.name: solvent for solvent in load_solvents()}
    solvent = solvents[str(config["solvent_name"])]
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    cache_file = Path(cache_path) if cache_path is not None else out / "cache.sqlite"
    cache = SQLiteCache(cache_file)

    rows: list[dict[str, object]] = []
    for name in config["monomers"]:
        monomer = monomers[str(name)]
        request = CalcRequest(
            species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
            method=method,
            solvent_eps_r=solvent.eps_r,
            quantity="solvation_free_energy",
            solvent_model_name=str(config["orca_cosmors_name"]),
        )
        try:
            result = cached_run(cache, engine, request, solvent.name)
            rows.append(
                {
                    "monomer_name": monomer.name,
                    "monomer_canonical_smiles": monomer.canonical_smiles,
                    "solvent_name": solvent.name,
                    "orca_solvent_name": config["orca_cosmors_name"],
                    "solvation_dG_kcal_mol": result.value,
                    "calc_status": "ok",
                    "calc_error": "",
                    "engine_method": method,
                }
            )
        except Exception as exc:  # noqa: BLE001 - pilot must preserve all failures.
            rows.append(
                {
                    "monomer_name": monomer.name,
                    "monomer_canonical_smiles": monomer.canonical_smiles,
                    "solvent_name": solvent.name,
                    "orca_solvent_name": config["orca_cosmors_name"],
                    "solvation_dG_kcal_mol": float("nan"),
                    "calc_status": "failed",
                    "calc_error": _error(exc),
                    "engine_method": method,
                }
            )
    points = pd.DataFrame(rows)
    points_path = out / "solvation_points.csv"
    points.to_csv(points_path, index=False)
    n_ok = int((points["calc_status"] == "ok").sum())
    return OrcaSolvationPilotResult(
        points=points,
        points_path=points_path,
        cache_path=cache_file,
        n_ok=n_ok,
        n_failed=int(len(points) - n_ok),
        engine_label=engine_label,
    )


def load_solvation_grid_config(path: str | Path = DEFAULT_SOLVATION_GRID_CONFIG_PATH) -> dict:
    """Load the monomer x solvent dGsolv grid configuration."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    grid = config.get("grid") if isinstance(config, dict) else None
    if not isinstance(grid, dict) or not {"monomers", "solvents"}.issubset(grid):
        raise ValueError(f"{path} must contain a grid mapping with monomers and solvents")
    return grid


def plan_solvation_grid(
    grid: dict,
    cache: SQLiteCache,
    method: str,
) -> pd.DataFrame:
    """Classify every (monomer, solvent) point as cached, compute, or deferred (pre-flight).

    The classification only reads the cache; it never runs the engine. ``cached`` means an
    identical (canonical SMILES, charge 0, method, library solvent, quantity) row already exists
    so the run will reuse it; ``compute`` means the run will call ORCA; ``deferred`` means the
    solvent has no ORCA built-in openCOSMO-RS sigma profile and is not computed by this pilot.
    """

    monomers = {monomer.name: monomer for monomer in load_monomers()}
    rows: list[dict[str, object]] = []
    for name in grid["monomers"]:
        monomer = monomers[str(name)]
        for entry in grid["solvents"]:
            solvent_name = str(entry["solvent_name"])
            key = CacheKey(
                canonical_smiles=monomer.canonical_smiles,
                charge=0,
                method=method,
                solvent_name=solvent_name,
                quantity="solvation_free_energy",
            )
            cached = cache.get(key) is not None
            rows.append(
                {
                    "monomer_name": monomer.name,
                    "solvent_name": solvent_name,
                    "orca_solvent_name": str(entry["orca_cosmors_name"]),
                    "status": "cached" if cached else "compute",
                    "reason": "",
                }
            )
        for entry in grid.get("deferred_solvents", []) or []:
            rows.append(
                {
                    "monomer_name": monomer.name,
                    "solvent_name": str(entry["solvent_name"]),
                    "orca_solvent_name": "",
                    "status": "deferred",
                    "reason": str(entry.get("reason", "")),
                }
            )
    return pd.DataFrame(rows)


def run_orca_solvation_grid_pilot(
    *,
    engine: Engine,
    method: str,
    config_path: str | Path = DEFAULT_SOLVATION_GRID_CONFIG_PATH,
    cache_path: str | Path | None = None,
    outdir: str | Path = DEFAULT_SOLVATION_GRID_OUTDIR,
    engine_label: str,
) -> OrcaSolvationGridResult:
    """Run the stratified monomer x solvent dGsolv grid through the Engine/cache path.

    Only points with an ORCA built-in openCOSMO-RS solvent are computed; cached points are
    reused transparently. Deferred (no built-in profile) points are recorded with NaN dGsolv so
    the points table is an honest, self-documenting computed-vs-needed record.
    """

    grid = load_solvation_grid_config(config_path)
    monomers = {monomer.name: monomer for monomer in load_monomers()}
    solvents = {solvent.name: solvent for solvent in load_solvents()}
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    cache_file = Path(cache_path) if cache_path is not None else out / "cache.sqlite"
    cache = SQLiteCache(cache_file)

    plan = plan_solvation_grid(grid, cache, method)
    plan_path = out / "solvation_grid_plan.csv"
    plan.to_csv(plan_path, index=False)
    n_cached = int((plan["status"] == "cached").sum())
    n_computed_planned = int((plan["status"] == "compute").sum())
    n_deferred = int((plan["status"] == "deferred").sum())

    rows: list[dict[str, object]] = []
    for name in grid["monomers"]:
        monomer = monomers[str(name)]
        for entry in grid["solvents"]:
            solvent_name = str(entry["solvent_name"])
            orca_name = str(entry["orca_cosmors_name"])
            solvent = solvents[solvent_name]
            was_cached = bool(
                cache.get(
                    CacheKey(
                        canonical_smiles=monomer.canonical_smiles,
                        charge=0,
                        method=method,
                        solvent_name=solvent_name,
                        quantity="solvation_free_energy",
                    )
                )
                is not None
            )
            request = CalcRequest(
                species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
                method=method,
                solvent_eps_r=solvent.eps_r,
                quantity="solvation_free_energy",
                solvent_model_name=orca_name,
            )
            try:
                result = cached_run(cache, engine, request, solvent.name)
                rows.append(
                    _grid_row(
                        monomer,
                        solvent_name,
                        orca_name,
                        method,
                        dG=result.value,
                        status="ok",
                        cache_hit=was_cached,
                        error="",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - pilot must preserve all failures.
                rows.append(
                    _grid_row(
                        monomer,
                        solvent_name,
                        orca_name,
                        method,
                        dG=float("nan"),
                        status="failed",
                        cache_hit=was_cached,
                        error=_error(exc),
                    )
                )
        for entry in grid.get("deferred_solvents", []) or []:
            rows.append(
                _grid_row(
                    monomer,
                    str(entry["solvent_name"]),
                    "",
                    method,
                    dG=float("nan"),
                    status="deferred",
                    cache_hit=False,
                    error=str(entry.get("reason", "")),
                )
            )

    points = pd.DataFrame(rows)
    points_path = out / "solvation_grid_points.csv"
    points.to_csv(points_path, index=False)
    n_ok = int((points["calc_status"] == "ok").sum())
    n_failed = int((points["calc_status"] == "failed").sum())
    return OrcaSolvationGridResult(
        points=points,
        plan=plan,
        points_path=points_path,
        plan_path=plan_path,
        cache_path=cache_file,
        n_ok=n_ok,
        n_failed=n_failed,
        n_cached=n_cached,
        n_computed=n_computed_planned,
        n_deferred=n_deferred,
        engine_label=engine_label,
    )


def build_real_orca_solvation_grid_engine(
    config_path: str | Path = DEFAULT_SOLVATION_GRID_CONFIG_PATH,
):
    """Construct the real ORCA/openCOSMO-RS engine and method label for the grid pilot."""

    grid = load_solvation_grid_config(config_path)
    config = OrcaConfig(
        nprocs=int(grid["nprocs"]),
        maxcore_mb=int(grid["maxcore_mb"]),
        optical_mode="cosmors",
    )
    return OrcaEngine(config), config.method_label()


def _grid_row(
    monomer,
    solvent_name: str,
    orca_name: str,
    method: str,
    *,
    dG: float,
    status: str,
    cache_hit: bool,
    error: str,
) -> dict[str, object]:
    return {
        "monomer_name": monomer.name,
        "monomer_class": monomer.monomer_class,
        "monomer_canonical_smiles": monomer.canonical_smiles,
        "solvent_name": solvent_name,
        "orca_solvent_name": orca_name,
        "solvation_dG_kcal_mol": dG,
        "calc_status": status,
        "cache_hit": cache_hit,
        "calc_error": error,
        "engine_method": method,
    }


def run_orca_optical_pilot(
    *,
    stda_engine: Engine,
    tddft_engine: Engine,
    stda_method: str,
    tddft_method: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    cache_path: str | Path | None = None,
    outdir: str | Path = DEFAULT_OPTICAL_OUTDIR,
    engine_label: str,
) -> OrcaOpticalPilotResult:
    """Pair sTDA and conventional TDA/TD-DFT gaps and fit TDDFT = a*sTDA+b."""

    config = load_orca_pilot_config(config_path)["optical"]
    monomers = {monomer.name: monomer for monomer in load_monomers()}
    specs = load_polymerization_specs()
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    cache_file = Path(cache_path) if cache_path is not None else out / "cache.sqlite"
    cache = SQLiteCache(cache_file)
    oligomer_n = int(config["oligomer_n"])

    rows: list[dict[str, object]] = []
    for name in config["monomers"]:
        monomer = monomers[str(name)]
        spec = specs[monomer.name]
        oligo = oligomer_smiles(monomer.canonical_smiles, spec, oligomer_n)
        species = SpeciesSpec(oligo, charge=0, multiplicity=1)
        common = {
            "monomer_name": monomer.name,
            "monomer_class": monomer.monomer_class,
            "oligomer_n": oligomer_n,
            "oligomer_canonical_smiles": oligo,
        }
        stda_value, stda_status, stda_error = _run_optical(
            cache, stda_engine, species, stda_method, str(config.get("solvent_name", ""))
        )
        tddft_value, tddft_status, tddft_error = _run_optical(
            cache, tddft_engine, species, tddft_method, str(config.get("solvent_name", ""))
        )
        rows.append(
            {
                **common,
                "stda_gap_eV": stda_value,
                "stda_calc_status": stda_status,
                "stda_calc_error": stda_error,
                "tddft_gap_eV": tddft_value,
                "tddft_calc_status": tddft_status,
                "tddft_calc_error": tddft_error,
                "stda_method": stda_method,
                "tddft_method": tddft_method,
            }
        )
    points = pd.DataFrame(rows)
    paired = points[
        (points["stda_calc_status"] == "ok") & (points["tddft_calc_status"] == "ok")
    ]
    calibration = None
    if len(paired) >= 2 and paired["stda_gap_eV"].nunique() >= 2:
        calibration = fit_linear_calibration(
            paired["stda_gap_eV"].to_numpy(dtype=float),
            paired["tddft_gap_eV"].to_numpy(dtype=float),
        )
    points_path = out / "optical_points.csv"
    calibration_path = out / "stda_to_tddft_calibration.json"
    report_path = out / "report.md"
    points.to_csv(points_path, index=False)
    payload = {
        "status": "pilot_only_not_production_calibration",
        "engine": engine_label,
        "n_paired": int(len(paired)),
        "stda_method": stda_method,
        "tddft_method": tddft_method,
        "calibration": None if calibration is None else calibration.__dict__,
    }
    calibration_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_optical_report(payload), encoding="utf-8")
    n_failed = int(len(points) - len(paired))
    return OrcaOpticalPilotResult(
        points=points,
        points_path=points_path,
        report_path=report_path,
        calibration_path=calibration_path,
        cache_path=cache_file,
        calibration=calibration,
        n_paired=int(len(paired)),
        n_failed=n_failed,
        engine_label=engine_label,
    )


def build_real_orca_pilot_engines(config_path: str | Path = DEFAULT_CONFIG_PATH):
    """Construct real ORCA engines and cache-safe method labels from YAML."""

    config = load_orca_pilot_config(config_path)
    solv = config["solvation"]
    optical = config["optical"]
    solvation_config = OrcaConfig(
        nprocs=int(solv["nprocs"]),
        maxcore_mb=int(solv["maxcore_mb"]),
        optical_mode="cosmors",
    )
    common = dict(
        nprocs=int(optical["nprocs"]),
        maxcore_mb=int(optical["maxcore_mb"]),
        functional=str(optical["functional"]),
        basis=str(optical["basis"]),
        optical_solvent=str(optical["orca_solvent_name"]),
        nroots=int(optical["nroots"]),
        ethresh_eV=float(optical["ethresh_eV"]),
    )
    stda_config = OrcaConfig(**common, optical_mode="stda")
    tddft_config = OrcaConfig(**common, optical_mode="tddft")
    return (
        OrcaEngine(solvation_config),
        solvation_config.method_label(),
        OrcaEngine(stda_config),
        stda_config.method_label(),
        OrcaEngine(tddft_config),
        tddft_config.method_label(),
    )


def build_mock_orca_pilot_engines():
    """Mock-first engines with distinct method labels for cache/provenance tests."""

    return (
        MockEngine(),
        "mock-orca-cosmors",
        MockEngine(),
        "mock-orca-stda",
        MockEngine(),
        "mock-orca-tddft",
    )


def _run_optical(
    cache: SQLiteCache,
    engine: Engine,
    species: SpeciesSpec,
    method: str,
    solvent_name: str,
) -> tuple[float, str, str]:
    request = CalcRequest(
        species=species,
        method=method,
        solvent_eps_r=None,
        quantity="optical_gap",
    )
    try:
        result = cached_run(cache, engine, request, solvent_name or None)
        return float(result.value), "ok", ""
    except Exception as exc:  # noqa: BLE001
        return float("nan"), "failed", _error(exc)


def _optical_report(payload: dict) -> str:
    lines = [
        "# ORCA optical calibration pilot",
        "",
        "Status: PILOT ONLY - not a production optical-gap calibration.",
        f"Engine: {payload['engine']}",
        f"Paired points: {payload['n_paired']}",
        f"sTDA method: `{payload['stda_method']}`",
        f"TDDFT reference: `{payload['tddft_method']}`",
        "",
    ]
    calibration = payload["calibration"]
    if calibration is None:
        lines.append("Calibration: not fitted (fewer than two non-degenerate paired points).")
    else:
        lines.extend(
            [
                "Calibration: `TDDFT_gap_eV = slope * sTDA_gap_eV + intercept`",
                f"- slope: {calibration['slope']:.6f}",
                f"- intercept_eV: {calibration['intercept']:.6f}",
                f"- R2: {calibration['r2']:.6f}",
                f"- in_sample_MAE_eV: {calibration['mae']:.6f}",
            ]
        )
    lines.extend(
        [
            "",
            "Caveat: this small dimer set validates the route and parser only. It must not replace",
            "the uncalibrated Tier-1 band-gap axis until a larger, per-class calibration is run.",
            "",
        ]
    )
    return "\n".join(lines)


def _error(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:500]

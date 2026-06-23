"""Tier-2 Gaussian pilot planning, single-task execution, harvest, and legacy refined screen.

The new pilot workflow is deliberately array-safe:

1. ``tier2-plan`` validates a selection CSV and writes one logical adiabatic-IP task per unique
   ``(monomer, solvent, Tier-2 method config)`` identity.
2. ``tier2-run-task`` executes exactly one manifest task through the Engine interface, with a
   task-local cache by default and atomic ``result.json`` writes.
3. ``tier2-harvest`` accepts only validated successful task results and emits a per-monomer-solvent
   Eox CSV consumable by ``tier2-screen``.

The legacy ``eps tier2 --dry-run`` input writer and ``eps tier2-screen`` refined screen are kept
backward compatible at the bottom of this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from rdkit import Chem

from eps.chemspace import load_solvents
from eps.engines.base import CalcRequest, SpeciesSpec
from eps.engines.gaussian import GaussianEngine, Tier2Config, build_gaussian_input, load_tier2_config
from eps.engines.mock import MockEngine
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.scoring import add_composite_score, load_scoring_config
from eps.storage import SQLiteCache, cached_run
from eps.workflow.tier1 import PROJECT_ROOT, load_tier1_config

# Rough per-input cost for a B3LYP/6-31G(d,p) Opt of a small monomer/cation on the cluster.
# Deliberately coarse — for human capacity planning only, not a benchmark.
DEFAULT_CPU_HOURS_PER_INPUT = 2.0

# Directive §4.2 refined window margin: the monomer adiabatic IP must sit at least this far BELOW
# the solvent anodic limit (tighter than the Tier-1 0.3 V gate) before a triad survives Tier-2.
DEFAULT_REFINED_WINDOW_MARGIN_V = 0.5

DEFAULT_TIER2_PLAN_OUTDIR = PROJECT_ROOT / "outputs" / "tier2_pilot_plan"
DEFAULT_TIER2_TASK_RESULTS_DIR = PROJECT_ROOT / "outputs" / "tier2_pilot_task_results"
DEFAULT_TIER2_WORK_ROOT = PROJECT_ROOT / "outputs" / "tier2_pilot_work"
DEFAULT_TIER2_HARVEST_OUTPUT = PROJECT_ROOT / "outputs" / "tier2_monomer_eox.csv"
DEFAULT_TIER2_HARVEST_REPORT = PROJECT_ROOT / "outputs" / "tier2_harvest_report.md"

TASK_MANIFEST_COLUMNS = (
    "task_id",
    "entity_type",
    "monomer_name",
    "canonical_smiles",
    "solvent_name",
    "quantity",
    "initial_charge",
    "initial_multiplicity",
    "final_charge",
    "final_multiplicity",
    "method_label",
    "config_hash",
    "status",
    "selection_role",
    "source_selection_row",
)

HARVEST_COLUMNS = (
    "task_id",
    "monomer_name",
    "monomer_canonical_smiles",
    "canonical_smiles",
    "solvent_name",
    "quantity",
    "method_label",
    "config_hash",
    "tier2_monomer_Eox_V_vs_AgAgCl",
    "dft_monomer_Eox_V_vs_AgAgCl",
    "adiabatic_ip_eV",
    "energy_basis",
    "initial_charge",
    "initial_multiplicity",
    "final_charge",
    "final_multiplicity",
    "neutral_scf_energy_Eh",
    "neutral_gibbs_free_energy_Eh",
    "cation_scf_energy_Eh",
    "cation_gibbs_free_energy_Eh",
    "frequency_requested",
    "neutral_imaginary_frequency_count",
    "cation_imaginary_frequency_count",
    "engine",
    "cache_path",
    "work_dir",
    "result_path",
)

# Recognized per-monomer DFT Eox columns in a Tier-2 DFT results CSV (already V vs Ag/AgCl).
_DFT_EOX_COLUMNS = (
    "tier2_monomer_Eox_V_vs_AgAgCl",
    "dft_monomer_Eox_V_vs_AgAgCl",
)


@dataclass
class Tier2PlanResult:
    """Artifacts emitted by ``eps tier2-plan`` for the monomer-Eox pilot."""

    outdir: Path
    manifest_path: Path
    summary_path: Path
    report_path: Path
    provenance_path: Path
    n_selection_rows: int
    n_tasks: int
    n_unique_monomers: int
    n_unique_monomer_solvent_pairs: int
    config_hash: str
    method_label: str


@dataclass
class Tier2TaskRunResult:
    """Result of executing one Tier-2 manifest task through an Engine."""

    task_id: str
    status: str
    result_path: Path
    status_path: Path
    cache_path: Path
    work_dir: Path
    error: str = ""


@dataclass
class Tier2HarvestResult:
    """Validated harvest of per-task Tier-2 adiabatic-IP results."""

    output_path: Path
    report_path: Path
    n_manifest_tasks: int
    n_success: int
    n_missing: int
    n_failed: int
    n_duplicate: int
    n_hash_mismatch: int
    n_identity_mismatch: int
    partial: bool
    missing_task_ids: list[str] = field(default_factory=list)
    failed_task_ids: list[str] = field(default_factory=list)
    duplicate_task_ids: list[str] = field(default_factory=list)
    hash_mismatch_task_ids: list[str] = field(default_factory=list)
    identity_mismatch_task_ids: list[str] = field(default_factory=list)


@dataclass
class Tier2DryRunResult:
    """Outputs of the legacy Tier-2 input-generation dry run (no g16 executed)."""

    outdir: Path
    n_survivors: int
    n_unique_monomers: int
    input_paths: list[Path] = field(default_factory=list)
    estimated_cpu_hours: float = 0.0


def plan_tier2_pilot(
    selection_path: str | Path,
    config_path: str | Path,
    outdir: str | Path,
) -> Tier2PlanResult:
    """Plan one Tier-2 adiabatic-IP request per unique monomer/solvent/config identity.

    The selection CSV must contain ``solvent_name`` and one monomer SMILES column
    (``monomer_canonical_smiles``, ``canonical_smiles``, ``monomer_smiles``, or ``smiles``).
    ``monomer_name`` and ``selection_role`` are optional. Repeated salts/cations collapse into a
    single task as long as the monomer, solvent, quantity, and method config are identical.
    """

    config = load_tier2_config(config_path)
    config_hash = tier2_config_hash(config, config_path)
    method_label = config.cache_method_label()
    selection = pd.read_csv(selection_path, keep_default_na=False)
    tasks = _manifest_rows_from_selection(selection, method_label=method_label, config_hash=config_hash)

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "task_manifest.csv"
    summary_path = out / "plan_summary.json"
    report_path = out / "plan_report.md"
    provenance_path = out / "provenance.json"

    manifest = pd.DataFrame(tasks, columns=list(TASK_MANIFEST_COLUMNS))
    _write_dataframe_atomic(manifest_path, manifest)

    summary = _plan_summary(
        selection_path=Path(selection_path),
        config_path=Path(config_path),
        config=config,
        config_hash=config_hash,
        method_label=method_label,
        n_selection_rows=int(len(selection)),
        n_tasks=int(len(manifest)),
    )
    _write_json_atomic(summary_path, summary)
    _write_text_atomic(report_path, _plan_report(summary))
    _write_json_atomic(
        provenance_path,
        {
            "schema_version": 1,
            "command": "tier2-plan",
            "created_at_utc": _utc_now(),
            "selection_path": str(selection_path),
            "selection_sha256": _sha256_file(selection_path),
            "config_path": str(config_path),
            "config_hash": config_hash,
            "method_label": method_label,
            "git": _env_git_record(),
        },
    )

    return Tier2PlanResult(
        outdir=out,
        manifest_path=manifest_path,
        summary_path=summary_path,
        report_path=report_path,
        provenance_path=provenance_path,
        n_selection_rows=int(len(selection)),
        n_tasks=int(len(manifest)),
        n_unique_monomers=int(manifest["canonical_smiles"].nunique()) if not manifest.empty else 0,
        n_unique_monomer_solvent_pairs=int(
            manifest[["canonical_smiles", "solvent_name"]].drop_duplicates().shape[0]
        )
        if not manifest.empty
        else 0,
        config_hash=config_hash,
        method_label=method_label,
    )


def run_tier2_task(
    manifest_path: str | Path,
    task_id: str,
    *,
    engine_name: str,
    result_dir: str | Path,
    work_root: str | Path,
    cache_path: str | Path | None = None,
    config_path: str | Path = PROJECT_ROOT / "configs" / "tier2.yaml",
) -> Tier2TaskRunResult:
    """Execute exactly one Tier-2 manifest task and write ``result.json`` atomically.

    The default cache path is ``<result-dir>/task_caches/<task-id>.sqlite`` so SGE array tasks do
    not concurrently write to one SQLite file over NFS.
    """

    task = _select_manifest_task(manifest_path, task_id)
    result_root = Path(result_dir) / task_id
    result_root.mkdir(parents=True, exist_ok=True)
    result_path = result_root / "result.json"
    status_path = result_root / "status.txt"
    task_cache = Path(cache_path) if cache_path is not None else Path(result_dir) / "task_caches" / f"{task_id}.sqlite"
    task_work_dir = Path(work_root) / task_id

    try:
        config = load_tier2_config(config_path)
        current_hash = tier2_config_hash(config, config_path)
        if str(task["config_hash"]) != current_hash:
            raise ValueError(
                f"manifest config_hash {task['config_hash']} does not match current config hash {current_hash}"
            )
        engine = _tier2_engine(engine_name, config=config, work_dir=task_work_dir)
        cache = SQLiteCache(task_cache)
        request = _task_request(task)
        result = cached_run(cache, engine, request, solvent_name=str(task["solvent_name"]))
        record = _successful_task_record(
            task,
            result_value_eV=float(result.value),
            result_unit=result.unit,
            result_method=result.method,
            raw=result.raw,
            engine_name=engine_name,
            cache_path=task_cache,
            work_dir=task_work_dir,
            config=config,
        )
        status = "success"
        error = ""
    except Exception as exc:  # noqa: BLE001 - task runner records failed tasks rather than crashing silently.
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
        record = _failed_task_record(
            task,
            engine_name=engine_name,
            cache_path=task_cache,
            work_dir=task_work_dir,
            error=error,
        )

    _write_json_atomic(result_path, record)
    _write_text_atomic(status_path, status + "\n")
    return Tier2TaskRunResult(
        task_id=task_id,
        status=status,
        result_path=result_path,
        status_path=status_path,
        cache_path=task_cache,
        work_dir=task_work_dir,
        error=error,
    )


def harvest_tier2_results(
    manifest_path: str | Path,
    result_dir: str | Path,
    output_path: str | Path,
    report_path: str | Path,
) -> Tier2HarvestResult:
    """Harvest validated Tier-2 task results into a per-monomer-solvent Eox CSV.

    Missing, failed, duplicate, mismatched-config, and mismatched-identity results are reported
    explicitly and excluded from the output. Failed Tier-2 values are never filled with Tier-1.
    """

    manifest = _read_manifest(manifest_path)
    result_files = _collect_result_files(result_dir)

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    failed: list[str] = []
    duplicate: list[str] = []
    hash_mismatch: list[str] = []
    identity_mismatch: list[str] = []

    for task in manifest.to_dict(orient="records"):
        task_id = str(task["task_id"])
        files = result_files.get(task_id, [])
        if not files:
            missing.append(task_id)
            continue
        if len(files) > 1:
            duplicate.append(task_id)
            continue
        result_path = files[0]
        try:
            record = json.loads(result_path.read_text(encoding="utf-8"))
        except Exception:
            failed.append(task_id)
            continue
        if record.get("status") != "success":
            failed.append(task_id)
            continue
        if str(record.get("config_hash", "")) != str(task["config_hash"]):
            hash_mismatch.append(task_id)
            continue
        if not _result_identity_matches(task, record):
            identity_mismatch.append(task_id)
            continue
        try:
            rows.append(_harvest_row(task, record, result_path))
        except Exception:
            failed.append(task_id)
            continue

    harvest = pd.DataFrame(rows, columns=list(HARVEST_COLUMNS))
    _write_dataframe_atomic(output_path, harvest)
    partial = len(rows) != len(manifest)
    report = _harvest_report(
        manifest=manifest,
        n_success=len(rows),
        missing=missing,
        failed=failed,
        duplicate=duplicate,
        hash_mismatch=hash_mismatch,
        identity_mismatch=identity_mismatch,
        output_path=Path(output_path),
        partial=partial,
    )
    _write_text_atomic(report_path, report)
    return Tier2HarvestResult(
        output_path=Path(output_path),
        report_path=Path(report_path),
        n_manifest_tasks=int(len(manifest)),
        n_success=len(rows),
        n_missing=len(missing),
        n_failed=len(failed),
        n_duplicate=len(duplicate),
        n_hash_mismatch=len(hash_mismatch),
        n_identity_mismatch=len(identity_mismatch),
        partial=partial,
        missing_task_ids=missing,
        failed_task_ids=failed,
        duplicate_task_ids=duplicate,
        hash_mismatch_task_ids=hash_mismatch,
        identity_mismatch_task_ids=identity_mismatch,
    )


def tier2_config_hash(config: Tier2Config, config_path: str | Path | None = None) -> str:
    """Return a full SHA-256 hash for the effective Tier-2 config and source file bytes."""

    raw_sha = _sha256_file(config_path) if config_path is not None and Path(config_path).exists() else "missing"
    payload = {
        "effective_config": asdict(config),
        "raw_config_sha256": raw_sha,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def write_tier2_dry_run_inputs(
    survivors_path: str | Path,
    outdir: str | Path,
    *,
    cpu_hours_per_input: float = DEFAULT_CPU_HOURS_PER_INPUT,
) -> Tier2DryRunResult:
    """Write neutral+cation .gjf inputs per unique survivor monomer. Does NOT run Gaussian."""

    frame = pd.read_csv(survivors_path)
    if "monomer_canonical_smiles" not in frame.columns:
        raise ValueError(
            f"{survivors_path} lacks a 'monomer_canonical_smiles' column required for Tier-2 inputs"
        )

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    seen: dict[str, str] = {}
    for _, row in frame.iterrows():
        smiles = str(row["monomer_canonical_smiles"])
        if smiles and smiles not in seen:
            seen[smiles] = str(row.get("monomer_name", smiles)) if "monomer_name" in frame.columns else smiles

    input_paths: list[Path] = []
    for index, (smiles, name) in enumerate(seen.items()):
        safe = _safe_name(name) or f"monomer{index:04d}"
        species = SpeciesSpec(canonical_smiles=smiles, charge=0, multiplicity=1)
        neutral = build_gaussian_input(species, charge=0, multiplicity=1)
        cation = build_gaussian_input(species, charge=1, multiplicity=2)
        neutral_path = out / f"{index:04d}_{safe}_neutral.gjf"
        cation_path = out / f"{index:04d}_{safe}_cation.gjf"
        neutral_path.write_text(neutral, encoding="utf-8")
        cation_path.write_text(cation, encoding="utf-8")
        input_paths.extend([neutral_path, cation_path])

    return Tier2DryRunResult(
        outdir=out,
        n_survivors=int(len(frame)),
        n_unique_monomers=len(seen),
        input_paths=input_paths,
        estimated_cpu_hours=len(input_paths) * float(cpu_hours_per_input),
    )


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_")


@dataclass
class Tier2RefinedResult:
    """Outputs of the Tier-2 refined screen (tighter window filter + §5 composite re-rank)."""

    refined: pd.DataFrame
    n_tier1_survivors: int
    n_tier2_survivors: int
    refined_window_margin_V: float
    tier2_dft_pending: bool
    output_path: Path


def run_tier2_refined_screen(
    survivors_path: str | Path,
    output_path: str | Path,
    *,
    dft_results_path: str | Path | None = None,
    tier1_config_path: str | Path | None = None,
    scoring_config_path: str | Path | None = None,
    refined_window_margin_V: float = DEFAULT_REFINED_WINDOW_MARGIN_V,
) -> Tier2RefinedResult:
    """Directive §4.2 refined screen: tighter window filter on Tier-1 survivors, then §5 re-rank.

    Takes the Tier-1 ranked survivors and applies the TIGHTER constraint ① — the monomer adiabatic
    IP must be at least ``refined_window_margin_V`` (default 0.5 V) below the solvent anodic limit —
    while KEEPING the Tier-1 anion-stability and solubility constraints. The refined survivors are
    re-ranked with the SAME §5 composite (reusing ``scoring.yaml`` — weights/formula unchanged;
    min-max is recomputed over the refined set). The monomer Eox uses the Tier-2 DFT value when a
    DFT results CSV is supplied (per-monomer, V vs Ag/AgCl); otherwise it falls back to the
    calibrated Tier-1 value and flags ``tier2_dft_pending=True`` so the path is exercisable now.
    Output ``outputs/tier2_refined.csv``. NO new hard constants beyond the 0.5 V margin; does NOT
    touch the pinned calibration / scoring weights / composite formula.
    """

    frame = pd.read_csv(survivors_path)
    n_tier1 = int(len(frame))
    tier1_config = load_tier1_config(tier1_config_path) if tier1_config_path else load_tier1_config()
    filters = tier1_config["filters"]

    eox_used, pending = _resolve_monomer_eox(frame, dft_results_path)
    refined = frame.copy()
    refined["monomer_Eox_used_V_vs_AgAgCl"] = eox_used
    refined["tier2_dft_pending"] = pending
    refined["refined_window_margin_V"] = (
        refined["solvent_anodic_limit_V"] - refined["monomer_Eox_used_V_vs_AgAgCl"]
    )

    pass_window = refined["refined_window_margin_V"] > float(refined_window_margin_V)
    pass_anion = refined["anion_stability_margin_V"] > float(filters["min_anion_stability_margin_V"])
    pass_solubility = refined["solvation_dG_kcal_mol"] < float(filters["max_solvation_dG_kcal_mol"])
    refined["pass_refined_window_margin"] = pass_window
    refined["passes_tier2_refined_filters"] = pass_window & pass_anion & pass_solubility

    survivors = refined.loc[refined["passes_tier2_refined_filters"]].reset_index(drop=True)
    # Re-rank the refined survivors with the §5 composite (drop the stale Tier-1 score columns so
    # add_composite_score recomputes cleanly over the refined set).
    survivors = survivors.drop(
        columns=[c for c in ("composite_score", "pareto_front") if c in survivors.columns],
        errors="ignore",
    )
    scored = add_composite_score(
        survivors,
        load_scoring_config(scoring_config_path) if scoring_config_path else load_scoring_config(),
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out, index=False)
    return Tier2RefinedResult(
        refined=scored,
        n_tier1_survivors=n_tier1,
        n_tier2_survivors=int(len(scored)),
        refined_window_margin_V=float(refined_window_margin_V),
        tier2_dft_pending=bool(pending),
        output_path=out,
    )


def _resolve_monomer_eox(
    frame: pd.DataFrame,
    dft_results_path: str | Path | None,
) -> tuple[pd.Series, bool]:
    """Return (per-row monomer Eox in V vs Ag/AgCl, tier2_dft_pending).

    Prefers a Tier-2 DFT Eox column (merged per monomer from ``dft_results_path``); otherwise falls
    back to the calibrated Tier-1 ``monomer_Eox_filter_V_vs_AgAgCl`` and flags the run as pending.
    """

    if dft_results_path is not None and Path(dft_results_path).exists():
        dft = pd.read_csv(dft_results_path)
        column = next((c for c in _DFT_EOX_COLUMNS if c in dft.columns), None)
        if column is not None and "monomer_canonical_smiles" in dft.columns:
            mapping = (
                dft.dropna(subset=[column])
                .drop_duplicates("monomer_canonical_smiles")
                .set_index("monomer_canonical_smiles")[column]
            )
            eox = frame["monomer_canonical_smiles"].map(mapping)
            if eox.notna().any():
                # Fill any monomer missing from the DFT set with the calibrated Tier-1 value.
                eox = eox.fillna(frame["monomer_Eox_filter_V_vs_AgAgCl"])
                return eox, False
    return frame["monomer_Eox_filter_V_vs_AgAgCl"], True


def _manifest_rows_from_selection(
    selection: pd.DataFrame,
    *,
    method_label: str,
    config_hash: str,
) -> list[dict[str, Any]]:
    _validate_selection_schema(selection)
    solvents = {solvent.name: solvent for solvent in load_solvents()}
    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for index, row in selection.iterrows():
        canonical_smiles = _canonical_smiles_from_selection(row, row_number=index + 2)
        solvent_name = str(row["solvent_name"]).strip()
        if solvent_name not in solvents:
            raise ValueError(f"row {index + 2}: unknown solvent_name {solvent_name!r}")
        monomer_name = str(row.get("monomer_name", canonical_smiles)).strip() or canonical_smiles
        selection_role = str(row.get("selection_role", "selected")).strip() or "selected"
        key = (canonical_smiles, solvent_name, "adiabatic_ip", method_label, config_hash)
        if key not in grouped:
            grouped[key] = {
                "entity_type": "monomer",
                "monomer_names": [],
                "canonical_smiles": canonical_smiles,
                "solvent_name": solvent_name,
                "quantity": "adiabatic_ip",
                "initial_charge": 0,
                "initial_multiplicity": 1,
                "final_charge": 1,
                "final_multiplicity": 2,
                "method_label": method_label,
                "config_hash": config_hash,
                "status": "planned",
                "selection_roles": [],
                "source_rows": [],
            }
        _append_unique(grouped[key]["monomer_names"], monomer_name)
        _append_unique(grouped[key]["selection_roles"], selection_role)
        grouped[key]["source_rows"].append(str(index + 2))

    rows = []
    for item in grouped.values():
        row = {
            "entity_type": item["entity_type"],
            "monomer_name": "|".join(item["monomer_names"]),
            "canonical_smiles": item["canonical_smiles"],
            "solvent_name": item["solvent_name"],
            "quantity": item["quantity"],
            "initial_charge": item["initial_charge"],
            "initial_multiplicity": item["initial_multiplicity"],
            "final_charge": item["final_charge"],
            "final_multiplicity": item["final_multiplicity"],
            "method_label": item["method_label"],
            "config_hash": item["config_hash"],
            "status": item["status"],
            "selection_role": "|".join(item["selection_roles"]),
            "source_selection_row": "|".join(item["source_rows"]),
        }
        row["task_id"] = _task_id(row)
        rows.append(row)

    return sorted(rows, key=lambda r: (r["solvent_name"], r["monomer_name"], r["canonical_smiles"]))


def _validate_selection_schema(selection: pd.DataFrame) -> None:
    if "solvent_name" not in selection.columns:
        raise ValueError("Tier-2 selection CSV is missing required column: solvent_name")
    if not any(column in selection.columns for column in _selection_smiles_columns()):
        raise ValueError(
            "Tier-2 selection CSV must include one monomer SMILES column: "
            + ", ".join(_selection_smiles_columns())
        )


def _selection_smiles_columns() -> tuple[str, ...]:
    return ("monomer_canonical_smiles", "canonical_smiles", "monomer_smiles", "smiles")


def _canonical_smiles_from_selection(row: pd.Series, *, row_number: int) -> str:
    for column in _selection_smiles_columns():
        if column not in row:
            continue
        value = str(row[column]).strip()
        if not value:
            continue
        mol = Chem.MolFromSmiles(value, sanitize=True)
        if mol is None:
            raise ValueError(f"row {row_number}: RDKit failed to sanitize {column}={value!r}")
        return Chem.MolToSmiles(mol, canonical=True)
    raise ValueError(f"row {row_number}: no non-empty monomer SMILES value")


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _task_id(row: dict[str, Any]) -> str:
    payload = {
        "canonical_smiles": row["canonical_smiles"],
        "solvent_name": row["solvent_name"],
        "quantity": row["quantity"],
        "method_label": row["method_label"],
        "config_hash": row["config_hash"],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return "t2_" + digest[:16]


def _plan_summary(
    *,
    selection_path: Path,
    config_path: Path,
    config: Tier2Config,
    config_hash: str,
    method_label: str,
    n_selection_rows: int,
    n_tasks: int,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "command": "tier2-plan",
        "created_at_utc": _utc_now(),
        "selection_path": str(selection_path),
        "config_path": str(config_path),
        "method_label": method_label,
        "method_description": config.method_label(),
        "config_hash": config_hash,
        "effective_config": asdict(config),
        "n_selection_rows": n_selection_rows,
        "n_unique_tasks": n_tasks,
        "n_gaussian_calculations": n_tasks * 2,
        "n_expected_result_json": n_tasks,
        "n_expected_raw_logs": n_tasks * 2,
        "n_expected_inputs": n_tasks * 2,
        "architecture": "one adiabatic-IP task per unique (monomer, solvent, method config); no triad-level quantum loop",
        "charge_multiplicity": {
            "neutral": {"charge": 0, "multiplicity": 1},
            "cation": {"charge": 1, "multiplicity": 2},
        },
    }


def _plan_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Tier-2 Pilot Plan",
            "",
            f"- created_at_utc: {summary['created_at_utc']}",
            f"- selection: `{summary['selection_path']}`",
            f"- config: `{summary['config_path']}`",
            f"- method: `{summary['method_label']}` ({summary['method_description']})",
            f"- config_hash: `{summary['config_hash']}`",
            f"- selection rows: {summary['n_selection_rows']}",
            f"- unique logical tasks: {summary['n_unique_tasks']}",
            f"- Gaussian calculations estimated: {summary['n_gaussian_calculations']} (neutral + cation)",
            f"- expected raw logs: {summary['n_expected_raw_logs']}",
            "",
            "The plan is per monomer-solvent task, not per triad. Repeated salts/cations in the selection collapse before any Engine call.",
            "Mock execution is suitable for plumbing only; real Gaussian execution remains a later reviewed cluster work unit.",
            "",
        ]
    )


def _select_manifest_task(manifest_path: str | Path, task_id: str) -> dict[str, Any]:
    manifest = _read_manifest(manifest_path)
    matches = manifest[manifest["task_id"] == task_id]
    if len(matches) != 1:
        raise ValueError(f"manifest must contain exactly one row for task_id={task_id!r}; found {len(matches)}")
    return matches.iloc[0].to_dict()


def _read_manifest(manifest_path: str | Path) -> pd.DataFrame:
    manifest = pd.read_csv(manifest_path, keep_default_na=False)
    missing = set(TASK_MANIFEST_COLUMNS).difference(manifest.columns)
    if missing:
        raise ValueError(f"{manifest_path} missing manifest columns: {', '.join(sorted(missing))}")
    return manifest


def _tier2_engine(engine_name: str, *, config: Tier2Config, work_dir: Path):
    if engine_name == "mock":
        return MockEngine()
    if engine_name == "gaussian":
        return GaussianEngine(config=config, work_root=work_dir)
    raise ValueError(f"Unknown Tier-2 task engine {engine_name!r}")


def _task_request(task: dict[str, Any]) -> CalcRequest:
    solvents = {solvent.name: solvent for solvent in load_solvents()}
    solvent = solvents.get(str(task["solvent_name"]))
    if solvent is None:
        raise ValueError(f"unknown solvent_name in manifest: {task['solvent_name']!r}")
    return CalcRequest(
        species=SpeciesSpec(
            canonical_smiles=str(task["canonical_smiles"]),
            charge=int(task["initial_charge"]),
            multiplicity=int(task["initial_multiplicity"]),
        ),
        method=str(task["method_label"]),
        solvent_eps_r=float(solvent.eps_r),
        solvent_model_name=str(task["solvent_name"]),
        quantity=str(task["quantity"]),
    )


def _successful_task_record(
    task: dict[str, Any],
    *,
    result_value_eV: float,
    result_unit: str,
    result_method: str,
    raw: dict[str, Any],
    engine_name: str,
    cache_path: Path,
    work_dir: Path,
    config: Tier2Config,
) -> dict[str, Any]:
    initial = raw.get("initial_parsed", {}) if isinstance(raw, dict) else {}
    final = raw.get("final_parsed", {}) if isinstance(raw, dict) else {}
    eox_v = ip_eV_to_potential_vs_AgAgCl(result_value_eV)
    return _json_safe(
        {
            "schema_version": 1,
            "created_at_utc": _utc_now(),
            "status": "success",
            "task_id": task["task_id"],
            "entity_type": task["entity_type"],
            "monomer_name": task["monomer_name"],
            "canonical_smiles": task["canonical_smiles"],
            "solvent_name": task["solvent_name"],
            "quantity": task["quantity"],
            "method_label": task["method_label"],
            "result_method": result_method,
            "config_hash": task["config_hash"],
            "effective_config": asdict(config),
            "engine": engine_name,
            "adiabatic_ip_eV": result_value_eV,
            "result_unit": result_unit,
            "tier2_monomer_Eox_V_vs_AgAgCl": eox_v,
            "initial_charge": int(task["initial_charge"]),
            "initial_multiplicity": int(task["initial_multiplicity"]),
            "final_charge": int(task["final_charge"]),
            "final_multiplicity": int(task["final_multiplicity"]),
            "energy_basis": _combined_energy_basis(initial, final),
            "frequency_requested": bool(config.use_freq),
            "neutral": _species_energy_record(initial),
            "cation": _species_energy_record(final),
            "raw": raw,
            "cache_path": str(cache_path),
            "work_dir": str(work_dir),
            "runtime": _runtime_record(),
        }
    )


def _failed_task_record(
    task: dict[str, Any],
    *,
    engine_name: str,
    cache_path: Path,
    work_dir: Path,
    error: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at_utc": _utc_now(),
        "status": "failed",
        "task_id": task["task_id"],
        "entity_type": task["entity_type"],
        "monomer_name": task["monomer_name"],
        "canonical_smiles": task["canonical_smiles"],
        "solvent_name": task["solvent_name"],
        "quantity": task["quantity"],
        "method_label": task["method_label"],
        "config_hash": task["config_hash"],
        "engine": engine_name,
        "error": error,
        "cache_path": str(cache_path),
        "work_dir": str(work_dir),
        "runtime": _runtime_record(),
    }


def _species_energy_record(parsed: dict[str, Any]) -> dict[str, Any]:
    return {
        "scf_energy_Eh": parsed.get("scf_energy_Eh"),
        "scf_energy_eV": parsed.get("scf_energy_eV"),
        "gibbs_free_energy_Eh": parsed.get("gibbs_free_energy_Eh"),
        "gibbs_free_energy_eV": parsed.get("gibbs_free_energy_eV"),
        "energy_basis": parsed.get("energy_basis"),
        "normal_termination": parsed.get("normal_termination"),
        "frequency_requested": parsed.get("frequency_requested"),
        "has_frequency_data": parsed.get("has_frequency_data"),
        "imaginary_frequency_count": parsed.get("imaginary_frequency_count"),
        "input_path": parsed.get("input_path"),
        "log_path": parsed.get("log_path"),
        "stdout_path": parsed.get("stdout_path"),
        "stderr_path": parsed.get("stderr_path"),
        "returncode": parsed.get("returncode"),
    }


def _combined_energy_basis(initial: dict[str, Any], final: dict[str, Any]) -> str:
    bases = {str(value) for value in (initial.get("energy_basis"), final.get("energy_basis")) if value}
    if not bases:
        return "mock_or_unknown"
    if len(bases) == 1:
        return bases.pop()
    return "mixed:" + "|".join(sorted(bases))


def _collect_result_files(result_dir: str | Path) -> dict[str, list[Path]]:
    root = Path(result_dir)
    files = list(root.glob("*/result.json")) + list(root.glob("*.result.json"))
    by_task: dict[str, list[Path]] = {}
    for path in files:
        task_id = path.parent.name if path.name == "result.json" else path.name.removesuffix(".result.json")
        by_task.setdefault(task_id, []).append(path)
    return by_task


def _result_identity_matches(task: dict[str, Any], record: dict[str, Any]) -> bool:
    for column in (
        "task_id",
        "canonical_smiles",
        "solvent_name",
        "quantity",
        "method_label",
        "initial_charge",
        "initial_multiplicity",
        "final_charge",
        "final_multiplicity",
    ):
        if str(record.get(column, "")) != str(task[column]):
            return False
    return True


def _harvest_row(task: dict[str, Any], record: dict[str, Any], result_path: Path) -> dict[str, Any]:
    ip_eV = float(record["adiabatic_ip_eV"])
    eox_v = ip_eV_to_potential_vs_AgAgCl(ip_eV)
    neutral = record.get("neutral", {})
    cation = record.get("cation", {})
    return {
        "task_id": task["task_id"],
        "monomer_name": task["monomer_name"],
        "monomer_canonical_smiles": task["canonical_smiles"],
        "canonical_smiles": task["canonical_smiles"],
        "solvent_name": task["solvent_name"],
        "quantity": task["quantity"],
        "method_label": task["method_label"],
        "config_hash": task["config_hash"],
        "tier2_monomer_Eox_V_vs_AgAgCl": eox_v,
        "dft_monomer_Eox_V_vs_AgAgCl": eox_v,
        "adiabatic_ip_eV": ip_eV,
        "energy_basis": record.get("energy_basis", ""),
        "initial_charge": task["initial_charge"],
        "initial_multiplicity": task["initial_multiplicity"],
        "final_charge": task["final_charge"],
        "final_multiplicity": task["final_multiplicity"],
        "neutral_scf_energy_Eh": neutral.get("scf_energy_Eh"),
        "neutral_gibbs_free_energy_Eh": neutral.get("gibbs_free_energy_Eh"),
        "cation_scf_energy_Eh": cation.get("scf_energy_Eh"),
        "cation_gibbs_free_energy_Eh": cation.get("gibbs_free_energy_Eh"),
        "frequency_requested": record.get("frequency_requested"),
        "neutral_imaginary_frequency_count": neutral.get("imaginary_frequency_count"),
        "cation_imaginary_frequency_count": cation.get("imaginary_frequency_count"),
        "engine": record.get("engine"),
        "cache_path": record.get("cache_path"),
        "work_dir": record.get("work_dir"),
        "result_path": str(result_path),
    }


def _harvest_report(
    *,
    manifest: pd.DataFrame,
    n_success: int,
    missing: list[str],
    failed: list[str],
    duplicate: list[str],
    hash_mismatch: list[str],
    identity_mismatch: list[str],
    output_path: Path,
    partial: bool,
) -> str:
    status = "PARTIAL" if partial else "COMPLETE"
    return "\n".join(
        [
            "# Tier-2 Harvest Report",
            "",
            f"- status: {status}",
            f"- manifest tasks: {len(manifest)}",
            f"- successful validated tasks: {n_success}",
            f"- missing: {len(missing)}",
            f"- failed/incomplete: {len(failed)}",
            f"- duplicate result IDs: {len(duplicate)}",
            f"- config-hash mismatches: {len(hash_mismatch)}",
            f"- identity mismatches: {len(identity_mismatch)}",
            f"- output: `{output_path}`",
            "",
            _task_list("missing_task_ids", missing),
            _task_list("failed_task_ids", failed),
            _task_list("duplicate_task_ids", duplicate),
            _task_list("hash_mismatch_task_ids", hash_mismatch),
            _task_list("identity_mismatch_task_ids", identity_mismatch),
            "",
            "Only validated successful Tier-2 task results were combined. Failed or missing values were not filled from Tier-1.",
            "",
        ]
    )


def _task_list(label: str, values: list[str]) -> str:
    return f"- {label}: " + (", ".join(values) if values else "none")


def _write_json_atomic(path: str | Path, payload: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=output.name, suffix=".tmp", dir=output.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(_json_safe(payload), handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_name, output)


def _write_text_atomic(path: str | Path, text: str) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=output.name, suffix=".tmp", dir=output.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(tmp_name, output)


def _write_dataframe_atomic(path: str | Path, frame: pd.DataFrame) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=output.name, suffix=".tmp", dir=output.parent)
    os.close(fd)
    frame.to_csv(tmp_name, index=False)
    os.replace(tmp_name, output)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return str(value)
    return value


def _sha256_file(path: str | Path | None) -> str:
    if path is None:
        return "missing"
    target = Path(path)
    if not target.exists():
        return "missing"
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _runtime_record() -> dict[str, Any]:
    return {
        "created_at_utc": _utc_now(),
        "python": platform.python_version(),
        "hostname": platform.node(),
        "cwd": str(Path.cwd()),
        "git": _env_git_record(),
        "environment": {
            key: os.environ.get(key, "")
            for key in (
                "COMBHTS_GIT_SHA",
                "JOB_ID",
                "SGE_TASK_ID",
                "HOSTNAME",
                "OMP_NUM_THREADS",
                "NSLOTS",
            )
        },
    }


def _env_git_record() -> dict[str, str]:
    return {
        "commit": os.environ.get("COMBHTS_GIT_SHA", "unknown"),
        "commit_short": os.environ.get("COMBHTS_GIT_SHA", "unknown")[:12]
        if os.environ.get("COMBHTS_GIT_SHA")
        else "unknown",
        "source": "COMBHTS_GIT_SHA environment variable",
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

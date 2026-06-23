from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

from eps.engines.gaussian import load_tier2_config
from eps.storage import SQLiteCache
from eps.workflow.tier2 import (
    TASK_MANIFEST_COLUMNS,
    harvest_tier2_results,
    plan_tier2_pilot,
    run_tier2_task,
    tier2_config_hash,
)


def _write_config(
    path: Path,
    *,
    method: str = "B3LYP",
    smd_solvent: str = "null",
    use_freq: bool = False,
) -> Path:
    path.write_text(
        "\n".join(
            [
                f"method: {method}",
                "basis: 6-31G(d,p)",
                f"smd_solvent: {smd_solvent}",
                f"use_freq: {str(use_freq).lower()}",
                "mem: 8GB",
                "nprocshared: 8",
                "calibration_set: benchmark_calibration_eligible",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_selection(path: Path, *, reverse: bool = False) -> Path:
    rows = [
        {
            "monomer_name": "thiophene",
            "monomer_canonical_smiles": "c1ccsc1",
            "solvent_name": "acetonitrile",
            "salt": "TBAPF6",
            "selection_role": "recommended",
        },
        {
            "monomer_name": "thiophene",
            "monomer_canonical_smiles": "c1ccsc1",
            "solvent_name": "acetonitrile",
            "salt": "TEAPF6",
            "selection_role": "recommended",
        },
        {
            "monomer_name": "thiophene",
            "monomer_canonical_smiles": "c1ccsc1",
            "solvent_name": "DCM",
            "salt": "TBAPF6",
            "selection_role": "contrast",
        },
        {
            "monomer_name": "EDOT",
            "monomer_canonical_smiles": "C1COc2ccsc2O1",
            "solvent_name": "acetonitrile",
            "salt": "TBAPF6",
            "selection_role": "recommended",
        },
    ]
    if reverse:
        rows = list(reversed(rows))
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _plan(tmp_path: Path):
    config = _write_config(tmp_path / "tier2.yaml")
    selection = _write_selection(tmp_path / "selection.csv")
    result = plan_tier2_pilot(selection, config, tmp_path / "plan")
    manifest = pd.read_csv(result.manifest_path, keep_default_na=False)
    return result, manifest, config


def test_plan_deduplicates_repeated_salts_but_keeps_monomer_solvent_identity(tmp_path: Path) -> None:
    result, manifest, _config = _plan(tmp_path)

    assert list(manifest.columns) == list(TASK_MANIFEST_COLUMNS)
    assert result.n_selection_rows == 4
    assert result.n_tasks == 3
    assert result.n_unique_monomer_solvent_pairs == 3
    assert set(manifest["solvent_name"]) == {"acetonitrile", "DCM"}

    thiophene = manifest[manifest["canonical_smiles"] == "c1ccsc1"]
    assert len(thiophene) == 2  # same monomer in two solvents remains two solvent-specific tasks
    acn_thiophene = thiophene[thiophene["solvent_name"] == "acetonitrile"].iloc[0]
    assert acn_thiophene["source_selection_row"] == "2|3"  # repeated salts/cations collapsed
    assert acn_thiophene["initial_charge"] == 0
    assert acn_thiophene["initial_multiplicity"] == 1
    assert acn_thiophene["final_charge"] == 1
    assert acn_thiophene["final_multiplicity"] == 2


def test_plan_config_hash_changes_on_method_solvent_and_freq(tmp_path: Path) -> None:
    gas = _write_config(tmp_path / "gas.yaml")
    solvent = _write_config(tmp_path / "smd.yaml", smd_solvent="acetonitrile")
    freq = _write_config(tmp_path / "freq.yaml", use_freq=True)
    method = _write_config(tmp_path / "pbe0.yaml", method="PBE0")

    hashes = {
        tier2_config_hash(load_tier2_config(path), path)
        for path in (gas, solvent, freq, method)
    }
    assert len(hashes) == 4


def test_plan_task_ids_are_deterministic_across_selection_order(tmp_path: Path) -> None:
    config = _write_config(tmp_path / "tier2.yaml")
    selection_a = _write_selection(tmp_path / "selection_a.csv")
    selection_b = _write_selection(tmp_path / "selection_b.csv", reverse=True)

    plan_a = plan_tier2_pilot(selection_a, config, tmp_path / "plan_a")
    plan_b = plan_tier2_pilot(selection_b, config, tmp_path / "plan_b")
    a = pd.read_csv(plan_a.manifest_path)
    b = pd.read_csv(plan_b.manifest_path)

    assert set(a["task_id"]) == set(b["task_id"])


def test_run_task_writes_atomic_result_and_task_local_cache(tmp_path: Path) -> None:
    _result, manifest, config = _plan(tmp_path)
    task_id = str(manifest.iloc[0]["task_id"])

    first = run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_id,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )
    assert first.status == "success"
    assert first.result_path.exists()
    assert first.status_path.read_text(encoding="utf-8") == "success\n"
    assert first.cache_path == tmp_path / "results" / "task_caches" / f"{task_id}.sqlite"
    assert not list(first.result_path.parent.glob("*.tmp"))

    record = json.loads(first.result_path.read_text(encoding="utf-8"))
    assert record["task_id"] == task_id
    assert record["status"] == "success"
    assert record["engine"] == "mock"
    assert "adiabatic_ip_eV" in record


def test_cache_separation_and_mock_idempotency(tmp_path: Path) -> None:
    _result, manifest, config = _plan(tmp_path)
    task_a = str(manifest.iloc[0]["task_id"])
    task_b = str(manifest.iloc[1]["task_id"])

    first = run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_a,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )
    second = run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_a,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )
    other = run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_b,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )

    assert first.cache_path != other.cache_path
    assert SQLiteCache(first.cache_path).count() == 1
    first_record = json.loads(first.result_path.read_text(encoding="utf-8"))
    second_record = json.loads(second.result_path.read_text(encoding="utf-8"))
    assert first_record["adiabatic_ip_eV"] == second_record["adiabatic_ip_eV"]


def test_harvest_reports_partial_missing_and_preserves_raw_fields(tmp_path: Path) -> None:
    _result, manifest, config = _plan(tmp_path)
    task_id = str(manifest.iloc[0]["task_id"])
    run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_id,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )

    harvest = harvest_tier2_results(
        tmp_path / "plan" / "task_manifest.csv",
        tmp_path / "results",
        tmp_path / "tier2_monomer_eox.csv",
        tmp_path / "harvest_report.md",
    )

    assert harvest.partial is True
    assert harvest.n_success == 1
    assert harvest.n_missing == len(manifest) - 1
    out = pd.read_csv(harvest.output_path)
    assert len(out) == 1
    assert "tier2_monomer_Eox_V_vs_AgAgCl" in out.columns
    assert "neutral_scf_energy_Eh" in out.columns
    report = harvest.report_path.read_text(encoding="utf-8")
    assert "PARTIAL" in report
    assert "not filled from Tier-1" in report


def test_harvest_rejects_hash_mismatch_and_incomplete_result(tmp_path: Path) -> None:
    _result, manifest, config = _plan(tmp_path)
    task_id = str(manifest.iloc[0]["task_id"])
    run = run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_id,
        engine_name="mock",
        result_dir=tmp_path / "results_hash",
        work_root=tmp_path / "work",
        config_path=config,
    )
    record = json.loads(run.result_path.read_text(encoding="utf-8"))
    record["config_hash"] = "bad"
    run.result_path.write_text(json.dumps(record), encoding="utf-8")

    mismatch = harvest_tier2_results(
        tmp_path / "plan" / "task_manifest.csv",
        tmp_path / "results_hash",
        tmp_path / "mismatch.csv",
        tmp_path / "mismatch.md",
    )
    assert mismatch.n_hash_mismatch == 1
    assert mismatch.n_success == 0

    result_dir = tmp_path / "results_incomplete" / task_id
    result_dir.mkdir(parents=True)
    incomplete = {
        "status": "success",
        "task_id": task_id,
        "canonical_smiles": manifest.iloc[0]["canonical_smiles"],
        "solvent_name": manifest.iloc[0]["solvent_name"],
        "quantity": manifest.iloc[0]["quantity"],
        "method_label": manifest.iloc[0]["method_label"],
        "config_hash": manifest.iloc[0]["config_hash"],
        "initial_charge": 0,
        "initial_multiplicity": 1,
        "final_charge": 1,
        "final_multiplicity": 2,
    }
    (result_dir / "result.json").write_text(json.dumps(incomplete), encoding="utf-8")
    bad = harvest_tier2_results(
        tmp_path / "plan" / "task_manifest.csv",
        tmp_path / "results_incomplete",
        tmp_path / "bad.csv",
        tmp_path / "bad.md",
    )
    assert bad.n_failed == 1
    assert bad.n_success == 0


def test_planner_and_harvester_do_not_spawn_subprocesses(tmp_path: Path, monkeypatch) -> None:
    def fail_subprocess(*args, **kwargs):
        raise AssertionError("planner/harvester must not spawn subprocesses")

    monkeypatch.setattr(subprocess, "run", fail_subprocess)

    _result, manifest, config = _plan(tmp_path)
    task_id = str(manifest.iloc[0]["task_id"])
    run_tier2_task(
        tmp_path / "plan" / "task_manifest.csv",
        task_id,
        engine_name="mock",
        result_dir=tmp_path / "results",
        work_root=tmp_path / "work",
        config_path=config,
    )
    harvest = harvest_tier2_results(
        tmp_path / "plan" / "task_manifest.csv",
        tmp_path / "results",
        tmp_path / "out.csv",
        tmp_path / "out.md",
    )
    assert harvest.n_success == 1

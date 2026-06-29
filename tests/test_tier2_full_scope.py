"""Tier-2 full §4.2 DFT scope: the planner emits the complete per-species state set."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.workflow.tier2 import (
    _harvest_row,
    _manifest_rows_from_selection,
    harvest_tier2_results,
    plan_tier2_pilot,
    run_tier2_task,
)


def _selection() -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "monomer_canonical_smiles": "c1ccsc1",
            "monomer_name": "thiophene",
            "solvent_name": "acetonitrile",
            "salt": "TBAPF6",
            "anion_canonical_smiles": "F[P-](F)(F)(F)(F)F",
            "cation_canonical_smiles": "CCCC[N+](CCCC)(CCCC)CCCC",
        }]
    )


def test_monomer_ip_scope_is_backward_compatible() -> None:
    rows = _manifest_rows_from_selection(_selection(), method_label="m", config_hash="h")
    assert len(rows) == 1
    assert rows[0]["entity_type"] == "monomer"
    assert rows[0]["quantity"] == "adiabatic_ip"


def test_full_scope_emits_all_directive_states() -> None:
    rows = _manifest_rows_from_selection(_selection(), method_label="m", config_hash="h", scope="full")
    got = {(r["entity_type"], r["quantity"]) for r in rows}
    assert got == {
        ("monomer", "adiabatic_ip"),          # monomer oxidation (AIP)
        ("monomer", "adiabatic_ea"),          # monomer reduction (anion state)
        ("solvent", "adiabatic_ip"),          # solvent anodic (self-solvent)
        ("solvent", "adiabatic_ea"),          # solvent cathodic
        ("electrolyte_anion", "adiabatic_ip"),    # anion oxidation
        ("electrolyte_cation", "adiabatic_ea"),   # cation reduction
    }
    # charge/multiplicity bookkeeping for the two ion states
    anion = next(r for r in rows if r["entity_type"] == "electrolyte_anion")
    assert (anion["initial_charge"], anion["final_charge"]) == (-1, 0)  # anion -> neutral radical
    cation = next(r for r in rows if r["entity_type"] == "electrolyte_cation")
    assert (cation["initial_charge"], cation["final_charge"]) == (1, 0)  # cation -> neutral radical
    # task ids are unique across the distinct (entity,species,solvent,quantity) tuples
    assert len({r["task_id"] for r in rows}) == len(rows)


def test_full_scope_dedupes_solvent_across_triads() -> None:
    # two monomers, same solvent/salt -> solvent + electrolyte tasks computed ONCE (per-species)
    sel = pd.concat([_selection(), _selection().assign(monomer_canonical_smiles="c1cc[nH]c1", monomer_name="pyrrole")])
    rows = _manifest_rows_from_selection(sel, method_label="m", config_hash="h", scope="full")
    solvent_tasks = [r for r in rows if r["entity_type"] == "solvent"]
    assert len(solvent_tasks) == 2  # one anodic + one cathodic for the single shared solvent
    monomer_ip = [r for r in rows if r["entity_type"] == "monomer" and r["quantity"] == "adiabatic_ip"]
    assert len(monomer_ip) == 2  # one per monomer


def test_full_scope_plan_run_harvest_chain_mock(tmp_path: Path) -> None:
    """End-to-end: plan(full) on the ORCA config -> run each task (mock) -> harvest, schema-clean."""
    sel = tmp_path / "sel.csv"
    _selection().to_csv(sel, index=False)
    config = Path(__file__).resolve().parents[1] / "configs" / "tier2_orca.yaml"
    plan = plan_tier2_pilot(sel, config, tmp_path / "plan", scope="full")
    assert plan.n_tasks == 6  # 1 triad: monomer IP+EA, solvent anodic+cathodic, anion-ox, cation-red

    manifest = tmp_path / "plan" / "task_manifest.csv"
    for tid in pd.read_csv(manifest)["task_id"]:
        # engine_name="mock" bypasses the orca engine-match guard; config_hash still validates.
        run_tier2_task(manifest, tid, engine_name="mock",
                       result_dir=tmp_path / "res", work_root=tmp_path / "work", config_path=config)
    h = harvest_tier2_results(manifest, tmp_path / "res", tmp_path / "harvest.csv", tmp_path / "rep.md")
    assert h.n_success == 6 and not h.partial
    df = pd.read_csv(tmp_path / "harvest.csv")
    assert "entity_type" in df.columns and "redox_potential_V_vs_AgAgCl" in df.columns
    # monomer-Eox column populated ONLY for the monomer oxidation row
    mono = df[df["entity_type"] == "monomer"]
    assert mono[mono["quantity"] == "adiabatic_ip"]["tier2_monomer_Eox_V_vs_AgAgCl"].notna().all()
    assert mono[mono["quantity"] == "adiabatic_ea"]["tier2_monomer_Eox_V_vs_AgAgCl"].isna().all()


def test_harvest_row_blanks_monomer_eox_for_non_monomer_oxidation() -> None:
    # a solvent oxidation row must NOT populate the monomer-Eox columns (only redox_potential).
    task = {
        "task_id": "t2_x", "entity_type": "solvent", "monomer_name": "acetonitrile",
        "canonical_smiles": "CC#N", "solvent_name": "acetonitrile", "quantity": "adiabatic_ip",
        "method_label": "m", "config_hash": "h",
        "initial_charge": 0, "initial_multiplicity": 1, "final_charge": 1, "final_multiplicity": 2,
    }
    record = {"adiabatic_ip_eV": 8.0, "neutral": {}, "cation": {}, "energy_basis": "scf"}
    from pathlib import Path

    row = _harvest_row(task, record, Path("/tmp/x.json"))
    assert row["tier2_monomer_Eox_V_vs_AgAgCl"] is None
    assert row["dft_monomer_Eox_V_vs_AgAgCl"] is None
    assert row["redox_potential_V_vs_AgAgCl"] is not None
    assert row["entity_type"] == "solvent"

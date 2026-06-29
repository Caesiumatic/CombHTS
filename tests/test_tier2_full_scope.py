"""Tier-2 full §4.2 DFT scope: the planner emits the complete per-species state set."""
from __future__ import annotations

import pandas as pd

from eps.workflow.tier2 import _harvest_row, _manifest_rows_from_selection


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

"""Unit tests for the decoupled openCOSMO-RS solvation module (pure / mockable parts).

The σ-profile DFT generation needs real ORCA (Lop); here we test the fixed-parameter template, the
combine-JSON assembly, and the dGsolv parse with a stubbed openCOSMORS binary.
"""
from __future__ import annotations

import json
from pathlib import Path

from eps.engines import cosmors
from eps.engines.cosmors import (
    COSMORS_24A_PARAMS,
    SigmaProfile,
    build_combine_payload,
    dgsolv_kcal_mol,
)


def _profile(tmp: Path, name: str, e_gas: float, ring: list[int]) -> SigmaProfile:
    p = tmp / f"{name}.orcacosmo"
    p.write_text("#dummy σ-profile\n", encoding="utf-8")
    return SigmaProfile(name, p, [e_gas, 0.0], ring)


def test_params_carry_the_fixed_24a_constants() -> None:
    # Verbatim from ORCA's validated template; per-species fields must NOT be baked in here.
    assert COSMORS_24A_PARAMS["Aeff"] == 5.925
    assert COSMORS_24A_PARAMS["SigmaHB"] == 0.009611
    assert COSMORS_24A_PARAMS["dGsolv_tau"]["16"] == 0.03499  # sulfur
    for leaked in ("dGsolv_E_gas", "dGsolv_numberOfAtomsInRing", "componentPaths", "calculations"):
        assert leaked not in COSMORS_24A_PARAMS


def test_build_combine_payload_inserts_solute_fields_and_both_profiles(tmp_path: Path) -> None:
    solute = _profile(tmp_path, "thiophene", -553.125910366615, [5, 0])
    solvent = _profile(tmp_path, "mecn", -132.817951195017, [0, 0])
    payload = build_combine_payload(solute, solvent, temperature=298.15)

    assert payload["dGsolv_E_gas"] == [-553.125910366615, 0.0]
    assert payload["dGsolv_numberOfAtomsInRing"] == [5, 0]
    assert payload["componentPaths"] == [str(solute.orcacosmo_path), str(solvent.orcacosmo_path)]
    assert payload["calculations"][0]["temperatures"] == [298.15]
    assert payload["calculations"][0]["component_indices"] == [0, 1]
    # fixed params still present and not mutated on the shared constant
    assert payload["Aeff"] == 5.925
    assert "dGsolv_E_gas" not in COSMORS_24A_PARAMS


def test_dgsolv_parses_opencosmors_output(tmp_path: Path, monkeypatch) -> None:
    solute = _profile(tmp_path, "thiophene", -553.1, [5, 0])
    solvent = _profile(tmp_path, "mecn", -132.8, [0, 0])

    def fake_run(cmd, check=False, capture_output=False, text=False):  # noqa: ARG001
        in_json, out_json = cmd[1], cmd[2]
        assert Path(in_json).exists()  # payload was written
        Path(out_json).write_text(json.dumps({"dGsolv": [[[-4.132111549377441, 0.0]]], "warnings": []}))

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(cosmors.subprocess, "run", fake_run)
    value = dgsolv_kcal_mol(solute, solvent, opencosmors_binary="/fake/openCOSMORS")
    assert value == -4.132111549377441


def test_load_cosmors_solvation_table(tmp_path: Path) -> None:
    from eps.properties import load_cosmors_solvation_table

    csv_path = tmp_path / "solvation_cosmors.csv"
    csv_path.write_text(
        "monomer_name,monomer_canonical_smiles,solvent_name,dGsolv_kcal_mol,method\n"
        "thiophene,c1ccsc1,acetonitrile,-4.154327,orca\n",
        encoding="utf-8",
    )
    table = load_cosmors_solvation_table(csv_path)
    assert table[("c1ccsc1", "acetonitrile")] == -4.154327
    assert load_cosmors_solvation_table(tmp_path / "absent.csv") == {}


def test_screen_reads_cosmors_table_first_then_alpb(tmp_path: Path) -> None:
    """compute_monomer_solvent_table uses the cosmors ΔGsolv where present, ALPB fallback otherwise."""
    from eps.chemspace.models import Monomer, Solvent
    from eps.engines.mock import MockEngine
    from eps.storage.cache import SQLiteCache
    from eps.workflow.tier1 import compute_monomer_solvent_table

    monomer = Monomer(name="thiophene", monomer_class="x", smiles="c1ccsc1", canonical_smiles="c1ccsc1")
    solv = Solvent(
        name="acetonitrile", smiles="CC#N", canonical_smiles="CC#N", eps_r=37.5,
        esw_anodic_V=3.3, esw_cathodic_V=-2.7, xtb_gbsa_name="acetonitrile",
    )
    table = {("c1ccsc1", "acetonitrile"): -5.55}
    df = compute_monomer_solvent_table(
        [monomer], [solv], MockEngine(), SQLiteCache(tmp_path / "c.sqlite"), solvation_table=table
    )
    row = df.iloc[0]
    assert row["solvation_dG_kcal_mol"] == -5.55
    assert row["solvation_dG_source"] == "opencosmors_csv"

    df_fallback = compute_monomer_solvent_table(
        [monomer], [solv], MockEngine(), SQLiteCache(tmp_path / "c2.sqlite"), solvation_table={}
    )
    assert df_fallback.iloc[0]["solvation_dG_source"] == "alpb_fallback"

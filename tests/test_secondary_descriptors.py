from __future__ import annotations

from pathlib import Path

import yaml

from eps.chemspace import load_electrolytes, load_monomers, load_solvents
from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.engines.base import SpeciesSpec
from eps.properties.secondary_descriptors import (
    anion_vdw_volume_descriptors,
    cation_reduction_descriptors,
    ionpair_descriptors,
    monomer_secondary_descriptors,
    solvent_secondary_descriptors,
)
from eps.storage import SQLiteCache
from eps.workflow.tier1 import run_tier1


class CountingEngine(Engine):
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.delegate.run(req)


def _mock(smiles: str, quantity: str, charge: int = 0, mult: int = 1, eps: float | None = None):
    return MockEngine().run(CalcRequest(SpeciesSpec(smiles, charge, mult), "mock-gfn2", eps, quantity))


def test_mock_new_quantities_are_physically_ordered() -> None:
    smi = "c1ccsc1"
    # vertical IP/EA must sit above the adiabatic value (reorganization energy >= 0).
    assert _mock(smi, "vertical_ip").value > _mock(smi, "adiabatic_ip").value
    assert _mock(smi, "vertical_ea").value > _mock(smi, "adiabatic_ea").value
    # LUMO is always above HOMO (positive fundamental gap).
    assert _mock(smi, "lumo").value > _mock(smi, "homo").value


def test_mock_spin_density_array_sums_to_one_and_matches_atom_count() -> None:
    from rdkit import Chem

    result = _mock("c1ccsc1", "spin_density", charge=1, mult=2)
    spins = result.raw["atomic_spin_density"]
    assert len(spins) == Chem.MolFromSmiles("c1ccsc1").GetNumAtoms()
    assert abs(sum(spins) - 1.0) < 1e-9


def test_monomer_secondary_descriptors_thiophene(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    d = monomer_secondary_descriptors(monomer, MockEngine(), SQLiteCache(tmp_path / "c.sqlite"))
    assert d["secondary_monomer_calc_status"] == "ok"
    assert d["monomer_LUMO_eV"] > d["monomer_HOMO_eV"]
    assert d["monomer_HL_gap_eV"] > 0
    # lambda_ox = vertical IP - adiabatic IP, and must be >= 0 (reorganization energy).
    assert d["monomer_lambda_ox_eV"] >= 0
    assert 0.0 <= d["monomer_cation_max_spin"] <= 1.0
    assert isinstance(d["monomer_cation_max_spin_is_alpha"], bool)
    assert d["monomer_cation_alpha_spin_sum"] == d["monomer_cation_alpha_spin_sum"]  # not NaN


def test_solvent_secondary_descriptors_acetonitrile(tmp_path: Path) -> None:
    solvent = next(s for s in load_solvents() if s.name == "acetonitrile")
    d = solvent_secondary_descriptors(solvent, MockEngine(), SQLiteCache(tmp_path / "c.sqlite"))
    assert d["secondary_solvent_calc_status"] == "ok"
    # Reorganization energies are vertical - adiabatic, both >= 0 in the mock.
    assert d["solvent_lambda_ox_eV"] >= 0
    assert d["solvent_lambda_red_eV"] >= 0


def test_electrolyte_secondary_descriptors(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()
    tbapf6 = next(e for e in load_electrolytes() if e.salt == "TBAPF6")
    acetonitrile = next(s for s in load_solvents() if s.name == "acetonitrile")

    vol = anion_vdw_volume_descriptors(tbapf6)
    assert vol["anion_volume_calc_status"] == "ok"
    assert vol["anion_vdw_volume_A3"] > 0  # PF6 uses the flagged Bondi fallback

    cat = cation_reduction_descriptors(tbapf6, acetonitrile, engine, cache)
    assert cat["cation_reduction_calc_status"] == "ok"
    assert cat["cation_reduction_raw_V_vs_AgAgCl"] == cat["cation_reduction_raw_V_vs_AgAgCl"]

    pair = ionpair_descriptors(tbapf6, engine, cache)
    assert pair["ionpair_calc_status"] == "ok"
    assert pair["ionpair_method"] == "alpb_contact_pair_approx"
    assert pair["ionpair_dissociation_dG_kcal"] == pair["ionpair_dissociation_dG_kcal"]


def test_secondary_descriptors_cache_reuse(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = CountingEngine()
    monomer_secondary_descriptors(monomer, engine, cache)
    assert engine.calls > 0
    second = CountingEngine()
    monomer_secondary_descriptors(monomer, second, cache)
    assert second.calls == 0  # all secondary-descriptor engine calls served from cache


def _run(enabled: bool, tmp_path: Path):
    cfg = yaml.safe_load(Path("configs/tier1.yaml").read_text())
    cfg["secondary_descriptors"] = {"enabled": enabled}
    cfg_path = tmp_path / f"tier1_{enabled}.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    return run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / f"c_{enabled}.sqlite",
        output_path=tmp_path / f"r_{enabled}.csv",
        tier1_config_path=cfg_path,
    )


def test_secondary_descriptors_are_strictly_additive(tmp_path: Path) -> None:
    on = _run(True, tmp_path)
    off = _run(False, tmp_path)

    # Same triad counts and survivor counts: secondary descriptors never gate survival.
    assert on.total_triads == off.total_triads
    assert on.surviving_triads == off.surviving_triads

    key = ["monomer_name", "solvent_name", "salt"]
    a = on.ranked.set_index(key)["composite_score"].sort_index()
    b = off.ranked.set_index(key)["composite_score"].sort_index()
    assert a.index.equals(b.index)
    assert float((a - b).abs().max()) == 0.0  # identical composite scores

    # The new §3 columns are present only when enabled.
    for column in (
        "monomer_HOMO_eV",
        "monomer_lambda_ox_eV",
        "monomer_cation_max_spin_is_alpha",
        "solvent_lambda_ox_eV",
        "solvent_lambda_red_eV",
        "anion_vdw_volume_A3",
        "cation_reduction_raw_V_vs_AgAgCl",
        "cation_reduction_below_solvent_cathodic",
        "ionpair_dissociation_dG_kcal",
    ):
        assert column in on.all_triads.columns
        assert column not in off.all_triads.columns


def test_secondary_descriptors_artifact_written(tmp_path: Path) -> None:
    result = _run(True, tmp_path)
    artifact = result.output_path.parent / "secondary_descriptors.csv"
    assert artifact.exists()
    import pandas as pd

    frame = pd.read_csv(artifact)
    assert {"monomer_name", "monomer_HOMO_eV", "monomer_cation_max_spin_is_alpha"}.issubset(
        frame.columns
    )
    assert len(frame) == len(load_monomers())

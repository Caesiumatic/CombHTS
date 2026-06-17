from __future__ import annotations

import math
import shutil
from pathlib import Path

import pytest

from eps.chemspace import load_electrolytes, load_solvents
from eps.engines import CalcRequest, CalcResult, Engine, MockEngine, SpeciesSpec
from eps.engines import XTBEngine
from eps.properties import (
    ip_eV_to_potential_vs_AgAgCl,
    solvent_anodic_limit,
    solvent_cathodic_limit,
)
from eps.storage import SQLiteCache
from eps.workflow.tier1 import compute_anion_solvent_table, compute_solvent_table

CALIBRATION = {"enabled": True, "slope": 0.725837, "intercept": -3.145372}


def _solvent(name: str):
    for solvent in load_solvents():
        if solvent.name == name:
            return solvent
    raise AssertionError(f"solvent {name!r} not found in library")


class CountingEngine(Engine):
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.delegate.run(req)


class FailingSolventEngine(Engine):
    def __init__(self, failing_smiles: str) -> None:
        self.failing_smiles = failing_smiles
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        if (
            req.quantity == "adiabatic_ip"
            and req.species.charge == 0
            and req.species.canonical_smiles == self.failing_smiles
        ):
            raise RuntimeError("synthetic solvent anodic failure")
        return self.delegate.run(req)


def _engine_value(solvent, quantity: str) -> float:
    req = CalcRequest(
        species=SpeciesSpec(solvent.canonical_smiles, charge=0, multiplicity=1),
        method="mock-gfn2",
        solvent_eps_r=solvent.eps_r,
        quantity=quantity,
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    return MockEngine().run(req).value


@pytest.mark.parametrize("name", ["acetonitrile", "water"])
def test_solvent_anodic_limit_projects_adiabatic_ip(tmp_path: Path, name: str) -> None:
    solvent = _solvent(name)
    cache = SQLiteCache(tmp_path / "cache.sqlite")

    value = solvent_anodic_limit(solvent, MockEngine(), cache)

    assert value == pytest.approx(ip_eV_to_potential_vs_AgAgCl(_engine_value(solvent, "adiabatic_ip")))


@pytest.mark.parametrize("name", ["acetonitrile", "water"])
def test_solvent_cathodic_limit_projects_adiabatic_ea(tmp_path: Path, name: str) -> None:
    solvent = _solvent(name)
    cache = SQLiteCache(tmp_path / "cache.sqlite")

    value = solvent_cathodic_limit(solvent, MockEngine(), cache)

    assert value == pytest.approx(ip_eV_to_potential_vs_AgAgCl(_engine_value(solvent, "adiabatic_ea")))


def test_solvent_anodic_limit_is_cached(tmp_path: Path) -> None:
    solvent = _solvent("acetonitrile")
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    engine = CountingEngine()

    first = solvent_anodic_limit(solvent, engine, cache)
    calls_after_first = engine.calls
    second = solvent_anodic_limit(solvent, engine, cache)

    assert calls_after_first > 0
    assert engine.calls == calls_after_first  # no further engine calls on the cached run
    assert first == pytest.approx(second)


def test_compute_solvent_table_marks_computed_under_mock(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    table = compute_solvent_table(load_solvents(), MockEngine(), cache)

    assert (table["solvent_anodic_limit_source"] == "computed").all()
    assert (table["solvent_cathodic_limit_source"] == "computed").all()
    assert (table["solvent_anodic_limit_V"] == table["solvent_anodic_limit_computed_V"]).all()


def test_compute_solvent_table_falls_back_to_csv_on_failure(tmp_path: Path) -> None:
    solvent = _solvent("acetonitrile")
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    engine = FailingSolventEngine(solvent.canonical_smiles)

    table = compute_solvent_table(load_solvents(), engine, cache)
    row = table[table["solvent_name"] == "acetonitrile"].iloc[0]

    assert row["solvent_anodic_limit_source"] == "csv_fallback"
    assert row["solvent_anodic_limit_calc_status"] == "failed"
    assert math.isnan(row["solvent_anodic_limit_computed_V"])
    assert row["solvent_anodic_limit_V"] == pytest.approx(solvent.esw_anodic_V)


def test_compute_solvent_table_calibrates_anodic_limit(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    table = compute_solvent_table(
        load_solvents(), MockEngine(), cache, calibration_config={"monomer_eox": CALIBRATION}
    )

    expected = CALIBRATION["slope"] * table["solvent_anodic_limit_computed_V"] + CALIBRATION["intercept"]
    assert table["solvent_anodic_limit_calibrated_V"].to_numpy() == pytest.approx(expected.to_numpy())
    # Downstream value is the calibrated column, not the raw computed column.
    assert table["solvent_anodic_limit_V"].to_numpy() == pytest.approx(
        table["solvent_anodic_limit_calibrated_V"].to_numpy()
    )
    assert not (table["solvent_anodic_limit_V"] == table["solvent_anodic_limit_computed_V"]).all()
    # Cathodic limit stays raw / uncalibrated.
    assert (table["solvent_cathodic_limit_V"] == table["solvent_cathodic_limit_computed_V"]).all()


def test_compute_solvent_table_uses_raw_when_calibration_absent(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    table = compute_solvent_table(load_solvents(), MockEngine(), cache)

    assert (table["solvent_anodic_limit_V"] == table["solvent_anodic_limit_computed_V"]).all()


def test_compute_anion_solvent_table_calibrates_anion_eox(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "cache.sqlite")
    table = compute_anion_solvent_table(
        load_electrolytes(),
        load_solvents(),
        MockEngine(),
        cache,
        calibration_config={"monomer_eox": CALIBRATION},
    )

    expected = CALIBRATION["slope"] * table["anion_Eox_raw_V_vs_AgAgCl"] + CALIBRATION["intercept"]
    assert table["anion_Eox_filter_V_vs_AgAgCl"].to_numpy() == pytest.approx(expected.to_numpy())
    assert table["anion_Eox_V"].to_numpy() == pytest.approx(
        table["anion_Eox_filter_V_vs_AgAgCl"].to_numpy()
    )


@pytest.mark.skipif(shutil.which("xtb") is None, reason="xtb not installed")
def test_solvent_anodic_limit_live_xtb_smoke(tmp_path: Path) -> None:
    solvent = _solvent("acetonitrile")
    cache = SQLiteCache(tmp_path / "cache.sqlite")

    value = solvent_anodic_limit(solvent, XTBEngine(), cache, method="gfn2-xtb")

    assert isinstance(value, float)
    assert math.isfinite(value)

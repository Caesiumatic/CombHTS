from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from eps.engines import CalcRequest, SpeciesSpec, XTBEngine
from eps.engines.xtb import parse_homo_lumo, parse_total_energy, solvent_flag


FIXTURES = Path(__file__).parent / "fixtures"


def test_solvent_flag_prefers_gbsa_keyword() -> None:
    assert solvent_flag("acetonitrile", 37.5) == ["--gbsa", "acetonitrile"]


def test_solvent_flag_uses_alpb_dielectric_when_keyword_missing() -> None:
    assert solvent_flag(None, 64.9) == ["--alpb", "64.9"]


def test_solvent_flag_uses_gas_phase_when_no_solvent() -> None:
    assert solvent_flag(None, None) == []


def test_parse_total_energy_from_xtb_fixture() -> None:
    text = (FIXTURES / "xtb_energy.txt").read_text(encoding="utf-8")

    assert parse_total_energy(text) == pytest.approx(-36.721234567890)


def test_parse_homo_lumo_from_xtb_fixture() -> None:
    text = (FIXTURES / "xtb_opt.txt").read_text(encoding="utf-8")

    assert parse_homo_lumo(text) == pytest.approx(1.9876)


@pytest.mark.skipif(shutil.which("xtb") is None, reason="xtb not installed")
def test_xtb_engine_live_gas_energy_smoke() -> None:
    engine = XTBEngine()
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method="gfn2-xtb",
        solvent_eps_r=None,
        quantity="gas_energy",
    )

    result = engine.run(req)

    assert result.unit == "eV"
    assert result.value < 0

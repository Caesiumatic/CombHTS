from __future__ import annotations

import shutil
import types
from pathlib import Path

import pytest

from eps.engines import CalcRequest, SpeciesSpec, XTBEngine
from eps.engines import xtb as xtb_module
from eps.engines.xtb import parse_homo_lumo, parse_total_energy, parse_xtb_json, solvent_flag

FIXTURES = Path(__file__).parent / "fixtures"


def test_solvent_flag_uses_alpb_keyword() -> None:
    assert solvent_flag("acetonitrile") == ["--alpb", "acetonitrile"]


def test_solvent_flag_uses_gas_phase_when_keyword_missing() -> None:
    assert solvent_flag(None) == []


def test_parse_total_energy_from_xtb_fixture() -> None:
    text = (FIXTURES / "xtb_opt.txt").read_text(encoding="utf-8")

    assert parse_total_energy(text) == pytest.approx(-77.123456789012)


def test_parse_homo_lumo_from_xtb_fixture() -> None:
    text = (FIXTURES / "xtb_opt.txt").read_text(encoding="utf-8")

    assert parse_homo_lumo(text) == pytest.approx(1.9876)


def test_parse_xtb_json_fixture() -> None:
    text = (FIXTURES / "xtbout.json").read_text(encoding="utf-8")

    parsed = parse_xtb_json(text)

    assert parsed["total_energy_Eh"] == pytest.approx(-36.789012345678)
    assert parsed["homo_lumo_gap_eV"] == pytest.approx(2.4567)


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


def test_run_xtb_nonzero_exit_raises_before_json_parse(monkeypatch, tmp_path) -> None:
    """A nonzero xTB exit must raise the xTB RuntimeError, not a JSON parse error,
    even when a present-but-garbage xtbout.json is on disk."""

    def fake_run(command, cwd, check, capture_output, text):
        # xTB "ran" but failed; it still left a corrupt xtbout.json behind.
        (Path(cwd) / "xtbout.json").write_text("{ this is not valid json", encoding="utf-8")
        return types.SimpleNamespace(
            returncode=1,
            stdout="normal termination not reached",
            stderr="#ERROR! SCF not converged",
        )

    monkeypatch.setattr(xtb_module.subprocess, "run", fake_run)

    engine = XTBEngine()
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method="gfn2-xtb",
        solvent_eps_r=None,
        quantity="gas_energy",
    )

    with pytest.raises(RuntimeError, match="xTB failed with exit code 1"):
        engine._run_xtb(req, charge=0, multiplicity=1, solvent_args=[], optimize=True)

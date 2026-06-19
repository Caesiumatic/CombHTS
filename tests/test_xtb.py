from __future__ import annotations

import shutil
import types
from pathlib import Path

import pytest

from eps.engines import CalcRequest, SpeciesSpec, XTBEngine
from eps.engines import xtb as xtb_module
from eps.engines.xtb import (
    parse_atomic_spin_populations,
    parse_frontier_orbital_eV,
    parse_homo_lumo,
    parse_stda_lowest_excitation,
    parse_total_energy,
    parse_xtb_json,
    solvent_flag,
)

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
    # Real xtb 6.4.1 `--json` dump captured on the Lop cluster (thiophene radical cation,
    # --gfn 2 --chrg 1 --uhf 1 single point) — STATUS debt #7 real-dump upgrade.
    text = (FIXTURES / "xtbout.json").read_text(encoding="utf-8")

    parsed = parse_xtb_json(text)

    assert parsed["total_energy_Eh"] == pytest.approx(-13.30795443)
    assert parsed["homo_lumo_gap_eV"] == pytest.approx(4.10812582)


# --- WS1 secondary-descriptor parsers, validated against REAL captured xtb 6.4.1 output ---
# Fixture: thiophene radical cation (c1ccsc1, charge +1, doublet), single point with the exact
# production WS1 invocation `xtb input.xyz --gfn 2 --chrg 1 --uhf 1 --iterations 500 --etemp 400.0
# --json`, captured on the Lop cluster (compute-1-4.local). Replaces the never-validated synthetic
# expectations these parsers shipped with.

def test_parse_frontier_orbital_eV_homo_from_real_stdout() -> None:
    text = (FIXTURES / "xtb_radical_cation_stdout.txt").read_text(encoding="utf-8")
    # Real tagged line: "13   1.4538   -0.6280103   -17.0890 (HOMO)" — eV is the last numeric field.
    assert parse_frontier_orbital_eV(text, "homo") == pytest.approx(-17.0890)


def test_parse_frontier_orbital_eV_lumo_from_real_stdout() -> None:
    text = (FIXTURES / "xtb_radical_cation_stdout.txt").read_text(encoding="utf-8")
    # Real tagged line: "14   -0.4770395   -12.9809 (LUMO)".
    assert parse_frontier_orbital_eV(text, "lumo") == pytest.approx(-12.9809)


def test_parse_frontier_orbital_eV_raises_when_tag_absent() -> None:
    with pytest.raises(ValueError, match="HOMO orbital energy"):
        parse_frontier_orbital_eV("no orbital block here\n", "homo")


def test_parse_atomic_spin_populations_empty_on_real_open_shell_stdout() -> None:
    """Regression documenting a VERIFIED xtb 6.4.1 limitation: at the production verbosity,
    an open-shell single point prints NO per-atom spin-population block (only the scalar setup
    line ``spin : 0.5``). The parser must degrade to ``[]`` (=> _spin_density NaN, descriptor
    marked failed), NOT raise or return garbage. See STATUS open debt on always-NaN spin_density.
    """

    text = (FIXTURES / "xtb_radical_cation_stdout.txt").read_text(encoding="utf-8")
    assert parse_atomic_spin_populations(text) == []


def test_parse_atomic_spin_populations_reads_block_when_present() -> None:
    """When a higher-verbosity run DOES print a spin-population block, the parser collects the
    trailing numeric column per atom row. Guards the regex/heuristic against silent regressions
    (this synthetic block is clearly labeled; real 6.4.1 production output omits it — see above).
    """

    block = (
        "Mulliken spin populations\n"
        "  #   Z   atom      spin\n"
        "  1   6   C       0.512\n"
        "  2  16   S       0.301\n"
        "  3   1   H       0.187\n"
        "\n"
    )
    spins = parse_atomic_spin_populations(block)
    assert spins == [pytest.approx(0.512), pytest.approx(0.301), pytest.approx(0.187)]
    assert sum(spins) == pytest.approx(1.0, abs=1e-9)


def test_parse_stda_lowest_excitation_returns_first_state() -> None:
    text = (FIXTURES / "stda_output.txt").read_text(encoding="utf-8")
    assert parse_stda_lowest_excitation(text) == pytest.approx(2.2340)


def test_parse_stda_lowest_excitation_raises_without_states() -> None:
    with pytest.raises(ValueError, match="sTDA excitation"):
        parse_stda_lowest_excitation("no excited states here\n")


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

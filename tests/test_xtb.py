from __future__ import annotations

import hashlib
import shutil
import types
from pathlib import Path

import pytest

from eps.engines import CalcRequest, SpeciesSpec, XTBEngine
from eps.engines import xtb as xtb_module
from eps.engines.xtb import (
    parse_atomic_spin_populations,
    parse_frontier_orbital_eV,
    parse_ipea_value,
    parse_homo_lumo,
    parse_stda_lowest_excitation,
    parse_total_energy,
    parse_xtb_json,
    solvent_flag,
)

FIXTURES = Path(__file__).parent / "fixtures"
FALLBACK_GAP_EV = 4.321
OPTIMIZED_XYZ = "3\noptimized geometry\nC 0.0 0.0 0.0\nH 0.0 0.0 1.0\nH 1.0 0.0 0.0\n"


def _optical_gap_request() -> CalcRequest:
    return CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method="gfn2-xtb",
        solvent_eps_r=None,
        quantity="optical_gap",
    )


def _xtb_json(gap_eV: float = FALLBACK_GAP_EV) -> str:
    return f'{{"total energy": -1.0, "HOMO-LUMO gap/eV": {gap_eV}}}'


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0) -> types.SimpleNamespace:
    return types.SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


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


def test_parse_ipea_value_reads_delta_scc_ip_and_ea() -> None:
    """IPEA-xTB (`xtb --vipea`) prints the final `delta SCC IP/EA (eV)` (empirical shift already
    applied); the parser must read those, not the `empirical IP shift` line. Real thiophene values."""

    stdout = (
        "          |        vertical delta SCC IP calculation        |\n"
        "empirical IP shift (eV):    4.8455\n"
        "delta SCC IP (eV):    9.0296\n"
        "          |        vertical delta SCC EA calculation        |\n"
        "empirical EA shift (eV):    4.8455\n"
        "delta SCC EA (eV):   -1.4056\n"
    )
    assert parse_ipea_value(stdout, "IP") == pytest.approx(9.0296)
    assert parse_ipea_value(stdout, "EA") == pytest.approx(-1.4056)


def test_parse_ipea_value_raises_when_absent() -> None:
    with pytest.raises(ValueError):
        parse_ipea_value("no ipea block here", "IP")


def test_parse_atomic_spin_populations_empty_without_xcontrol_block() -> None:
    """Without the xcontrol ``$write/spin population=true`` request, xtb 6.4.1 prints NO per-atom
    spin block (only the scalar setup line ``spin : 0.5``); the parser must degrade to ``[]`` (=>
    _spin_density NaN), NOT raise or return garbage. ``XTBEngine._spin_density`` now always passes
    that xcontrol file (see the (R)spin-density test below), but the no-block degrade path must stay
    robust for any run made without it.
    """

    text = (FIXTURES / "xtb_radical_cation_stdout.txt").read_text(encoding="utf-8")
    assert parse_atomic_spin_populations(text) == []


def test_parse_atomic_spin_populations_reads_real_R_spin_density_block() -> None:
    """The real xtb 6.4.1 block (emitted with the xcontrol ``$write/spin population=true`` file):
    atom rows start with a fused index+element token (``1C``, ``4S``) and the FIRST float per row is
    that atom's total spin population. The parser must take numbers[0], not the trailing column.
    """

    block = (
        " (R)spin-density population\n"
        "\n"
        " Mulliken population  n(s)   n(p)   n(d)\n"
        "     1C     0.1704   0.000  0.170  0.000\n"
        "     4S     0.3261   0.000  0.319  0.007\n"
        "     6H     0.0000   0.000  0.000  0.000\n"
        "\n"
        " #   Z          covCN\n"
    )
    spins = parse_atomic_spin_populations(block)
    assert spins == [pytest.approx(0.1704), pytest.approx(0.3261), pytest.approx(0.0)]


def test_parse_atomic_spin_populations_reads_single_column_block() -> None:
    """A simpler labeled block with one trailing spin float per row also parses (numbers[0] is the
    only float). Guards the heuristic against silent regressions.
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


def test_optical_gap_stda_uses_optimized_xyz_and_records_success(monkeypatch) -> None:
    captured_stda_prep_inputs: list[str] = []

    def fake_run(command, cwd, check, capture_output, text):
        cwd_path = Path(cwd)
        if command[0] == "xtb" and "--opt" in command:
            (cwd_path / "xtbout.json").write_text(_xtb_json(), encoding="utf-8")
            (cwd_path / "xtbopt.xyz").write_text(OPTIMIZED_XYZ, encoding="utf-8")
            return _completed(stdout=f"HOMO-LUMO GAP {FALLBACK_GAP_EV} eV")
        if command[0] == "xtb4stda":
            captured_stda_prep_inputs.append((cwd_path / "input.xyz").read_text(encoding="utf-8"))
            (cwd_path / "wfn.xtb").write_text("wfn", encoding="utf-8")
            return _completed(stdout="sTDA preparation complete")
        if command[0] == "stda":
            return _completed(stdout=" state   eV    nm\n 1   2.345   528.7\n")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(xtb_module.shutil, "which", lambda binary: f"/fake/bin/{binary}")
    monkeypatch.setattr(xtb_module.subprocess, "run", fake_run)

    result = XTBEngine().run(_optical_gap_request())

    assert result.value == pytest.approx(2.345)
    assert captured_stda_prep_inputs == [OPTIMIZED_XYZ]
    assert result.raw["optical_gap_method"] == "stda-xtb"
    assert result.raw["optical_gap_geometry_source"] == "xtbopt.xyz"
    assert result.raw["optimized_geometry_available"] is True
    assert result.raw["optimized_geometry_sha256"] == hashlib.sha256(
        OPTIMIZED_XYZ.encode("utf-8")
    ).hexdigest()
    assert result.raw["stda_available"] is True
    assert result.raw["stda_attempted"] is True
    assert result.raw["stda_status"] == "success"
    assert result.raw["fallback_used"] is False
    assert result.raw["stda_failure_type"] == ""
    assert result.raw["stda_failure_message"] == ""
    assert "optimized_xyz" not in result.raw


def test_optical_gap_stda_preparation_failure_falls_back_with_provenance(monkeypatch) -> None:
    stda_called = False

    def fake_run(command, cwd, check, capture_output, text):
        nonlocal stda_called
        cwd_path = Path(cwd)
        if command[0] == "xtb" and "--opt" in command:
            (cwd_path / "xtbout.json").write_text(_xtb_json(), encoding="utf-8")
            (cwd_path / "xtbopt.xyz").write_text(OPTIMIZED_XYZ, encoding="utf-8")
            return _completed(stdout=f"HOMO-LUMO GAP {FALLBACK_GAP_EV} eV")
        if command[0] == "xtb4stda":
            assert (cwd_path / "input.xyz").read_text(encoding="utf-8") == OPTIMIZED_XYZ
            return _completed(
                stderr="prep failed at wavefunction write\nextra diagnostics",
                returncode=17,
            )
        if command[0] == "stda":
            stda_called = True
            return _completed()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(xtb_module.shutil, "which", lambda binary: f"/fake/bin/{binary}")
    monkeypatch.setattr(xtb_module.subprocess, "run", fake_run)

    result = XTBEngine().run(_optical_gap_request())

    assert result.value == pytest.approx(FALLBACK_GAP_EV)
    assert stda_called is False
    assert result.raw["optical_gap_method"] == "homo_lumo_hexamer_fallback"
    assert result.raw["optimized_geometry_available"] is True
    assert result.raw["stda_available"] is True
    assert result.raw["stda_attempted"] is True
    assert result.raw["stda_status"] == "stda_preparation_failed"
    assert result.raw["fallback_used"] is True
    assert result.raw["stda_failure_type"] == "STDAStageError"
    assert result.raw["stda_failure_message"] == (
        "xtb4stda (for sTDA) failed: exit 17. STDERR: prep failed at wavefunction write"
    )


def test_optical_gap_missing_stda_records_not_available_fallback(monkeypatch) -> None:
    def fake_run(command, cwd, check, capture_output, text):
        cwd_path = Path(cwd)
        if command[0] == "xtb" and "--opt" in command:
            (cwd_path / "xtbout.json").write_text(_xtb_json(), encoding="utf-8")
            (cwd_path / "xtbopt.xyz").write_text(OPTIMIZED_XYZ, encoding="utf-8")
            return _completed(stdout=f"HOMO-LUMO GAP {FALLBACK_GAP_EV} eV")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(
        xtb_module.shutil,
        "which",
        lambda binary: f"/fake/bin/{binary}" if binary == "xtb" else None,
    )
    monkeypatch.setattr(xtb_module.subprocess, "run", fake_run)

    result = XTBEngine().run(_optical_gap_request())

    assert result.value == pytest.approx(FALLBACK_GAP_EV)
    assert result.raw["optical_gap_method"] == "homo_lumo_hexamer_fallback"
    assert result.raw["optimized_geometry_available"] is True
    assert result.raw["stda_available"] is False
    assert result.raw["stda_attempted"] is False
    assert result.raw["stda_status"] == "not_available"
    assert result.raw["fallback_used"] is True
    assert result.raw["stda_failure_type"] == "STDAUnavailableError"
    assert result.raw["stda_failure_message"] == "sTDA binary 'stda' was not found on PATH"


def test_optical_gap_missing_optimized_geometry_records_fallback_reason(monkeypatch) -> None:
    def fake_run(command, cwd, check, capture_output, text):
        if command[0] == "xtb" and "--opt" in command:
            (Path(cwd) / "xtbout.json").write_text(_xtb_json(), encoding="utf-8")
            return _completed(stdout=f"HOMO-LUMO GAP {FALLBACK_GAP_EV} eV")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(xtb_module.shutil, "which", lambda binary: f"/fake/bin/{binary}")
    monkeypatch.setattr(xtb_module.subprocess, "run", fake_run)

    result = XTBEngine().run(_optical_gap_request())

    assert result.value == pytest.approx(FALLBACK_GAP_EV)
    assert result.raw["optical_gap_method"] == "homo_lumo_hexamer_fallback"
    assert result.raw["optical_gap_geometry_source"] == ""
    assert result.raw["optimized_geometry_available"] is False
    assert result.raw["optimized_geometry_sha256"] == ""
    assert result.raw["stda_available"] is True
    assert result.raw["stda_attempted"] is False
    assert result.raw["stda_status"] == "missing_optimized_geometry"
    assert result.raw["fallback_used"] is True
    assert result.raw["stda_failure_type"] == "OptimizedGeometryMissingError"
    assert result.raw["stda_failure_message"] == "optimized geometry was not captured from xtbopt.xyz"


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

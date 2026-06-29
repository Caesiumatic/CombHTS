"""Unit tests for the ORCA Tier-2 ΔSCF redox path (directive §4.2), with a stubbed ORCA binary.

Real ORCA runs on Lop; here we test the input builder, the energy/Gibbs/Hirshfeld parsers, and the
adiabatic IP/EA sign + ΔE-vs-ΔG selection against synthetic ORCA-format output.
"""
from __future__ import annotations

from eps.engines import orca
from eps.engines.base import CalcRequest, SpeciesSpec
from eps.engines.orca import (
    HARTREE_TO_EV,
    OrcaConfig,
    OrcaEngine,
    build_orca_redox_input,
    parse_orca_final_scf_energy_eh,
    parse_orca_gibbs_energy_eh,
    parse_orca_hirshfeld_spin_populations,
    parse_orca_homo_lumo_eV,
)

_THIOPHENE = SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1)


def test_build_redox_input_gas_phase_minimal() -> None:
    text = build_orca_redox_input(_THIOPHENE, 0, 1)
    assert text.startswith("! B3LYP 6-31G(d,p) Opt TightSCF\n")
    assert "* xyz 0 1" in text
    assert "smd true" not in text  # no solvent -> gas phase
    assert "Freq" not in text
    assert "P_Hirshfeld" not in text


def test_build_redox_input_smd_freq_hirshfeld() -> None:
    text = build_orca_redox_input(
        _THIOPHENE, 1, 2, use_freq=True, hirshfeld=True, smd_solvent="acetonitrile"
    )
    assert "! B3LYP 6-31G(d,p) Opt TightSCF Freq\n" in text
    assert 'SMDsolvent "acetonitrile"' in text
    assert "smd true" in text
    assert "Print[P_Hirshfeld] 1" in text
    assert "* xyz 1 2" in text


def test_parse_final_scf_energy_takes_last() -> None:
    out = (
        "FINAL SINGLE POINT ENERGY      -551.100000\n"
        "...geometry step...\n"
        "FINAL SINGLE POINT ENERGY      -551.234567\n"
    )
    assert parse_orca_final_scf_energy_eh(out) == -551.234567


def test_parse_gibbs_energy() -> None:
    out = "Final Gibbs free energy         ...   -551.111111 Eh\n"
    assert parse_orca_gibbs_energy_eh(out) == -551.111111


def test_parse_hirshfeld_spin_populations() -> None:
    out = (
        "HIRSHFELD ANALYSIS\n"
        "  ATOM     CHARGE      SPIN\n"
        "   0 C    0.012000    0.350000\n"
        "   1 C   -0.030000    0.120000\n"
        "   2 S    0.080000    0.530000\n"
    )
    spins = parse_orca_hirshfeld_spin_populations(out)
    assert spins == [0.350000, 0.120000, 0.530000]


def test_parse_homo_lumo() -> None:
    out = (
        "ORBITAL ENERGIES\n----------------\n"
        "  NO   OCC          E(Eh)            E(eV)\n"
        "   0   2.0000     -10.123456      -275.4789\n"
        "  19   2.0000      -0.250000        -6.8027\n"  # HOMO
        "  20   0.0000      -0.050000        -1.3605\n"  # LUMO
        "  21   0.0000       0.100000         2.7211\n"
    )
    homo, lumo = parse_orca_homo_lumo_eV(out)
    assert homo == -6.8027
    assert lumo == -1.3605


def test_homo_quantity_returns_homo_with_smd(monkeypatch) -> None:
    monkeypatch.setattr(orca.shutil, "which", lambda _name: "/fake/orca")
    captured = {}

    def fake_run(cmd, check=False, capture_output=False, text=False, cwd=None):  # noqa: ARG001
        from pathlib import Path

        captured["inp"] = Path(cmd[1]).read_text(encoding="utf-8")
        return type("R", (), {"returncode": 0, "stderr": "", "stdout": (
            "ORBITAL ENERGIES\n  NO OCC E(Eh) E(eV)\n"
            "  0 2.0000 -0.30 -8.0\n  1 0.0000 -0.05 -1.5\n"
            "ORCA TERMINATED NORMALLY\n"
        )})()

    monkeypatch.setattr(orca.subprocess, "run", fake_run)
    engine = OrcaEngine(OrcaConfig(redox_smd=True))
    req = CalcRequest(species=_THIOPHENE, method="m", solvent_eps_r=37.5,
                      solvent_model_name="acetonitrile", quantity="homo")
    result = engine.run(req)
    assert result.value == -8.0
    assert result.raw["lumo_eV"] == -1.5
    assert "Opt" not in captured["inp"]  # single point, no optimization
    assert 'SMDsolvent "acetonitrile"' in captured["inp"]


def _normal(stdout: str):
    class _R:
        returncode = 0

        def __init__(self) -> None:
            self.stdout = stdout
            self.stderr = ""

    return _R()


def _redox_engine_with_stub(monkeypatch, *, use_freq: bool):
    """Stub ORCA: read the written .inp, return an energy keyed on the molecular charge."""

    monkeypatch.setattr(orca.shutil, "which", lambda _name: "/fake/orca")

    def fake_run(cmd, check=False, capture_output=False, text=False, cwd=None):  # noqa: ARG001
        from pathlib import Path

        inp = Path(cmd[1]).read_text(encoding="utf-8")
        charge = int(inp.split("* xyz", 1)[1].split()[0])
        scf = {0: -100.000000, 1: -99.700000, -1: -100.050000}[charge]
        gibbs = scf + 0.010000  # arbitrary thermal shift, identical structure for all states
        body = f"FINAL SINGLE POINT ENERGY      {scf:.6f}\n"
        if use_freq:
            body += f"Final Gibbs free energy         ...   {gibbs:.6f} Eh\n"
        if "P_Hirshfeld" in inp:
            body += (
                "HIRSHFELD ANALYSIS\n   0 C   0.01   0.40\n   1 S   0.05   0.60\n"
            )
        body += "ORCA TERMINATED NORMALLY\n"
        return _normal(body)

    monkeypatch.setattr(orca.subprocess, "run", fake_run)
    return OrcaEngine(OrcaConfig(redox_use_freq=use_freq, redox_smd=True))


def test_adiabatic_ip_sign_and_value_deltaE(monkeypatch) -> None:
    engine = _redox_engine_with_stub(monkeypatch, use_freq=False)
    req = CalcRequest(
        species=_THIOPHENE, method="orca6.1/b3lyp/6-31g(d,p)/smd/freq:off",
        solvent_eps_r=37.5, solvent_model_name="acetonitrile", quantity="adiabatic_ip",
    )
    result = engine.run(req)
    # IP = (E_cation - E_neutral) = (-99.7 - (-100.0)) Eh = 0.3 Eh
    assert result.value == round(0.3 * HARTREE_TO_EV, 6) or abs(result.value - 0.3 * HARTREE_TO_EV) < 1e-6
    assert result.raw["final_parsed"]["hirshfeld_spin_populations"] == [0.40, 0.60]
    assert result.raw["smd_solvent"] == "acetonitrile"


def test_adiabatic_ea_sign(monkeypatch) -> None:
    engine = _redox_engine_with_stub(monkeypatch, use_freq=False)
    req = CalcRequest(
        species=_THIOPHENE, method="orca6.1/b3lyp/6-31g(d,p)/smd/freq:off",
        solvent_eps_r=37.5, solvent_model_name="acetonitrile", quantity="adiabatic_ea",
    )
    result = engine.run(req)
    # EA = (E_neutral - E_anion) = (-100.0 - (-100.05)) Eh = 0.05 Eh
    assert abs(result.value - 0.05 * HARTREE_TO_EV) < 1e-6


def test_redox_uses_gibbs_when_freq_on(monkeypatch) -> None:
    engine = _redox_engine_with_stub(monkeypatch, use_freq=True)
    req = CalcRequest(
        species=_THIOPHENE, method="orca6.1/b3lyp/6-31g(d,p)/smd/freq:on",
        solvent_eps_r=37.5, solvent_model_name="acetonitrile", quantity="adiabatic_ip",
    )
    result = engine.run(req)
    # Gibbs shift is identical for both states, so ΔG == ΔE here = 0.3 Eh, but basis must be gibbs.
    assert result.raw["final_parsed"]["energy_basis"] == "gibbs"
    assert abs(result.value - 0.3 * HARTREE_TO_EV) < 1e-6


def test_gas_energy_returns_optimized_energy_with_smd(monkeypatch) -> None:
    monkeypatch.setattr(orca.shutil, "which", lambda _name: "/fake/orca")
    captured = {}

    def fake_run(cmd, check=False, capture_output=False, text=False, cwd=None):  # noqa: ARG001
        from pathlib import Path

        captured["inp"] = Path(cmd[1]).read_text(encoding="utf-8")
        return _normal(
            "FINAL SINGLE POINT ENERGY  -553.250000\n"
            "Final Gibbs free energy  ...  -553.100000 Eh\n"
            "ORCA TERMINATED NORMALLY\n"
        )

    monkeypatch.setattr(orca.subprocess, "run", fake_run)
    engine = OrcaEngine(OrcaConfig(redox_use_freq=True, redox_smd=True))
    req = CalcRequest(
        species=_THIOPHENE, method="m", solvent_eps_r=37.5,
        solvent_model_name="acetonitrile", quantity="gas_energy",
    )
    result = engine.run(req)
    # Freq on -> Gibbs (-553.1 Eh) selected, converted to eV; SMD block present.
    assert abs(result.value - (-553.100000 * HARTREE_TO_EV)) < 1e-6
    assert 'SMDsolvent "acetonitrile"' in captured["inp"]
    assert result.raw["energy_basis"] == "gibbs"


def test_redox_gas_phase_when_smd_disabled(monkeypatch) -> None:
    monkeypatch.setattr(orca.shutil, "which", lambda _name: "/fake/orca")
    captured = {}

    def fake_run(cmd, check=False, capture_output=False, text=False, cwd=None):  # noqa: ARG001
        from pathlib import Path

        captured["inp"] = Path(cmd[1]).read_text(encoding="utf-8")
        return _normal("FINAL SINGLE POINT ENERGY  -100.0\nORCA TERMINATED NORMALLY\n")

    monkeypatch.setattr(orca.subprocess, "run", fake_run)
    engine = OrcaEngine(OrcaConfig(redox_smd=False, redox_hirshfeld=False))
    req = CalcRequest(
        species=_THIOPHENE, method="m", solvent_eps_r=37.5,
        solvent_model_name="acetonitrile", quantity="adiabatic_ip",
    )
    engine.run(req)
    assert "smd true" not in captured["inp"]  # redox_smd=False -> ignore the request solvent

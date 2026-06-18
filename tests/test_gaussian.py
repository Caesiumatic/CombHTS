from __future__ import annotations

import shutil
import types
from pathlib import Path

import pytest

from eps.engines import CalcRequest, GaussianEngine, SpeciesSpec
from eps.engines import gaussian as gaussian_module
from eps.engines.gaussian import (
    GAUSSIAN_METHOD_LABEL,
    build_gaussian_input,
    parse_gaussian_log,
)
from eps.engines.xtb import HARTREE_TO_EV

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_gaussian_input_route_charge_multiplicity_and_smd() -> None:
    species = SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1)

    cation = build_gaussian_input(species, charge=1, multiplicity=2)
    lines = cation.splitlines()

    assert lines[0] == "#p B3LYP/6-31G(d,p) Opt SCF=Tight"
    assert "SCRF" not in cation
    # Route, blank, title, blank, then the charge/multiplicity line.
    assert lines[4] == "1 2"
    # Cartesian coordinates follow (element + 3 floats).
    atom_tokens = lines[5].split()
    assert len(atom_tokens) == 4
    assert cation.endswith("\n")

    solvated = build_gaussian_input(species, charge=0, multiplicity=1, solvent_smd="Acetonitrile")
    assert "SCRF=(SMD,Solvent=Acetonitrile)" in solvated.splitlines()[0]


def test_build_gaussian_input_can_disable_optimization() -> None:
    species = SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1)
    sp = build_gaussian_input(species, charge=0, multiplicity=1, optimize=False)
    assert "Opt" not in sp.splitlines()[0]
    assert "SCF=Tight" in sp.splitlines()[0]


def test_parse_gaussian_log_extracts_final_scf_and_gibbs() -> None:
    text = (FIXTURES / "gaussian_scf.log").read_text(encoding="utf-8")

    parsed = parse_gaussian_log(text)

    # The LAST SCF Done value is taken (final optimization step).
    assert parsed["scf_energy_Eh"] == pytest.approx(-250.123456789)
    assert parsed["scf_energy_eV"] == pytest.approx(-250.123456789 * HARTREE_TO_EV)
    assert parsed["gibbs_free_energy_Eh"] == pytest.approx(-250.052223)
    assert parsed["gibbs_free_energy_eV"] == pytest.approx(-250.052223 * HARTREE_TO_EV)


def test_parse_gaussian_log_gibbs_optional() -> None:
    text = " SCF Done:  E(RB3LYP) =  -100.5     A.U. after 8 cycles\n Normal termination\n"
    parsed = parse_gaussian_log(text)
    assert parsed["scf_energy_Eh"] == pytest.approx(-100.5)
    assert parsed["gibbs_free_energy_Eh"] is None
    assert parsed["gibbs_free_energy_eV"] is None


def test_parse_gaussian_log_raises_without_scf() -> None:
    with pytest.raises(ValueError, match="SCF Done"):
        parse_gaussian_log("no energy lines here\n")


def test_run_raises_when_binary_absent_never_fakes() -> None:
    engine = GaussianEngine(binary="definitely-not-g16-xyz")
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method=GAUSSIAN_METHOD_LABEL,
        solvent_eps_r=None,
        quantity="gas_energy",
    )
    with pytest.raises(RuntimeError, match="was not found on PATH"):
        engine.run(req)


def test_run_gaussian_nonzero_exit_raises_before_log_parse(monkeypatch) -> None:
    """A nonzero g16 exit must raise the Gaussian RuntimeError, not a parse error,
    even when a present-but-garbage input.log is on disk (Task-1a lesson)."""

    def fake_run(command, cwd, check, capture_output, text):
        (Path(cwd) / "input.log").write_text("garbage, no SCF here", encoding="utf-8")
        return types.SimpleNamespace(returncode=1, stdout="", stderr="Error termination")

    monkeypatch.setattr(gaussian_module.subprocess, "run", fake_run)

    engine = GaussianEngine()
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method=GAUSSIAN_METHOD_LABEL,
        solvent_eps_r=None,
        quantity="gas_energy",
    )
    with pytest.raises(RuntimeError, match="Gaussian failed with exit code 1"):
        engine._run_gaussian(req, charge=0, multiplicity=1, optimize=True, solvent_smd=None)


def test_tier2_dry_run_writes_inputs_without_running_g16(tmp_path, monkeypatch) -> None:
    import pandas as pd

    from eps.workflow.tier2 import write_tier2_dry_run_inputs

    # Guard: if anything tried to launch g16, this would raise.
    import eps.engines.gaussian as gaussian_mod

    def _boom(*args, **kwargs):
        raise AssertionError("tier2 dry-run must NOT execute any subprocess")

    monkeypatch.setattr(gaussian_mod.subprocess, "run", _boom)

    survivors = tmp_path / "survivors.csv"
    pd.DataFrame(
        {
            "monomer_name": ["thiophene", "thiophene", "EDOT"],  # duplicate monomer -> dedup
            "monomer_canonical_smiles": ["c1ccsc1", "c1ccsc1", "C1COc2ccsc2O1"],
            "solvent_name": ["acetonitrile", "DCM", "acetonitrile"],
        }
    ).to_csv(survivors, index=False)

    result = write_tier2_dry_run_inputs(survivors, tmp_path / "tier2_inputs")

    assert result.n_survivors == 3
    assert result.n_unique_monomers == 2  # deduplicated by canonical SMILES
    assert len(result.input_paths) == 4  # neutral + cation per unique monomer
    assert all(path.exists() and path.read_text().startswith("#p B3LYP") for path in result.input_paths)
    assert result.estimated_cpu_hours > 0
    # One cation input should carry charge/multiplicity "1 2".
    cation = next(p for p in result.input_paths if p.name.endswith("_cation.gjf"))
    assert "1 2" in cation.read_text()


@pytest.mark.skipif(shutil.which("g16") is None, reason="g16 not installed")
def test_gaussian_engine_live_gas_energy_smoke() -> None:
    engine = GaussianEngine()
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method=GAUSSIAN_METHOD_LABEL,
        solvent_eps_r=None,
        quantity="gas_energy",
    )
    result = engine.run(req)
    assert result.unit == "eV"
    assert result.value < 0

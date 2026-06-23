from __future__ import annotations

import math
import shutil
from pathlib import Path

import pytest

from eps.engines import CalcRequest, OrcaConfig, OrcaEngine, SpeciesSpec
from eps.engines.orca import (
    build_orca_cosmors_input,
    build_orca_optical_input,
    parse_orca_cosmors_dg_kcal_mol,
    parse_orca_lowest_excitation_eV,
)
from eps.storage import SQLiteCache
from eps.workflow.orca_pilots import (
    build_mock_orca_pilot_engines,
    load_solvation_grid_config,
    plan_solvation_grid,
    run_orca_optical_pilot,
    run_orca_solvation_grid_pilot,
    run_orca_solvation_pilot,
)


def test_orca_cosmors_input_uses_internal_solvent_and_explicit_state() -> None:
    species = SpeciesSpec("c1ccsc1", 0, 1)
    text = build_orca_cosmors_input(species, "Acetonitrile", nprocs=4, maxcore_mb=2000)
    assert "COSMORS(Acetonitrile)" in text
    assert "%pal nprocs 4 end" in text
    assert "* xyz 0 1" in text


def test_parse_orca_cosmors_dg_kcal_mol() -> None:
    output = "Free energy of solvation (dGsolv) : -0.006626234385 Eh   -4.158026 kcal/mol"
    assert parse_orca_cosmors_dg_kcal_mol(output) == pytest.approx(-4.158026)


@pytest.mark.parametrize("mode", ["stda", "tddft"])
def test_orca_optical_input_modes(mode: str) -> None:
    config = OrcaConfig(optical_mode=mode)
    text = build_orca_optical_input(SpeciesSpec("c1ccsc1", 0, 1), config)
    assert "CAM-B3LYP" in text
    if mode == "stda":
        assert "Mode sTDA" in text
    else:
        assert "TDA true" in text
        assert "NRoots 5" in text


def test_parse_orca_explicit_and_absorption_excitation_formats() -> None:
    explicit = "STATE  1:  E=   0.08000 au      2.17691 eV"
    assert parse_orca_lowest_excitation_eV(explicit) == pytest.approx(2.17691)
    absorption = "   0   16964.7    589.5   0.000083715   0.00162   0.02872  -0.02828  -0.00022"
    s_tda_output = f"""
       1       2.0       3.0       4.0       5.0       6.0       7.0       8.0
       ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS
       State   Energy  Wavelength   fosc         T2         TX        TY        TZ
       {absorption}
       ABSORPTION SPECTRUM VIA TRANSITION VELOCITY DIPOLE MOMENTS
    """
    assert parse_orca_lowest_excitation_eV(s_tda_output) == pytest.approx(
        16964.7 / 8065.544005
    )


def test_orca_pilots_are_mock_first_and_write_a_fit(tmp_path: Path) -> None:
    solv_engine, solv_method, stda_engine, stda_method, tddft_engine, tddft_method = (
        build_mock_orca_pilot_engines()
    )
    solvation = run_orca_solvation_pilot(
        engine=solv_engine,
        method=solv_method,
        cache_path=tmp_path / "solv.sqlite",
        outdir=tmp_path / "solv",
        engine_label="mock",
    )
    optical = run_orca_optical_pilot(
        stda_engine=stda_engine,
        tddft_engine=tddft_engine,
        stda_method=stda_method,
        tddft_method=tddft_method,
        cache_path=tmp_path / "opt.sqlite",
        outdir=tmp_path / "opt",
        engine_label="mock",
    )
    assert solvation.n_ok == 3
    assert solvation.n_failed == 0
    assert optical.n_paired == 3
    assert optical.n_failed == 0
    assert optical.calibration is not None
    assert math.isfinite(optical.calibration.r2)
    assert 0.0 <= optical.calibration.r2 <= 1.0
    assert optical.points_path.exists()
    assert optical.calibration_path.exists()


def test_orca_persistent_relative_work_root_passes_a_valid_input_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_orca = tmp_path / "fake-orca"
    fake_orca.write_text(
        "#!/bin/sh\n"
        "test -f \"$1\" || exit 2\n"
        "printf 'ORCA TERMINATED NORMALLY\\n'\n",
        encoding="utf-8",
    )
    fake_orca.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EPS_ORCA_WORK_ROOT", "relative-raw")

    output = OrcaEngine()._run(str(fake_orca), "! fake\n")

    assert "ORCA TERMINATED NORMALLY" in output
    assert len(list((tmp_path / "relative-raw").glob("eps-orca-*/pilot.out"))) == 1


def test_solvation_grid_config_solvents_are_orca_builtin() -> None:
    """The shipped grid config must only compute solvents ORCA recognizes, and defer the rest."""

    grid = load_solvation_grid_config()
    computed = {str(entry["orca_cosmors_name"]) for entry in grid["solvents"]}
    # Verified against ORCA 6.1.0-418's COSMORS(...) keyword table on Lop (2026-06-22).
    assert computed == {"Acetonitrile", "Nitromethane", "Water"}
    deferred = {str(entry["solvent_name"]) for entry in grid["deferred_solvents"]}
    assert deferred == {"propylene carbonate", "NMP"}


def test_solvation_grid_is_mock_first_with_deferred_and_cache_reuse(tmp_path: Path) -> None:
    engine, method = build_mock_orca_pilot_engines()[0], build_mock_orca_pilot_engines()[1]
    grid = load_solvation_grid_config()
    n_monomers = len(grid["monomers"])
    n_compute_solvents = len(grid["solvents"])
    n_deferred_solvents = len(grid["deferred_solvents"])

    cache_path = tmp_path / "grid.sqlite"
    outdir = tmp_path / "grid"
    result = run_orca_solvation_grid_pilot(
        engine=engine, method=method, cache_path=cache_path, outdir=outdir, engine_label="mock"
    )
    assert result.n_ok == n_monomers * n_compute_solvents
    assert result.n_failed == 0
    assert result.n_deferred == n_monomers * n_deferred_solvents
    assert result.n_computed == n_monomers * n_compute_solvents  # nothing cached on first run
    assert result.points_path.exists()
    assert result.plan_path.exists()
    # Deferred rows carry no computed value.
    deferred_rows = result.points[result.points["calc_status"] == "deferred"]
    assert deferred_rows["solvation_dG_kcal_mol"].isna().all()

    # Pre-flight plan over the populated cache must mark every computable point as cached.
    plan = plan_solvation_grid(grid, SQLiteCache(cache_path), method)
    assert int((plan["status"] == "cached").sum()) == n_monomers * n_compute_solvents
    assert int((plan["status"] == "deferred").sum()) == n_monomers * n_deferred_solvents
    assert int((plan["status"] == "compute").sum()) == 0


@pytest.mark.skipif(shutil.which("orca") is None, reason="ORCA not installed")
def test_orca_live_cosmors_single_monomer(tmp_path: Path) -> None:
    engine = OrcaEngine(OrcaConfig(optical_mode="cosmors", nprocs=1, maxcore_mb=1000))
    result = engine.run(
        CalcRequest(
            species=SpeciesSpec("c1ccsc1", 0, 1),
            method="orca-live-cosmors",
            solvent_eps_r=37.5,
            quantity="solvation_free_energy",
            solvent_model_name="Acetonitrile",
        )
    )
    assert result.unit == "kcal/mol"

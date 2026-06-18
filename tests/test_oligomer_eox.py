from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from eps.chemspace import load_monomers
from eps.engines import CalcRequest, MockEngine, SpeciesSpec
from eps.engines.base import CalcResult
from eps.properties.calculators import optical_gap_oligomer
from eps.properties.oligomer_series import (
    compute_oligomer_eox_series,
    extrapolate_infinite_chain,
)
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage import SQLiteCache, cached_run
from eps.structures.oligomer import load_polymerization_specs
from eps.workflow.tier1 import (
    annotate_tier1_filters,
    apply_tier1_filters,
    load_tier1_config,
)


def _spec(name: str):
    return load_polymerization_specs()[name]


# --- 1. Pure 1/n extrapolation math --------------------------------------------------------

def test_extrapolate_infinite_chain_recovers_intercept_exactly() -> None:
    # Construct points that are EXACTLY linear in 1/n: Eox(n) = a + b*(1/n).
    a, b = 5.0, 2.0
    eox_by_n = {n: a + b * (1.0 / n) for n in (1, 2, 3, 4, 6)}
    infinite, r2 = extrapolate_infinite_chain(eox_by_n)
    assert infinite == pytest.approx(a)  # the 1/n -> 0 limit is the intercept
    assert r2 == pytest.approx(1.0)


def test_extrapolate_infinite_chain_needs_two_points() -> None:
    assert all(np.isnan(v) for v in extrapolate_infinite_chain({2: 6.0}))
    assert all(np.isnan(v) for v in extrapolate_infinite_chain({}))


# --- 2. Per-n computation + assembly/truncation reuse --------------------------------------

def test_series_computes_each_n_and_reuses_optical_gap_oligomer(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = _spec("thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()

    cols = compute_oligomer_eox_series(
        monomer, spec, engine, cache, method="mock-gfn2", lengths=(2, 3, 4, 6)
    )

    assert cols["oligomer_Eox_calc_status"] == "ok"
    for n in (1, 2, 3, 4, 6):
        assert np.isfinite(cols[f"oligomer_Eox_raw_n{n}"])
    assert cols["oligomer_Eox_fit_n_points"] == 5
    assert np.isfinite(cols["oligomer_Eox_infinite_raw_eV"])
    assert cols["oligomer_Eox_calibration_out_of_domain"] is True

    # The n=1 raw value must equal the adiabatic_ip on the SAME (truncated) oligomer SMILES the
    # optical-gap path builds — proving the assembly + truncation reuse.
    oligo_smiles_n1, _ = optical_gap_oligomer(monomer, spec, 1)
    expected_n1 = cached_run(
        cache,
        engine,
        CalcRequest(
            species=SpeciesSpec(oligo_smiles_n1, charge=0, multiplicity=1),
            method="mock-gfn2",
            solvent_eps_r=None,
            quantity="adiabatic_ip",
        ),
        solvent_name=None,
    ).value
    assert cols["oligomer_Eox_raw_n1"] == pytest.approx(expected_n1)


def test_series_truncation_flag_mirrors_optical_gap(tmp_path: Path) -> None:
    # 3-hexylthiophene has a long inert alkyl chain -> the optical-gap truncation trims it.
    monomer = next(m for m in load_monomers() if m.name == "3-hexylthiophene")
    spec = _spec("3-hexylthiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")

    cols = compute_oligomer_eox_series(monomer, spec, MockEngine(), cache, method="mock-gfn2")
    _, expected_truncated = optical_gap_oligomer(monomer, spec, 6)
    assert cols["oligomer_Eox_sidechain_truncated"] == expected_truncated
    assert expected_truncated is True


def test_calibrated_infinite_uses_pinned_calibration_via_redox_projection(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = _spec("thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    calibration = {"enabled": True, "slope": 0.725837, "intercept": -3.145372}

    cols = compute_oligomer_eox_series(
        monomer, spec, MockEngine(), cache, method="mock-gfn2", calibration=calibration
    )
    infinite_raw = cols["oligomer_Eox_infinite_raw_eV"]
    descriptor_V = ip_eV_to_potential_vs_AgAgCl(infinite_raw)
    expected = calibration["slope"] * descriptor_V + calibration["intercept"]
    assert cols["oligomer_Eox_infinite_calibrated_V_vs_AgAgCl"] == pytest.approx(expected)
    assert cols["oligomer_Eox_calibration_out_of_domain"] is True


# --- 3. Failure tolerance ------------------------------------------------------------------

class FailIfLongEngine(MockEngine):
    """MockEngine that raises for oligomers whose SMILES exceeds max_len (i.e. longer chains)."""

    def __init__(self, max_len: int) -> None:
        self.max_len = max_len

    def run(self, req: CalcRequest) -> CalcResult:
        if len(req.species.canonical_smiles) > self.max_len:
            raise RuntimeError("simulated embedding failure on long oligomer")
        return super().run(req)


def test_partial_failure_still_extrapolates_and_records_error(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = _spec("thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")

    # Threshold so the short oligomers succeed but the long ones fail.
    cols = compute_oligomer_eox_series(
        monomer, spec, FailIfLongEngine(max_len=18), cache, method="mock-gfn2", lengths=(2, 3, 4, 6)
    )

    assert cols["oligomer_Eox_calc_status"] == "partial"
    assert cols["oligomer_Eox_fit_n_points"] >= 2
    assert "n=" in cols["oligomer_Eox_calc_error"]
    # Extrapolation still produced from surviving points; the batch never crashed.
    assert np.isfinite(cols["oligomer_Eox_infinite_raw_eV"])


def test_total_failure_is_failed_not_crashed(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = _spec("thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")

    cols = compute_oligomer_eox_series(
        monomer, spec, FailIfLongEngine(max_len=0), cache, method="mock-gfn2"
    )
    assert cols["oligomer_Eox_calc_status"] == "failed"
    assert np.isnan(cols["oligomer_Eox_infinite_raw_eV"])


def test_missing_spec_is_failed_not_crashed(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    cols = compute_oligomer_eox_series(monomer, None, MockEngine(), cache, method="mock-gfn2")
    assert cols["oligomer_Eox_calc_status"] == "failed"
    assert "no polymerization spec" in cols["oligomer_Eox_calc_error"]


# --- 4. Additivity: the descriptor never touches filters or survivor selection -------------

def test_oligomer_eox_columns_do_not_affect_tier1_filters() -> None:
    config = load_tier1_config()
    base = pd.DataFrame(
        {
            "monomer_name": ["m1", "m2"],
            "solvent_name": ["acetonitrile", "acetonitrile"],
            "salt": ["TBABF4", "TBABF4"],
            "window_margin_V": [0.5, 0.5],
            "anion_stability_margin_V": [0.5, 0.5],
            "solvation_dG_kcal_mol": [-5.0, -5.0],
            "monomer_Eox_calc_status": ["ok", "ok"],
            "solvation_calc_status": ["ok", "ok"],
            "anion_Eox_calc_status": ["ok", "ok"],
            "optical_gap_calc_status": ["ok", "ok"],
            "dimerization_calc_status": ["ok", "ok"],
        }
    )
    with_cols = base.copy()
    # A FAILED oligomer-Eox status on one row must NOT remove it (additive, not a filter input).
    with_cols["oligomer_Eox_calc_status"] = ["ok", "failed"]
    with_cols["oligomer_Eox_infinite_raw_eV"] = [5.4, float("nan")]

    survivors_base = apply_tier1_filters(annotate_tier1_filters(base, config), config)
    survivors_with = apply_tier1_filters(annotate_tier1_filters(with_cols, config), config)

    # Same survivor identities; the oligomer-Eox failure did not drop the second triad.
    assert set(map(tuple, survivors_base[["monomer_name", "solvent_name", "salt"]].to_numpy())) == set(
        map(tuple, survivors_with[["monomer_name", "solvent_name", "salt"]].to_numpy())
    )
    assert len(survivors_with) == 2

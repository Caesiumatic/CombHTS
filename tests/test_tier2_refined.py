from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.engines import MockEngine
from eps.workflow.tier1 import run_tier1
from eps.workflow.tier2 import DEFAULT_REFINED_WINDOW_MARGIN_V, run_tier2_refined_screen


def _tier1(tmp_path: Path):
    return run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / "c.sqlite",
        output_path=tmp_path / "ranked.csv",
    )


def test_refined_screen_tighter_than_tier1_and_pending_without_dft(tmp_path: Path) -> None:
    t1 = _tier1(tmp_path)
    result = run_tier2_refined_screen(tmp_path / "ranked.csv", tmp_path / "refined.csv")

    assert result.tier2_dft_pending is True  # no DFT CSV supplied
    assert result.refined_window_margin_V == DEFAULT_REFINED_WINDOW_MARGIN_V
    # The 0.5 V margin is tighter than the Tier-1 0.3 V gate, so refined <= Tier-1 survivors.
    assert result.n_tier2_survivors <= t1.surviving_triads
    assert result.output_path.exists()

    refined = result.refined
    # Every refined survivor passes the tighter window margin, and the composite is re-ranked.
    assert (refined["refined_window_margin_V"] > DEFAULT_REFINED_WINDOW_MARGIN_V).all()
    assert refined["composite_score"].between(0, 1).all()
    assert refined["composite_score"].is_monotonic_decreasing  # sorted best-first
    assert (refined["tier2_dft_pending"]).all()


def test_refined_screen_uses_dft_eox_when_supplied(tmp_path: Path) -> None:
    t1 = _tier1(tmp_path)
    # Synthetic Tier-2 DFT results: a distinct per-monomer Eox in V vs Ag/AgCl.
    monomers = t1.ranked[["monomer_canonical_smiles"]].drop_duplicates().copy()
    monomers["tier2_monomer_Eox_V_vs_AgAgCl"] = 0.42
    dft_path = tmp_path / "dft.csv"
    monomers.to_csv(dft_path, index=False)

    result = run_tier2_refined_screen(
        tmp_path / "ranked.csv", tmp_path / "refined_dft.csv", dft_results_path=dft_path
    )
    assert result.tier2_dft_pending is False
    # Read the full refined-before-filter via the output: every surviving row used the DFT Eox.
    refined = pd.read_csv(result.output_path)
    if not refined.empty:
        assert (refined["monomer_Eox_used_V_vs_AgAgCl"] == 0.42).all()


def test_refined_screen_keeps_anion_and_solubility_constraints(tmp_path: Path) -> None:
    _tier1(tmp_path)
    result = run_tier2_refined_screen(tmp_path / "ranked.csv", tmp_path / "refined.csv")
    refined = result.refined
    # Tier-1 thresholds (0.2 V anion stability, -3.0 kcal/mol solvation) still hold on survivors.
    assert (refined["anion_stability_margin_V"] > 0.2).all()
    assert (refined["solvation_dG_kcal_mol"] < -3.0).all()

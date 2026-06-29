from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.engines import MockEngine
from eps.workflow.tier1 import run_tier1
from eps.workflow.tier2 import (
    DEFAULT_REFINED_WINDOW_MARGIN_V,
    run_tier2_bandgap,
    run_tier2_dimerization,
    run_tier2_refined_screen,
)


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


def test_refined_screen_uses_dft_solvent_anodic_when_full_scope_harvest(tmp_path: Path) -> None:
    t1 = _tier1(tmp_path)
    monomers = t1.ranked["monomer_canonical_smiles"].drop_duplicates().tolist()
    solvents = t1.ranked["solvent_name"].drop_duplicates().tolist()
    rows = []
    for m in monomers:  # monomer oxidation rows (populate the monomer-Eox column)
        rows.append({
            "entity_type": "monomer", "quantity": "adiabatic_ip",
            "monomer_canonical_smiles": m, "canonical_smiles": m, "solvent_name": solvents[0],
            "tier2_monomer_Eox_V_vs_AgAgCl": 0.50, "redox_potential_V_vs_AgAgCl": 0.50,
        })
    for s in solvents:  # solvent anodic rows with a deliberately HIGH DFT anodic limit (9.0 V)
        rows.append({
            "entity_type": "solvent", "quantity": "adiabatic_ip",
            "monomer_canonical_smiles": "", "canonical_smiles": "CC#N", "solvent_name": s,
            "tier2_monomer_Eox_V_vs_AgAgCl": None, "redox_potential_V_vs_AgAgCl": 9.0,
        })
    dft_path = tmp_path / "dft_full.csv"
    pd.DataFrame(rows).to_csv(dft_path, index=False)

    result = run_tier2_refined_screen(
        tmp_path / "ranked.csv", tmp_path / "refined_full.csv", dft_results_path=dft_path
    )
    refined = result.refined
    if not refined.empty:
        assert (refined["solvent_anodic_source"] == "tier2_dft").all()
        # refined window = DFT anodic (9.0) - DFT monomer Eox (0.50) = 8.5 V
        assert (refined["refined_window_margin_V"].round(2) == 8.50).all()


def test_run_tier2_dimerization_mock(tmp_path: Path) -> None:
    surv = tmp_path / "surv.csv"
    pd.DataFrame([
        {"monomer_canonical_smiles": "c1ccsc1", "monomer_name": "thiophene", "solvent_name": "acetonitrile"},
    ]).to_csv(surv, index=False)
    config = Path(__file__).resolve().parents[1] / "configs" / "tier2_orca.yaml"
    out = run_tier2_dimerization(surv, config, tmp_path / "dim.csv", engine=MockEngine())
    row = out.iloc[0]
    assert row["status"] == "ok"
    assert pd.notna(row["tier2_dimerization_dG_kcal_mol"])
    assert (tmp_path / "dim.csv").exists()


def test_refined_screen_consumes_dft_dimerization(tmp_path: Path) -> None:
    _tier1(tmp_path)
    surv = pd.read_csv(tmp_path / "ranked.csv")
    pairs = surv[["monomer_canonical_smiles", "solvent_name"]].drop_duplicates()
    # synthetic strongly-favorable DFT dimerization for every surviving pair
    pairs["tier2_dimerization_dG_kcal_mol"] = -25.0
    dim_path = tmp_path / "dim.csv"
    pairs.to_csv(dim_path, index=False)

    result = run_tier2_refined_screen(
        tmp_path / "ranked.csv", tmp_path / "refined_dim.csv", dimerization_dft_path=dim_path
    )
    refined = result.refined
    if not refined.empty:
        assert (refined["dimerization_source"] == "tier2_dft").all()
        assert (refined["dimerization_dG_kcal_mol"] == -25.0).all()


def test_dimerization_sharding_partitions_pairs(tmp_path: Path) -> None:
    surv = tmp_path / "surv.csv"
    pd.DataFrame([
        {"monomer_canonical_smiles": "c1ccsc1", "monomer_name": "thiophene", "solvent_name": "acetonitrile"},
        {"monomer_canonical_smiles": "c1cc[nH]c1", "monomer_name": "pyrrole", "solvent_name": "acetonitrile"},
    ]).to_csv(surv, index=False)
    config = Path(__file__).resolve().parents[1] / "configs" / "tier2_orca.yaml"
    s0 = run_tier2_dimerization(surv, config, tmp_path / "d0.csv", engine=MockEngine(), n_shards=2, shard_index=0)
    s1 = run_tier2_dimerization(surv, config, tmp_path / "d1.csv", engine=MockEngine(), n_shards=2, shard_index=1)
    assert len(s0) == 1 and len(s1) == 1  # 2 pairs split across 2 shards
    assert set(s0["monomer_name"]) | set(s1["monomer_name"]) == {"thiophene", "pyrrole"}


def test_run_tier2_bandgap_mock(tmp_path: Path) -> None:
    surv = tmp_path / "surv.csv"
    pd.DataFrame([
        {"monomer_canonical_smiles": "c1ccsc1", "monomer_name": "thiophene"},
    ]).to_csv(surv, index=False)
    out = run_tier2_bandgap(surv, tmp_path / "bg.csv", engine=MockEngine(), lengths=(1, 2))
    row = out.iloc[0]
    assert pd.notna(row["tier2_optical_gap_eV"])
    assert (tmp_path / "bg.csv").exists()


def test_refined_screen_consumes_dft_bandgap(tmp_path: Path) -> None:
    _tier1(tmp_path)
    surv = pd.read_csv(tmp_path / "ranked.csv")
    monos = surv[["monomer_canonical_smiles"]].drop_duplicates()
    monos["tier2_optical_gap_eV"] = 1.80  # exactly the target gap -> zero deviation
    opt_path = tmp_path / "bg.csv"
    monos.to_csv(opt_path, index=False)
    result = run_tier2_refined_screen(
        tmp_path / "ranked.csv", tmp_path / "refined_bg.csv", optical_dft_path=opt_path
    )
    refined = result.refined
    if not refined.empty:
        assert (refined["optical_gap_source"] == "tier2_tddft").all()
        assert (refined["optical_gap_eV"] == 1.80).all()


def test_refined_screen_keeps_anion_and_solubility_constraints(tmp_path: Path) -> None:
    _tier1(tmp_path)
    result = run_tier2_refined_screen(tmp_path / "ranked.csv", tmp_path / "refined.csv")
    refined = result.refined
    # Tier-1 thresholds (0.2 V anion stability, -3.0 kcal/mol solvation) still hold on survivors.
    assert (refined["anion_stability_margin_V"] > 0.2).all()
    assert (refined["solvation_dG_kcal_mol"] < -3.0).all()

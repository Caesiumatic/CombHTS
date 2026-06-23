from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

from eps.engines import MockEngine
from eps.validation.directive import (
    _applicability_domain_status,
    _bootstrap_mean_ci,
    _compute_esw_descriptor_points,
    _compute_esw_gate_diagnostics,
    _compute_feasibility_outputs,
    _feasibility_bootstrap_ci,
    run_directive_validation,
)
from eps.validation.solvent_benchmark import SOLVENT_BENCHMARK_COLUMNS


def _canon(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None
    return Chem.MolToSmiles(mol)


def _minimal_harvest(path: Path, *, unsafe: bool = False) -> Path:
    measured = 3.245
    final = 3.50 if unsafe else 3.00
    frame = pd.DataFrame(
        [
            {
                "monomer_name": "EDOT",
                "monomer_canonical_smiles": _canon("c1scc2c1OCCO2"),
                "solvent_name": "acetonitrile",
                "salt": "TBAPF6",
                "anion_smiles": "F[P-](F)(F)(F)(F)F",
                "passes_all_tier1_filters": True,
                "solvent_window_condition_match": "solvent_only_conservative",
                "solvent_window_measurement_anodic_V": measured,
                "solvent_window_measurement_source": "test source",
                "solvent_window_measurement_tier": "A",
                "solvent_window_measurement_electrode": "Pt",
                "solvent_window_measurement_electrolyte": "0.1 M test",
                "solvent_window_measurement_reference": "Ag/AgCl",
                "solvent_anodic_limit_csv_V": 3.30,
                "solvent_anodic_limit_calibrated_V": 3.10,
                "solvent_anodic_limit_V": final,
                "solvent_window_conservative_cap_source": "fallback_conservative_min_csv_computed",
                "solvent_window_cap_applied": final < measured,
                "solvent_window_limit_set_by_electrolyte": True,
            }
        ]
    )
    frame.to_csv(path, index=False)
    return path


def _labels(path: Path, rows: list[dict]) -> Path:
    columns = [
        "monomer_name",
        "monomer_smiles",
        "solvent",
        "electrolyte",
        "electrode",
        "outcome",
        "negative_type",
        "experimental_basis",
        "reference_electrode",
        "source_doi",
        "source_locator",
        "reliability_tier",
        "medium_class",
        "flags",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame.to_csv(path, index=False)
    return path


def _label(smiles: str, outcome: str, *, electrolyte: str = "TBAPF6") -> dict:
    return {
        "monomer_name": "m",
        "monomer_smiles": smiles,
        "solvent": "MeCN",
        "electrolyte": electrolyte,
        "electrode": "Pt",
        "outcome": outcome,
        "negative_type": "NA",
        "experimental_basis": "test",
        "reference_electrode": "SCE",
        "source_doi": "10.test/example",
        "source_locator": "fixture",
        "reliability_tier": "A",
        "medium_class": "baseline_MeCN_TBA",
        "flags": "",
    }


def test_validate_directive_outputs_are_deterministic_and_labeled_mock(tmp_path: Path) -> None:
    harvest = _minimal_harvest(tmp_path / "harvest.csv")
    outdir = tmp_path / "out"

    first = run_directive_validation(
        engine=MockEngine(),
        engine_name="mock",
        method="mock-gfn2",
        cache_path=tmp_path / "cache.sqlite",
        harvest_path=harvest,
        outdir=outdir,
        generated_at_utc="2026-06-23T00:00:00+00:00",
    )
    first_summary = json.loads(first.summary_path.read_text(encoding="utf-8"))
    second = run_directive_validation(
        engine=MockEngine(),
        engine_name="mock",
        method="mock-gfn2",
        cache_path=tmp_path / "cache.sqlite",
        harvest_path=harvest,
        outdir=outdir,
        generated_at_utc="2026-06-23T00:00:00+00:00",
    )
    second_summary = json.loads(second.summary_path.read_text(encoding="utf-8"))

    assert first_summary == second_summary
    assert first_summary["mock_non_physical"] is True
    assert "NON-PHYSICAL" in second.report_path.read_text(encoding="utf-8")
    for artifact in first_summary["artifacts"].values():
        assert Path(artifact).exists()


def test_validate_directive_empty_benchmark_is_machine_readable(tmp_path: Path) -> None:
    benchmark = pd.read_csv("data/benchmark.csv", keep_default_na=False).head(0)
    benchmark_path = tmp_path / "empty_benchmark.csv"
    benchmark.to_csv(benchmark_path, index=False)

    result = run_directive_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "cache.sqlite",
        harvest_path=_minimal_harvest(tmp_path / "harvest.csv"),
        outdir=tmp_path / "out",
        benchmark_path=benchmark_path,
        generated_at_utc="2026-06-23T00:00:00+00:00",
    )
    profiles = pd.read_csv(result.eox_profile_summary_path)

    assert set(profiles["profile_status"]) == {"skipped_empty_benchmark"}
    eox_row = next(
        row for row in result.metric_table if row["metric"].startswith("Tier-1 monomer Eox")
    )
    assert eox_row["status"] == "NOT_YET_TESTABLE"


def test_validate_directive_missing_harvest_reports_not_testable(tmp_path: Path) -> None:
    result = run_directive_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "cache.sqlite",
        harvest_path=tmp_path / "missing.csv",
        outdir=tmp_path / "out",
        generated_at_utc="2026-06-23T00:00:00+00:00",
    )
    gate_row = next(row for row in result.metric_table if row["metric"] == "Production ESW gate unsafe widening")
    feasibility_row = next(row for row in result.metric_table if row["metric"].startswith("Qualitative"))

    assert gate_row["status"] == "NOT_YET_TESTABLE"
    assert feasibility_row["status"] == "NOT_YET_TESTABLE"
    assert result.summary["esw_gate"]["harvest_found"] is False


def test_feasibility_no_matches_and_exact_anion_matching(tmp_path: Path) -> None:
    thio = _canon("c1ccsc1")
    labels = _labels(tmp_path / "labels.csv", [_label("c1ccsc1", "YES", electrolyte="Et4NBF4 (BF4-)")])
    mismatched_harvest = pd.DataFrame(
        [
            {
                "monomer_canonical_smiles": thio,
                "solvent_name": "acetonitrile",
                "salt": "TBAPF6",
                "passes_all_tier1_filters": True,
            }
        ]
    )
    mismatch_path = tmp_path / "mismatch.csv"
    mismatched_harvest.to_csv(mismatch_path, index=False)
    _, mismatch = _compute_feasibility_outputs(
        labels_path=labels, harvest_path=mismatch_path, bootstrap_seed=7
    )
    assert mismatch["n_matched"] == 0
    assert mismatch["computable"] is False

    matched_harvest = mismatched_harvest.assign(salt="TBABF4")
    match_path = tmp_path / "match.csv"
    matched_harvest.to_csv(match_path, index=False)
    matches, meta = _compute_feasibility_outputs(labels_path=labels, harvest_path=match_path, bootstrap_seed=7)
    assert meta["exact_anion_matches"] == 1
    assert matches.iloc[0]["match_basis"] == "specified-anion"


def test_applicability_domain_boundary_behavior() -> None:
    assert _applicability_domain_status(0.9, 1.0, 2.0) == ("below-domain", pytest.approx(0.1))
    assert _applicability_domain_status(1.0, 1.0, 2.0) == ("in-domain", 0.0)
    assert _applicability_domain_status(2.0, 1.0, 2.0) == ("in-domain", 0.0)
    assert _applicability_domain_status(2.2, 1.0, 2.0) == ("above-domain", pytest.approx(0.2))


def test_esw_gate_unsafe_widening_and_conservative_behavior(tmp_path: Path) -> None:
    unsafe_harvest = _minimal_harvest(tmp_path / "unsafe.csv", unsafe=True)
    unsafe_diag, unsafe_meta = _compute_esw_gate_diagnostics(unsafe_harvest)
    assert unsafe_meta["unsafe_widening_count"] == 1
    assert bool(unsafe_diag.iloc[0]["unsafe_widening"])

    safe_harvest = _minimal_harvest(tmp_path / "safe.csv", unsafe=False)
    safe_diag, safe_meta = _compute_esw_gate_diagnostics(safe_harvest)
    assert safe_meta["unsafe_widening_count"] == 0
    assert safe_diag.iloc[0]["conservatism_V"] == pytest.approx(0.245)
    assert bool(safe_diag.iloc[0]["cap_applied"])


def test_bootstrap_seed_reproducibility() -> None:
    values = [0.1, 0.2, 0.4, 0.8]
    assert _bootstrap_mean_ci(values, seed=123) == _bootstrap_mean_ci(values, seed=123)
    matches = pd.DataFrame(
        [
            {"outcome": "YES", "predicted": "YES"},
            {"outcome": "YES", "predicted": "NO"},
            {"outcome": "NO", "predicted": "NO"},
            {"outcome": "NO", "predicted": "YES"},
        ]
    )
    assert _feasibility_bootstrap_ci(matches, seed=123) == _feasibility_bootstrap_ci(matches, seed=123)


def test_solvent_descriptor_csv_preserves_hash_smiles(tmp_path: Path) -> None:
    benchmark = pd.DataFrame(
        [
            {
                "solvent": "acetonitrile",
                "smiles": "CC#N",
                "exp_anodic_V_vs_AgAgCl": 3.3,
                "exp_cathodic_V_vs_AgAgCl": -2.8,
                "reference": "Ag/AgCl",
                "electrolyte": "test",
                "electrode": "GC",
                "source": "fixture",
                "tier": "A",
            }
        ],
        columns=list(SOLVENT_BENCHMARK_COLUMNS),
    )
    benchmark_path = tmp_path / "solvent_benchmark.csv"
    benchmark.to_csv(benchmark_path, index=False)

    points, meta = _compute_esw_descriptor_points(
        engine=MockEngine(),
        method="mock-gfn2",
        cache_path=tmp_path / "cache.sqlite",
        benchmark_path=benchmark_path,
    )

    assert points.iloc[0]["smiles"] == "CC#N"
    assert meta["anodic_n"] == 1

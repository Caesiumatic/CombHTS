from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from rdkit import Chem

from eps.chemspace import load_electrolytes, load_monomers, load_solvents
from eps.engines import MockEngine
from eps.storage import SQLiteCache
from eps.validation.directive import run_directive_validation
from eps.workflow.tier1 import (
    compute_anion_solvent_table,
    compute_monomer_solvent_table,
    compute_monomer_table,
    compute_solvent_table,
    load_tier1_config,
    run_tier1,
)


def _assert_columns(frame: pd.DataFrame, required: set[str]) -> None:
    assert required.issubset(frame.columns), sorted(required.difference(frame.columns))


def _canon(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None
    return Chem.MolToSmiles(mol)


def _minimal_harvest(path: Path) -> Path:
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
                "solvent_window_measurement_anodic_V": 3.245,
                "solvent_window_measurement_source": "test source",
                "solvent_window_measurement_tier": "A",
                "solvent_window_measurement_electrode": "Pt",
                "solvent_window_measurement_electrolyte": "0.1 M test",
                "solvent_window_measurement_reference": "Ag/AgCl",
                "solvent_anodic_limit_csv_V": 3.30,
                "solvent_anodic_limit_calibrated_V": 3.10,
                "solvent_anodic_limit_V": 3.00,
                "solvent_window_conservative_cap_source": "fallback_conservative_min_csv_computed",
                "solvent_window_cap_applied": True,
                "solvent_window_limit_set_by_electrolyte": True,
            }
        ]
    )
    frame.to_csv(path, index=False)
    return path


def test_tier1_ranked_and_all_triads_public_schema_contract(tmp_path: Path) -> None:
    result = run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / "tier1.sqlite",
        output_path=tmp_path / "tier1_ranked.csv",
        all_output_path=tmp_path / "tier1_all.csv",
    )

    triad_required = {
        "monomer_name",
        "monomer_canonical_smiles",
        "solvent_name",
        "salt",
        "cation_smiles",
        "anion_smiles",
        "monomer_Eox_raw_V_vs_AgAgCl",
        "monomer_Eox_calibrated_V_vs_AgAgCl",
        "monomer_Eox_filter_V_vs_AgAgCl",
        "monomer_Eox_V",
        "solvent_window_condition_match",
        "solvent_window_measurement_anodic_V",
        "solvent_window_conservative_cap_source",
        "solvent_anodic_limit_V",
        "anion_Eox_raw_V_vs_AgAgCl",
        "anion_Eox_calibrated_V_vs_AgAgCl",
        "anion_Eox_filter_V_vs_AgAgCl",
        "pass_window_margin",
        "pass_anion_stability",
        "pass_solvation",
        "passes_all_tier1_filters",
        "failed_filter_reasons",
        "window_margin_V",
        "anion_stability_margin_V",
        "solvation_dG_kcal_mol",
        "solvation_calc_status",
        "solvation_calc_error",
        "optical_gap_eV",
        "optical_gap_method",
        "optical_gap_calc_status",
        "optical_gap_calc_error",
        "dimerization_dG_kcal_mol",
        "dimerization_calc_status",
        "dimerization_calc_error",
        "band_gap_deviation_eV",
        "composite_score",
        "pareto_front",
        "norm_window_margin",
        "norm_anion_stability",
        "norm_solubility",
        "norm_dimerization",
        "norm_band_gap",
    }
    ranked_required = triad_required | {"salts_tied", "n_tied"}

    _assert_columns(result.all_triads, triad_required)
    _assert_columns(result.ranked, ranked_required)


def test_tier1_per_species_table_public_schema_contract(tmp_path: Path) -> None:
    engine = MockEngine()
    cache = SQLiteCache(tmp_path / "species.sqlite")
    config = load_tier1_config()
    monomers = load_monomers()[:2]
    solvents = load_solvents()[:2]
    electrolytes = load_electrolytes()[:2]
    method = "mock-gfn2"

    monomer_table = compute_monomer_table(
        monomers,
        engine,
        cache,
        method=method,
        calibration_config=config.get("calibration", {}),
        secondary_descriptors=True,
        bandgap_convergence=config.get("bandgap_convergence", {}),
    )
    monomer_solvent_table = compute_monomer_solvent_table(
        monomers,
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=config.get("calibration", {}),
    )
    solvent_table = compute_solvent_table(
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=config.get("calibration", {}),
        secondary_descriptors=True,
    )
    anion_table = compute_anion_solvent_table(
        electrolytes,
        solvents,
        engine,
        cache,
        method=method,
        calibration_config=config.get("calibration", {}),
        secondary_descriptors=True,
    )

    _assert_columns(
        monomer_table,
        {
            "monomer_name",
            "monomer_canonical_smiles",
            "optical_gap_eV",
            "optical_gap_method",
            "optical_gap_oligomer_n",
            "optical_gap_calc_status",
            "optical_gap_calc_error",
            "dimerization_dG_kcal_mol",
            "dimerization_reaction",
            "dimerization_calc_status",
            "dimerization_calc_error",
            "oligomer_Eox_raw_n1",
            "oligomer_Eox_infinite_raw_eV",
            "oligomer_Eox_calc_status",
            "oligomer_Eox_calc_error",
            "monomer_HOMO_eV",
            "monomer_lambda_ox_eV",
            "secondary_monomer_calc_status",
            "secondary_monomer_calc_error",
            "optical_gap_converged",
            "optical_gap_convergence_calc_status",
            "optical_gap_convergence_calc_error",
        },
    )
    _assert_columns(
        monomer_solvent_table,
        {
            "monomer_canonical_smiles",
            "solvent_name",
            "monomer_Eox_raw_V_vs_AgAgCl",
            "monomer_Eox_calibrated_V_vs_AgAgCl",
            "monomer_Eox_filter_V_vs_AgAgCl",
            "monomer_Eox_V",
            "monomer_Eox_calc_status",
            "monomer_Eox_calc_error",
            "solvation_dG_kcal_mol",
            "solvation_calc_status",
            "solvation_calc_error",
        },
    )
    _assert_columns(
        solvent_table,
        {
            "solvent_name",
            "solvent_anodic_limit_computed_V",
            "solvent_anodic_limit_calibrated_V",
            "solvent_anodic_limit_csv_V",
            "solvent_anodic_limit_V",
            "solvent_anodic_limit_source",
            "solvent_anodic_limit_calc_status",
            "solvent_anodic_limit_calc_error",
            "solvent_cathodic_limit_computed_V",
            "solvent_cathodic_limit_csv_V",
            "solvent_cathodic_limit_V",
            "solvent_cathodic_limit_source",
            "solvent_lambda_ox_eV",
            "secondary_solvent_calc_status",
            "secondary_solvent_calc_error",
        },
    )
    _assert_columns(
        anion_table,
        {
            "anion_canonical_smiles",
            "solvent_name",
            "anion_Eox_raw_V_vs_AgAgCl",
            "anion_Eox_calibrated_V_vs_AgAgCl",
            "anion_Eox_filter_V_vs_AgAgCl",
            "anion_Eox_V",
            "anion_Eox_calc_status",
            "anion_Eox_calc_error",
            "anion_vdw_volume_A3",
            "anion_volume_method",
            "anion_volume_calc_status",
            "anion_volume_calc_error",
        },
    )


def test_directive_validation_public_artifact_contract(tmp_path: Path) -> None:
    result = run_directive_validation(
        engine=MockEngine(),
        engine_name="mock",
        method="mock-gfn2",
        cache_path=tmp_path / "directive.sqlite",
        harvest_path=_minimal_harvest(tmp_path / "harvest.csv"),
        outdir=tmp_path / "directive",
        generated_at_utc="2026-06-25T00:00:00+00:00",
    )

    assert {path.name for path in result.outdir.iterdir() if path.is_file()} == {
        "validation_summary.json",
        "validation_report.md",
        "eox_profile_summary.csv",
        "eox_points.csv",
        "esw_descriptor_points.csv",
        "esw_gate_diagnostics.csv",
        "feasibility_matches.csv",
        "provenance.json",
    }

    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert {
        "generated_at_utc",
        "engine",
        "base_method",
        "production_method",
        "mock_non_physical",
        "bootstrap_seed",
        "directive_status_table",
        "eox",
        "esw_descriptor",
        "esw_gate",
        "feasibility",
        "artifacts",
    }.issubset(summary)

    provenance = json.loads(result.provenance_path.read_text(encoding="utf-8"))
    assert {
        "engine",
        "method",
        "mock_non_physical",
        "git",
        "config_sha256",
        "library_sizes",
        "inputs",
        "input_sha256",
        "bootstrap_seed",
        "directive_status_table",
    }.issubset(provenance)

    _assert_columns(
        pd.read_csv(result.eox_profile_summary_path),
        {
            "profile_name",
            "profile_status",
            "reference_frame",
            "label_types",
            "is_active_production_profile",
            "is_config_default_profile",
            "collapsed_calibration_group_count",
            "slope",
            "intercept",
            "r2",
            "mae_after_V",
            "loo_mae_after_V",
            "reference_floor_note",
        },
    )
    _assert_columns(
        pd.read_csv(result.eox_points_path),
        {
            "profile_name",
            "point_kind",
            "group_id",
            "monomer_name",
            "canonical_smiles",
            "solvent_name",
            "pred_Eox_V_vs_AgAgCl",
            "exp_Eox_V_vs_AgAgCl",
            "calibrated_Eox_V_vs_AgAgCl",
            "residual_after_V",
            "loo_residual_after_V",
            "high_leverage_flag",
            "applicability_domain_status",
            "distance_outside_domain_V",
        },
    )
    _assert_columns(
        pd.read_csv(result.esw_descriptor_points_path),
        {
            "solvent",
            "smiles",
            "reference",
            "electrolyte",
            "exp_anodic_V_vs_AgAgCl",
            "computed_anodic_descriptor_V_vs_AgAgCl",
            "anodic_abs_error_V",
            "exp_cathodic_V_vs_AgAgCl",
            "computed_cathodic_descriptor_V_vs_AgAgCl",
            "cathodic_abs_error_V",
            "comparison_label",
        },
    )
    _assert_columns(
        pd.read_csv(result.esw_gate_diagnostics_path),
        {
            "monomer_name",
            "solvent_name",
            "salt",
            "selected_measured_anodic_V",
            "measurement_match",
            "final_gate_V",
            "unsafe_widening",
            "conservatism_V",
        },
    )
    _assert_columns(
        pd.read_csv(result.feasibility_matches_path),
        {
            "monomer_name",
            "monomer_smiles",
            "solvent",
            "electrolyte",
            "match_basis",
            "outcome",
            "predicted",
            "reliability_tier",
            "medium_class",
        },
    )

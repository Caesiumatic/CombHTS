from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from rdkit import Chem

from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.properties.redox import potential_vs_AgAgCl_to_ip_eV
from eps.validation import (
    load_calibration_profiles,
    run_all_calibration_profiles,
    run_benchmark_validation,
    run_calibration_profile,
)


def test_validation_runner_writes_report_with_finite_mock_mae(tmp_path: Path) -> None:
    result = run_benchmark_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "validation.sqlite",
        report_path=tmp_path / "validation_report.csv",
    )

    assert result.report_path.exists()
    assert len(result.rows) >= 10
    assert np.isfinite(result.mae_before_V)
    assert np.isfinite(result.mae_after_V)
    assert np.isfinite(result.within_group_spread_V)
    assert result.n_calibration_points >= 2
    assert "residual_before_V" in result.rows.columns
    assert "residual_after_V" in result.rows.columns
    assert "in_calibration_set" in result.rows.columns

    written = pd.read_csv(result.report_path)
    assert len(written) == len(result.rows)


def test_perfect_synthetic_predictor_has_zero_mae(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.csv"
    benchmark_path.write_text(
        "\n".join(
            [
                "monomer_name,monomer_smiles,solvent_name,electrolyte,exp_Eox_V_vs_AgAgCl,source_doi_or_ref,notes",
                "methane,C,acetonitrile,TBAPF6,0.50,synthetic,perfect",
                "ethane,CC,acetonitrile,TBAPF6,1.25,synthetic,perfect",
                "propane,CCC,acetonitrile,TBAPF6,1.75,synthetic,perfect",
            ]
        ),
        encoding="utf-8",
    )
    engine = PerfectEoxEngine({"C": 0.50, "CC": 1.25, "CCC": 1.75})

    result = run_benchmark_validation(
        engine=engine,
        cache_path=tmp_path / "perfect.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "perfect_report.csv",
    )

    assert result.mae_before_V == pytest.approx(0.0, abs=1e-12)
    assert result.mae_after_V == pytest.approx(0.0, abs=1e-12)
    assert result.loo_mae_after_V == pytest.approx(0.0, abs=1e-12)
    assert result.tier1_xtb_pass


def test_default_real_benchmark_selection_excludes_aqueous_and_tier_c(tmp_path: Path) -> None:
    result = run_benchmark_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "real_selection.sqlite",
        report_path=tmp_path / "real_selection_report.csv",
    )

    selected = result.rows["in_calibration_set"]
    assert not result.rows.loc[result.rows["medium"] == "aqueous", "in_calibration_set"].any()
    assert not result.rows.loc[result.rows["reliability_tier"] == "C", "in_calibration_set"].any()
    assert int(selected.sum()) == 48
    assert result.raw_benchmark_rows == 48
    assert result.calibration_eligible_rows == 48
    assert result.n_calibration_points == 47  # 48 rows; only the two pyrrole peak rows collapse to one group
    assert "calibration_exclusion_reason" in result.rows.columns


def test_strict_benchmark_v1_data_shape_and_identity_conversion() -> None:
    benchmark = pd.read_csv(Path("data/benchmark.csv"), keep_default_na=False)
    candidates = pd.read_csv(Path("data/benchmark_candidates.csv"), keep_default_na=False)

    assert len(benchmark) == 48
    assert len(candidates) == 37
    assert benchmark["calibration_eligible"].map(lambda value: str(value).lower() == "true").all()
    assert (benchmark["reference_frame"] == "agagcl").all()
    assert pd.to_numeric(benchmark["exp_Eox_V_vs_AgAgCl"], errors="coerce").notna().all()
    assert (benchmark["converted_reference_electrode"] == "Ag/AgCl").all()
    conversion = pd.to_numeric(benchmark["conversion_to_AgAgCl_V"], errors="coerce")
    # native + conversion must reproduce the Ag/AgCl value for EVERY row: identity (0.0) for the
    # native-Ag/AgCl rows, and the explicit +0.044 V SCE->Ag/AgCl shift for the 3-methylthiophene row.
    native = pd.to_numeric(benchmark["native_potential_V"], errors="coerce")
    exp = pd.to_numeric(benchmark["exp_Eox_V_vs_AgAgCl"], errors="coerce")
    assert ((native + conversion - exp).abs() < 1e-6).all()
    assert (
        conversion[
            benchmark["monomer_name"].str.startswith(("FSeF", "FSF", "DFA", "OSeO", "SSeS", "SeSeSe"))
        ]
        == 0.0
    ).all()

    for smiles in benchmark["monomer_smiles"]:
        assert smiles
        assert Chem.MolFromSmiles(smiles, sanitize=True) is not None


def test_strict_benchmark_v1_collapses_by_smiles_solvent_and_label(tmp_path: Path) -> None:
    result = run_benchmark_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "strict_v1.sqlite",
        report_path=tmp_path / "strict_v1_report.csv",
    )
    grouped = result.rows.groupby(["canonical_smiles", "solvent_name", "label_type"], dropna=False).size()

    assert len(grouped) == 47
    assert result.n_calibration_points == 47
    thiophene_acn = result.rows[
        (result.rows["monomer_smiles"] == "c1ccsc1")
        & (result.rows["solvent_name"] == "acetonitrile")
    ]
    assert set(thiophene_acn["label_type"]) == {
        "monomer_oxidation_peak",
        "monomer_oxidation_onset",
    }
    assert thiophene_acn["group_id"].nunique() == 2


def test_reference_frame_defaults_to_agagcl_when_column_absent(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "no_reference_frame.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
        ],
    )

    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25}),
        cache_path=tmp_path / "no_reference_frame.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "no_reference_frame_report.csv",
    )

    assert "reference_frame" in result.rows.columns
    assert (result.rows["reference_frame"] == "agagcl").all()


def test_peak_and_onset_profiles_use_disjoint_groups_and_different_fits(tmp_path: Path) -> None:
    peak = run_calibration_profile(
        "agagcl_peak_relaxed",
        engine=MockEngine(),
        cache_path=tmp_path / "profiles.sqlite",
        report_path=tmp_path / "peak_report.csv",
    )
    onset = run_calibration_profile(
        "agagcl_onset_relaxed",
        engine=MockEngine(),
        cache_path=tmp_path / "profiles.sqlite",
        report_path=tmp_path / "onset_report.csv",
    )

    peak_groups = set(peak.rows.loc[peak.rows["in_calibration_set"], "group_id"])
    onset_groups = set(onset.rows.loc[onset.rows["in_calibration_set"], "group_id"])

    assert peak_groups
    assert onset_groups
    assert peak_groups.isdisjoint(onset_groups)
    assert peak.n_calibration_points == 29
    assert onset.n_calibration_points == 18
    assert (
        peak.calibration.slope,
        peak.calibration.intercept,
    ) != pytest.approx((onset.calibration.slope, onset.calibration.intercept))


def test_run_all_calibration_profiles_skips_insufficient_points_and_writes_csv(tmp_path: Path) -> None:
    comparison_path = tmp_path / "profile_comparison.csv"

    comparison = run_all_calibration_profiles(
        engine=MockEngine(),
        cache_path=tmp_path / "all_profiles.sqlite",
        report_path=tmp_path / "profile_report.csv",
        comparison_path=comparison_path,
    )
    configured = load_calibration_profiles()

    assert comparison_path.exists()
    assert len(comparison) == len(configured["profiles"])
    skipped = comparison.loc[comparison["profile_name"].str.startswith("fc_")]
    assert set(skipped["status"]) == {"skipped_insufficient_points"}
    assert (skipped["n_points"] == 0).all()

    written = pd.read_csv(comparison_path)
    assert len(written) == len(configured["profiles"])


def test_oseo_and_fsef_share_canonical_smiles_but_keep_solvent_groups(tmp_path: Path) -> None:
    result = run_calibration_profile(
        "agagcl_peak_relaxed",
        engine=MockEngine(),
        cache_path=tmp_path / "oseo_fsef.sqlite",
        report_path=tmp_path / "oseo_fsef_report.csv",
    )

    fsef = result.rows[result.rows["monomer_name"].str.startswith("FSeF")].iloc[0]
    oseo = result.rows[result.rows["monomer_name"].str.startswith("OSeO")].iloc[0]

    assert fsef["canonical_smiles"] == oseo["canonical_smiles"]
    assert fsef["solvent_name"] == "acetonitrile"
    assert oseo["solvent_name"] == "DCM"
    assert fsef["group_id"] != oseo["group_id"]
    assert bool(fsef["in_calibration_set"])
    assert bool(oseo["in_calibration_set"])


def test_equivalent_smiles_collapse_to_same_benchmark_group(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "equivalent_smiles.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row("ethanol_a", "CCO", 1.00, "monomer_oxidation_onset", True),
            _ontology_row("ethanol_b", "OCC", 1.00, "monomer_oxidation_onset", True),
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_peak", True),
        ],
    )

    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"CCO": 1.00, "C": 0.50}),
        cache_path=tmp_path / "equivalent_smiles.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "equivalent_smiles_report.csv",
    )

    ethanol_rows = result.rows[result.rows["canonical_smiles"] == "CCO"]
    assert len(ethanol_rows) == 2
    assert ethanol_rows["group_id"].nunique() == 1
    assert int(result.rows["in_calibration_set"].sum()) == 3
    assert result.n_calibration_points == 2


def test_source_doi_can_be_blank_with_reference_and_locator(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "blank_doi_with_ref.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row(
                "methane",
                "C",
                0.50,
                "monomer_oxidation_onset",
                True,
                source_doi="",
                source_locator="Table 1",
            ),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
        ],
    )

    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25}),
        cache_path=tmp_path / "blank_doi_with_ref.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "blank_doi_with_ref_report.csv",
    )

    assert result.n_calibration_points == 2
    assert result.rows["in_calibration_set"].all()


def test_blank_source_doi_requires_reference_or_low_confidence(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "blank_doi_without_ref.csv"
    row = _ontology_row(
        "methane",
        "C",
        0.50,
        "monomer_oxidation_onset",
        True,
        source_doi="",
        source_locator="Table 1",
    )
    row["source_doi_or_ref"] = ""
    _write_ontology_benchmark(
        benchmark_path,
        [
            row,
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
        ],
    )

    with pytest.raises(ValueError, match="source_doi"):
        run_benchmark_validation(
            engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25}),
            cache_path=tmp_path / "blank_doi_without_ref.sqlite",
            benchmark_path=benchmark_path,
            report_path=tmp_path / "blank_doi_without_ref_report.csv",
        )


def test_benchmark_candidates_are_not_used_for_default_calibration(tmp_path: Path) -> None:
    result = run_benchmark_validation(
        engine=MockEngine(),
        cache_path=tmp_path / "default_no_candidates.sqlite",
        report_path=tmp_path / "default_no_candidates_report.csv",
    )

    assert result.raw_benchmark_rows == 48
    assert "curation_status" not in result.rows.columns


def test_electropolymerization_growth_setpoint_is_excluded_from_calibration(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "ontology.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
            _ontology_row(
                "propane",
                "CCC",
                1.75,
                "electropolymerization_growth_setpoint",
                False,
                exclusion_reason="growth setpoint is not a monomer oxidation label",
                reported_potential_type="setpoint",
            ),
        ],
    )

    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25, "CCC": 1.75}),
        cache_path=tmp_path / "ontology.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "ontology_report.csv",
    )

    setpoint = result.rows.loc[result.rows["label_type"] == "electropolymerization_growth_setpoint"].iloc[0]
    assert not bool(setpoint["in_calibration_set"])
    assert "disallowed_label_type:electropolymerization_growth_setpoint" in setpoint[
        "calibration_exclusion_reason"
    ]
    assert result.n_calibration_points == 2


def test_calibration_ineligible_rows_require_exclusion_reason(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "missing_reason.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True),
            _ontology_row("ethane", "CC", 1.25, "unknown_or_mixed", False, exclusion_reason=""),
        ],
    )

    with pytest.raises(ValueError, match="exclusion_reason"):
        run_benchmark_validation(
            engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25}),
            cache_path=tmp_path / "missing_reason.sqlite",
            benchmark_path=benchmark_path,
            report_path=tmp_path / "missing_reason_report.csv",
        )


def test_source_metadata_required_unless_low_confidence(tmp_path: Path) -> None:
    missing_locator_path = tmp_path / "missing_locator.csv"
    _write_ontology_benchmark(
        missing_locator_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True, source_locator=""),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
        ],
    )

    with pytest.raises(ValueError, match="source_locator"):
        run_benchmark_validation(
            engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25}),
            cache_path=tmp_path / "missing_locator.sqlite",
            benchmark_path=missing_locator_path,
            report_path=tmp_path / "missing_locator_report.csv",
        )

    low_confidence_path = tmp_path / "low_confidence_missing_source.csv"
    _write_ontology_benchmark(
        low_confidence_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
            _ontology_row(
                "propane",
                "CCC",
                1.75,
                "unknown_or_mixed",
                False,
                exclusion_reason="low-confidence sanity check only",
                source_doi="",
                source_locator="",
                source_confidence="low",
            ),
        ],
    )
    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25, "CCC": 1.75}),
        cache_path=tmp_path / "low_confidence.sqlite",
        benchmark_path=low_confidence_path,
        report_path=tmp_path / "low_confidence_report.csv",
    )
    assert result.n_calibration_points == 2


def test_calibration_point_count_uses_only_eligible_rows(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "eligible_count.csv"
    _write_ontology_benchmark(
        benchmark_path,
        [
            _ontology_row("methane", "C", 0.50, "monomer_oxidation_onset", True),
            _ontology_row("ethane", "CC", 1.25, "monomer_oxidation_peak", True),
            _ontology_row(
                "propane",
                "CCC",
                1.75,
                "unknown_or_mixed",
                False,
                exclusion_reason="not a clean monomer oxidation label",
            ),
        ],
    )

    result = run_benchmark_validation(
        engine=PerfectEoxEngine({"C": 0.50, "CC": 1.25, "CCC": 1.75}),
        cache_path=tmp_path / "eligible_count.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "eligible_count_report.csv",
    )

    assert int(result.rows["in_calibration_set"].sum()) == 2
    assert result.n_calibration_points == 2


def test_validation_reports_accuracy_metrics(tmp_path: Path) -> None:
    result = run_calibration_profile(
        "agagcl_peak_relaxed",
        engine=MockEngine(),
        cache_path=tmp_path / "metrics.sqlite",
        report_path=tmp_path / "metrics_report.csv",
    )

    assert np.isfinite(result.spearman_rho)
    assert -1.0 <= result.spearman_rho <= 1.0
    assert np.isfinite(result.residual_std_after_V)
    assert result.residual_std_after_V >= 0.0

    worst = result.worst_predicted
    assert len(worst) == 5
    assert list(worst.columns) == [
        "monomer_name",
        "chemical_family",
        "calibrated_Eox_V_vs_AgAgCl",
        "exp_Eox_V_vs_AgAgCl",
        "residual_after_V",
    ]
    # Worst rows are sorted by absolute residual, descending.
    abs_residuals = worst["residual_after_V"].abs().to_numpy()
    assert np.all(np.diff(abs_residuals) <= 1e-9)

    assert result.family_mae
    assert all({"mae_V", "n"} <= set(stats) for stats in result.family_mae.values())
    assert sum(stats["n"] for stats in result.family_mae.values()) == result.n_calibration_points

    written = pd.read_csv(result.report_path)
    assert "chemical_family" in written.columns


def test_perfect_predictor_has_unit_spearman_and_zero_residual_std(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.csv"
    benchmark_path.write_text(
        "\n".join(
            [
                "monomer_name,monomer_smiles,solvent_name,electrolyte,exp_Eox_V_vs_AgAgCl,source_doi_or_ref,notes",
                "methane,C,acetonitrile,TBAPF6,0.50,synthetic,perfect",
                "ethane,CC,acetonitrile,TBAPF6,1.25,synthetic,perfect",
                "propane,CCC,acetonitrile,TBAPF6,1.75,synthetic,perfect",
                "butane,CCCC,acetonitrile,TBAPF6,2.10,synthetic,perfect",
            ]
        ),
        encoding="utf-8",
    )
    engine = PerfectEoxEngine({"C": 0.50, "CC": 1.25, "CCC": 1.75, "CCCC": 2.10})

    result = run_benchmark_validation(
        engine=engine,
        cache_path=tmp_path / "perfect_metrics.sqlite",
        benchmark_path=benchmark_path,
        report_path=tmp_path / "perfect_metrics_report.csv",
    )

    assert result.spearman_rho == pytest.approx(1.0)
    assert result.residual_std_after_V == pytest.approx(0.0, abs=1e-9)


def test_profile_comparison_csv_includes_new_metric_columns(tmp_path: Path) -> None:
    comparison = run_all_calibration_profiles(
        engine=MockEngine(),
        cache_path=tmp_path / "compare.sqlite",
        report_path=tmp_path / "compare_report.csv",
        comparison_path=tmp_path / "compare.csv",
    )

    assert "spearman_rho" in comparison.columns
    assert "residual_std_after_V" in comparison.columns
    fitted = comparison[comparison["status"] == "fit"]
    assert fitted["spearman_rho"].notna().all()


class PerfectEoxEngine(Engine):
    def __init__(self, potential_by_smiles: dict[str, float]) -> None:
        self.potential_by_smiles = potential_by_smiles

    def run(self, req: CalcRequest) -> CalcResult:
        if req.quantity != "adiabatic_ip":
            raise ValueError(f"Unexpected quantity in synthetic test: {req.quantity}")
        potential = self.potential_by_smiles[req.species.canonical_smiles]
        return CalcResult(
            value=potential_vs_AgAgCl_to_ip_eV(potential),
            unit="eV",
            method=req.method,
            raw={"engine": "PerfectEoxEngine"},
        )


ONTOLOGY_COLUMNS = [
    "monomer_name",
    "monomer_smiles",
    "solvent_name",
    "electrolyte",
    "native_potential_V",
    "native_reference",
    "potential_type",
    "conversion_to_AgAgCl_V",
    "conversion_source",
    "exp_Eox_V_vs_AgAgCl",
    "medium",
    "working_electrode",
    "scan_rate_mV_s",
    "source_doi_or_ref",
    "source_citation",
    "reliability_tier",
    "notes",
    "label_type",
    "calibration_eligible",
    "exclusion_reason",
    "reported_potential_type",
    "reported_reference_electrode",
    "converted_reference_electrode",
    "conversion_method",
    "source_doi",
    "source_locator",
    "source_confidence",
    "medium_class",
]


def _write_ontology_benchmark(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame(rows, columns=ONTOLOGY_COLUMNS).to_csv(path, index=False)


def _ontology_row(
    monomer_name: str,
    monomer_smiles: str,
    exp_eox: float,
    label_type: str,
    calibration_eligible: bool,
    *,
    exclusion_reason: str = "",
    reported_potential_type: str = "Eonset",
    source_doi: str = "10.0000/synthetic",
    source_locator: str = "Table S1",
    source_confidence: str = "medium",
) -> dict[str, object]:
    return {
        "monomer_name": monomer_name,
        "monomer_smiles": monomer_smiles,
        "solvent_name": "acetonitrile",
        "electrolyte": "synthetic",
        "native_potential_V": exp_eox,
        "native_reference": "Ag/AgCl",
        "potential_type": "onset",
        "conversion_to_AgAgCl_V": 0.0,
        "conversion_source": "synthetic no-op conversion",
        "exp_Eox_V_vs_AgAgCl": exp_eox,
        "medium": "nonaqueous",
        "working_electrode": "",
        "scan_rate_mV_s": "",
        "source_doi_or_ref": source_doi or "synthetic",
        "source_citation": "Synthetic ontology test",
        "reliability_tier": "B",
        "notes": "Synthetic ontology test row",
        "label_type": label_type,
        "calibration_eligible": str(calibration_eligible).lower(),
        "exclusion_reason": exclusion_reason,
        "reported_potential_type": reported_potential_type,
        "reported_reference_electrode": "Ag/AgCl",
        "converted_reference_electrode": "Ag/AgCl",
        "conversion_method": "native value already on Ag/AgCl scale",
        "source_doi": source_doi,
        "source_locator": source_locator,
        "source_confidence": source_confidence,
        "medium_class": "nonaqueous",
    }

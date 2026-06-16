from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.properties.redox import potential_vs_AgAgCl_to_ip_eV
from eps.validation import run_benchmark_validation


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
    assert int(selected.sum()) == 8
    assert result.n_calibration_points == 5
    assert "calibration_exclusion_reason" in result.rows.columns


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

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

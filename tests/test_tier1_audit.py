from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from eps.engines import MockEngine
from eps.workflow.tier1 import (
    _apply_linear_calibration,
    annotate_tier1_filters,
    run_tier1,
)


def test_tier1_audit_exposes_raw_calibrated_filter_and_alias_columns(tmp_path: Path) -> None:
    result = run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / "tier1.sqlite",
        output_path=tmp_path / "tier1_ranked.csv",
    )

    required = {
        "monomer_Eox_raw_V_vs_AgAgCl",
        "monomer_Eox_calibrated_V_vs_AgAgCl",
        "monomer_Eox_filter_V_vs_AgAgCl",
        "monomer_Eox_V",
    }
    assert required.issubset(result.all_triads.columns)
    assert (result.all_triads["monomer_Eox_V"] == result.all_triads["monomer_Eox_filter_V_vs_AgAgCl"]).all()


def test_tier1_monomer_eox_calibration_formula_is_applied() -> None:
    raw = 6.456936
    calibrated = _apply_linear_calibration(raw, {"enabled": True, "slope": 0.623, "intercept": -2.872})

    assert calibrated == pytest.approx(0.623 * 6.456936 - 2.872)


def test_window_margin_uses_filter_eox_not_raw_eox(tmp_path: Path) -> None:
    result = run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / "tier1.sqlite",
        output_path=tmp_path / "tier1_ranked.csv",
    )

    row = result.all_triads.iloc[0]
    assert row["window_margin_V"] == pytest.approx(
        row["solvent_anodic_limit_V"] - row["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    assert row["monomer_Eox_filter_V_vs_AgAgCl"] != pytest.approx(row["monomer_Eox_raw_V_vs_AgAgCl"])


def test_failed_filter_reasons_include_all_failed_hard_filters() -> None:
    triads = pd.DataFrame(
        [
            {
                "window_margin_V": -0.1,
                "anion_stability_margin_V": 1.0,
                "solvation_dG_kcal_mol": 2.0,
            }
        ]
    )
    config = {
        "filters": {
            "min_window_margin_V": 0.3,
            "min_anion_stability_margin_V": 0.2,
            "max_solvation_dG_kcal_mol": -3.0,
        }
    }

    annotated = annotate_tier1_filters(triads, config)

    assert annotated.loc[0, "failed_filter_reasons"] == "window_margin;solvation"


def test_zero_survivor_behavior_writes_full_audit_with_reasons(tmp_path: Path) -> None:
    ranked_path = tmp_path / "tier1_ranked.csv"
    all_path = tmp_path / "tier1_all.csv"
    config_path = tmp_path / "tier1.yaml"
    config_path.write_text(
        "\n".join(
            [
                "filters:",
                "  min_window_margin_V: 999.0",
                "  min_anion_stability_margin_V: 999.0",
                "  max_solvation_dG_kcal_mol: -999.0",
                "calibration:",
                "  monomer_eox:",
                "    enabled: true",
                "    scope: monomer_only",
                "    source: test",
                "    slope: 0.623",
                "    intercept: -2.872",
            ]
        ),
        encoding="utf-8",
    )

    result = run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / "tier1.sqlite",
        output_path=ranked_path,
        all_output_path=all_path,
        tier1_config_path=config_path,
    )

    ranked = pd.read_csv(ranked_path)
    audit = pd.read_csv(all_path)
    assert result.surviving_triads == 0
    assert ranked.empty
    assert len(audit) == result.total_triads
    assert len(audit) == len(result.all_triads)
    assert audit["failed_filter_reasons"].ne("").all()

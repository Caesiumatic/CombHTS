from __future__ import annotations

import pandas as pd
import pytest

from eps.engines import MockEngine
from eps.properties.solvent_windows import (
    apply_condition_aware_solvent_windows,
    load_solvent_window_measurements,
)
from eps.workflow.tier1 import run_tier1


@pytest.fixture(scope="module")
def mock_harvest(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("conditioned-window-harvest")
    return run_tier1(
        engine=MockEngine(),
        cache_path=root / "cache.sqlite",
        output_path=root / "ranked.csv",
        all_output_path=root / "all.csv",
    )


def _base_triads() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "solvent_name": "acetonitrile",
                "salt": "TBABF4",
                "solvent_anodic_limit_V": 3.9,
                "solvent_anodic_limit_csv_V": 3.3,
                "solvent_anodic_limit_calibrated_V": 3.9,
                "solvent_anodic_limit_source": "computed",
                "solvent_cathodic_limit_V": -2.7,
            },
            {
                "solvent_name": "acetonitrile",
                "salt": "TBAPF6",
                "solvent_anodic_limit_V": 3.9,
                "solvent_anodic_limit_csv_V": 3.3,
                "solvent_anodic_limit_calibrated_V": 3.9,
                "solvent_anodic_limit_source": "computed",
                "solvent_cathodic_limit_V": -2.7,
            },
            {
                "solvent_name": "THF",
                "salt": "TBAPF6",
                "solvent_anodic_limit_V": 3.4,
                "solvent_anodic_limit_csv_V": 2.9,
                "solvent_anodic_limit_calibrated_V": 3.4,
                "solvent_anodic_limit_source": "computed",
                "solvent_cathodic_limit_V": -2.4,
            },
        ]
    )


def test_exact_salt_measurement_precedes_solvent_only_conservative_value() -> None:
    selected = apply_condition_aware_solvent_windows(
        _base_triads(), load_solvent_window_measurements()
    )
    exact = selected.iloc[0]
    generic = selected.iloc[1]

    assert exact["solvent_anodic_limit_V"] == pytest.approx(3.245)
    assert exact["solvent_window_condition_match"] == "exact_salt_conservative"
    # No TBAPF6-specific MeCN row: take the lowest measured MeCN formulation (LiClO4).
    assert generic["solvent_anodic_limit_V"] == pytest.approx(2.445)
    assert generic["solvent_window_condition_match"] == "solvent_only_conservative"


def test_no_measurement_uses_conservative_minimum_of_csv_and_computed() -> None:
    selected = apply_condition_aware_solvent_windows(
        _base_triads(), load_solvent_window_measurements()
    )
    thf = selected.iloc[2]
    assert thf["solvent_anodic_limit_V"] == pytest.approx(2.9)
    assert thf["solvent_anodic_limit_source"] == "fallback_conservative_min_csv_computed"
    assert thf["solvent_anodic_limit_prior_V"] == pytest.approx(3.4)


def test_wide_generic_measurement_cannot_relax_the_conservative_prior() -> None:
    triad = pd.DataFrame(
        [
            {
                "solvent_name": "GBL",
                "salt": "TBAPF6",
                "solvent_anodic_limit_V": 2.69,
                "solvent_anodic_limit_csv_V": 3.0,
                "solvent_anodic_limit_calibrated_V": 2.69,
                "solvent_anodic_limit_source": "computed",
                "solvent_cathodic_limit_V": -2.5,
            }
        ]
    )
    selected = apply_condition_aware_solvent_windows(
        triad, load_solvent_window_measurements()
    ).iloc[0]
    assert selected["solvent_window_measurement_anodic_V"] == pytest.approx(5.2)
    assert selected["solvent_window_conservative_cap_V"] == pytest.approx(2.69)
    assert bool(selected["solvent_window_cap_applied"])
    assert selected["solvent_anodic_limit_V"] == pytest.approx(2.69)
    assert selected["solvent_anodic_limit_source"] == (
        "measured_conditioned_capped_by_fallback"
    )


@pytest.mark.parametrize(
    ("solvent", "salt", "measured_limit"),
    [
        ("water", "KCl", 1.145),
        ("acetonitrile", "TBABF4", 3.245),
        ("DCM", "TBAClO4", 1.845),
        ("DMF", "TBAClO4", 1.745),
        ("DMSO", "TBAPF6", 1.045),
    ],
)
def test_mandatory_control_formulations_are_measured_and_conservative(
    mock_harvest, solvent: str, salt: str, measured_limit: float
) -> None:
    rows = mock_harvest.all_triads[
        (mock_harvest.all_triads["solvent_name"] == solvent)
        & (mock_harvest.all_triads["salt"] == salt)
    ]
    assert not rows.empty
    expected = rows[
        ["solvent_anodic_limit_csv_V", "solvent_anodic_limit_calibrated_V"]
    ].min(axis=1).clip(upper=measured_limit)
    assert set(rows["solvent_window_measurement_anodic_V"]) == {measured_limit}
    assert rows["solvent_anodic_limit_V"].to_numpy() == pytest.approx(expected.to_numpy())
    assert rows["window_margin_V"].to_numpy() == pytest.approx(
        expected.to_numpy() - rows["monomer_Eox_filter_V_vs_AgAgCl"].to_numpy()
    )


def test_water_gate_never_exceeds_measured_or_prior_evidence(mock_harvest) -> None:
    water = mock_harvest.all_triads[
        (mock_harvest.all_triads["solvent_name"] == "water")
        & (mock_harvest.all_triads["salt"] == "KCl")
    ]
    expected = water[
        ["solvent_anodic_limit_csv_V", "solvent_anodic_limit_calibrated_V"]
    ].min(axis=1).clip(upper=1.145)
    assert water["solvent_anodic_limit_V"].to_numpy() == pytest.approx(expected.to_numpy())
    assert set(water["solvent_window_measurement_anodic_V"]) == {1.145}
    assert (water["solvent_anodic_limit_V"] <= water["solvent_anodic_limit_prior_V"]).all()
    assert (water["solvent_anodic_limit_V"] <= water["solvent_anodic_limit_csv_V"]).all()

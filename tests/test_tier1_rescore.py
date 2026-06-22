from __future__ import annotations

from pathlib import Path

import pytest

from eps.engines import MockEngine
from eps.workflow.tier1 import run_tier1
from eps.workflow.tier1_rescore import rescore_tier1_harvest


@pytest.fixture(scope="module")
def source_harvest(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("rescore-source")
    result = run_tier1(
        engine=MockEngine(),
        cache_path=root / "cache.sqlite",
        output_path=root / "ranked.csv",
        all_output_path=root / "all.csv",
    )
    return result.all_output_path


def test_rescore_uses_measured_water_window_without_an_engine(
    source_harvest: Path, tmp_path: Path
) -> None:
    result = rescore_tier1_harvest(
        source_harvest,
        output_path=tmp_path / "ranked.csv",
        all_output_path=tmp_path / "all.csv",
    )
    water = result.all_triads[
        (result.all_triads["solvent_name"] == "water")
        & (result.all_triads["salt"] == "KCl")
    ]
    assert not water.empty
    expected = water[
        ["solvent_anodic_limit_csv_V", "solvent_anodic_limit_calibrated_V"]
    ].min(axis=1).clip(upper=1.145)
    assert water["solvent_anodic_limit_V"].to_numpy() == pytest.approx(expected.to_numpy())
    assert set(water["solvent_window_measurement_anodic_V"]) == {1.145}
    assert result.output_path.exists()
    assert result.all_output_path.exists()
    assert not any(column.endswith("_x") or column.endswith("_y") for column in result.all_triads)


def test_rescore_is_idempotent(source_harvest: Path, tmp_path: Path) -> None:
    first = rescore_tier1_harvest(
        source_harvest,
        output_path=tmp_path / "first_ranked.csv",
        all_output_path=tmp_path / "first_all.csv",
    )
    second = rescore_tier1_harvest(
        first.all_output_path,
        output_path=tmp_path / "second_ranked.csv",
        all_output_path=tmp_path / "second_all.csv",
    )
    assert second.surviving_triads == first.surviving_triads
    assert second.all_triads["solvent_anodic_limit_V"].to_numpy() == pytest.approx(
        first.all_triads["solvent_anodic_limit_V"].to_numpy()
    )

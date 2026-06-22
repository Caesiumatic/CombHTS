from __future__ import annotations

from pathlib import Path

import pandas as pd
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


def test_rescore_hydrates_roles_and_keeps_full_salt_audit(source_harvest: Path, tmp_path: Path) -> None:
    # Simulate the pre-role harvest that the human will re-score on Lop.
    legacy = pd.read_csv(source_harvest, low_memory=False).drop(
        columns=[
            "electrolyte_role",
            "supporting_electrolyte_ok",
            "electrolyte_role_justification",
        ]
    )
    legacy_path = tmp_path / "legacy_all.csv"
    legacy.to_csv(legacy_path, index=False)

    result = rescore_tier1_harvest(
        legacy_path,
        output_path=tmp_path / "ranked.csv",
        all_output_path=tmp_path / "all.csv",
    )
    audit = pd.read_csv(result.all_output_path, low_memory=False)

    assert len(audit) == len(legacy)
    for salt, role in (("AgClO4", "reference_only"), ("HClO4", "acid")):
        rows = audit[audit["salt"] == salt]
        assert not rows.empty
        assert rows["electrolyte_role"].eq(role).all()
        assert (~rows["pass_supporting_electrolyte_role"].astype(bool)).all()
        assert rows["supporting_electrolyte_reason"].eq(
            f"salt not a supporting electrolyte: {role}"
        ).all()
        assert (~rows["passes_all_tier1_filters"].astype(bool)).all()

    supporting = audit[audit["salt"] == "TBABF4"]
    assert supporting["pass_supporting_electrolyte_role"].astype(bool).all()
    assert supporting["supporting_electrolyte_calc_status"].eq("ok").all()

    # Ranked is collapsed, but its tied-salt membership reconciles exactly to every scored audit row.
    assert result.ranked["n_tied"].max() > 1
    assert int(result.ranked["n_tied"].sum()) == result.surviving_triads
    assert result.surviving_triads == int(audit["composite_score"].notna().sum())
    assert len(result.ranked) < result.surviving_triads

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from eps.engines import MockEngine
from eps.validation import run_physical_sanity_checks, write_validation_memo

# Monomer Eox values (acetonitrile) chosen so every directional check passes:
# EDOT<thiophene, 3-hexylthiophene<thiophene, EDOP<pyrrole, EDOS<selenophene, bithiophene<thiophene.
_PASSING_EOX = {
    "thiophene": 1.50,
    "EDOT": 1.00,
    "3-hexylthiophene": 1.20,
    "pyrrole": 1.10,
    "EDOP": 0.70,
    "selenophene": 1.40,
    "EDOS": 1.05,
    "bithiophene": 1.15,
}


def _write_harvest(path: Path, eox_by_monomer: dict[str, float], *, extra_rows=()) -> None:
    rows = [
        {
            "monomer_name": name,
            "solvent_name": "acetonitrile",
            "monomer_Eox_calibrated_V_vs_AgAgCl": value,
        }
        for name, value in eox_by_monomer.items()
    ]
    rows.extend(extra_rows)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_sanity_all_pass(tmp_path: Path) -> None:
    harvest = tmp_path / "harvest.csv"
    _write_harvest(harvest, _PASSING_EOX)

    result = run_physical_sanity_checks(harvest)

    assert result.n_pass == 5
    assert result.n_fail == 0
    assert result.n_skip == 0
    assert result.all_pass


def test_sanity_detects_violation(tmp_path: Path) -> None:
    harvest = tmp_path / "harvest.csv"
    bad = dict(_PASSING_EOX)
    bad["EDOT"] = 2.00  # now EDOT > thiophene -> FAIL
    _write_harvest(harvest, bad)

    result = run_physical_sanity_checks(harvest)

    edot_check = next(c for c in result.checks if c.lower_monomer == "EDOT")
    assert edot_check.status == "FAIL"
    assert result.n_fail == 1
    assert not result.all_pass


def test_sanity_skips_missing_monomers(tmp_path: Path) -> None:
    harvest = tmp_path / "harvest.csv"
    _write_harvest(harvest, {"thiophene": 1.50, "EDOT": 1.00})

    result = run_physical_sanity_checks(harvest)

    edot_check = next(c for c in result.checks if c.lower_monomer == "EDOT")
    pyrrole_check = next(c for c in result.checks if c.reference_monomer == "pyrrole")
    assert edot_check.status == "PASS"
    assert pyrrole_check.status == "SKIP"  # pyrrole/EDOP not in harvest


def test_sanity_compares_within_single_solvent(tmp_path: Path) -> None:
    harvest = tmp_path / "harvest.csv"
    # A DCM row with an absurd EDOT value must not affect the acetonitrile comparison.
    extra = [
        {
            "monomer_name": "EDOT",
            "solvent_name": "DCM",
            "monomer_Eox_calibrated_V_vs_AgAgCl": 9.0,
        }
    ]
    _write_harvest(harvest, _PASSING_EOX, extra_rows=extra)

    result = run_physical_sanity_checks(harvest, solvent_name="acetonitrile")

    assert result.all_pass


def test_memo_written_with_required_sections_and_no_fabricated_gaps(tmp_path: Path) -> None:
    memo_path = write_validation_memo(
        engine=MockEngine(),
        cache_path=tmp_path / "memo.sqlite",
        report_path=tmp_path / "memo_report.csv",
        harvest_path=tmp_path / "missing_harvest.csv",
        memo_dir=tmp_path / "docs",
        memo_date=date(2026, 6, 17),
    )

    assert memo_path.exists()
    text = memo_path.read_text(encoding="utf-8")
    assert "Monomer Eox accuracy by calibration profile" in text
    assert "What we CANNOT validate yet" in text
    assert "Solvent ESW MAE" in text and "not computable yet" in text
    assert "yes/no" in text
    assert "ENGINE = MOCK" in text  # mock banner present
    assert "Spearman" in text


def test_mock_memo_uses_reserved_preview_filename(tmp_path: Path) -> None:
    memo_path = write_validation_memo(
        engine=MockEngine(),
        cache_path=tmp_path / "memo_name.sqlite",
        report_path=tmp_path / "memo_name_report.csv",
        harvest_path=tmp_path / "missing_harvest.csv",
        memo_dir=tmp_path / "docs",
        memo_date=date(2026, 6, 17),
    )

    assert memo_path.name == "validation_memo_MOCK_PREVIEW.md"


def test_memo_includes_sanity_results_when_harvest_present(tmp_path: Path) -> None:
    harvest = tmp_path / "tier1_all_xtb.csv"
    _write_harvest(harvest, _PASSING_EOX)

    memo_path = write_validation_memo(
        engine=MockEngine(),
        cache_path=tmp_path / "memo2.sqlite",
        report_path=tmp_path / "memo2_report.csv",
        harvest_path=harvest,
        memo_dir=tmp_path / "docs",
        memo_date=date(2026, 6, 17),
    )

    text = memo_path.read_text(encoding="utf-8")
    assert "Physical sanity checks" in text
    assert "5 PASS, 0 FAIL, 0 SKIP" in text

"""Scientific-invariant regression tests.

These lock in the SCIENCE against future refactors — they catch the silent-failure class
(scale mismatches, no-op checks, fabricated honesty caveats) rather than mere plumbing. All
use the mock engine + small synthetic data; no real xtb/g16 runs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from eps.analysis import build_shortlist
from eps.analysis.plots import DIAGNOSTIC_LABEL
from eps.analysis.summary import DIAGNOSTIC_NOTE
from eps.chemspace import load_electrolytes, load_monomers, load_solvents
from eps.engines import MockEngine
from eps.properties.redox import (
    ABS_SHE_V,
    AGAGCL_SHIFT_V,
    ip_eV_to_potential_vs_AgAgCl,
    potential_vs_AgAgCl_to_ip_eV,
)
from eps.storage import SQLiteCache
from eps.validation import run_physical_sanity_checks, write_validation_memo
from eps.workflow.tier1 import (
    compute_anion_solvent_table,
    compute_monomer_solvent_table,
    compute_solvent_table,
    load_tier1_config,
)

PINNED_SLOPE = 0.725837
PINNED_INTERCEPT = -3.145372


# --- 1. Redox conversion: pinned constants + monotonic + round-trip -----------------------

def test_redox_conversion_reproduces_pinned_constants_and_is_monotonic() -> None:
    assert ABS_SHE_V == 4.28
    assert AGAGCL_SHIFT_V == -0.197

    # Known input -> known output.
    assert ip_eV_to_potential_vs_AgAgCl(5.0) == pytest.approx(5.0 - 4.28 - 0.197)

    # Strictly increasing in energy.
    values = [ip_eV_to_potential_vs_AgAgCl(x) for x in (4.0, 5.0, 6.0, 7.0)]
    assert all(b > a for a, b in zip(values, values[1:]))

    # Round-trips through the inverse.
    assert potential_vs_AgAgCl_to_ip_eV(ip_eV_to_potential_vs_AgAgCl(6.137)) == pytest.approx(6.137)


# --- 2. Shared oxidation calibration (T11): one transform for all three oxidation axes -----

def test_single_oxidation_calibration_applies_identically_to_all_three_axes(tmp_path: Path) -> None:
    config = load_tier1_config()
    calibration_config = config["calibration"]
    cal = calibration_config["monomer_eox"]
    slope, intercept = float(cal["slope"]), float(cal["intercept"])

    # The pinned single calibration (guards against silent edits to tier1.yaml).
    assert (slope, intercept) == (PINNED_SLOPE, PINNED_INTERCEPT)
    assert bool(cal["enabled"])

    monomers = load_monomers()[:2]
    solvents = load_solvents()[:2]
    electrolytes = load_electrolytes()[:2]
    cache = SQLiteCache(tmp_path / "inv.sqlite")
    engine = MockEngine()

    monomer_table = compute_monomer_solvent_table(
        monomers, solvents, engine, cache, calibration_config=calibration_config
    )
    solvent_table = compute_solvent_table(
        solvents, engine, cache, calibration_config=calibration_config
    )
    anion_table = compute_anion_solvent_table(
        electrolytes, solvents, engine, cache, calibration_config=calibration_config
    )

    m_ok = monomer_table["monomer_Eox_calc_status"] == "ok"
    assert m_ok.any()
    assert np.allclose(
        monomer_table.loc[m_ok, "monomer_Eox_calibrated_V_vs_AgAgCl"],
        slope * monomer_table.loc[m_ok, "monomer_Eox_raw_V_vs_AgAgCl"] + intercept,
    )

    s_ok = solvent_table["solvent_anodic_limit_calc_status"] == "ok"
    assert s_ok.any()
    assert np.allclose(
        solvent_table.loc[s_ok, "solvent_anodic_limit_calibrated_V"],
        slope * solvent_table.loc[s_ok, "solvent_anodic_limit_computed_V"] + intercept,
    )

    a_ok = anion_table["anion_Eox_calc_status"] == "ok"
    assert a_ok.any()
    assert np.allclose(
        anion_table.loc[a_ok, "anion_Eox_calibrated_V_vs_AgAgCl"],
        slope * anion_table.loc[a_ok, "anion_Eox_raw_V_vs_AgAgCl"] + intercept,
    )


# --- 3 & 4. Sanity can FAIL (not a no-op) and directional ordering holds in a clean harvest -

def _write_harvest(path: Path, eox_by_monomer: dict[str, float]) -> Path:
    rows = [
        {
            "monomer_name": name,
            "solvent_name": "acetonitrile",
            "monomer_Eox_calibrated_V_vs_AgAgCl": value,
        }
        for name, value in eox_by_monomer.items()
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


_CLEAN_ORDERING = {
    "thiophene": 1.50,
    "EDOT": 1.00,
    "3-hexylthiophene": 1.20,
    "pyrrole": 1.10,
    "EDOP": 0.70,
    "selenophene": 1.40,
    "EDOS": 1.05,
    "bithiophene": 1.15,
}


def test_sanity_check_can_fail_is_not_a_no_op(tmp_path: Path) -> None:
    broken = dict(_CLEAN_ORDERING)
    broken["EDOT"] = 1.90  # deliberately ABOVE thiophene (1.50)
    harvest = _write_harvest(tmp_path / "broken.csv", broken)

    result = run_physical_sanity_checks(harvest)
    edot = next(c for c in result.checks if c.lower_monomer == "EDOT" and c.reference_monomer == "thiophene")

    assert edot.status == "FAIL"
    assert result.n_fail >= 1


def test_directional_ordering_holds_in_clean_mock_harvest(tmp_path: Path) -> None:
    harvest = _write_harvest(tmp_path / "clean.csv", _CLEAN_ORDERING)
    result = run_physical_sanity_checks(harvest)

    by_pair = {(c.lower_monomer, c.reference_monomer): c.status for c in result.checks}
    assert by_pair[("EDOT", "thiophene")] == "PASS"
    assert by_pair[("EDOP", "pyrrole")] == "PASS"
    assert by_pair[("EDOS", "selenophene")] == "PASS"
    assert by_pair[("bithiophene", "thiophene")] == "PASS"
    assert result.n_fail == 0


# --- 5. Honesty invariants: memo never fabricates the two §7 gaps; analyze labels diagnostics -

def test_memo_marks_feasibility_gap_not_computable_and_solvent_esw_computable(tmp_path: Path) -> None:
    memo_path = write_validation_memo(
        engine=MockEngine(),
        cache_path=tmp_path / "memo.sqlite",
        report_path=tmp_path / "memo_report.csv",
        harvest_path=tmp_path / "missing.csv",
        memo_dir=tmp_path / "docs",
    )
    text = memo_path.read_text(encoding="utf-8")

    assert "Solvent ESW MAE" in text
    assert "yes/no" in text
    # The solvent-ESW gap is now closed (seeded benchmark -> a real, never-fabricated number),
    # while the qualitative yes/no feasibility metric remains explicitly not computable.
    assert "NOW COMPUTABLE" in text
    assert "not computable yet" in text


def test_analyze_honesty_labels_are_screening_grade_not_validated() -> None:
    # The two axes are now REAL physics but uncalibrated/proton-referenced; the labels must say
    # screening-grade and NOT claim validation, while still flagging the diagnostic status.
    assert "SCREENING-GRADE" in DIAGNOSTIC_LABEL
    assert "SCREENING-GRADE" in DIAGNOSTIC_NOTE
    assert "NOT a validated experimental recommendation" in DIAGNOSTIC_NOTE
    assert "uncalibrated" in DIAGNOSTIC_LABEL.lower()

    frame = pd.DataFrame(
        {
            "monomer_canonical_smiles": ["c1ccsc1", "C1COc2ccsc2O1"],
            "composite_score": [0.9, 0.5],
            "pareto_front": [True, True],
            "window_margin_V": [1.0, 0.8],
            "solubility_score": [5.0, 4.0],
        }
    )
    shortlist = build_shortlist(frame)
    assert (shortlist["diagnostic_note"].str.contains("SCREENING-GRADE")).all()

"""Tests for the §7 qualitative yes/no feasibility DIAGNOSTIC (eps.validation.feasibility).

The honesty contract: the metric must NEVER return a single raw-accuracy pass/fail, must report the
small-negative-count caveat verbatim, and must degrade cleanly (no harvest / zero matches) without
fabricating a number.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from rdkit import Chem

from eps.validation.feasibility import (
    FEASIBILITY_STATUS_NOTE,
    LABEL_COLUMNS,
    FeasibilityResult,
    compute_feasibility_metric,
    format_feasibility_report,
    load_polymerizability_labels,
)


def _canon(smiles: str) -> str:
    return Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def _label(monomer_smiles: str, outcome: str, *, solvent="MeCN", electrolyte="TBAPF6",
           medium_class="baseline_MeCN_TBA", reference_electrode="SCE", flags="",
           negative_type="NA", name="m") -> dict:
    row = {col: "" for col in LABEL_COLUMNS}
    row.update(
        monomer_name=name, monomer_smiles=monomer_smiles, solvent=solvent, electrolyte=electrolyte,
        electrode="Pt", outcome=outcome, negative_type=negative_type, experimental_basis="basis",
        reference_electrode=reference_electrode, reliability_tier="A", medium_class=medium_class,
        flags=flags,
    )
    return row


def _labels_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=list(LABEL_COLUMNS))


def _harvest(triads: list[tuple[str, str, str, bool]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "monomer_canonical_smiles": smi,
                "solvent_name": solv,
                "salt": salt,
                "passes_all_tier1_filters": survivor,
            }
            for smi, solv, salt, survivor in triads
        ]
    )


THIO = _canon("c1ccsc1")
PYR = _canon("c1cc[nH]c1")
ANI = _canon("Nc1ccccc1")


def test_no_harvest_reports_cleanly_without_fabricating() -> None:
    result = compute_feasibility_metric(harvest_path=None)
    assert result.computable is False
    assert result.message == "no harvest to score against"
    # The label set + caveat are still reported (never a number invented from nothing).
    assert result.balanced_accuracy is None


def test_status_note_carries_negative_count_caveat_verbatim() -> None:
    result = compute_feasibility_metric(harvest_path=None)
    assert result.status_note == FEASIBILITY_STATUS_NOTE
    note = result.status_note
    assert "PRELIMINARY" in note
    assert "18 YES / 16 NO" in note
    assert "only 16 negatives" in note
    assert "~53%" in note
    assert "balanced accuracy + confusion matrix" in note
    # The >85% target is explicitly NOT claimed.
    assert "NOT claimed" in note


def test_result_never_exposes_a_single_raw_accuracy_or_pass_flag() -> None:
    # The dataclass must not carry a raw-accuracy figure or a >85% pass/fail boolean.
    for forbidden in ("accuracy", "raw_accuracy", "passed", "pass", "exceeds_85", "meets_target"):
        assert not hasattr(FeasibilityResult, forbidden)
        assert not hasattr(
            FeasibilityResult(computable=False, message=""), forbidden
        )


def test_zero_matched_is_not_computable_message() -> None:
    labels = _labels_frame([_label(THIO, "YES")])
    # Harvest has the monomer but a different salt -> no triad match.
    harvest = _harvest([(THIO, "acetonitrile", "TBABF4", True)])
    result = compute_feasibility_metric(labels=labels, harvest=harvest)
    assert result.computable is False
    assert result.message == "0 matched — metric not computable on current library"
    assert result.n_matched == 0
    assert result.balanced_accuracy is None


def test_balanced_accuracy_is_mean_of_per_class_recall_not_raw_accuracy() -> None:
    # 2 YES + 1 NO; the screen predicts YES (survivor) for ALL three.
    labels = _labels_frame(
        [
            _label(THIO, "YES", name="a"),
            _label(PYR, "YES", name="b"),
            _label(ANI, "NO", name="c"),
        ]
    )
    harvest = _harvest(
        [
            (THIO, "acetonitrile", "TBAPF6", True),
            (PYR, "acetonitrile", "TBAPF6", True),
            (ANI, "acetonitrile", "TBAPF6", True),
        ]
    )
    result = compute_feasibility_metric(labels=labels, harvest=harvest)
    assert result.computable is True
    assert (result.tp, result.fn, result.fp, result.tn) == (2, 0, 1, 0)
    # recall_YES = 2/2 = 1.0 ; recall_NO = 0/1 = 0.0 ; BALANCED = 0.5
    assert result.recall_yes == pytest.approx(1.0)
    assert result.recall_no == pytest.approx(0.0)
    assert result.balanced_accuracy == pytest.approx(0.5)
    # The raw accuracy (2/3) must NOT be what we report — balanced differs from raw here.
    raw_accuracy = (result.tp + result.tn) / result.n_matched
    assert raw_accuracy == pytest.approx(2 / 3)
    assert result.balanced_accuracy != pytest.approx(raw_accuracy)
    # The human report says BALANCED, never a bare PASS.
    text = format_feasibility_report(result)
    assert "BALANCED accuracy" in text and "NOT raw accuracy" in text
    assert "PASS" not in text


def test_single_class_matched_blocks_balanced_accuracy() -> None:
    # Only positives match -> the NO class is empty -> balanced accuracy not computable (never faked).
    labels = _labels_frame([_label(THIO, "YES"), _label(PYR, "YES")])
    harvest = _harvest(
        [
            (THIO, "acetonitrile", "TBAPF6", True),
            (PYR, "acetonitrile", "TBAPF6", False),
        ]
    )
    result = compute_feasibility_metric(labels=labels, harvest=harvest)
    assert result.n_matched == 2
    assert result.computable is False
    assert result.balanced_accuracy is None
    assert "balanced accuracy not computable" in result.message


def test_out_of_scope_media_excluded_and_reported() -> None:
    labels = _labels_frame(
        [
            _label(THIO, "YES"),  # in scope, won't match (no harvest triad) but stays in-scope
            _label(ANI, "NO", solvent="H2O", electrolyte="H2SO4", medium_class="aqueous_acid"),
            _label(_canon("c1ccoc1"), "NO", solvent="pure BFEE", electrolyte="-",
                   medium_class="BFEE"),
            _label(THIO, "YES", reference_electrode="Ag pseudo", flags="FLAG: Ag pseudo-ref"),
        ]
    )
    harvest = _harvest([(PYR, "acetonitrile", "TBAPF6", True)])  # nothing matches
    result = compute_feasibility_metric(labels=labels, harvest=harvest)
    assert result.n_out_of_scope == 3
    reasons = result.out_of_scope_breakdown
    assert any("aqueous-acid" in k for k in reasons)
    assert any("BFEE" in k for k in reasons)
    assert any("Ag pseudo-reference" in k for k in reasons)
    assert result.n_in_scope == 1


def test_repo_labels_file_loads_with_expected_schema_and_balance() -> None:
    frame = load_polymerizability_labels()
    assert list(frame.columns) == list(LABEL_COLUMNS)
    assert len(frame) == 34
    assert int((frame["outcome"] == "YES").sum()) == 18
    assert int((frame["outcome"] == "NO").sum()) == 16


def test_specified_electrolyte_matches_by_anion_not_salt_name() -> None:
    # Anion-based matching: a label specifying Et4NBF4 (BF4-) must match a harvest TBABF4 triad
    # (both BF4-) even though the salt NAMES differ; a PF6- harvest must NOT match.
    labels = _labels_frame([_label(THIO, "YES", electrolyte="Et4NBF4 (BF4-)")])
    matched = compute_feasibility_metric(
        labels=labels, harvest=_harvest([(THIO, "acetonitrile", "TBABF4", True)])
    )
    assert matched.n_matched == 1 and matched.tp == 1

    mismatched = compute_feasibility_metric(
        labels=labels, harvest=_harvest([(THIO, "acetonitrile", "TBAPF6", True)])
    )
    assert mismatched.n_matched == 0  # BF4- label vs PF6- harvest -> no anion match


def test_unspecified_electrolyte_matches_on_monomer_plus_solvent() -> None:
    # Generic "TBA salt" -> match on (monomer, solvent): predicted-YES if ANY triad survives.
    labels = _labels_frame([_label(THIO, "YES", electrolyte="TBA salt")])
    any_survives = compute_feasibility_metric(
        labels=labels,
        harvest=_harvest(
            [(THIO, "acetonitrile", "TBAPF6", False), (THIO, "acetonitrile", "TBAClO4", True)]
        ),
    )
    assert any_survives.n_matched == 1 and any_survives.tp == 1

    # In the harvest but NOTHING survives -> predicted-NO (YES label -> false negative).
    none_survive = compute_feasibility_metric(
        labels=labels,
        harvest=_harvest(
            [(THIO, "acetonitrile", "TBAPF6", False), (THIO, "acetonitrile", "TBAClO4", False)]
        ),
    )
    assert none_survive.n_matched == 1 and none_survive.fn == 1

    # monomer+solvent ABSENT from the harvest -> out-of-scope (not matched), reported not dropped.
    absent = compute_feasibility_metric(
        labels=labels, harvest=_harvest([(PYR, "acetonitrile", "TBAPF6", True)])
    )
    assert absent.n_matched == 0
    assert any("monomer+solvent not in" in reason for reason in absent.out_of_scope_breakdown)


def test_real_labels_against_synthetic_harvest_uses_both_match_modes() -> None:
    # End-to-end with the real CSV. The synthetic harvest covers the in-scope library monomers in
    # acetonitrile/water so BOTH specified-anion and unspecified monomer+solvent labels match.
    from eps.chemspace import load_monomers

    lib = {m.name: m.canonical_smiles for m in load_monomers()}
    harvest = _harvest(
        [
            (lib["EDOT"], "acetonitrile", "TBAPF6", True),     # EDOT/MeCN/PF6 (specified) YES
            (lib["EDOT"], "water", "TBAPF6", True),            # EDOT/H2O (unspecified) YES
            (lib["pyrrole"], "acetonitrile", "TBABF4", True),  # pyrrole/Et4NBF4->BF4 (specified) YES
            (lib["N-methylpyrrole"], "acetonitrile", "TBABF4", True),  # N-Me pyrrole BF4 YES
            (lib["3-methoxythiophene"], "acetonitrile", "TBAPF6", True),  # unspecified YES
            (lib["carbazole"], "acetonitrile", "TBAPF6", True),  # unspecified YES
            (lib["EDOS"], "acetonitrile", "TBAClO4", True),    # EDOS/ClO4 (specified) YES
            (lib["EDOP"], "water", "pTSA", True),              # EDOP/water/pTS (specified) YES
            (lib["furan"], "acetonitrile", "TBAPF6", False),   # furan/TBA salt (unspecified) NO
            (lib["aniline"], "acetonitrile", "LiClO4", False),  # aniline/MeCN/ClO4 (specified) NO
            (lib["aniline"], "water", "NaClO4", False),        # aniline/water (unspecified) NO
            (lib["thiophene"], "water", "NaClO4", False),      # thiophene/water (unspecified) NO
        ]
    )
    result = compute_feasibility_metric(harvest=harvest)
    assert result.computable is True
    assert result.n_matched == 12  # up from 3 under the old salt-name matcher
    # 8 YES all predicted YES; 4 NO all predicted NO -> a perfectly-separated synthetic harvest.
    assert (result.tp, result.fn, result.fp, result.tn) == (8, 0, 0, 4)
    assert result.balanced_accuracy == pytest.approx(1.0)
    # Non-library carbazoles under a generic electrolyte are reported out-of-scope, not dropped.
    assert any("monomer+solvent not in" in reason for reason in result.out_of_scope_breakdown)
    text = format_feasibility_report(result)
    assert "coverage: 12 matched" in text
    assert "BALANCED accuracy" in text and "PASS" not in text

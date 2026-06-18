from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from eps.analysis import build_shortlist, compute_summary, run_analyze

_MONOMERS = [
    ("thiophene", "c1ccsc1", "heteroaromatic"),
    ("EDOT", "C1COc2ccsc2O1", "alkylenedioxythiophene"),
    ("pyrrole", "c1cc[nH]c1", "heteroaromatic"),
    ("aniline", "Nc1ccccc1", "aniline"),
]
_SOLVENTS = [("acetonitrile", 37.5), ("DCM", 8.9)]
_SALTS = [("TBAPF6", "hexafluorophosphate"), ("TBABF4", "tetrafluoroborate")]


def _synthetic_harvest(n_per_monomer: int = 4) -> pd.DataFrame:
    """Deterministic synthetic Tier-1 harvest with all scoring columns present."""

    rows = []
    counter = 0
    for m_name, smiles, m_class in _MONOMERS:
        for s_name, eps in _SOLVENTS:
            for salt, salt_class in _SALTS:
                counter += 1
                rows.append(
                    {
                        "monomer_name": m_name,
                        "monomer_class": m_class,
                        "monomer_canonical_smiles": smiles,
                        "solvent_name": s_name,
                        "solvent_eps_r": eps,
                        "salt": salt,
                        "salt_class": salt_class,
                        "monomer_Eox_calibrated_V_vs_AgAgCl": 0.5 + 0.1 * counter,
                        "solvation_dG_kcal_mol": -2.0 - 0.3 * counter,
                        "optical_gap_eV": 1.0 + 0.05 * counter,
                        "dimerization_dG_kcal_mol": -6.0 + 0.4 * counter,
                        "window_margin_V": -0.4 + 0.12 * counter,
                        "anion_stability_margin_V": -0.2 + 0.08 * counter,
                        "solubility_score": 2.0 + 0.3 * counter,
                        "band_gap_deviation_eV": 0.1 * (counter % 5),
                        "composite_score": (counter % 7) / 7.0,
                        "pareto_front": counter % 3 == 0,
                        "passes_all_tier1_filters": counter % 2 == 0,
                        "monomer_Eox_calc_status": "ok",
                        "solvation_calc_status": "ok",
                        "anion_Eox_calc_status": "failed" if counter == 3 else "ok",
                        "optical_gap_calc_status": "ok",
                        "dimerization_calc_status": "ok",
                    }
                )
    return pd.DataFrame(rows).head(len(_MONOMERS) * len(_SOLVENTS) * len(_SALTS))


def _write_harvest(path: Path, frame: pd.DataFrame) -> Path:
    frame.to_csv(path, index=False)
    return path


def test_analyze_writes_summary_and_shortlist_with_correct_counts(tmp_path: Path) -> None:
    frame = _synthetic_harvest()
    harvest = _write_harvest(tmp_path / "harvest.csv", frame)

    result = run_analyze(harvest, tmp_path / "analysis")

    assert result.summary_path.exists()
    assert result.summary_path.name == "summary.csv"
    assert result.total_triads == len(frame)
    assert result.surviving_triads == int(frame["passes_all_tier1_filters"].sum())

    summary = pd.read_csv(result.summary_path)
    assert set(summary.columns) == {
        "section",
        "key",
        "total_triads",
        "surviving_triads",
        "retention_fraction",
        "failure_count",
    }
    assert "overall" in set(summary["section"])
    # The one synthetic anion failure is counted.
    anion_failures = summary.loc[
        (summary["section"] == "failure_count") & (summary["key"] == "anion_Eox"),
        "failure_count",
    ].iloc[0]
    assert int(anion_failures) == 1

    assert result.shortlist_path is not None
    assert result.shortlist_path.exists()


def test_shortlist_carries_diagnostic_note(tmp_path: Path) -> None:
    frame = _synthetic_harvest()
    harvest = _write_harvest(tmp_path / "harvest.csv", frame)

    result = run_analyze(harvest, tmp_path / "analysis")
    text = result.shortlist_path.read_text(encoding="utf-8")

    assert "SCREENING-GRADE" in text
    assert "NOT a validated experimental recommendation" in text
    parsed = pd.read_csv(result.shortlist_path, comment="#")
    assert "diagnostic_note" in parsed.columns
    assert (parsed["pareto_front"]).all()


def test_shortlist_skipped_when_scoring_columns_absent(tmp_path: Path) -> None:
    frame = _synthetic_harvest().drop(columns=["composite_score", "pareto_front"])
    harvest = _write_harvest(tmp_path / "harvest.csv", frame)

    result = run_analyze(harvest, tmp_path / "analysis")

    assert result.shortlist_path is None
    assert any("shortlist.csv SKIPPED" in note for note in result.notes)
    assert build_shortlist(frame) is None


def test_analyze_writes_distribution_and_pareto_pngs(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    frame = _synthetic_harvest()
    harvest = _write_harvest(tmp_path / "harvest.csv", frame)

    result = run_analyze(harvest, tmp_path / "analysis")
    names = {p.name for p in result.figure_paths}

    assert "dist_window_margin_V.png" in names
    assert "dist_anion_stability_margin_V.png" in names
    assert "pareto_window_vs_solubility.png" in names
    for path in result.figure_paths:
        assert path.exists() and path.stat().st_size > 0


def test_analyze_small_n_uses_pca_fallback_without_error(tmp_path: Path) -> None:
    pytest.importorskip("matplotlib")
    pytest.importorskip("sklearn")
    frame = _synthetic_harvest().head(6)  # n < 10 -> PCA(2) fallback path
    harvest = _write_harvest(tmp_path / "harvest.csv", frame)

    result = run_analyze(harvest, tmp_path / "analysis")
    names = {p.name for p in result.figure_paths}

    # Chemical-space map still produced via the PCA fallback (no crash, no skip note).
    assert "chemspace_by_monomer_class.png" in names
    assert not any("Chemical-space map SKIPPED" in note for note in result.notes)


def test_compute_summary_handles_missing_survivor_column(tmp_path: Path) -> None:
    frame = _synthetic_harvest().drop(columns=["passes_all_tier1_filters"])

    summary = compute_summary(frame)

    overall = summary[summary["section"] == "overall"].iloc[0]
    assert int(overall["surviving_triads"]) == 0

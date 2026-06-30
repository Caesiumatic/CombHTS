from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from eps.calibration import LinearCalibration
from eps.engines import CalcRequest, GaussianEngine, MockEngine
from eps.engines.base import CalcResult, Engine
from eps.engines.gaussian import GAUSSIAN_METHOD_LABEL
from eps.workflow.dft_calibration import (
    MOCK_DFT_METHOD,
    MOCK_XTB_METHOD,
    POINTS_COLUMNS,
    compose_xtb_to_agagcl,
    core_monomer_reference_flag,
    run_dft_calibration,
)


class CountingEngine(Engine):
    """Wrap a real engine and count how many times ``run`` is invoked (cache-reuse probe)."""

    def __init__(self, inner: Engine) -> None:
        self.inner = inner
        self.calls = 0

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.inner.run(req)


class FailingDFTEngine(MockEngine):
    """MockEngine that raises for one canonical SMILES to exercise the per-monomer skip path."""

    def __init__(self, fail_smiles: str) -> None:
        self.fail_smiles = fail_smiles

    def run(self, req: CalcRequest) -> CalcResult:
        if req.species.canonical_smiles == self.fail_smiles:
            raise RuntimeError("simulated DFT optimization failure")
        return super().run(req)


def _run(tmp_path: Path, **kwargs):
    return run_dft_calibration(
        cache_path=tmp_path / "cache.sqlite",
        outdir=tmp_path / "out",
        **kwargs,
    )


def test_points_schema_and_dedup_by_canonical_smiles(tmp_path: Path) -> None:
    result = _run(tmp_path)
    points = result.points

    # Exact schema (directive §2e).
    assert list(points.columns) == list(POINTS_COLUMNS)

    # Dedup by canonical SMILES: the benchmark has duplicate rows (thiophene x3 etc.), so the
    # point count must be strictly fewer than the eligible-row count and have unique SMILES.
    bench = pd.read_csv("data/benchmark.csv", keep_default_na=False)
    eligible = bench[bench["calibration_eligible"].astype(str).str.lower().isin(["true", "1", "yes"])]
    assert len(points) == points["canonical_smiles"].nunique()
    assert len(points) < len(eligible)


def test_both_linear_fits_and_artifacts_written(tmp_path: Path) -> None:
    result = _run(tmp_path)

    # Both fits exist (mock data -> >= 2 points).
    assert result.xtb_to_dft is not None
    assert result.dft_to_exp is not None
    # The fits use the documented x/y assignment.
    assert result.xtb_method == MOCK_XTB_METHOD
    assert result.dft_method == MOCK_DFT_METHOD

    assert result.points_path.exists()
    assert result.report_path.exists()
    assert result.json_path.exists()

    report = result.report_path.read_text(encoding="utf-8")
    assert "xTB -> DFT calibration" in report
    assert "DFT -> experiment validation" in report
    assert "Side-by-side" in report
    # The pinned xTB->experiment slope/intercept appear, clearly labeled and unchanged.
    assert "0.730448" in report
    assert "0.092948" in report

    record = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert record["calibration"] == "xtb_to_dft"
    assert record["fit"]["r2"] == pytest.approx(result.xtb_to_dft.r2)
    assert record["n_points"] == result.n_points
    assert "does NOT replace" in record["provenance"]["note"]


def test_fit2_uses_peak_rows_only(tmp_path: Path) -> None:
    from eps.calibration import fit_linear_calibration

    result = _run(tmp_path)
    points = result.points

    # label_type is carried into the points frame.
    assert "label_type" in points.columns
    assert set(points["label_type"].unique()) <= {
        "monomer_oxidation_peak",
        "monomer_oxidation_onset",
    }

    # The peak/onset split accounts for every ok point.
    assert result.n_dft_to_exp_peak_points + result.n_nonpeak_excluded == result.n_points
    assert result.n_dft_to_exp_peak_points >= 2
    assert result.n_nonpeak_excluded >= 1  # the strict v3 benchmark has onset rows to exclude

    # Fit 2 equals a manual fit over PEAK rows only (proves onset rows are excluded).
    ok = points[points["dft_calc_status"] == "ok"]
    peak = ok[ok["label_type"] == "monomer_oxidation_peak"]
    expected = fit_linear_calibration(
        peak["dft_Eox_eV"].to_numpy(float), peak["exp_Eox_V_vs_AgAgCl"].to_numpy(float)
    )
    assert result.dft_to_exp.slope == pytest.approx(expected.slope)
    assert result.dft_to_exp.intercept == pytest.approx(expected.intercept)

    # Fit 1 (xTB->DFT) still uses ALL ok points (peak + onset), NOT just peak.
    all_xtb_dft = fit_linear_calibration(
        ok["xtb_descriptor"].to_numpy(float), ok["dft_Eox_eV"].to_numpy(float)
    )
    assert result.xtb_to_dft.slope == pytest.approx(all_xtb_dft.slope)

    report = result.report_path.read_text(encoding="utf-8")
    assert "PEAK rows only" in report
    assert "onset) monomer(s) were EXCLUDED" in report


def test_core_monomer_reference_flag_fires_above_threshold_silent_below() -> None:
    # Core-monomer residuals well above 0.15 V -> the flag FIRES.
    fired_hi, msg_hi = core_monomer_reference_flag({"thiophene": 0.30, "EDOT": -0.25})
    assert fired_hi is True
    assert "FLAG: core-monomer DFT->exp MAE" in msg_hi
    assert "re-examine the reference-conversion constant" in msg_hi

    # Core-monomer residuals within the reference floor -> SILENT (no flag).
    fired_lo, msg_lo = core_monomer_reference_flag({"thiophene": 0.05, "EDOT": -0.08})
    assert fired_lo is False
    assert "FLAG:" not in msg_lo

    # No core monomers present -> says so, does not fire.
    fired_none, msg_none = core_monomer_reference_flag({"some-exotic-monomer": 0.9})
    assert fired_none is False
    assert "No core monomers" in msg_none


def test_reference_floor_note_in_report(tmp_path: Path) -> None:
    result = _run(tmp_path)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Reference floor + core-monomer check" in report
    assert "Pavlishchuk & Addison 2000" in report
    assert "Do NOT report MAE below ~0.05 V" in report
    # A core-monomer check line is present (thiophene/EDOT/pyrrole are in the benchmark).
    assert "core-monomer DFT->exp MAE" in report or "No core monomers" in report


def test_dft_results_cached_not_recomputed_on_second_call(tmp_path: Path) -> None:
    cache_path = tmp_path / "cache.sqlite"
    outdir = tmp_path / "out"

    dft_engine = CountingEngine(MockEngine())
    first = run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=dft_engine,
        cache_path=cache_path,
        outdir=outdir,
        limit=3,
    )
    assert first.n_points == 3
    assert dft_engine.calls == 3  # one adiabatic_ip per unique monomer

    # Second call, SAME cache: the DFT engine must not be invoked at all (neutral + cation both
    # served from cache; DFT never recomputed when cached).
    dft_engine_2 = CountingEngine(MockEngine())
    second = run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=dft_engine_2,
        cache_path=cache_path,
        outdir=outdir,
        limit=3,
    )
    assert dft_engine_2.calls == 0
    # Same numbers reproduced from cache.
    pd.testing.assert_frame_equal(first.points, second.points)


def test_dft_cache_key_encodes_tier2_config_so_smd_freq_forces_recompute(tmp_path: Path) -> None:
    """THINK T13 regression: editing configs/tier2.yaml must change the DFT cache key.

    The config-derived ``dft_method`` label is what flows into the per-species cache key. With the
    old config-blind wiring both a gas-phase config and an SMD(acetonitrile)+freq config produced
    the SAME static label, so the SMD+freq run silently reused the stale gas-phase cached value
    (no recompute). This asserts the two configs yield DIFFERENT labels AND that the second config
    recomputes against a shared cache. FAILS on the pre-fix code (identical static label).
    """

    from eps.cli import _dft_calibration_engines

    gas_cfg = tmp_path / "tier2_gas.yaml"
    gas_cfg.write_text(
        "method: B3LYP\nbasis: 6-31G(d,p)\nsmd_solvent: null\nuse_freq: false\n", encoding="utf-8"
    )
    smd_cfg = tmp_path / "tier2_smd.yaml"
    smd_cfg.write_text(
        "method: B3LYP\nbasis: 6-31G(d,p)\nsmd_solvent: acetonitrile\nuse_freq: true\n",
        encoding="utf-8",
    )

    # Production wiring (CLI -> run_dft_calibration): index 3 is the dft_method cache label.
    dft_method_gas = _dft_calibration_engines("gaussian", gas_cfg)[3]
    dft_method_smd = _dft_calibration_engines("gaussian", smd_cfg)[3]

    # The config now changes the cache method label (it was a single static constant before).
    assert dft_method_gas != dft_method_smd
    assert dft_method_gas == "b3lyp/6-31g(d,p)/gas/freq:off"
    assert dft_method_smd == "b3lyp/6-31g(d,p)/smd:acetonitrile/freq:on"

    cache_path = tmp_path / "shared.sqlite"

    gas_engine = CountingEngine(MockEngine())
    run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=gas_engine,
        dft_method=dft_method_gas,
        cache_path=cache_path,
        outdir=tmp_path / "out_gas",
        only="thiophene",
    )
    assert gas_engine.calls == 1  # one adiabatic_ip for thiophene under the gas config

    # SAME cache, SMD+freq config: a DIFFERENT key -> the DFT engine MUST be re-invoked
    # (recompute), never served the stale gas-phase value.
    smd_engine = CountingEngine(MockEngine())
    run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=smd_engine,
        dft_method=dft_method_smd,
        cache_path=cache_path,
        outdir=tmp_path / "out_smd",
        only="thiophene",
    )
    assert smd_engine.calls == 1  # recomputed under the new config; did NOT reuse the gas cache


def test_per_monomer_failure_is_skipped_not_crashed(tmp_path: Path) -> None:
    # thiophene is the first eligible row; make its DFT fail.
    failing = FailingDFTEngine(fail_smiles="c1ccsc1")
    result = run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=failing,
        cache_path=tmp_path / "cache.sqlite",
        outdir=tmp_path / "out",
    )

    points = result.points
    failed = points[points["dft_calc_status"] == "failed"]
    assert (failed["canonical_smiles"] == "c1ccsc1").any()
    # The failed monomer carries a reason and is excluded from the fitted point count.
    assert failed["dft_calc_error"].str.contains("dft:").any()
    assert result.n_skipped >= 1
    assert result.n_points == int((points["dft_calc_status"] == "ok").sum())
    # The batch still produced fits from the surviving monomers.
    assert result.xtb_to_dft is not None


def test_only_flag_runs_single_monomer(tmp_path: Path) -> None:
    result = _run(tmp_path, only="thiophene")
    assert len(result.points) == 1
    assert result.points.iloc[0]["monomer_name"] == "thiophene"
    # A single point cannot be fitted; both fits report None rather than crashing.
    assert result.xtb_to_dft is None
    assert result.dft_to_exp is None


def test_xtb_descriptor_matches_existing_calibration_path(tmp_path: Path) -> None:
    """The xtb_descriptor column must equal monomer_eox_vs_AgAgCl on the SAME cache/method,
    proving the new fit reuses the IDENTICAL descriptor as the xTB->experiment calibration."""

    from eps.chemspace import load_solvents
    from eps.properties import monomer_eox_vs_AgAgCl
    from eps.storage import SQLiteCache
    from eps.validation.benchmark import _benchmark_monomer, _load_benchmark

    cache_path = tmp_path / "cache.sqlite"
    result = _run(tmp_path, only="thiophene")

    # Recompute the descriptor independently through the documented path.
    bench = _load_benchmark("data/benchmark.csv")
    row = next(r for r in bench.to_dict(orient="records") if r["monomer_name"] == "thiophene")
    monomer = _benchmark_monomer(row)
    solvents = {s.name: s for s in load_solvents()}
    expected = monomer_eox_vs_AgAgCl(
        monomer, solvents[row["solvent_name"]], MockEngine(), SQLiteCache(cache_path),
        method=MOCK_XTB_METHOD,
    )
    assert result.points.iloc[0]["xtb_descriptor"] == pytest.approx(expected)


def test_compose_xtb_to_agagcl_arithmetic() -> None:
    # Known fit1 (xTB->DFT) and fit2 (DFT->exp peak); the composed map must be their substitution.
    fit1 = LinearCalibration(slope=2.0, intercept=0.5, r2=1.0, mae=0.1)   # dft = 2.0*x + 0.5
    fit2 = LinearCalibration(slope=3.0, intercept=-1.0, r2=1.0, mae=0.2)  # exp = 3.0*dft - 1.0

    composed = compose_xtb_to_agagcl(
        fit1, fit2, n_points_xtb_to_dft=10, n_points_dft_to_exp_peak=7
    )
    assert composed is not None
    # composed_slope = fit2.slope * fit1.slope = 3.0 * 2.0
    assert composed["slope"] == pytest.approx(6.0)
    # composed_intercept = fit2.slope * fit1.intercept + fit2.intercept = 3.0*0.5 + (-1.0)
    assert composed["intercept"] == pytest.approx(0.5)
    # mae_V is the experimental (Fit 2) MAE on the peak set.
    assert composed["mae_V"] == pytest.approx(0.2)
    assert composed["n_points_xtb_to_dft"] == 10
    assert composed["n_points_dft_to_exp_peak"] == 7

    # A spot point composes correctly end-to-end: exp(x) = fit2.apply(fit1.apply(x)).
    x = 1.234
    assert composed["slope"] * x + composed["intercept"] == pytest.approx(
        fit2.apply(fit1.apply(x))
    )

    # Missing either stage fit -> None (never a fabricated calibration).
    assert compose_xtb_to_agagcl(None, fit2, n_points_xtb_to_dft=0, n_points_dft_to_exp_peak=0) is None
    assert compose_xtb_to_agagcl(fit1, None, n_points_xtb_to_dft=0, n_points_dft_to_exp_peak=0) is None


def test_composed_calibration_emitted_to_json_and_report(tmp_path: Path) -> None:
    result = _run(tmp_path)

    # The result carries the composed map = fit2 o fit1.
    composed = result.composed_xtb_to_agagcl
    assert composed is not None
    assert composed["slope"] == pytest.approx(result.dft_to_exp.slope * result.xtb_to_dft.slope)
    assert composed["intercept"] == pytest.approx(
        result.dft_to_exp.slope * result.xtb_to_dft.intercept + result.dft_to_exp.intercept
    )
    assert composed["mae_V"] == pytest.approx(result.dft_to_exp.mae)
    assert composed["n_points_xtb_to_dft"] == result.n_points
    assert composed["n_points_dft_to_exp_peak"] == result.n_dft_to_exp_peak_points

    # JSON carries the exact directive key + fields, and does NOT touch the pinned default.
    record = json.loads(result.json_path.read_text(encoding="utf-8"))
    emitted = record["composed_xtb_to_AgAgCl_V"]
    assert emitted["slope"] == pytest.approx(composed["slope"])
    assert emitted["intercept"] == pytest.approx(composed["intercept"])
    assert emitted["mae_V"] == pytest.approx(composed["mae_V"])
    assert set(emitted) == {
        "slope", "intercept", "mae_V", "n_points_xtb_to_dft", "n_points_dft_to_exp_peak"
    }

    # Report has the clearly-labeled section + the pinned side-by-side + the switch note.
    report = result.report_path.read_text(encoding="utf-8")
    assert "Screen-ready calibration (DFT-anchored, directive §7)" in report
    assert "0.730448" in report and "0.092948" in report  # pinned IPEA-xTB line (relaxed peak), shown unchanged
    assert "replace the tier1.yaml monomer_eox slope/intercept with these composed values" in report

    # tier1.yaml is NEVER written by this workflow.
    assert not (tmp_path / "out" / "tier1.yaml").exists()


@pytest.mark.skipif(shutil.which("g16") is None, reason="g16 not installed")
def test_calibrate_dft_live_g16_single_monomer_smoke(tmp_path: Path) -> None:
    """Live g16 smoke on ONE monomer (skips without g16). Uses the mock xTB descriptor so the
    test exercises the real Gaussian adiabatic_ip path without also requiring xtb."""

    result = run_dft_calibration(
        xtb_engine=MockEngine(),
        dft_engine=GaussianEngine(),
        xtb_method=MOCK_XTB_METHOD,
        dft_method=GAUSSIAN_METHOD_LABEL,
        cache_path=tmp_path / "cache.sqlite",
        outdir=tmp_path / "out",
        only="thiophene",
    )
    assert len(result.points) == 1
    point = result.points.iloc[0]
    assert point["dft_calc_status"] == "ok"
    assert pd.notna(point["dft_Eox_eV"])

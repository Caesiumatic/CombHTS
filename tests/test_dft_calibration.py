from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from eps.engines import CalcRequest, GaussianEngine, MockEngine
from eps.engines.base import CalcResult, Engine
from eps.engines.gaussian import GAUSSIAN_METHOD_LABEL
from eps.workflow.dft_calibration import (
    MOCK_DFT_METHOD,
    MOCK_XTB_METHOD,
    POINTS_COLUMNS,
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
    assert "0.725837" in report
    assert "-3.145372" in report

    record = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert record["calibration"] == "xtb_to_dft"
    assert record["fit"]["r2"] == pytest.approx(result.xtb_to_dft.r2)
    assert record["n_points"] == result.n_points
    assert "does NOT replace" in record["provenance"]["note"]


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

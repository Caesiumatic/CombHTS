from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.validation.memo import write_validation_memo
from eps.validation.solvent_benchmark import (
    SOLVENT_BENCHMARK_COLUMNS,
    compute_solvent_esw_mae,
    load_solvent_benchmark,
)


class CountingEngine(Engine):
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.delegate.run(req)


def test_repo_solvent_benchmark_is_seeded_with_correct_schema() -> None:
    # The benchmark is now seeded with measured Ag/AgCl rows (directive §7). The required
    # SOLVENT_BENCHMARK_COLUMNS are preserved as the leading columns, with one appended
    # boolean column `limit_set_by_electrolyte` that the validation reader tolerates.
    frame = load_solvent_benchmark()
    assert list(frame.columns)[: len(SOLVENT_BENCHMARK_COLUMNS)] == list(SOLVENT_BENCHMARK_COLUMNS)
    assert "limit_set_by_electrolyte" in frame.columns
    assert not frame.empty
    assert set(frame["solvent"]) >= {
        "acetonitrile", "propylene carbonate", "GBL",
        "nitromethane", "benzonitrile", "nitrobenzene",
    }


def test_solvent_esw_mae_not_computable_without_rows(tmp_path: Path) -> None:
    # A HEADER-ONLY benchmark -> not computable AND no engine calls (short-circuits).
    header_only = tmp_path / "header_only.csv"
    pd.DataFrame(columns=list(SOLVENT_BENCHMARK_COLUMNS)).to_csv(header_only, index=False)
    engine = CountingEngine()
    result = compute_solvent_esw_mae(
        engine=engine, cache_path=tmp_path / "c.sqlite", benchmark_path=header_only
    )
    assert result.computable is False
    assert result.n_benchmark_rows == 0
    assert engine.calls == 0
    assert result.anodic_mae_V != result.anodic_mae_V  # NaN, never fabricated


def _write_benchmark(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows, columns=list(SOLVENT_BENCHMARK_COLUMNS)).to_csv(path, index=False)
    return path


def test_solvent_esw_mae_real_number_once_rows_land(tmp_path: Path) -> None:
    bench = _write_benchmark(
        tmp_path / "sb.csv",
        [
            {"solvent": "acetonitrile", "smiles": "CC#N", "exp_anodic_V_vs_AgAgCl": 2.4,
             "exp_cathodic_V_vs_AgAgCl": -2.5, "reference": "r", "electrolyte": "e",
             "electrode": "Pt", "source": "s", "tier": "A"},
            {"solvent": "water", "smiles": "O", "exp_anodic_V_vs_AgAgCl": 1.2,
             "exp_cathodic_V_vs_AgAgCl": -0.9, "reference": "r", "electrolyte": "e",
             "electrode": "Pt", "source": "s", "tier": "A"},
        ],
    )
    result = compute_solvent_esw_mae(
        engine=MockEngine(), cache_path=tmp_path / "c.sqlite", benchmark_path=bench
    )
    assert result.computable is True
    assert result.n_matched == 2
    assert result.anodic_mae_V >= 0
    assert result.cathodic_mae_V >= 0
    # The MAE is the mean absolute deviation over the matched solvents.
    assert len(result.per_solvent) == 2


def test_memo_marks_solvent_esw_computable_with_seeded_benchmark(tmp_path: Path) -> None:
    # With the seeded repo benchmark, the memo now reports the solvent-ESW MAE as COMPUTABLE
    # (a real number, never fabricated), while the qualitative yes/no feasibility gap remains
    # not computable.
    memo_path = write_validation_memo(
        engine=MockEngine(),
        cache_path=tmp_path / "memo.sqlite",
        report_path=tmp_path / "rep.csv",
        harvest_path=tmp_path / "missing.csv",
        memo_dir=tmp_path / "docs",
    )
    text = memo_path.read_text(encoding="utf-8")
    assert "Solvent ESW MAE" in text
    assert "NOW COMPUTABLE" in text
    # The remaining §7 gap (yes/no feasibility) is still explicitly not computable.
    assert "yes/no" in text
    assert "not computable yet" in text

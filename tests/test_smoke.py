from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.chemspace import load_electrolytes, load_monomers, load_solvents
from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.workflow.tier1 import run_tier1


class CountingEngine(Engine):
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.delegate.run(req)


def test_tier1_end_to_end_uses_cache_on_second_run(tmp_path: Path) -> None:
    cache_path = tmp_path / "tier1.sqlite"
    output_path = tmp_path / "tier1_ranked.csv"

    first_engine = CountingEngine()
    first = run_tier1(engine=first_engine, cache_path=cache_path, output_path=output_path)

    # The screen must enumerate the FULL monomer x solvent x electrolyte cross product of whatever
    # the (now-expanded) library holds, and must never shrink below the validated 15 x 11 x 10 seed.
    expected_triads = len(load_monomers()) * len(load_solvents()) * len(load_electrolytes())
    assert output_path.exists()
    assert first.total_triads == expected_triads
    assert first.total_triads >= 15 * 11 * 10
    assert first.surviving_triads > 0
    assert first_engine.calls > 0

    ranked = pd.read_csv(output_path)
    assert not ranked.empty
    assert ranked["composite_score"].between(0, 1).all()

    second_engine = CountingEngine()
    second = run_tier1(engine=second_engine, cache_path=cache_path, output_path=output_path)

    assert second.surviving_triads == first.surviving_triads
    assert second_engine.calls < first_engine.calls
    assert second_engine.calls == 0

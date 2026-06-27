"""Regression tests for the SQLite per-species cache, focused on the NaN-value path.

A failed real-xTB spin_density parse returns value=NaN with the per-atom data only in
raw['atomic_spin_density']. SQLite stores IEEE NaN as NULL, which previously violated the
results.value NOT NULL constraint (IntegrityError) and crashed the secondary-descriptor pass.
cached_run must instead return the result without caching a non-finite scalar.
"""
from __future__ import annotations

import math
from pathlib import Path

from eps.engines.base import CalcRequest, CalcResult, Engine, SpeciesSpec
from eps.storage.cache import SQLiteCache, cached_run


class _CountingEngine(Engine):
    def __init__(self, result: CalcResult) -> None:
        self._result = result
        self.calls = 0

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self._result


def _req(quantity: str) -> CalcRequest:
    return CalcRequest(
        species=SpeciesSpec("c1ccsc1", charge=1, multiplicity=2),
        method="gfn2-xtb",
        solvent_eps_r=None,
        quantity=quantity,
    )


def test_nan_value_is_returned_but_not_cached(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "nan.sqlite")
    nan_spin = CalcResult(
        value=float("nan"),
        unit="fraction",
        method="gfn2-xtb",
        raw={"atomic_spin_density": []},
    )
    engine = _CountingEngine(nan_spin)

    # Must not raise sqlite3.IntegrityError (NaN -> NULL on a NOT NULL column).
    result = cached_run(cache, engine, _req("spin_density"), solvent_name=None)
    assert math.isnan(result.value)
    assert result.raw == {"atomic_spin_density": []}
    # A non-finite scalar is not cached, so the next call recomputes (no sticky failure).
    assert cache.count() == 0
    cached_run(cache, engine, _req("spin_density"), solvent_name=None)
    assert engine.calls == 2
    assert cache.count() == 0


def test_finite_value_is_cached_and_reused(tmp_path: Path) -> None:
    cache = SQLiteCache(tmp_path / "finite.sqlite")
    engine = _CountingEngine(
        CalcResult(value=8.12, unit="eV", method="gfn2-xtb", raw={"ok": True})
    )

    first = cached_run(cache, engine, _req("adiabatic_ip"), solvent_name=None)
    assert first.value == 8.12
    assert cache.count() == 1
    second = cached_run(cache, engine, _req("adiabatic_ip"), solvent_name=None)
    assert second.value == 8.12
    assert engine.calls == 1  # served from cache, engine not re-run

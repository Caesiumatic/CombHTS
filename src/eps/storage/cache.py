"""SQLite cache for idempotent per-species engine results."""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from eps.engines.base import CalcRequest, CalcResult, Engine

GAS_SOLVENT_NAME = "__gas__"


@dataclass(frozen=True)
class CacheKey:
    """Primary key for a cached engine result."""

    canonical_smiles: str
    charge: int
    method: str
    solvent_name: str
    quantity: str


class SQLiteCache:
    """SQLite-backed cache keyed by species, charge, method, solvent, and quantity."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def get(self, key: CacheKey) -> CalcResult | None:
        """Return a cached result, or None on a cache miss."""

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT value, unit, raw_json
                FROM results
                WHERE canonical_smiles = ?
                  AND charge = ?
                  AND method = ?
                  AND solvent_name = ?
                  AND quantity = ?
                """,
                (
                    key.canonical_smiles,
                    key.charge,
                    key.method,
                    key.solvent_name,
                    key.quantity,
                ),
            ).fetchone()
        if row is None:
            return None
        cached_value = row["value"]
        return CalcResult(
            value=float(cached_value) if cached_value is not None else float("nan"),
            unit=str(row["unit"]),
            method=key.method,
            raw=json.loads(row["raw_json"]),
        )

    def put(self, key: CacheKey, result: CalcResult) -> None:
        """Store or replace one engine result."""

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO results (
                    canonical_smiles,
                    charge,
                    method,
                    solvent_name,
                    quantity,
                    value,
                    unit,
                    raw_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key.canonical_smiles,
                    key.charge,
                    key.method,
                    key.solvent_name,
                    key.quantity,
                    result.value,
                    result.unit,
                    json.dumps(result.raw, sort_keys=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def count(self) -> int:
        """Return the number of cached result rows."""

        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM results").fetchone()
        return int(row["n"])

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    canonical_smiles TEXT NOT NULL,
                    charge INTEGER NOT NULL,
                    method TEXT NOT NULL,
                    solvent_name TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (
                        canonical_smiles,
                        charge,
                        method,
                        solvent_name,
                        quantity
                    )
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


def cached_run(
    cache: SQLiteCache,
    engine: Engine,
    req: CalcRequest,
    solvent_name: str | None,
) -> CalcResult:
    """Run an engine request through the SQLite cache."""

    key = CacheKey(
        canonical_smiles=req.species.canonical_smiles,
        charge=req.species.charge,
        method=req.method,
        solvent_name=solvent_name or GAS_SOLVENT_NAME,
        quantity=req.quantity,
    )
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = engine.run(req)
    # Do not cache a non-finite scalar value. SQLite stores IEEE NaN as NULL, which violates the
    # results.value NOT NULL constraint (IntegrityError) — this is exactly how a failed-to-parse
    # spin_density (value=NaN, data only in raw['atomic_spin_density']) used to crash the per-monomer
    # secondary-descriptor pass. Skipping the write also avoids stickily caching a transient failure:
    # the next run recomputes instead of returning a cached NaN. Array/raw payloads whose scalar
    # value is meaningful (finite) still cache normally.
    if result.value is not None and math.isfinite(result.value):
        cache.put(key, result)
    return result

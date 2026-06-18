"""Native provenance sidecars for primary outputs.

Whenever a command writes a primary output, ``write_provenance`` drops a
``<output>.provenance.json`` next to it recording enough to reproduce the run: a UTC
timestamp, the git commit (short+long) and a dirty flag, the installed ``eps`` version, the
engine/method, SHA-256 hashes of the pinned config files, and the library (CSV) row counts.

Pure standard library + pandas; no new dependencies and no network. Everything degrades
gracefully (git missing / not a repo / package not installed / config absent) to ``"unknown"``
or ``"missing"`` rather than raising, so a provenance hiccup never breaks the actual command.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILES = (
    "configs/tier1.yaml",
    "configs/scoring.yaml",
    "configs/calibration_profiles.yaml",
    "configs/validation.yaml",
)
LIBRARY_FILES = (
    "data/monomers.csv",
    "data/solvents.csv",
    "data/electrolytes.csv",
)


def write_provenance(
    output_path: str | Path,
    *,
    engine: str,
    method: str,
    extra: dict[str, Any] | None = None,
    project_root: str | Path = PROJECT_ROOT,
) -> Path:
    """Write ``<output_path>.provenance.json`` and return its path."""

    output = Path(output_path)
    root = Path(project_root)
    record: dict[str, Any] = {
        "output": output.name,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "eps_version": _eps_version(),
        "engine": engine,
        "method": method,
        "git": git_info(root),
        "config_sha256": config_hashes(root),
        "library_sizes": library_sizes(root),
    }
    if extra:
        record["extra"] = extra

    sidecar = output.with_name(output.name + ".provenance.json")
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return sidecar


def _eps_version() -> str:
    try:
        return metadata.version("combhts")
    except Exception:  # noqa: BLE001 - package may not be installed (running from source tree).
        return "unknown"


def git_info(project_root: str | Path = PROJECT_ROOT) -> dict[str, str | bool]:
    """Return git commit short/long hashes and a dirty flag; ``"unknown"`` if unavailable."""

    root = str(project_root)
    long_hash = _git(["rev-parse", "HEAD"], root)
    short_hash = _git(["rev-parse", "--short", "HEAD"], root)
    status = _git(["status", "--porcelain"], root)
    if long_hash is None or short_hash is None or status is None:
        return {"commit": "unknown", "commit_short": "unknown", "dirty": "unknown"}
    return {"commit": long_hash, "commit_short": short_hash, "dirty": bool(status.strip())}


def _git(args: list[str], cwd: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def config_hashes(project_root: str | Path = PROJECT_ROOT) -> dict[str, str]:
    """Return SHA-256 of each pinned config file (``"missing"`` if absent)."""

    root = Path(project_root)
    hashes: dict[str, str] = {}
    for relative in CONFIG_FILES:
        path = root / relative
        if path.exists():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            hashes[relative] = "missing"
    return hashes


def library_sizes(project_root: str | Path = PROJECT_ROOT) -> dict[str, int | str]:
    """Return the row count of each library CSV (``"missing"`` if absent / unreadable)."""

    root = Path(project_root)
    sizes: dict[str, int | str] = {}
    for relative in LIBRARY_FILES:
        path = root / relative
        try:
            sizes[relative] = int(len(pd.read_csv(path)))
        except Exception:  # noqa: BLE001 - missing/unreadable library degrades to "missing".
            sizes[relative] = "missing"
    return sizes

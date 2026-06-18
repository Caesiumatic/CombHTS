"""``eps doctor`` — a no-compute environment readiness self-check.

Reports PASS / WARN / FAIL for the things that have actually bitten this project (a broken
venv, a missing module, an unparseable config, an absent data file). It runs no calculations,
makes no network calls, and uses no subprocess beyond ``shutil.which`` for the cluster
binaries. ``xtb`` / ``g16`` are cluster-only, so their absence is a WARN, never a FAIL.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIN_PYTHON = (3, 11)
REQUIRED_IMPORTS = ("rdkit", "pandas", "numpy")
OPTIONAL_IMPORTS = ("matplotlib", "sklearn")
CLUSTER_BINARIES = ("xtb", "g16")
PINNED_CONFIGS = (
    "configs/tier1.yaml",
    "configs/scoring.yaml",
    "configs/calibration_profiles.yaml",
    "configs/validation.yaml",
)
EXPECTED_DATA = (
    "data/monomers.csv",
    "data/solvents.csv",
    "data/electrolytes.csv",
    "data/benchmark.csv",
)

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


@dataclass(frozen=True)
class DoctorCheck:
    """One readiness check with a tri-state status."""

    name: str
    status: str
    detail: str


@dataclass
class DoctorReport:
    """Collected readiness checks."""

    checks: list[DoctorCheck] = field(default_factory=list)

    @property
    def has_failure(self) -> bool:
        return any(check.status == FAIL for check in self.checks)

    @property
    def n_warn(self) -> int:
        return sum(1 for check in self.checks if check.status == WARN)


def run_doctor(project_root: str | Path = PROJECT_ROOT) -> DoctorReport:
    """Run all readiness checks and return a report. Never raises."""

    root = Path(project_root)
    checks: list[DoctorCheck] = []

    version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info[:2] >= MIN_PYTHON:
        checks.append(DoctorCheck("python", PASS, f"Python {version} (>= 3.11)"))
    else:
        checks.append(DoctorCheck("python", FAIL, f"Python {version} (< 3.11 required)"))

    for binary in CLUSTER_BINARIES:
        path = shutil.which(binary)
        if path:
            checks.append(DoctorCheck(f"binary:{binary}", PASS, path))
        else:
            checks.append(DoctorCheck(f"binary:{binary}", WARN, "not on PATH (cluster-only; fine locally)"))

    for module in REQUIRED_IMPORTS:
        checks.append(_import_check(module, required=True))
    for module in OPTIONAL_IMPORTS:
        checks.append(_import_check(module, required=False))

    for relative in PINNED_CONFIGS:
        checks.append(_config_check(root / relative, relative))

    for relative in EXPECTED_DATA:
        path = root / relative
        if path.exists():
            checks.append(DoctorCheck(f"data:{relative}", PASS, "present"))
        else:
            checks.append(DoctorCheck(f"data:{relative}", FAIL, "missing"))

    return DoctorReport(checks=checks)


def _import_check(module: str, *, required: bool) -> DoctorCheck:
    try:
        found = importlib.util.find_spec(module) is not None
    except Exception:  # noqa: BLE001 - a broken parent package counts as not importable.
        found = False
    if found:
        return DoctorCheck(f"import:{module}", PASS, "importable")
    status = FAIL if required else WARN
    suffix = "required" if required else "optional (needed only for eps analyze figures)"
    return DoctorCheck(f"import:{module}", status, f"not importable ({suffix})")


def _config_check(path: Path, relative: str) -> DoctorCheck:
    if not path.exists():
        return DoctorCheck(f"config:{relative}", FAIL, "missing")
    try:
        with path.open("r", encoding="utf-8") as handle:
            yaml.safe_load(handle)
    except Exception as exc:  # noqa: BLE001 - unparseable config is a hard failure.
        return DoctorCheck(f"config:{relative}", FAIL, f"unparseable: {type(exc).__name__}")
    return DoctorCheck(f"config:{relative}", PASS, "present and parseable")

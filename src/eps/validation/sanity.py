"""Physical sanity checks on the calibrated monomer Eox harvest.

These are DIRECTIONAL checks on calibrated monomer oxidation potentials only: known
substituent/conjugation effects should lower Eox. Because the calibrated monomer Eox is
solvent-dependent, every comparison is made WITHIN A SINGLE SOLVENT (acetonitrile by
default). No oligomer assembly is attempted (not built); these only compare monomer Eox
values already present in the Tier-1 harvest CSV.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HARVEST_PATH = PROJECT_ROOT / "outputs" / "tier1_all_xtb.csv"
DEFAULT_SOLVENT = "acetonitrile"

MONOMER_NAME_COLUMN = "monomer_name"
EOX_COLUMN = "monomer_Eox_calibrated_V_vs_AgAgCl"

# (description, lower-Eox monomer, reference monomer). The check passes when
# Eox(lower) < Eox(reference) within the chosen solvent.
SANITY_CHECKS: tuple[tuple[str, str, str], ...] = (
    ("dioxy substitution lowers Eox", "EDOT", "thiophene"),
    ("alkyl substitution lowers Eox", "3-hexylthiophene", "thiophene"),
    ("dioxy substitution lowers Eox", "EDOP", "pyrrole"),
    ("dioxy substitution lowers Eox", "EDOS", "selenophene"),
    ("extended conjugation lowers Eox", "bithiophene", "thiophene"),
)


@dataclass(frozen=True)
class SanityCheck:
    """One directional monomer-Eox comparison within a single solvent."""

    description: str
    lower_monomer: str
    reference_monomer: str
    lower_eox_V: float | None
    reference_eox_V: float | None
    status: str  # "PASS", "FAIL", or "SKIP"
    detail: str


@dataclass(frozen=True)
class SanityResult:
    """Collected physical sanity checks for one harvest CSV and solvent."""

    harvest_path: Path
    solvent_name: str
    checks: list[SanityCheck] = field(default_factory=list)

    @property
    def n_pass(self) -> int:
        return sum(1 for check in self.checks if check.status == "PASS")

    @property
    def n_fail(self) -> int:
        return sum(1 for check in self.checks if check.status == "FAIL")

    @property
    def n_skip(self) -> int:
        return sum(1 for check in self.checks if check.status == "SKIP")

    @property
    def all_pass(self) -> bool:
        return self.n_fail == 0 and self.n_pass > 0


def run_physical_sanity_checks(
    harvest_path: str | Path = DEFAULT_HARVEST_PATH,
    *,
    solvent_name: str = DEFAULT_SOLVENT,
) -> SanityResult:
    """Run the directional monomer-Eox sanity checks against a Tier-1 harvest CSV."""

    path = Path(harvest_path)
    frame = pd.read_csv(path)
    for column in (MONOMER_NAME_COLUMN, EOX_COLUMN, "solvent_name"):
        if column not in frame.columns:
            raise ValueError(f"{path} is missing required column {column!r}")

    solvent_rows = frame[frame["solvent_name"] == solvent_name]
    eox_by_monomer = _eox_by_monomer(solvent_rows)

    checks = [
        _evaluate_check(description, lower, reference, eox_by_monomer)
        for description, lower, reference in SANITY_CHECKS
    ]
    return SanityResult(harvest_path=path, solvent_name=solvent_name, checks=checks)


def _eox_by_monomer(solvent_rows: pd.DataFrame) -> dict[str, float]:
    """Map monomer_name -> calibrated Eox (first finite value) within one solvent."""

    eox_by_monomer: dict[str, float] = {}
    for _, row in solvent_rows.iterrows():
        name = str(row[MONOMER_NAME_COLUMN])
        value = pd.to_numeric(row[EOX_COLUMN], errors="coerce")
        if name not in eox_by_monomer and pd.notna(value):
            eox_by_monomer[name] = float(value)
    return eox_by_monomer


def _lookup_eox(name: str, eox_by_monomer: dict[str, float]) -> float | None:
    """Look up a monomer Eox, tolerant of case and surrounding whitespace."""

    if name in eox_by_monomer:
        return eox_by_monomer[name]
    target = name.strip().lower()
    for candidate, value in eox_by_monomer.items():
        if candidate.strip().lower() == target:
            return value
    return None


def _evaluate_check(
    description: str,
    lower: str,
    reference: str,
    eox_by_monomer: dict[str, float],
) -> SanityCheck:
    lower_eox = _lookup_eox(lower, eox_by_monomer)
    reference_eox = _lookup_eox(reference, eox_by_monomer)

    if lower_eox is None or reference_eox is None:
        missing = [
            name
            for name, value in ((lower, lower_eox), (reference, reference_eox))
            if value is None
        ]
        return SanityCheck(
            description=description,
            lower_monomer=lower,
            reference_monomer=reference,
            lower_eox_V=lower_eox,
            reference_eox_V=reference_eox,
            status="SKIP",
            detail=f"monomer(s) not found in harvest: {', '.join(missing)}",
        )

    passed = lower_eox < reference_eox
    return SanityCheck(
        description=description,
        lower_monomer=lower,
        reference_monomer=reference,
        lower_eox_V=lower_eox,
        reference_eox_V=reference_eox,
        status="PASS" if passed else "FAIL",
        detail=f"Eox({lower})={lower_eox:.3f} V {'<' if passed else '>='} Eox({reference})={reference_eox:.3f} V",
    )

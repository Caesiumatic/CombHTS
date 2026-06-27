"""Abstract calculation-engine API for per-species quantum chemistry quantities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

SUPPORTED_QUANTITIES = frozenset(
    {
        "adiabatic_ip",
        "adiabatic_ea",
        "gas_energy",
        "solvation_free_energy",
        "optical_gap",
        "spin_density",
        "homo",
        "lumo",
        "vertical_ip",
        "vertical_ea",
        # IPEA-xTB vertical IP/EA (directive §4.1 Tier-1 monomer/solvent oxidation engine).
        "ipea_ip",
        "ipea_ea",
    }
)


@dataclass(frozen=True)
class SpeciesSpec:
    """A single molecular species and electronic state requested from an engine.

    Attributes:
        canonical_smiles: RDKit canonical SMILES for the species.
        charge: Formal charge state in units of elementary charge.
        multiplicity: Spin multiplicity, dimensionless.
    """

    canonical_smiles: str
    charge: int
    multiplicity: int


@dataclass(frozen=True)
class CalcRequest:
    """A request for one physical quantity for one species.

    Attributes:
        species: Molecular species and electronic state.
        method: Engine method label, such as ``mock-gfn2`` or later ``gfn2-xtb``.
        solvent_eps_r: Relative dielectric constant of the solvent, or None for gas phase.
        xtb_gbsa_name: Optional xTB ALPB solvent keyword for real xTB backends.
        solvent_model_name: Optional backend-native solvent name (for example the ORCA
            openCOSMO-RS internal database key). The SQLite key still uses the explicit
            ``solvent_name`` passed to ``cached_run``.
        quantity: Requested quantity. Supported values are listed in
            ``SUPPORTED_QUANTITIES``.
    """

    species: SpeciesSpec
    method: str
    solvent_eps_r: float | None
    quantity: str
    xtb_gbsa_name: str | None = None
    solvent_model_name: str | None = None
    supported_quantities: ClassVar[frozenset[str]] = SUPPORTED_QUANTITIES

    def __post_init__(self) -> None:
        if self.quantity not in self.supported_quantities:
            supported = ", ".join(sorted(self.supported_quantities))
            raise ValueError(f"Unsupported quantity {self.quantity!r}; expected one of: {supported}")
        if self.solvent_eps_r is not None and self.solvent_eps_r <= 0:
            raise ValueError("solvent_eps_r must be positive when provided")


@dataclass(frozen=True)
class CalcResult:
    """A scalar engine result with explicit unit and provenance.

    Attributes:
        value: Numeric value of the requested quantity.
        unit: Unit of value, e.g. eV, kcal/mol, or fraction.
        method: Engine method label that produced the value.
        raw: Backend-specific provenance and parser details.
    """

    value: float
    unit: str
    method: str
    raw: dict[str, Any] = field(default_factory=dict)


class Engine(ABC):
    """Backend interface for computing one per-species quantity at a time."""

    @abstractmethod
    def run(self, req: CalcRequest) -> CalcResult:
        """Run a calculation request and return a scalar result with units."""

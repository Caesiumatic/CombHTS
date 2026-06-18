"""Deterministic mock calculation engine for fast pipeline development."""

from __future__ import annotations

import hashlib

from eps.engines.base import CalcRequest, CalcResult, Engine


class MockEngine(Engine):
    """Return physically plausible deterministic values for supported quantities.

    Values are generated from a stable SHA-256 hash of the canonical SMILES, charge,
    quantity, and method. Solvent effects are then applied analytically from eps_r,
    so a gas-phase base value is stable while polar solvents shift appropriate
    quantities in a reproducible way.
    """

    def run(self, req: CalcRequest) -> CalcResult:
        """Compute one mock property for one species.

        Returned units are eV for redox and gap quantities, kcal/mol for free
        energies, and fraction for spin density.
        """

        base = self._unit_float(req)
        quantity = req.quantity

        if quantity == "adiabatic_ip":
            gas_ip_eV = self._scale(base, 5.5, 7.5)
            solvent_shift_eV = 0.45 * _polarity_factor(req.solvent_eps_r)
            value = gas_ip_eV - solvent_shift_eV
            unit = "eV"
        elif quantity == "adiabatic_ea":
            gas_ea_eV = self._scale(base, 0.2, 2.5)
            solvent_shift_eV = 0.25 * _polarity_factor(req.solvent_eps_r)
            value = gas_ea_eV + solvent_shift_eV
            unit = "eV"
        elif quantity == "gas_energy":
            value = self._scale(base, -650.0, -50.0)
            unit = "eV"
        elif quantity == "solvation_free_energy":
            value = self._scale(base, -12.0, -2.0)
            unit = "kcal/mol"
        elif quantity == "optical_gap":
            value = self._scale(base, 1.0, 3.0)
            unit = "eV"
        elif quantity == "spin_density":
            value = self._scale(base, 0.0, 1.0)
            unit = "fraction"
        else:
            raise ValueError(f"Unsupported quantity {quantity!r}")

        raw = {
            "engine": "MockEngine",
            "hash_basis": self._hash_basis(req),
            "solvent_polarity_factor": _polarity_factor(req.solvent_eps_r),
        }
        if quantity == "optical_gap":
            raw["optical_gap_method"] = "mock-deterministic"
        return CalcResult(value=value, unit=unit, method=req.method, raw=raw)

    @staticmethod
    def _scale(unit_value: float, low: float, high: float) -> float:
        return low + unit_value * (high - low)

    @classmethod
    def _unit_float(cls, req: CalcRequest) -> float:
        digest = hashlib.sha256(cls._hash_basis(req).encode("utf-8")).digest()
        integer = int.from_bytes(digest[:8], byteorder="big", signed=False)
        return integer / float(2**64 - 1)

    @staticmethod
    def _hash_basis(req: CalcRequest) -> str:
        species = req.species
        return "|".join(
            [
                species.canonical_smiles,
                str(species.charge),
                req.quantity,
                req.method,
            ]
        )


def _polarity_factor(solvent_eps_r: float | None) -> float:
    """Return Born-like solvent polarity factor ``1 - 1/eps_r``."""

    if solvent_eps_r is None:
        return 0.0
    return 1.0 - (1.0 / solvent_eps_r)

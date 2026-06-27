"""Deterministic mock calculation engine for fast pipeline development."""

from __future__ import annotations

import hashlib

from rdkit import Chem

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

        raw = {
            "engine": "MockEngine",
            "hash_basis": self._hash_basis(req),
            "solvent_polarity_factor": _polarity_factor(req.solvent_eps_r),
        }

        if quantity == "adiabatic_ip":
            value = self._adiabatic_ip_value(req)
            unit = "eV"
        elif quantity == "adiabatic_ea":
            value = self._adiabatic_ea_value(req)
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
            raw["optical_gap_method"] = "mock-deterministic"
        elif quantity == "homo":
            # lumo (>= -3.0) is always above homo (<= -5.0), so the gap is always positive.
            value = self._scale(base, -9.0, -5.0)
            unit = "eV"
        elif quantity == "lumo":
            value = self._scale(base, -3.0, 0.5)
            unit = "eV"
        elif quantity == "vertical_ip":
            # vertical IP = adiabatic IP + non-negative reorganization energy (lambda_ox >= 0).
            reorg = self._scale(base, 0.05, 0.40)
            value = self._adiabatic_ip_value(req) + reorg
            unit = "eV"
            raw["reorganization_eV"] = reorg
        elif quantity == "vertical_ea":
            # vertical EA = adiabatic EA + non-negative reorganization energy (lambda_red >= 0).
            reorg = self._scale(base, 0.05, 0.40)
            value = self._adiabatic_ea_value(req) + reorg
            unit = "eV"
            raw["reorganization_eV"] = reorg
        elif quantity == "ipea_ip":
            # IPEA-xTB vertical IP (directive §4.1): own deterministic basis, IPEA absolute scale
            # (~7.5-9.5 eV). Calibration absorbs the offset, so only monotonicity/determinism matter.
            value = self._scale(self._unit_float_for(req, "ipea_ip"), 7.5, 9.5)
            unit = "eV"
        elif quantity == "ipea_ea":
            value = self._scale(self._unit_float_for(req, "ipea_ea"), -2.0, 0.5)
            unit = "eV"
        elif quantity == "spin_density":
            value = self._scale(base, 0.0, 1.0)
            unit = "fraction"
            raw["atomic_spin_density"] = self._atomic_spin_density(req)
        else:
            raise ValueError(f"Unsupported quantity {quantity!r}")

        return CalcResult(value=value, unit=unit, method=req.method, raw=raw)

    def _adiabatic_ip_value(self, req: CalcRequest) -> float:
        """Mock adiabatic IP in eV (its own deterministic hash basis)."""

        base = self._unit_float_for(req, "adiabatic_ip")
        gas_ip_eV = self._scale(base, 5.5, 7.5)
        solvent_shift_eV = 0.45 * _polarity_factor(req.solvent_eps_r)
        return gas_ip_eV - solvent_shift_eV

    def _adiabatic_ea_value(self, req: CalcRequest) -> float:
        """Mock adiabatic EA in eV (its own deterministic hash basis)."""

        base = self._unit_float_for(req, "adiabatic_ea")
        gas_ea_eV = self._scale(base, 0.2, 2.5)
        solvent_shift_eV = 0.25 * _polarity_factor(req.solvent_eps_r)
        return gas_ea_eV + solvent_shift_eV

    def _atomic_spin_density(self, req: CalcRequest) -> list[float]:
        """Per-heavy-atom spin density that sums to 1.0 (a single unpaired electron).

        Each heavy atom i gets a deterministic weight from a hash that also includes the
        atom index; the list is normalized to sum to 1.0. Returns ``[]`` if RDKit cannot
        parse the SMILES (never raises, so the screen's _safe_calculate path is unused here).
        """

        mol = Chem.MolFromSmiles(req.species.canonical_smiles)
        if mol is None:
            return []
        n_atoms = mol.GetNumAtoms()
        if n_atoms == 0:
            return []
        weights = [self._unit_float_for_atom(req, "spin_density", i) for i in range(n_atoms)]
        total = sum(weights)
        if total <= 0.0:
            return [1.0 / n_atoms for _ in range(n_atoms)]
        return [w / total for w in weights]

    @staticmethod
    def _scale(unit_value: float, low: float, high: float) -> float:
        return low + unit_value * (high - low)

    @classmethod
    def _unit_float(cls, req: CalcRequest) -> float:
        return cls._unit_float_from_basis(cls._hash_basis(req))

    @classmethod
    def _unit_float_for(cls, req: CalcRequest, quantity: str) -> float:
        """unit_float in [0, 1) for an ARBITRARY quantity string given req.

        Lets a derived quantity (e.g. ``vertical_ip``) reference another's deterministic
        value (``adiabatic_ip``) without sharing its hash.
        """

        return cls._unit_float_from_basis(cls._basis_for(req, quantity))

    @classmethod
    def _unit_float_for_atom(cls, req: CalcRequest, quantity: str, atom_index: int) -> float:
        basis = f"{cls._basis_for(req, quantity)}|{atom_index}"
        return cls._unit_float_from_basis(basis)

    @staticmethod
    def _unit_float_from_basis(basis: str) -> float:
        digest = hashlib.sha256(basis.encode("utf-8")).digest()
        integer = int.from_bytes(digest[:8], byteorder="big", signed=False)
        return integer / float(2**64 - 1)

    @staticmethod
    def _hash_basis(req: CalcRequest) -> str:
        return MockEngine._basis_for(req, req.quantity)

    @staticmethod
    def _basis_for(req: CalcRequest, quantity: str) -> str:
        species = req.species
        return "|".join(
            [
                species.canonical_smiles,
                str(species.charge),
                quantity,
                req.method,
            ]
        )


def _polarity_factor(solvent_eps_r: float | None) -> float:
    """Return Born-like solvent polarity factor ``1 - 1/eps_r``."""

    if solvent_eps_r is None:
        return 0.0
    return 1.0 - (1.0 / solvent_eps_r)

"""GFN2-xTB backend for the Engine interface."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from eps.engines.base import CalcRequest, CalcResult, Engine
from eps.structures import smiles_to_xyz

HARTREE_TO_EV = 27.211386245988
HARTREE_TO_KCAL_MOL = 627.5094740631
XTB_METHOD = "gfn2-xtb"


class XTBEngine(Engine):
    """Run real GFN2-xTB calculations through subprocess.

    Charge/multiplicity rule for adiabatic redox:
    - IP oxidizes the requested state from (q, multiplicity m) to (q+1, m+1).
    - EA reduces the requested state from (q, multiplicity m) to (q-1, m+1).

    Thus an anion request with charge=-1 correctly oxidizes to a neutral radical
    for IP, while a neutral singlet oxidizes to a radical cation doublet.
    xTB receives multiplicity through ``--uhf multiplicity-1``.
    """

    def __init__(self, binary: str = "xtb") -> None:
        self.binary = binary

    def run(self, req: CalcRequest) -> CalcResult:
        """Run one xTB calculation request and return a scalar result."""

        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"xTB binary {self.binary!r} was not found on PATH. Install xtb or use MockEngine."
            )

        if req.quantity == "adiabatic_ip":
            value, raw = self._adiabatic_redox(req, charge_delta=1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        if req.quantity == "adiabatic_ea":
            value, raw = self._adiabatic_redox(req, charge_delta=-1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        if req.quantity == "solvation_free_energy":
            value, raw = self._solvation_free_energy(req)
            return CalcResult(value=value, unit="kcal/mol", method=req.method, raw=raw)
        if req.quantity == "optical_gap":
            stdout = self._run_xtb(req, charge=req.species.charge, multiplicity=req.species.multiplicity)
            return CalcResult(
                value=parse_homo_lumo(stdout),
                unit="eV",
                method=req.method,
                raw={"engine": "XTBEngine", "quantity": req.quantity, "stdout": stdout},
            )
        if req.quantity == "gas_energy":
            stdout = self._run_xtb(
                req,
                charge=req.species.charge,
                multiplicity=req.species.multiplicity,
                solvent_args=[],
                optimize=True,
            )
            return CalcResult(
                value=parse_total_energy(stdout) * HARTREE_TO_EV,
                unit="eV",
                method=req.method,
                raw={"engine": "XTBEngine", "quantity": req.quantity, "stdout": stdout},
            )
        raise NotImplementedError(f"XTBEngine does not implement quantity {req.quantity!r}")

    def _adiabatic_redox(self, req: CalcRequest, charge_delta: int) -> tuple[float, dict]:
        initial = req.species
        final_charge = initial.charge + charge_delta
        final_multiplicity = initial.multiplicity + 1
        solvent_args = solvent_flag(req.xtb_gbsa_name, req.solvent_eps_r)

        initial_stdout = self._run_xtb(
            req,
            charge=initial.charge,
            multiplicity=initial.multiplicity,
            solvent_args=solvent_args,
            optimize=True,
        )
        final_stdout = self._run_xtb(
            req,
            charge=final_charge,
            multiplicity=final_multiplicity,
            solvent_args=solvent_args,
            optimize=True,
        )
        initial_energy = parse_total_energy(initial_stdout)
        final_energy = parse_total_energy(final_stdout)
        delta_eV = (final_energy - initial_energy) * HARTREE_TO_EV
        if charge_delta == -1:
            delta_eV = (initial_energy - final_energy) * HARTREE_TO_EV
        return delta_eV, {
            "engine": "XTBEngine",
            "quantity": req.quantity,
            "initial_charge": initial.charge,
            "initial_multiplicity": initial.multiplicity,
            "final_charge": final_charge,
            "final_multiplicity": final_multiplicity,
            "solvent_args": solvent_args,
            "initial_stdout": initial_stdout,
            "final_stdout": final_stdout,
        }

    def _solvation_free_energy(self, req: CalcRequest) -> tuple[float, dict]:
        gas_stdout = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=[],
            optimize=False,
        )
        solvated_stdout = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=solvent_flag(req.xtb_gbsa_name, req.solvent_eps_r),
            optimize=False,
        )
        gas_energy = parse_total_energy(gas_stdout)
        solvated_energy = parse_total_energy(solvated_stdout)
        return (solvated_energy - gas_energy) * HARTREE_TO_KCAL_MOL, {
            "engine": "XTBEngine",
            "quantity": req.quantity,
            "gas_stdout": gas_stdout,
            "solvated_stdout": solvated_stdout,
        }

    def _run_xtb(
        self,
        req: CalcRequest,
        *,
        charge: int,
        multiplicity: int,
        solvent_args: list[str] | None = None,
        optimize: bool = False,
    ) -> str:
        xyz = smiles_to_xyz(req.species.canonical_smiles, charge=charge)
        args = solvent_args if solvent_args is not None else solvent_flag(req.xtb_gbsa_name, req.solvent_eps_r)
        with tempfile.TemporaryDirectory(prefix="eps-xtb-") as tmpdir:
            xyz_path = Path(tmpdir) / "input.xyz"
            xyz_path.write_text(xyz, encoding="utf-8")
            command = [
                self.binary,
                str(xyz_path),
                "--gfn",
                "2",
                "--chrg",
                str(charge),
                "--uhf",
                str(max(multiplicity - 1, 0)),
                *args,
            ]
            if optimize:
                command.append("--opt")
            completed = subprocess.run(
                command,
                cwd=tmpdir,
                check=False,
                capture_output=True,
                text=True,
            )
        if completed.returncode != 0:
            raise RuntimeError(
                "xTB failed with exit code "
                f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed.stdout


def solvent_flag(xtb_gbsa_name: str | None, eps_r: float | None) -> list[str]:
    """Return xTB solvent arguments from a GBSA keyword or dielectric constant."""

    if xtb_gbsa_name:
        return ["--gbsa", xtb_gbsa_name]
    if eps_r is not None:
        return ["--alpb", str(eps_r)]
    return []


def parse_total_energy(stdout: str) -> float:
    """Parse xTB total energy in Hartree from stdout text."""

    patterns = [
        r"TOTAL\s+ENERGY\s+(-?\d+(?:\.\d+)?)\s+Eh",
        r"\|\s*TOTAL\s+ENERGY\s+(-?\d+(?:\.\d+)?)",
        r"total\s+energy\s+(-?\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, stdout, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    raise ValueError("Could not parse xTB total energy from stdout")


def parse_homo_lumo(stdout: str) -> float:
    """Parse HOMO-LUMO gap in eV from xTB stdout text.

    TODO: Replace this placeholder gap with sTDA-xTB excited-state output when the
    optical-gap workflow is added.
    """

    patterns = [
        r"HOMO[-\s]LUMO\s+GAP\s+(-?\d+(?:\.\d+)?)\s+eV",
        r"HL[-\s]Gap\s+(-?\d+(?:\.\d+)?)\s+eV",
        r"gap\s+(-?\d+(?:\.\d+)?)\s+eV",
    ]
    for pattern in patterns:
        match = re.search(pattern, stdout, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    raise ValueError("Could not parse xTB HOMO-LUMO gap from stdout")

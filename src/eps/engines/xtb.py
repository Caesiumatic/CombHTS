"""GFN2-xTB backend for the Engine interface."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eps.engines.base import CalcRequest, CalcResult, Engine
from eps.structures import smiles_to_xyz

HARTREE_TO_EV = 27.211386245988
HARTREE_TO_KCAL_MOL = 627.5094740631
XTB_METHOD = "gfn2-xtb"


@dataclass(frozen=True)
class XTBRunOutput:
    """Raw xTB stdout plus optional structured JSON output."""

    stdout: str
    parsed_json: dict[str, float | None] | None


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
            output = self._run_xtb(req, charge=req.species.charge, multiplicity=req.species.multiplicity)
            return CalcResult(
                value=_gap_from_output(output),
                unit="eV",
                method=req.method,
                raw={
                    "engine": "XTBEngine",
                    "quantity": req.quantity,
                    "stdout": output.stdout,
                    "parsed_json": output.parsed_json,
                },
            )
        if req.quantity == "gas_energy":
            output = self._run_xtb(
                req,
                charge=req.species.charge,
                multiplicity=req.species.multiplicity,
                solvent_args=[],
                optimize=True,
            )
            return CalcResult(
                value=_energy_from_output(output) * HARTREE_TO_EV,
                unit="eV",
                method=req.method,
                raw={
                    "engine": "XTBEngine",
                    "quantity": req.quantity,
                    "stdout": output.stdout,
                    "parsed_json": output.parsed_json,
                },
            )
        raise NotImplementedError(f"XTBEngine does not implement quantity {req.quantity!r}")

    def _adiabatic_redox(self, req: CalcRequest, charge_delta: int) -> tuple[float, dict]:
        initial = req.species
        final_charge = initial.charge + charge_delta
        final_multiplicity = initial.multiplicity + 1
        solvent_args = solvent_flag(req.xtb_gbsa_name)

        initial_output = self._run_xtb(
            req,
            charge=initial.charge,
            multiplicity=initial.multiplicity,
            solvent_args=solvent_args,
            optimize=True,
        )
        final_output = self._run_xtb(
            req,
            charge=final_charge,
            multiplicity=final_multiplicity,
            solvent_args=solvent_args,
            optimize=True,
        )
        initial_energy = _energy_from_output(initial_output)
        final_energy = _energy_from_output(final_output)
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
            "initial_stdout": initial_output.stdout,
            "final_stdout": final_output.stdout,
            "initial_json": initial_output.parsed_json,
            "final_json": final_output.parsed_json,
        }

    def _solvation_free_energy(self, req: CalcRequest) -> tuple[float, dict]:
        gas_output = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=[],
            optimize=False,
        )
        solvated_output = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=solvent_flag(req.xtb_gbsa_name),
            optimize=False,
        )
        gas_energy = _energy_from_output(gas_output)
        solvated_energy = _energy_from_output(solvated_output)
        return (solvated_energy - gas_energy) * HARTREE_TO_KCAL_MOL, {
            "engine": "XTBEngine",
            "quantity": req.quantity,
            "gas_stdout": gas_output.stdout,
            "solvated_stdout": solvated_output.stdout,
            "gas_json": gas_output.parsed_json,
            "solvated_json": solvated_output.parsed_json,
        }

    def _run_xtb(
        self,
        req: CalcRequest,
        *,
        charge: int,
        multiplicity: int,
        solvent_args: list[str] | None = None,
        optimize: bool = False,
    ) -> XTBRunOutput:
        xyz = smiles_to_xyz(req.species.canonical_smiles, charge=charge)
        args = solvent_args if solvent_args is not None else solvent_flag(req.xtb_gbsa_name)
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
                "--iterations",
                "500",
                "--etemp",
                "400.0",
                *args,
                "--json",
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
            json_path = Path(tmpdir) / "xtbout.json"
            parsed_json = None
            if json_path.exists():
                parsed_json = parse_xtb_json(json_path.read_text(encoding="utf-8"))
        if completed.returncode != 0:
            raise RuntimeError(
                "xTB failed with exit code "
                f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return XTBRunOutput(stdout=completed.stdout, parsed_json=parsed_json)


def solvent_flag(xtb_gbsa_name: str | None) -> list[str]:
    """Return xTB ALPB solvent arguments from a versioned solvent keyword."""

    if xtb_gbsa_name:
        return ["--alpb", xtb_gbsa_name]
    return []


def parse_xtb_json(json_text: str) -> dict[str, float | None]:
    """Parse structured xTB JSON text into normalized property keys."""

    data = json.loads(json_text)
    total_energy = _find_json_number(data, "total energy")
    homo_lumo_gap = _find_json_number(data, "HOMO-LUMO gap/eV")
    if total_energy is None:
        raise ValueError("Could not parse 'total energy' from xtbout.json")
    return {
        "total_energy_Eh": total_energy,
        "homo_lumo_gap_eV": homo_lumo_gap,
    }


def parse_total_energy(stdout: str) -> float:
    """Parse the last xTB total energy in Hartree from stdout fallback text."""

    patterns = [
        r"TOTAL\s+ENERGY\s+(-?\d+(?:\.\d+)?)\s+Eh",
        r"\|\s*TOTAL\s+ENERGY\s+(-?\d+(?:\.\d+)?)",
        r"total\s+energy\s+(-?\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, stdout, flags=re.IGNORECASE)
        if matches:
            return float(matches[-1])
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
        matches = re.findall(pattern, stdout, flags=re.IGNORECASE)
        if matches:
            return float(matches[-1])
    raise ValueError("Could not parse xTB HOMO-LUMO gap from stdout")


def _energy_from_output(output: XTBRunOutput) -> float:
    if output.parsed_json is not None:
        return float(output.parsed_json["total_energy_Eh"])
    return parse_total_energy(output.stdout)


def _gap_from_output(output: XTBRunOutput) -> float:
    if output.parsed_json is not None and output.parsed_json["homo_lumo_gap_eV"] is not None:
        return float(output.parsed_json["homo_lumo_gap_eV"])
    return parse_homo_lumo(output.stdout)


def _find_json_number(data: Any, key: str) -> float | None:
    if isinstance(data, dict):
        for candidate_key, value in data.items():
            if candidate_key == key:
                return float(value)
            found = _find_json_number(value, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_json_number(item, key)
            if found is not None:
                return found
    return None

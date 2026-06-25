"""GFN2-xTB backend for the Engine interface."""

from __future__ import annotations

import hashlib
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
STDA_FAILURE_MESSAGE_LIMIT = 240


@dataclass(frozen=True)
class XTBRunOutput:
    """Raw xTB stdout, optional structured JSON output, and optimized geometry."""

    stdout: str
    parsed_json: dict[str, float | None] | None
    optimized_xyz: str | None = None


class STDAStageError(RuntimeError):
    """sTDA workflow failure with the failed stage preserved for provenance."""

    def __init__(self, stage: str, message: str) -> None:
        super().__init__(message)
        self.stage = stage


class STDAUnavailableError(RuntimeError):
    """sTDA binary is not available for the optical-gap workflow."""


class OptimizedGeometryMissingError(RuntimeError):
    """Optimized xTB geometry was expected but not captured."""


class XTBEngine(Engine):
    """Run real GFN2-xTB calculations through subprocess.

    Charge/multiplicity rule for adiabatic redox:
    - IP oxidizes the requested state from (q, multiplicity m) to (q+1, m+1).
    - EA reduces the requested state from (q, multiplicity m) to (q-1, m+1).

    Thus an anion request with charge=-1 correctly oxidizes to a neutral radical
    for IP, while a neutral singlet oxidizes to a radical cation doublet.
    xTB receives multiplicity through ``--uhf multiplicity-1``.
    """

    def __init__(
        self,
        binary: str = "xtb",
        *,
        stda_binary: str = "stda",
        stda_energy_window_eV: float = 10.0,
    ) -> None:
        self.binary = binary
        self.stda_binary = stda_binary
        self.stda_energy_window_eV = stda_energy_window_eV

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
            value, output, optical_gap_metadata = self._optical_gap(req)
            return CalcResult(
                value=value,
                unit="eV",
                method=req.method,
                raw={
                    "engine": "XTBEngine",
                    "quantity": req.quantity,
                    **optical_gap_metadata,
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
        if req.quantity in ("homo", "lumo"):
            value, output = self._frontier_orbital(req, req.quantity)
            return CalcResult(
                value=value,
                unit="eV",
                method=req.method,
                raw={
                    "engine": "XTBEngine",
                    "quantity": req.quantity,
                    "stdout": output.stdout,
                    "parsed_json": output.parsed_json,
                },
            )
        if req.quantity in ("vertical_ip", "vertical_ea"):
            value, raw = self._vertical_redox(req)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        if req.quantity == "spin_density":
            value, raw = self._spin_density(req)
            return CalcResult(value=value, unit="fraction", method=req.method, raw=raw)
        raise NotImplementedError(f"XTBEngine does not implement quantity {req.quantity!r}")

    def _frontier_orbital(self, req: CalcRequest, which: str) -> tuple[float, "XTBRunOutput"]:
        """Parse the HOMO or LUMO eigenvalue (eV) from an xTB single-point orbital block.

        Screening approximation: GFN2-xTB frontier orbital energies, no separate optimization
        of the neutral (geometry is the ETKDG embedding; xTB does a single point).
        """

        output = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=solvent_flag(req.xtb_gbsa_name),
            optimize=False,
        )
        return parse_frontier_orbital_eV(output.stdout, which), output

    def _vertical_redox(self, req: CalcRequest) -> tuple[float, dict]:
        """Vertical IP/EA via single-point (optimize=False) ion and neutral energies.

        Screening approximation: the neutral and ion energies use INDEPENDENTLY embedded
        geometries (no shared/frozen geometry, no relaxation), so this is a coarse screening
        estimate of the vertical quantity rather than a strict frozen-geometry vertical value.
        """

        neutral = req.species
        if req.quantity == "vertical_ip":
            ion_charge = neutral.charge + 1
        else:
            ion_charge = neutral.charge - 1
        ion_multiplicity = neutral.multiplicity + 1
        solvent_args = solvent_flag(req.xtb_gbsa_name)

        neutral_output = self._run_xtb(
            req,
            charge=neutral.charge,
            multiplicity=neutral.multiplicity,
            solvent_args=solvent_args,
            optimize=False,
        )
        ion_output = self._run_xtb(
            req,
            charge=ion_charge,
            multiplicity=ion_multiplicity,
            solvent_args=solvent_args,
            optimize=False,
        )
        neutral_energy = _energy_from_output(neutral_output)
        ion_energy = _energy_from_output(ion_output)
        if req.quantity == "vertical_ip":
            delta_eV = (ion_energy - neutral_energy) * HARTREE_TO_EV
        else:
            delta_eV = (neutral_energy - ion_energy) * HARTREE_TO_EV
        return delta_eV, {
            "engine": "XTBEngine",
            "quantity": req.quantity,
            "approximation": "single_point_independent_geometries_screening",
            "neutral_charge": neutral.charge,
            "ion_charge": ion_charge,
            "ion_multiplicity": ion_multiplicity,
            "solvent_args": solvent_args,
            "neutral_stdout": neutral_output.stdout,
            "ion_stdout": ion_output.stdout,
            "neutral_json": neutral_output.parsed_json,
            "ion_json": ion_output.parsed_json,
        }

    def _spin_density(self, req: CalcRequest) -> tuple[float, dict]:
        """Best-effort Mulliken atomic spin populations from a single-point xTB run.

        ``value`` is the maximum atomic spin population; ``raw['atomic_spin_density']`` is the
        per-atom list. If the spin block cannot be parsed the list is empty and value is NaN
        (the screen's _safe_calculate marks the descriptor failed — acceptable, screening-grade).
        """

        output = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=solvent_flag(req.xtb_gbsa_name),
            optimize=False,
        )
        spins = parse_atomic_spin_populations(output.stdout)
        value = max(spins) if spins else float("nan")
        return value, {
            "engine": "XTBEngine",
            "quantity": req.quantity,
            "atomic_spin_density": spins,
            "stdout": output.stdout,
            "parsed_json": output.parsed_json,
        }

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
            # Check the subprocess exit code FIRST: a nonzero exit means xTB failed, and a
            # present-but-garbage xtbout.json must not mask that with a JSON parse error.
            # Parse the JSON only on success.
            if completed.returncode != 0:
                raise RuntimeError(
                    "xTB failed with exit code "
                    f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
                )
            json_path = Path(tmpdir) / "xtbout.json"
            parsed_json = None
            if json_path.exists():
                parsed_json = parse_xtb_json(json_path.read_text(encoding="utf-8"))
            optimized_xyz = None
            opt_path = Path(tmpdir) / "xtbopt.xyz"
            if optimize and opt_path.exists():
                optimized_xyz = opt_path.read_text(encoding="utf-8")
        return XTBRunOutput(
            stdout=completed.stdout,
            parsed_json=parsed_json,
            optimized_xyz=optimized_xyz,
        )

    def _optical_gap(self, req: CalcRequest) -> tuple[float, "XTBRunOutput", dict[str, object]]:
        """Lowest singlet excitation via sTDA-xTB if ``stda`` is available, else the
        oligomer GFN2-xTB HOMO–LUMO gap as a clearly-labeled screening proxy (directive §4.1).
        """

        output = self._run_xtb(
            req,
            charge=req.species.charge,
            multiplicity=req.species.multiplicity,
            solvent_args=[],
            optimize=True,
        )
        stda_available = shutil.which(self.stda_binary) is not None
        if not stda_available:
            failure_type, failure_message = _failure_details(
                STDAUnavailableError(f"sTDA binary {self.stda_binary!r} was not found on PATH")
            )
            return (
                _gap_from_output(output),
                output,
                _optical_gap_metadata(
                    output,
                    optical_gap_method="homo_lumo_hexamer_fallback",
                    stda_available=False,
                    stda_attempted=False,
                    stda_status="not_available",
                    fallback_used=True,
                    stda_failure_type=failure_type,
                    stda_failure_message=failure_message,
                ),
            )
        if output.optimized_xyz is None:
            failure_type, failure_message = _failure_details(
                OptimizedGeometryMissingError(
                    "optimized geometry was not captured from xtbopt.xyz"
                )
            )
            return (
                _gap_from_output(output),
                output,
                _optical_gap_metadata(
                    output,
                    optical_gap_method="homo_lumo_hexamer_fallback",
                    stda_available=True,
                    stda_attempted=False,
                    stda_status="missing_optimized_geometry",
                    fallback_used=True,
                    stda_failure_type=failure_type,
                    stda_failure_message=failure_message,
                ),
            )
        try:
            excitation_eV = self._stda_lowest_excitation(req, output.optimized_xyz)
        except Exception as exc:  # noqa: BLE001 - all sTDA failures degrade with provenance.
            failure_type, failure_message = _failure_details(exc)
            status = exc.stage if isinstance(exc, STDAStageError) else "stda_failed"
            return (
                _gap_from_output(output),
                output,
                _optical_gap_metadata(
                    output,
                    optical_gap_method="homo_lumo_hexamer_fallback",
                    stda_available=True,
                    stda_attempted=True,
                    stda_status=status,
                    fallback_used=True,
                    stda_failure_type=failure_type,
                    stda_failure_message=failure_message,
                ),
            )
        return (
            excitation_eV,
            output,
            _optical_gap_metadata(
                output,
                optical_gap_method="stda-xtb",
                stda_available=True,
                stda_attempted=True,
                stda_status="success",
                fallback_used=False,
                stda_failure_type="",
                stda_failure_message="",
            ),
        )

    def _stda_lowest_excitation(self, req: CalcRequest, xyz: str) -> float:
        """Run xTB (dump wavefunction) + ``stda -xtb`` and return the lowest singlet eV."""

        with tempfile.TemporaryDirectory(prefix="eps-stda-") as tmpdir:
            xyz_path = Path(tmpdir) / "input.xyz"
            xyz_path.write_text(xyz, encoding="utf-8")
            # xtb writes the sTDA wavefunction (wfn.xtb) when asked to.
            xtb_cmd = [
                self.binary,
                str(xyz_path),
                "--gfn",
                "2",
                "--chrg",
                str(req.species.charge),
                "--uhf",
                str(max(req.species.multiplicity - 1, 0)),
                *solvent_flag(req.xtb_gbsa_name),
            ]
            xtb_done = subprocess.run(xtb_cmd, cwd=tmpdir, check=False, capture_output=True, text=True)
            if xtb_done.returncode != 0:
                raise STDAStageError(
                    "stda_preparation_failed",
                    f"xtb (for sTDA) failed: exit {xtb_done.returncode}. STDERR: {xtb_done.stderr}",
                )
            stda_done = subprocess.run(
                [self.stda_binary, "-xtb", "-e", str(self.stda_energy_window_eV)],
                cwd=tmpdir, check=False, capture_output=True, text=True,
            )
            if stda_done.returncode != 0:
                raise STDAStageError(
                    "stda_failed",
                    f"stda failed: exit {stda_done.returncode}. STDERR: {stda_done.stderr}",
                )
            try:
                return parse_stda_lowest_excitation(stda_done.stdout)
            except ValueError as exc:
                raise STDAStageError("parse_failed", str(exc)) from exc


def _optical_gap_metadata(
    output: XTBRunOutput,
    *,
    optical_gap_method: str,
    stda_available: bool,
    stda_attempted: bool,
    stda_status: str,
    fallback_used: bool,
    stda_failure_type: str,
    stda_failure_message: str,
) -> dict[str, object]:
    optimized_xyz = output.optimized_xyz
    optimized_geometry_available = optimized_xyz is not None
    optimized_geometry_sha256 = (
        hashlib.sha256(optimized_xyz.encode("utf-8")).hexdigest()
        if optimized_geometry_available
        else ""
    )
    return {
        "optical_gap_method": optical_gap_method,
        "optical_gap_geometry_source": "xtbopt.xyz" if optimized_geometry_available else "",
        "optimized_geometry_available": optimized_geometry_available,
        "optimized_geometry_sha256": optimized_geometry_sha256,
        "stda_available": stda_available,
        "stda_attempted": stda_attempted,
        "stda_status": stda_status,
        "fallback_used": fallback_used,
        "stda_failure_type": stda_failure_type,
        "stda_failure_message": _trim_failure_message(stda_failure_message),
    }


def _failure_details(exc: BaseException) -> tuple[str, str]:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return exc.__class__.__name__, _trim_failure_message(message)


def _trim_failure_message(message: str) -> str:
    first_line = message.splitlines()[0] if message else ""
    return first_line[:STDA_FAILURE_MESSAGE_LIMIT]


def solvent_flag(xtb_gbsa_name: str | None) -> list[str]:
    """Return xTB ALPB solvent arguments from a versioned solvent keyword."""

    if xtb_gbsa_name:
        return ["--alpb", xtb_gbsa_name]
    return []


def parse_stda_lowest_excitation(stdout: str) -> float:
    """Parse the lowest singlet excitation energy (eV) from ``stda -xtb`` output.

    sTDA prints a state table whose rows start with a state index followed by the
    excitation energy in eV. The first state is the lowest singlet excitation = the
    sTDA-xTB optical gap (directive §4.1).
    """

    in_table = False
    for line in stdout.splitlines():
        header = line.lower()
        if "state" in header and "eV".lower() in header and ("nm" in header or "ev" in header):
            in_table = True
            continue
        if in_table:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    int(parts[0])
                    return float(parts[1])
                except (ValueError, IndexError):
                    continue
    raise ValueError("Could not parse a sTDA excitation energy from stda output")


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

    This parser supports the explicit HOMO-LUMO fallback used when the sTDA-xTB
    optical-gap workflow is unavailable or fails.
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


def parse_frontier_orbital_eV(stdout: str, which: str) -> float:
    """Parse the HOMO or LUMO orbital energy (eV) from the xTB orbital eigenvalue block.

    xTB prints an "Orbital Energies and Occupations" table whose occupied/virtual boundary
    rows are tagged ``(HOMO)`` and ``(LUMO)``. Each row is::

        #    Occupation    Energy/Eh     Energy/eV
       21        2.0000    -0.4...      -12.3...  (HOMO)

    The eV column is the last numeric field on the tagged line.
    """

    tag = "(HOMO)" if which == "homo" else "(LUMO)"
    for line in stdout.splitlines():
        if tag in line:
            numbers = re.findall(r"-?\d+\.\d+", line)
            if numbers:
                return float(numbers[-1])
    raise ValueError(f"Could not parse {which.upper()} orbital energy from xTB stdout")


def parse_atomic_spin_populations(stdout: str) -> list[float]:
    """Parse per-atom Mulliken spin populations from xTB stdout (best-effort).

    Scans for a spin-population section (a header containing "spin" plus "population"/"density")
    and collects the trailing numeric column per atom row. Returns ``[]`` when no such block is
    present, so the caller can degrade gracefully.

    VERIFIED LIMITATION (xtb 6.4.1, captured real open-shell radical-cation single point — see
    ``tests/fixtures/xtb_radical_cation_stdout.txt``): at the production verbosity used by
    ``XTBEngine._run_xtb`` (no ``--verbose``/raised print level), xtb 6.4.1 emits **no per-atom
    spin-population block** — the only "spin" token is the scalar setup line ``spin : 0.5``, and
    ``xtbout.json`` carries only ``partial charges`` (no atomic spin density). This parser therefore
    returns ``[]`` for the real production output, so ``_spin_density`` yields NaN and the screen's
    ``_safe_calculate`` marks the descriptor failed (screening-grade, acceptable). The regex is kept
    correct for the case where a higher-verbosity run does print such a block; see STATUS open debt
    for the always-NaN ``spin_density`` finding.
    """

    lines = stdout.splitlines()
    spins: list[float] = []
    in_block = False
    for line in lines:
        lowered = line.lower()
        if "spin" in lowered and ("population" in lowered or "density" in lowered):
            in_block = True
            spins = []
            continue
        if in_block:
            parts = line.split()
            if not parts:
                if spins:
                    break
                continue
            try:
                int(parts[0])
            except ValueError:
                if spins:
                    break
                continue
            numbers = re.findall(r"-?\d+\.\d+", line)
            if numbers:
                spins.append(float(numbers[-1]))
    return spins


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

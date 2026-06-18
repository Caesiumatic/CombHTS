"""Gaussian 16 (B3LYP) Tier-2 DFT backend for the Engine interface — BUILD ONLY.

This adapter mirrors ``XTBEngine``'s structure and the SAME charge/multiplicity convention
for adiabatic redox (oxidation -> charge+1, multiplicity+1; the Eox-relevant ΔSCF is
``ΔG = G(cation) − G(neutral)``). It NEVER fabricates a value: if the ``g16`` binary is
absent, ``run()`` raises a clear RuntimeError. Following the Task-1a lesson, the subprocess
return code is checked BEFORE the log is parsed, so a present-but-truncated log cannot mask a
real Gaussian failure.

No Gaussian job is launched anywhere in the test suite; live behavior is exercised only when
``g16`` is actually on PATH (the live test skips otherwise, exactly like the xtb tests).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from eps.engines.base import CalcRequest, CalcResult, Engine
from eps.engines.xtb import HARTREE_TO_EV
from eps.structures import smiles_to_xyz

GAUSSIAN_METHOD_LABEL = "b3lyp-6-31g(d,p)-smd"
DEFAULT_METHOD = "B3LYP"
DEFAULT_BASIS = "6-31G(d,p)"

_SCF_DONE_RE = re.compile(r"SCF Done:\s+E\([^)]*\)\s*=\s*(-?\d+\.\d+)")
_GIBBS_RE = re.compile(r"Sum of electronic and thermal Free Energies=\s*(-?\d+\.\d+)")


class GaussianEngine(Engine):
    """Run Gaussian 16 ΔSCF calculations through subprocess (build-only scaffold).

    Charge/multiplicity rule for adiabatic redox (identical to XTBEngine):
    - IP oxidizes (q, m) -> (q+1, m+1); ΔG = G(cation) − G(neutral).
    - EA reduces  (q, m) -> (q-1, m+1); ΔG = G(neutral) − G(anion).
    """

    def __init__(self, binary: str = "g16") -> None:
        self.binary = binary

    def run(self, req: CalcRequest) -> CalcResult:
        """Run one Gaussian request and return a scalar result. Never fakes a value."""

        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"Gaussian binary {self.binary!r} was not found on PATH. "
                "Load gaussian/g16 on the cluster; this engine never fabricates a value."
            )

        if req.quantity == "gas_energy":
            parsed = self._run_gaussian(
                req, charge=req.species.charge, multiplicity=req.species.multiplicity,
                optimize=True, solvent_smd=None,
            )
            return CalcResult(
                value=parsed["scf_energy_eV"], unit="eV", method=req.method,
                raw={"engine": "GaussianEngine", "quantity": req.quantity, "parsed": parsed},
            )
        if req.quantity == "adiabatic_ip":
            value, raw = self._adiabatic_redox(req, charge_delta=1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        if req.quantity == "adiabatic_ea":
            value, raw = self._adiabatic_redox(req, charge_delta=-1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        raise NotImplementedError(f"GaussianEngine does not implement quantity {req.quantity!r}")

    def _adiabatic_redox(self, req: CalcRequest, charge_delta: int) -> tuple[float, dict]:
        initial = req.species
        final_charge = initial.charge + charge_delta
        final_multiplicity = initial.multiplicity + 1

        initial_parsed = self._run_gaussian(
            req, charge=initial.charge, multiplicity=initial.multiplicity,
            optimize=True, solvent_smd=None,
        )
        final_parsed = self._run_gaussian(
            req, charge=final_charge, multiplicity=final_multiplicity,
            optimize=True, solvent_smd=None,
        )
        initial_energy = _redox_energy_Eh(initial_parsed)
        final_energy = _redox_energy_Eh(final_parsed)
        if charge_delta == -1:
            delta_eV = (initial_energy - final_energy) * HARTREE_TO_EV
        else:
            delta_eV = (final_energy - initial_energy) * HARTREE_TO_EV
        return delta_eV, {
            "engine": "GaussianEngine",
            "quantity": req.quantity,
            "initial_charge": initial.charge,
            "initial_multiplicity": initial.multiplicity,
            "final_charge": final_charge,
            "final_multiplicity": final_multiplicity,
            "initial_parsed": initial_parsed,
            "final_parsed": final_parsed,
        }

    def _run_gaussian(
        self,
        req: CalcRequest,
        *,
        charge: int,
        multiplicity: int,
        optimize: bool,
        solvent_smd: str | None,
    ) -> dict[str, float | None]:
        gjf = build_gaussian_input(
            req.species, charge, multiplicity, optimize=optimize, solvent_smd=solvent_smd
        )
        with tempfile.TemporaryDirectory(prefix="eps-g16-") as tmpdir:
            input_path = Path(tmpdir) / "input.gjf"
            input_path.write_text(gjf, encoding="utf-8")
            completed = subprocess.run(
                [self.binary, "input.gjf"],
                cwd=tmpdir,
                check=False,
                capture_output=True,
                text=True,
            )
            # Check the exit code FIRST (Task-1a lesson): a nonzero exit means Gaussian failed,
            # and a truncated/garbage log must not mask that with a parse error.
            if completed.returncode != 0:
                raise RuntimeError(
                    "Gaussian failed with exit code "
                    f"{completed.returncode}.\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
                )
            log_path = Path(tmpdir) / "input.log"
            log_text = log_path.read_text(encoding="utf-8") if log_path.exists() else completed.stdout
        return parse_gaussian_log(log_text)


def build_gaussian_input(
    species,
    charge: int,
    multiplicity: int,
    *,
    method: str = DEFAULT_METHOD,
    basis: str = DEFAULT_BASIS,
    optimize: bool = True,
    solvent_smd: str | None = None,
) -> str:
    """Return a valid Gaussian ``.gjf`` input string for one species/charge/multiplicity."""

    xyz = smiles_to_xyz(species.canonical_smiles, charge=charge)
    coordinate_lines = xyz.splitlines()[2:]  # drop the XYZ atom-count and comment lines

    keywords = [f"#p {method}/{basis}"]
    if optimize:
        keywords.append("Opt")
    keywords.append("SCF=Tight")
    if solvent_smd:
        keywords.append(f"SCRF=(SMD,Solvent={solvent_smd})")
    route = " ".join(keywords)

    title = f"CombHTS Tier-2 {species.canonical_smiles} charge={charge} mult={multiplicity}"
    lines = [route, "", title, "", f"{charge} {multiplicity}", *coordinate_lines, ""]
    return "\n".join(lines) + "\n"


def parse_gaussian_log(text: str) -> dict[str, float | None]:
    """Parse final SCF energy and (if present) thermally corrected Gibbs free energy.

    Returns energies in both Hartree and eV. Raises ValueError if no SCF energy is found.
    """

    scf_matches = _SCF_DONE_RE.findall(text)
    if not scf_matches:
        raise ValueError("Could not parse 'SCF Done' energy from Gaussian log")
    scf_energy_Eh = float(scf_matches[-1])

    gibbs_matches = _GIBBS_RE.findall(text)
    gibbs_energy_Eh = float(gibbs_matches[-1]) if gibbs_matches else None

    return {
        "scf_energy_Eh": scf_energy_Eh,
        "scf_energy_eV": scf_energy_Eh * HARTREE_TO_EV,
        "gibbs_free_energy_Eh": gibbs_energy_Eh,
        "gibbs_free_energy_eV": None if gibbs_energy_Eh is None else gibbs_energy_Eh * HARTREE_TO_EV,
    }


def _redox_energy_Eh(parsed: dict[str, float | None]) -> float:
    """Prefer the thermally corrected Gibbs free energy; fall back to the SCF energy."""

    gibbs = parsed.get("gibbs_free_energy_Eh")
    if gibbs is not None:
        return float(gibbs)
    return float(parsed["scf_energy_Eh"])

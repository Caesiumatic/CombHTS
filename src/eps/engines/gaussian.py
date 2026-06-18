"""Gaussian 16 (B3LYP) Tier-2 DFT backend for the Engine interface — BUILD ONLY.

This adapter mirrors ``XTBEngine``'s structure and the SAME charge/multiplicity convention
for adiabatic redox (oxidation -> charge+1, multiplicity+1; the Eox-relevant ΔSCF is
``ΔG = G(cation) − G(neutral)``). It NEVER fabricates a value: if the ``g16`` binary is
absent, ``run()`` raises a clear RuntimeError. Following the Task-1a lesson, the subprocess
return code is checked BEFORE the log is parsed, so a present-but-truncated log cannot mask a
real Gaussian failure.

The SMD solvent and the Freq/thermal-correction toggle are read from ``configs/tier2.yaml``
(via :func:`load_tier2_config`), not hardcoded: v1 defaults (smd_solvent=null, use_freq=false)
keep the original gas-phase ΔSCF behavior, while flipping those keys upgrades Eox to a solvated
ΔG. Gaussian Link0 ``%mem`` / ``%nprocshared`` lines are likewise config-driven so a real g16
job uses the requested memory and core count instead of single-core defaults.

No Gaussian job is launched anywhere in the test suite; live behavior is exercised only when
``g16`` is actually on PATH (the live test skips otherwise, exactly like the xtb tests).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from eps.engines.base import CalcRequest, CalcResult, Engine
from eps.engines.xtb import HARTREE_TO_EV
from eps.structures import smiles_to_xyz

GAUSSIAN_METHOD_LABEL = "b3lyp-6-31g(d,p)-smd"
DEFAULT_METHOD = "B3LYP"
DEFAULT_BASIS = "6-31G(d,p)"
DEFAULT_MEM = "8GB"
DEFAULT_NPROCSHARED = 8

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIER2_CONFIG = PROJECT_ROOT / "configs" / "tier2.yaml"

_SCF_DONE_RE = re.compile(r"SCF Done:\s+E\([^)]*\)\s*=\s*(-?\d+\.\d+)")
_GIBBS_RE = re.compile(r"Sum of electronic and thermal Free Energies=\s*(-?\d+\.\d+)")


@dataclass(frozen=True)
class Tier2Config:
    """Tier-2 DFT job parameters, normally loaded from ``configs/tier2.yaml``.

    v1 defaults reproduce the original build-only behavior (gas-phase ΔSCF, opt only):
    ``smd_solvent=None`` and ``use_freq=False``. Setting ``smd_solvent`` (e.g.
    ``"acetonitrile"``) and ``use_freq=True`` is the documented rigor toggle that upgrades
    Eox to a solvated ΔG. ``mem`` / ``nprocshared`` feed the Gaussian Link0 lines.
    """

    method: str = DEFAULT_METHOD
    basis: str = DEFAULT_BASIS
    smd_solvent: str | None = None
    use_freq: bool = False
    mem: str = DEFAULT_MEM
    nprocshared: int = DEFAULT_NPROCSHARED
    calibration_set: str = "benchmark_calibration_eligible"

    def method_label(self) -> str:
        """Human-readable one-line description of the effective Tier-2 method."""

        phase = f"SMD({self.smd_solvent})" if self.smd_solvent else "gas phase"
        rigor = "opt+freq (ΔG)" if self.use_freq else "opt only (ΔE_SCF)"
        return f"{self.method}/{self.basis}, {phase}, {rigor}"


def load_tier2_config(path: str | Path = DEFAULT_TIER2_CONFIG) -> Tier2Config:
    """Load Tier-2 DFT config from YAML, falling back to v1 defaults.

    A missing or empty file yields the gas-phase v1 defaults rather than raising, so the
    build-only scaffold and mock tests work without the file. Unknown keys are ignored.
    """

    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")

    smd = data.get("smd_solvent", None)
    smd_solvent = None if smd in (None, "", "null") else str(smd)
    return Tier2Config(
        method=str(data.get("method", DEFAULT_METHOD)),
        basis=str(data.get("basis", DEFAULT_BASIS)),
        smd_solvent=smd_solvent,
        use_freq=bool(data.get("use_freq", False)),
        mem=str(data.get("mem", DEFAULT_MEM)),
        nprocshared=int(data.get("nprocshared", DEFAULT_NPROCSHARED)),
        calibration_set=str(data.get("calibration_set", "benchmark_calibration_eligible")),
    )


class GaussianEngine(Engine):
    """Run Gaussian 16 ΔSCF calculations through subprocess (build-only scaffold).

    Charge/multiplicity rule for adiabatic redox (identical to XTBEngine):
    - IP oxidizes (q, m) -> (q+1, m+1); ΔG = G(cation) − G(neutral).
    - EA reduces  (q, m) -> (q-1, m+1); ΔG = G(neutral) − G(anion).
    """

    def __init__(self, binary: str = "g16", config: Tier2Config | None = None) -> None:
        self.binary = binary
        # Config-driven SMD/Freq/Link0; defaults to configs/tier2.yaml (v1 gas-phase ΔSCF).
        self.config = config if config is not None else load_tier2_config()

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
                optimize=True, solvent_smd=self.config.smd_solvent,
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
            optimize=True, solvent_smd=self.config.smd_solvent,
        )
        final_parsed = self._run_gaussian(
            req, charge=final_charge, multiplicity=final_multiplicity,
            optimize=True, solvent_smd=self.config.smd_solvent,
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
            "smd_solvent": self.config.smd_solvent,
            "use_freq": self.config.use_freq,
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
            req.species,
            charge,
            multiplicity,
            method=self.config.method,
            basis=self.config.basis,
            optimize=optimize,
            solvent_smd=solvent_smd,
            use_freq=self.config.use_freq,
            mem=self.config.mem,
            nprocshared=self.config.nprocshared,
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
    use_freq: bool = False,
    mem: str | None = DEFAULT_MEM,
    nprocshared: int | None = DEFAULT_NPROCSHARED,
) -> str:
    """Return a valid Gaussian ``.gjf`` input string for one species/charge/multiplicity.

    The Gaussian Link0 lines ``%mem`` / ``%nprocshared`` are prepended at the very top of the
    file (when provided) so a real g16 run uses the requested memory and core count instead of
    the single-core, default-memory behavior. ``use_freq`` adds the ``Freq`` route keyword for
    a thermal free-energy correction (the documented Tier-2 rigor toggle).
    """

    xyz = smiles_to_xyz(species.canonical_smiles, charge=charge)
    coordinate_lines = xyz.splitlines()[2:]  # drop the XYZ atom-count and comment lines

    keywords = [f"#p {method}/{basis}"]
    if optimize:
        keywords.append("Opt")
    if use_freq:
        keywords.append("Freq")
    keywords.append("SCF=Tight")
    if solvent_smd:
        keywords.append(f"SCRF=(SMD,Solvent={solvent_smd})")
    route = " ".join(keywords)

    link0: list[str] = []
    if mem:
        link0.append(f"%mem={mem}")
    if nprocshared:
        link0.append(f"%nprocshared={nprocshared}")

    title = f"CombHTS Tier-2 {species.canonical_smiles} charge={charge} mult={multiplicity}"
    lines = [*link0, route, "", title, "", f"{charge} {multiplicity}", *coordinate_lines, ""]
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

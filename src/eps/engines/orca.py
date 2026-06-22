"""ORCA 6.1 backend for the small openCOSMO-RS and optical-calibration pilots.

This is a real :class:`~eps.engines.base.Engine` implementation, but deliberately narrow:

- ``solvation_free_energy`` uses ORCA/openCOSMO-RS 24a (BP86/def2-TZVPD parametrization) and
  returns dGsolv in kcal/mol;
- ``optical_gap`` uses either ORCA sTDA or conventional TDA/TD-DFT on the identical geometry
  and returns the lowest singlet excitation in eV.

Every subprocess return code and the normal-termination marker are checked before parsing. No
value is fabricated when ORCA is absent or a calculation fails.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

from eps.engines.base import CalcRequest, CalcResult, Engine, SpeciesSpec
from eps.structures import smiles_to_xyz

_COSMORS_DGSOLV_RE = re.compile(
    r"Free energy of solvation \(dGsolv\)\s*:\s*[-+0-9.Ee]+\s+Eh\s+([-+0-9.Ee]+)\s+kcal/mol"
)
_EXPLICIT_STATE_EV_RE = re.compile(
    r"STATE\s+\d+\s*:\s*E=\s*[-+0-9.Ee]+\s+au\s+([-+0-9.Ee]+)\s+eV",
    re.IGNORECASE,
)
_ABSORPTION_ROW_RE = re.compile(
    r"^\s*\d+\s+([-+0-9.]+)\s+[-+0-9.]+\s+[-+0-9.Ee]+(?:\s+[-+0-9.Ee]+){4}\s*$",
    re.MULTILINE,
)
_ELECTRIC_ABSORPTION_HEADER = "ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS"
_VELOCITY_ABSORPTION_HEADER = "ABSORPTION SPECTRUM VIA TRANSITION VELOCITY DIPOLE MOMENTS"
CM1_PER_EV = 8065.544005


@dataclass(frozen=True)
class OrcaConfig:
    """ORCA pilot settings with explicit method identity and memory units."""

    binary: str = "orca"
    nprocs: int = 4
    maxcore_mb: int = 2000
    functional: str = "CAM-B3LYP"
    basis: str = "def2-SVP"
    optical_mode: str = "stda"
    optical_solvent: str | None = "Acetonitrile"
    nroots: int = 5
    ethresh_eV: float = 6.0

    def method_label(self) -> str:
        """Cache-safe label describing the effective ORCA calculation."""

        if self.optical_mode == "cosmors":
            return "orca6.1/opencosmors24a/bp86/def2-tzvpd"
        solvent = self.optical_solvent.lower() if self.optical_solvent else "gas"
        return (
            f"orca6.1/{self.functional.lower()}/{self.basis.lower()}/"
            f"{self.optical_mode.lower()}/{solvent}"
        )


class OrcaEngine(Engine):
    """Run one ORCA 6.1 pilot quantity through the standard Engine interface."""

    def __init__(self, config: OrcaConfig | None = None) -> None:
        self.config = config if config is not None else OrcaConfig()

    def run(self, req: CalcRequest) -> CalcResult:
        """Run a supported ORCA request, checking process success before parsing."""

        binary = shutil.which(self.config.binary)
        if binary is None:
            raise RuntimeError(
                f"ORCA binary {self.config.binary!r} was not found on PATH. "
                "Load openmpi/4.1.8 and orca/6.1.0-418 on Lop."
            )
        if req.quantity == "solvation_free_energy":
            if not req.solvent_model_name:
                raise ValueError("ORCA openCOSMO-RS requires CalcRequest.solvent_model_name")
            input_text = build_orca_cosmors_input(
                req.species,
                req.solvent_model_name,
                nprocs=self.config.nprocs,
                maxcore_mb=self.config.maxcore_mb,
            )
            output = self._run(binary, input_text)
            value = parse_orca_cosmors_dg_kcal_mol(output)
            return CalcResult(
                value=value,
                unit="kcal/mol",
                method=req.method,
                raw={
                    "engine": "OrcaEngine",
                    "quantity": req.quantity,
                    "orca_solvent": req.solvent_model_name,
                    "method_label": self.config.method_label(),
                },
            )
        if req.quantity == "optical_gap":
            input_text = build_orca_optical_input(req.species, self.config)
            output = self._run(binary, input_text)
            value = parse_orca_lowest_excitation_eV(output)
            return CalcResult(
                value=value,
                unit="eV",
                method=req.method,
                raw={
                    "engine": "OrcaEngine",
                    "quantity": req.quantity,
                    "optical_mode": self.config.optical_mode,
                    "functional": self.config.functional,
                    "basis": self.config.basis,
                    "solvent": self.config.optical_solvent,
                },
            )
        raise NotImplementedError(f"OrcaEngine does not implement quantity {req.quantity!r}")

    def _run(self, binary: str, input_text: str) -> str:
        persistent_root = os.environ.get("EPS_ORCA_WORK_ROOT")
        if persistent_root:
            root = Path(persistent_root).resolve()
            root.mkdir(parents=True, exist_ok=True)
            context = nullcontext(tempfile.mkdtemp(prefix="eps-orca-", dir=root))
        else:
            context = tempfile.TemporaryDirectory(prefix="eps-orca-")
        with context as tmpdir:
            input_path = Path(tmpdir) / "pilot.inp"
            input_path.write_text(input_text, encoding="utf-8")
            completed = subprocess.run(
                [binary, str(input_path)],
                cwd=tmpdir,
                check=False,
                capture_output=True,
                text=True,
            )
            output = completed.stdout + "\n" + completed.stderr
            if persistent_root:
                (Path(tmpdir) / "pilot.out").write_text(output, encoding="utf-8")
        if completed.returncode != 0:
            tail = "\n".join(output.splitlines()[-30:])
            raise RuntimeError(f"ORCA failed with exit {completed.returncode}:\n{tail}")
        if "ORCA TERMINATED NORMALLY" not in output:
            tail = "\n".join(output.splitlines()[-30:])
            raise RuntimeError(f"ORCA output lacks normal-termination marker:\n{tail}")
        return output


def build_orca_cosmors_input(
    species: SpeciesSpec,
    solvent_model_name: str,
    *,
    nprocs: int = 4,
    maxcore_mb: int = 2000,
) -> str:
    """Build an ORCA/openCOSMO-RS 24a input using the internal solvent database."""

    coordinates = _coordinates(species)
    return (
        f"! COSMORS({solvent_model_name}) TightSCF\n"
        f"%pal nprocs {nprocs} end\n"
        f"%maxcore {maxcore_mb}\n"
        f"* xyz {species.charge} {species.multiplicity}\n"
        f"{coordinates}\n*\n"
    )


def build_orca_optical_input(species: SpeciesSpec, config: OrcaConfig) -> str:
    """Build an ORCA sTDA or conventional TDA/TD-DFT single-point input."""

    mode = config.optical_mode.lower()
    if mode not in {"stda", "tddft"}:
        raise ValueError(f"optical_mode must be 'stda' or 'tddft', got {config.optical_mode!r}")
    solvent = f" CPCM({config.optical_solvent})" if config.optical_solvent else ""
    header = (
        f"! {config.functional} {config.basis} RIJCOSX def2/J TightSCF "
        f"SmallPrint PrintGap NoPop{solvent}\n"
    )
    serial_memory = config.maxcore_mb * config.nprocs
    if mode == "stda":
        tddft = (
            "%tddft\n"
            "  Mode sTDA\n"
            f"  EThresh {config.ethresh_eV}\n"
            f"  MaxCore {serial_memory}\n"
            "end\n"
        )
    else:
        tddft = (
            "%tddft\n"
            f"  NRoots {config.nroots}\n"
            "  TDA true\n"
            f"  MaxCore {config.maxcore_mb}\n"
            "end\n"
        )
    return (
        header
        + f"%pal nprocs {config.nprocs} end\n"
        + f"%maxcore {config.maxcore_mb}\n"
        + tddft
        + f"* xyz {species.charge} {species.multiplicity}\n"
        + _coordinates(species)
        + "\n*\n"
    )


def parse_orca_cosmors_dg_kcal_mol(output: str) -> float:
    """Parse ORCA's openCOSMO-RS free energy of solvation in kcal/mol."""

    match = _COSMORS_DGSOLV_RE.search(output)
    if match is None:
        raise ValueError("Could not parse ORCA openCOSMO-RS dGsolv")
    return float(match.group(1))


def parse_orca_lowest_excitation_eV(output: str) -> float:
    """Parse the lowest singlet excitation in eV from ORCA sTDA or TDA/TD-DFT output."""

    explicit = [float(value) for value in _EXPLICIT_STATE_EV_RE.findall(output) if float(value) > 0]
    if explicit:
        return min(explicit)
    wavenumbers: list[float] = []
    for block in _electric_absorption_blocks(output):
        wavenumbers.extend(
            float(value) for value in _ABSORPTION_ROW_RE.findall(block) if float(value) > 0
        )
    if wavenumbers:
        return min(wavenumbers) / CM1_PER_EV
    raise ValueError("Could not parse an ORCA sTDA/TD-DFT excitation energy")


def _electric_absorption_blocks(output: str) -> list[str]:
    """Return only electric-dipole spectrum blocks, excluding unrelated numeric tables."""

    blocks: list[str] = []
    remainder = output
    while _ELECTRIC_ABSORPTION_HEADER in remainder:
        _, after_header = remainder.split(_ELECTRIC_ABSORPTION_HEADER, 1)
        if _VELOCITY_ABSORPTION_HEADER in after_header:
            block, remainder = after_header.split(_VELOCITY_ABSORPTION_HEADER, 1)
        else:
            block, remainder = after_header, ""
        blocks.append(block)
    return blocks


def _coordinates(species: SpeciesSpec) -> str:
    xyz = smiles_to_xyz(species.canonical_smiles, charge=species.charge)
    lines = xyz.splitlines()
    if len(lines) < 3:
        raise ValueError("Generated XYZ contains no coordinates")
    return "\n".join(lines[2:])

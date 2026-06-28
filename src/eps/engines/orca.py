"""ORCA 6.1 backend for the openCOSMO-RS, optical-calibration, and Tier-2 DFT-redox work.

This is a real :class:`~eps.engines.base.Engine` implementation:

- ``solvation_free_energy`` uses ORCA/openCOSMO-RS 24a (BP86/def2-TZVPD parametrization) and
  returns dGsolv in kcal/mol;
- ``optical_gap`` uses either ORCA sTDA or conventional TDA/TD-DFT on the identical geometry
  and returns the lowest singlet excitation in eV;
- ``adiabatic_ip`` / ``adiabatic_ea`` run the directive §4.2 Tier-2 ΔSCF redox: a B3LYP/6-31G(d,p)
  geometry optimization of the neutral and the cation (IP) or anion (EA), optionally with
  per-solvent SMD continuum and a Freq thermal/ZPE correction (ΔG instead of ΔE_SCF), and a
  Hirshfeld spin-population read on the open-shell radical for α–α′/α–β site mapping.

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
HARTREE_TO_EV = 27.211386245988

# After a geometry optimization ORCA prints "FINAL SINGLE POINT ENERGY" once per SCF cycle; the
# LAST occurrence is the converged optimized electronic energy.
_FINAL_SCF_ENERGY_RE = re.compile(r"FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)")
# With Freq, the thermochemistry block prints the thermally + ZPE corrected Gibbs free energy.
_GIBBS_ENERGY_RE = re.compile(r"Final Gibbs free energy\s*\.*\s*(-?\d+\.\d+)\s*Eh", re.IGNORECASE)
# "%output Print[P_Hirshfeld] 1 end" emits a HIRSHFELD ANALYSIS table: "<idx> <element> <charge> <spin>".
_HIRSHFELD_ROW_RE = re.compile(
    r"^\s*\d+\s+[A-Z][a-z]?\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$", re.MULTILINE
)


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
    # Tier-2 DFT ΔSCF redox (directive §4.2). These are independent of the optical/cosmos fields
    # above so the same OrcaConfig dataclass can drive any ORCA quantity.
    redox_functional: str = "B3LYP"
    redox_basis: str = "6-31G(d,p)"
    redox_use_freq: bool = False  # True -> Opt+Freq, Eox = ΔG (thermal + ZPE); False -> ΔE_SCF.
    redox_hirshfeld: bool = True  # Hirshfeld spin populations on the open-shell radical.
    redox_smd: bool = True  # Apply per-request SMD (req.solvent_model_name); gas phase if no solvent.

    def method_label(self) -> str:
        """Cache-safe label describing the effective ORCA calculation."""

        if self.optical_mode == "cosmors":
            return "orca6.1/opencosmors24a/bp86/def2-tzvpd"
        solvent = self.optical_solvent.lower() if self.optical_solvent else "gas"
        return (
            f"orca6.1/{self.functional.lower()}/{self.basis.lower()}/"
            f"{self.optical_mode.lower()}/{solvent}"
        )

    def redox_method_label(self) -> str:
        """Cache-safe label for the Tier-2 ΔSCF redox config.

        The specific SMD solvent is NOT encoded here — it varies per triad and already enters the
        SQLite cache key via ``solvent_name`` — so this label captures only functional/basis and the
        SMD-on/Freq-on toggles (e.g. ``orca6.1/b3lyp/6-31g(d,p)/smd/freq:on``).
        """

        phase = "smd" if self.redox_smd else "gas"
        freq = "freq:on" if self.redox_use_freq else "freq:off"
        return f"orca6.1/{self.redox_functional.lower()}/{self.redox_basis.lower()}/{phase}/{freq}"


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
        if req.quantity == "adiabatic_ip":
            value, raw = self._adiabatic_redox(binary, req, charge_delta=1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        if req.quantity == "adiabatic_ea":
            value, raw = self._adiabatic_redox(binary, req, charge_delta=-1)
            return CalcResult(value=value, unit="eV", method=req.method, raw=raw)
        raise NotImplementedError(f"OrcaEngine does not implement quantity {req.quantity!r}")

    def _adiabatic_redox(self, binary: str, req: CalcRequest, charge_delta: int) -> tuple[float, dict]:
        """Directive §4.2 adiabatic ΔSCF: optimize neutral + ion, return ΔE_SCF or ΔG in eV.

        IP (charge_delta=+1): ΔX = X(cation) − X(neutral); EA (−1): ΔX = X(neutral) − X(anion).
        X = Gibbs free energy when ``redox_use_freq`` else the optimized SCF energy. The ion is the
        open-shell radical (multiplicity +1) whose Hirshfeld spin populations are returned for
        α–α′/α–β coupling-site mapping.
        """

        cfg = self.config
        initial = req.species
        final_charge = initial.charge + charge_delta
        final_multiplicity = initial.multiplicity + 1
        smd_solvent = req.solvent_model_name if cfg.redox_smd else None

        initial_parsed = self._run_redox_species(
            binary, initial, charge=initial.charge, multiplicity=initial.multiplicity,
            smd_solvent=smd_solvent, hirshfeld=False,
        )
        final_parsed = self._run_redox_species(
            binary, initial, charge=final_charge, multiplicity=final_multiplicity,
            smd_solvent=smd_solvent, hirshfeld=cfg.redox_hirshfeld,
        )
        initial_energy = _redox_energy_eh(initial_parsed)
        final_energy = _redox_energy_eh(final_parsed)
        if charge_delta == -1:
            delta_eV = (initial_energy - final_energy) * HARTREE_TO_EV
        else:
            delta_eV = (final_energy - initial_energy) * HARTREE_TO_EV
        return delta_eV, {
            "engine": "OrcaEngine",
            "quantity": req.quantity,
            "method_label": cfg.redox_method_label(),
            "smd_solvent": smd_solvent,
            "use_freq": cfg.redox_use_freq,
            "initial_charge": initial.charge,
            "initial_multiplicity": initial.multiplicity,
            "final_charge": final_charge,
            "final_multiplicity": final_multiplicity,
            "initial_parsed": initial_parsed,
            "final_parsed": final_parsed,
        }

    def _run_redox_species(
        self,
        binary: str,
        species: SpeciesSpec,
        *,
        charge: int,
        multiplicity: int,
        smd_solvent: str | None,
        hirshfeld: bool,
    ) -> dict:
        cfg = self.config
        input_text = build_orca_redox_input(
            species, charge, multiplicity,
            functional=cfg.redox_functional, basis=cfg.redox_basis,
            use_freq=cfg.redox_use_freq, hirshfeld=hirshfeld, smd_solvent=smd_solvent,
            nprocs=cfg.nprocs, maxcore_mb=cfg.maxcore_mb,
        )
        output = self._run(binary, input_text)
        scf_eh = parse_orca_final_scf_energy_eh(output)
        parsed: dict = {"scf_energy_Eh": scf_eh, "energy_basis": "scf"}
        if cfg.redox_use_freq:
            parsed["gibbs_free_energy_Eh"] = parse_orca_gibbs_energy_eh(output)
            parsed["energy_basis"] = "gibbs"
        if hirshfeld:
            parsed["hirshfeld_spin_populations"] = parse_orca_hirshfeld_spin_populations(output)
        return parsed

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


def build_orca_redox_input(
    species: SpeciesSpec,
    charge: int,
    multiplicity: int,
    *,
    functional: str = "B3LYP",
    basis: str = "6-31G(d,p)",
    use_freq: bool = False,
    hirshfeld: bool = False,
    smd_solvent: str | None = None,
    nprocs: int = 4,
    maxcore_mb: int = 2000,
) -> str:
    """Build an ORCA §4.2 ΔSCF redox input (Opt, optional Freq / SMD / Hirshfeld).

    SMD is requested through the CPCM block (``smd true`` + ``SMDsolvent``), the directive's
    solvent-specific continuum. Hirshfeld spin populations are requested via
    ``%output Print[P_Hirshfeld] 1``.
    """

    keywords = [f"! {functional} {basis} Opt TightSCF"]
    if use_freq:
        keywords[0] += " Freq"
    blocks = [f"%pal nprocs {nprocs} end", f"%maxcore {maxcore_mb}"]
    if smd_solvent:
        blocks.append(f'%cpcm\n  smd true\n  SMDsolvent "{smd_solvent}"\nend')
    if hirshfeld:
        blocks.append("%output\n  Print[P_Hirshfeld] 1\nend")
    coordinates = _coordinates_for(species, charge)
    return (
        "\n".join(keywords)
        + "\n"
        + "\n".join(blocks)
        + "\n"
        + f"* xyz {charge} {multiplicity}\n"
        + coordinates
        + "\n*\n"
    )


def parse_orca_final_scf_energy_eh(output: str) -> float:
    """Parse the converged (last) ``FINAL SINGLE POINT ENERGY`` in Hartree."""

    matches = _FINAL_SCF_ENERGY_RE.findall(output)
    if not matches:
        raise ValueError("Could not parse an ORCA FINAL SINGLE POINT ENERGY")
    return float(matches[-1])


def parse_orca_gibbs_energy_eh(output: str) -> float:
    """Parse the (last) thermally + ZPE corrected ``Final Gibbs free energy`` in Hartree."""

    matches = _GIBBS_ENERGY_RE.findall(output)
    if not matches:
        raise ValueError("Could not parse an ORCA Final Gibbs free energy (was Freq requested?)")
    return float(matches[-1])


def parse_orca_hirshfeld_spin_populations(output: str) -> list[float]:
    """Parse the per-atom Hirshfeld SPIN column from the HIRSHFELD ANALYSIS table."""

    if "HIRSHFELD ANALYSIS" not in output:
        raise ValueError("ORCA output has no HIRSHFELD ANALYSIS block")
    block = output.split("HIRSHFELD ANALYSIS", 1)[1]
    return [float(spin) for _charge, spin in _HIRSHFELD_ROW_RE.findall(block)]


def _redox_energy_eh(parsed: dict) -> float:
    """Prefer the thermally corrected Gibbs free energy; fall back to the SCF energy."""

    gibbs = parsed.get("gibbs_free_energy_Eh")
    return float(gibbs) if gibbs is not None else float(parsed["scf_energy_Eh"])


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
    return _coordinates_for(species, species.charge)


def _coordinates_for(species: SpeciesSpec, charge: int) -> str:
    xyz = smiles_to_xyz(species.canonical_smiles, charge=charge)
    lines = xyz.splitlines()
    if len(lines) < 3:
        raise ValueError("Generated XYZ contains no coordinates")
    return "\n".join(lines[2:])

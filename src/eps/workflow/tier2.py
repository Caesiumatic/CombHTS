"""Tier-2 DFT dry-run: write Gaussian .gjf inputs for inspection. NEVER runs g16.

This is an EXPERIMENTAL, build-only helper. It reads a Tier-1 survivors CSV and writes the
neutral + cation Gaussian inputs for each UNIQUE monomer (gas-phase ΔSCF for Eox depends only
on the monomer, so inputs are deduplicated by canonical SMILES). A human inspects the inputs;
launching the Tier-2 batch at scale is a PI / T8 decision and is out of scope here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from eps.engines.base import SpeciesSpec
from eps.engines.gaussian import build_gaussian_input

# Rough per-input cost for a B3LYP/6-31G(d,p) Opt of a small monomer/cation on the cluster.
# Deliberately coarse — for human capacity planning only, not a benchmark.
DEFAULT_CPU_HOURS_PER_INPUT = 2.0


@dataclass
class Tier2DryRunResult:
    """Outputs of the Tier-2 input-generation dry run (no g16 executed)."""

    outdir: Path
    n_survivors: int
    n_unique_monomers: int
    input_paths: list[Path] = field(default_factory=list)
    estimated_cpu_hours: float = 0.0


def write_tier2_dry_run_inputs(
    survivors_path: str | Path,
    outdir: str | Path,
    *,
    cpu_hours_per_input: float = DEFAULT_CPU_HOURS_PER_INPUT,
) -> Tier2DryRunResult:
    """Write neutral+cation .gjf inputs per unique survivor monomer. Does NOT run Gaussian."""

    frame = pd.read_csv(survivors_path)
    if "monomer_canonical_smiles" not in frame.columns:
        raise ValueError(
            f"{survivors_path} lacks a 'monomer_canonical_smiles' column required for Tier-2 inputs"
        )

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)

    seen: dict[str, str] = {}
    for _, row in frame.iterrows():
        smiles = str(row["monomer_canonical_smiles"])
        if smiles and smiles not in seen:
            seen[smiles] = str(row.get("monomer_name", smiles)) if "monomer_name" in frame.columns else smiles

    input_paths: list[Path] = []
    for index, (smiles, name) in enumerate(seen.items()):
        safe = _safe_name(name) or f"monomer{index:04d}"
        species = SpeciesSpec(canonical_smiles=smiles, charge=0, multiplicity=1)
        neutral = build_gaussian_input(species, charge=0, multiplicity=1)
        cation = build_gaussian_input(species, charge=1, multiplicity=2)
        neutral_path = out / f"{index:04d}_{safe}_neutral.gjf"
        cation_path = out / f"{index:04d}_{safe}_cation.gjf"
        neutral_path.write_text(neutral, encoding="utf-8")
        cation_path.write_text(cation, encoding="utf-8")
        input_paths.extend([neutral_path, cation_path])

    return Tier2DryRunResult(
        outdir=out,
        n_survivors=int(len(frame)),
        n_unique_monomers=len(seen),
        input_paths=input_paths,
        estimated_cpu_hours=len(input_paths) * float(cpu_hours_per_input),
    )


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_")

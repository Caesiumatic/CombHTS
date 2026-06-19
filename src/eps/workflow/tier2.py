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
from eps.scoring import add_composite_score, load_scoring_config
from eps.workflow.tier1 import load_tier1_config

# Rough per-input cost for a B3LYP/6-31G(d,p) Opt of a small monomer/cation on the cluster.
# Deliberately coarse — for human capacity planning only, not a benchmark.
DEFAULT_CPU_HOURS_PER_INPUT = 2.0

# Directive §4.2 refined window margin: the monomer adiabatic IP must sit at least this far BELOW
# the solvent anodic limit (tighter than the Tier-1 0.3 V gate) before a triad survives Tier-2.
DEFAULT_REFINED_WINDOW_MARGIN_V = 0.5

# Recognized per-monomer DFT Eox columns in a Tier-2 DFT results CSV (already V vs Ag/AgCl).
_DFT_EOX_COLUMNS = (
    "tier2_monomer_Eox_V_vs_AgAgCl",
    "dft_monomer_Eox_V_vs_AgAgCl",
)


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


@dataclass
class Tier2RefinedResult:
    """Outputs of the Tier-2 refined screen (tighter window filter + §5 composite re-rank)."""

    refined: pd.DataFrame
    n_tier1_survivors: int
    n_tier2_survivors: int
    refined_window_margin_V: float
    tier2_dft_pending: bool
    output_path: Path


def run_tier2_refined_screen(
    survivors_path: str | Path,
    output_path: str | Path,
    *,
    dft_results_path: str | Path | None = None,
    tier1_config_path: str | Path | None = None,
    scoring_config_path: str | Path | None = None,
    refined_window_margin_V: float = DEFAULT_REFINED_WINDOW_MARGIN_V,
) -> Tier2RefinedResult:
    """Directive §4.2 refined screen: tighter window filter on Tier-1 survivors, then §5 re-rank.

    Takes the Tier-1 ranked survivors and applies the TIGHTER constraint ① — the monomer adiabatic
    IP must be at least ``refined_window_margin_V`` (default 0.5 V) below the solvent anodic limit —
    while KEEPING the Tier-1 anion-stability and solubility constraints. The refined survivors are
    re-ranked with the SAME §5 composite (reusing ``scoring.yaml`` — weights/formula unchanged;
    min-max is recomputed over the refined set). The monomer Eox uses the Tier-2 DFT value when a
    DFT results CSV is supplied (per-monomer, V vs Ag/AgCl); otherwise it falls back to the
    calibrated Tier-1 value and flags ``tier2_dft_pending=True`` so the path is exercisable now.
    Output ``outputs/tier2_refined.csv``. NO new hard constants beyond the 0.5 V margin; does NOT
    touch the pinned calibration / scoring weights / composite formula.
    """

    frame = pd.read_csv(survivors_path)
    n_tier1 = int(len(frame))
    tier1_config = load_tier1_config(tier1_config_path) if tier1_config_path else load_tier1_config()
    filters = tier1_config["filters"]

    eox_used, pending = _resolve_monomer_eox(frame, dft_results_path)
    refined = frame.copy()
    refined["monomer_Eox_used_V_vs_AgAgCl"] = eox_used
    refined["tier2_dft_pending"] = pending
    refined["refined_window_margin_V"] = (
        refined["solvent_anodic_limit_V"] - refined["monomer_Eox_used_V_vs_AgAgCl"]
    )

    pass_window = refined["refined_window_margin_V"] > float(refined_window_margin_V)
    pass_anion = refined["anion_stability_margin_V"] > float(filters["min_anion_stability_margin_V"])
    pass_solubility = refined["solvation_dG_kcal_mol"] < float(filters["max_solvation_dG_kcal_mol"])
    refined["pass_refined_window_margin"] = pass_window
    refined["passes_tier2_refined_filters"] = pass_window & pass_anion & pass_solubility

    survivors = refined.loc[refined["passes_tier2_refined_filters"]].reset_index(drop=True)
    # Re-rank the refined survivors with the §5 composite (drop the stale Tier-1 score columns so
    # add_composite_score recomputes cleanly over the refined set).
    survivors = survivors.drop(
        columns=[c for c in ("composite_score", "pareto_front") if c in survivors.columns],
        errors="ignore",
    )
    scored = add_composite_score(
        survivors,
        load_scoring_config(scoring_config_path) if scoring_config_path else load_scoring_config(),
    )

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out, index=False)
    return Tier2RefinedResult(
        refined=scored,
        n_tier1_survivors=n_tier1,
        n_tier2_survivors=int(len(scored)),
        refined_window_margin_V=float(refined_window_margin_V),
        tier2_dft_pending=bool(pending),
        output_path=out,
    )


def _resolve_monomer_eox(
    frame: pd.DataFrame,
    dft_results_path: str | Path | None,
) -> tuple[pd.Series, bool]:
    """Return (per-row monomer Eox in V vs Ag/AgCl, tier2_dft_pending).

    Prefers a Tier-2 DFT Eox column (merged per monomer from ``dft_results_path``); otherwise falls
    back to the calibrated Tier-1 ``monomer_Eox_filter_V_vs_AgAgCl`` and flags the run as pending.
    """

    if dft_results_path is not None and Path(dft_results_path).exists():
        dft = pd.read_csv(dft_results_path)
        column = next((c for c in _DFT_EOX_COLUMNS if c in dft.columns), None)
        if column is not None and "monomer_canonical_smiles" in dft.columns:
            mapping = (
                dft.dropna(subset=[column])
                .drop_duplicates("monomer_canonical_smiles")
                .set_index("monomer_canonical_smiles")[column]
            )
            eox = frame["monomer_canonical_smiles"].map(mapping)
            if eox.notna().any():
                # Fill any monomer missing from the DFT set with the calibrated Tier-1 value.
                eox = eox.fillna(frame["monomer_Eox_filter_V_vs_AgAgCl"])
                return eox, False
    return frame["monomer_Eox_filter_V_vs_AgAgCl"], True

"""Tier-3 high-rigor scaffold (directive §4.3) — OPTIONAL and NOT validated.

Method (a) — a RANGE-SEPARATED hybrid DFT (CAM-B3LYP or wB97X-D / 6-311+G(d,p) / SMD) — is a REAL
config option on the existing Gaussian engine: ``configs/tier3.yaml`` uses the SAME schema as
``configs/tier2.yaml``, so ``GaussianEngine(config=load_tier3_config())`` runs it unchanged. The
build path here writes the ``.gjf`` inputs for inspection and never launches g16 in the test suite
(a live run is gated on g16 being on PATH and a PI decision).

Methods (b) explicit-solvation shell (2–4 explicit solvents, cluster-continuum), (c) GFN2-xTB BOMD
(5–10 ps) radical stability, and (d) Au(111)/ITO slab adsorption are DOCUMENTED HOOKS that return a
flagged ``tier3_optional_not_run`` result until wired. None runs in the test suite. The whole tier
is optional and not validated; nothing here pins a production decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from eps.engines.base import SpeciesSpec
from eps.engines.gaussian import Tier2Config, build_gaussian_input, load_tier2_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIER3_CONFIG = PROJECT_ROOT / "configs" / "tier3.yaml"

# Tier-3 method identifiers.
RANGE_SEPARATED_DFT = "range_separated_dft"            # (a) REAL on the Gaussian engine.
EXPLICIT_SOLVATION = "explicit_solvation_shell"        # (b) documented hook.
AIMD_RADICAL_STABILITY = "aimd_radical_stability"      # (c) documented hook.
SLAB_ADSORPTION = "slab_adsorption"                    # (d) documented hook.
TIER3_OPTIONAL_HOOK_METHODS = (EXPLICIT_SOLVATION, AIMD_RADICAL_STABILITY, SLAB_ADSORPTION)

TIER3_NOT_RUN_STATUS = "tier3_optional_not_run"

_HOOK_DESCRIPTIONS = {
    EXPLICIT_SOLVATION: (
        "explicit solvation shell — place 2–4 explicit solvent molecules around the monomer/cation "
        "and treat the cluster with cluster-continuum (explicit shell + SMD) DFT; captures specific "
        "ion–solvent interactions the continuum misses."
    ),
    AIMD_RADICAL_STABILITY: (
        "GFN2-xTB Born–Oppenheimer molecular dynamics (5–10 ps) of the radical cation to probe "
        "radical stability / unwanted side reactions (bond breaking, H transfer) before coupling."
    ),
    SLAB_ADSORPTION: (
        "Au(111)/ITO slab adsorption energy of the monomer (periodic DFT) to model the "
        "electrode–monomer interaction that initiates electropolymerization."
    ),
}


def load_tier3_config(path: str | Path = DEFAULT_TIER3_CONFIG) -> Tier2Config:
    """Load the Tier-3 DFT config (range-separated hybrid). Same schema as Tier-2.

    Falls back to the (heavier) v1-style defaults from ``load_tier2_config`` if the file is absent,
    so the scaffold imports cleanly; the shipped ``configs/tier3.yaml`` sets CAM-B3LYP/6-311+G(d,p)/SMD.
    """

    return load_tier2_config(path)


@dataclass
class Tier3DftResult:
    """Outputs of the Tier-3 range-separated DFT input generation (no g16 executed)."""

    outdir: Path
    method_label: str
    n_survivors: int
    n_unique_monomers: int
    input_paths: list[Path] = field(default_factory=list)


def write_tier3_dft_inputs(
    survivors_path: str | Path,
    outdir: str | Path,
    *,
    config: Tier2Config | None = None,
) -> Tier3DftResult:
    """Write neutral+cation range-separated-DFT ``.gjf`` inputs per unique survivor monomer.

    Method (a): REAL config on the Gaussian engine — uses the Tier-3 functional/basis/SMD/Freq. Does
    NOT run g16 (build-only, like the Tier-2 dry run); a human inspects the inputs and a live batch
    is a PI decision.
    """

    config = config if config is not None else load_tier3_config()
    frame = pd.read_csv(survivors_path)
    if "monomer_canonical_smiles" not in frame.columns:
        raise ValueError(
            f"{survivors_path} lacks a 'monomer_canonical_smiles' column required for Tier-3 inputs"
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
        for charge, multiplicity, tag in ((0, 1, "neutral"), (1, 2, "cation")):
            gjf = build_gaussian_input(
                species, charge, multiplicity,
                method=config.method, basis=config.basis, optimize=True,
                solvent_smd=config.smd_solvent, use_freq=config.use_freq,
                mem=config.mem, nprocshared=config.nprocshared,
            )
            path = out / f"{index:04d}_{safe}_{tag}.gjf"
            path.write_text(gjf, encoding="utf-8")
            input_paths.append(path)

    return Tier3DftResult(
        outdir=out,
        method_label=config.method_label(),
        n_survivors=int(len(frame)),
        n_unique_monomers=len(seen),
        input_paths=input_paths,
    )


@dataclass(frozen=True)
class Tier3HookResult:
    """A documented Tier-3 optional method that is NOT wired/run."""

    method: str
    ran: bool
    status: str
    note: str


def run_tier3_optional_hook(method: str, **_kwargs) -> Tier3HookResult:
    """Return the flagged not-run result for an optional Tier-3 method (b/c/d).

    These are documented placeholders; they never run anything (no DFT/MD/slab job is launched).
    Wiring one is future work and a PI decision.
    """

    if method not in _HOOK_DESCRIPTIONS:
        raise ValueError(
            f"Unknown Tier-3 optional method {method!r}; expected one of {TIER3_OPTIONAL_HOOK_METHODS}"
        )
    return Tier3HookResult(
        method=method,
        ran=False,
        status=TIER3_NOT_RUN_STATUS,
        note=f"DOCUMENTED HOOK (not wired): {_HOOK_DESCRIPTIONS[method]}",
    )


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_")

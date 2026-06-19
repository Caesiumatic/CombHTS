"""Deterministic RDKit 3D geometry generation for xTB input.

By default a single deterministic ETKDGv3 conformer is generated (the historical behavior). The
directive's §4.1 MMFF94 CONFORMER SEARCH is available as a config toggle: when enabled, several
ETKDGv3 conformers are embedded, MMFF94-optimized, and the lowest-energy one is handed to xTB.
This CHANGES geometries (and therefore the harvest and the scores) — it is NOT additive. The
active setting is threaded into the engine cache key (see ``conformer_method_suffix``), so a
config change does not silently reuse stale single-conformer geometries.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass

from rdkit import Chem
from rdkit.Chem import AllChem

ETKDG_RANDOM_SEED = 61453
# Fallback seeds tried (with random starting coordinates) when the deterministic embed fails;
# large/floppy oligomers (e.g. the dioctylfluorene hexamer) often need random coordinates.
ETKDG_FALLBACK_SEEDS = (0xC0FFEE, 1, 7, 42, 2024)
ETKDG_MAX_ITERATIONS = 2000


@dataclass(frozen=True)
class ConformerSearchConfig:
    """Conformer-search setting for geometry generation (directive §4.1).

    enabled=False is the historical single-deterministic-conformer path. When enabled, embed
    ``n_conformers`` ETKDGv3 conformers, MMFF94-optimize each, keep the lowest-energy one.
    """

    enabled: bool = False
    n_conformers: int = 1
    method: str = "none"


SINGLE_CONFORMER = ConformerSearchConfig()
_ACTIVE_CONFORMER_SEARCH: ConformerSearchConfig = SINGLE_CONFORMER


@contextmanager
def conformer_search_active(config: ConformerSearchConfig):
    """Scope the module-active conformer-search config (restored on exit; no leakage)."""

    global _ACTIVE_CONFORMER_SEARCH
    previous = _ACTIVE_CONFORMER_SEARCH
    _ACTIVE_CONFORMER_SEARCH = config
    try:
        yield
    finally:
        _ACTIVE_CONFORMER_SEARCH = previous


def conformer_method_suffix(config: ConformerSearchConfig | None) -> str:
    """Cache-key suffix encoding the conformer setting (empty when disabled).

    Folded into the engine ``method`` string so geometries from a different conformer setting are
    never reused from cache — the same fix pattern as the config-blind DFT cache (THINK T13).
    """

    if config is not None and config.enabled:
        return f"+conf-{config.method}-n{config.n_conformers}"
    return ""


def _embed(canonical_smiles: str):
    """Embed a 3D conformer, hardening against large/floppy systems.

    Tries the deterministic ETKDGv3 embed first (for reproducibility), then retries with
    random starting coordinates across several seeds and a larger iteration budget. Raises a
    clear ValueError if every attempt fails — never returns an un-embedded molecule.
    """

    mol = Chem.MolFromSmiles(canonical_smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES for geometry generation: {canonical_smiles}")
    mol = Chem.AddHs(mol)

    attempts = [(ETKDG_RANDOM_SEED, False)] + [(seed, True) for seed in ETKDG_FALLBACK_SEEDS]
    for seed, use_random_coords in attempts:
        params = AllChem.ETKDGv3()
        params.randomSeed = seed
        params.useRandomCoords = use_random_coords
        params.maxIterations = ETKDG_MAX_ITERATIONS
        if AllChem.EmbedMolecule(mol, params) == 0:
            return mol
    raise ValueError(
        f"RDKit failed to embed SMILES after {len(attempts)} attempts "
        f"(deterministic + random-coordinate retries): {canonical_smiles}"
    )


def _mmff94_multi_conformer_search(canonical_smiles: str, n_conformers: int):
    """Embed n ETKDGv3 conformers, MMFF94-optimize each, return the mol at the lowest-energy one.

    Returns None to fall back to the single-conformer path when MMFF cannot type every atom
    (e.g. Se), so the T10 Se-skip logic is preserved exactly. Returns None on any embed/opt
    failure so the caller degrades to the hardened single-conformer embed.
    """

    mol = Chem.MolFromSmiles(canonical_smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES for geometry generation: {canonical_smiles}")
    mol = Chem.AddHs(mol)
    if not AllChem.MMFFHasAllMoleculeParams(mol):
        return None  # non-MMFF-typable (Se, …): fall back to the single-conformer Se-skip path.
    params = AllChem.ETKDGv3()
    params.randomSeed = ETKDG_RANDOM_SEED
    params.useRandomCoords = True
    params.maxIterations = ETKDG_MAX_ITERATIONS
    conf_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=max(int(n_conformers), 1), params=params))
    if not conf_ids:
        return None
    results = AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=500)
    energies = [energy for _converged, energy in results]
    best = min(range(len(energies)), key=lambda i: energies[i])
    best_conf_id = conf_ids[best]
    for conf_id in [c for c in conf_ids if c != best_conf_id]:
        mol.RemoveConformer(conf_id)
    return mol


def _xyz_from_mol(mol, canonical_smiles: str, charge: int) -> str:
    conformer = mol.GetConformer()
    lines = [str(mol.GetNumAtoms()), f"generated from {canonical_smiles}; charge={charge}"]
    for atom in mol.GetAtoms():
        pos = conformer.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {pos.x:.8f} {pos.y:.8f} {pos.z:.8f}")
    return "\n".join(lines) + "\n"


def smiles_to_xyz(
    canonical_smiles: str,
    charge: int = 0,
    *,
    conformer_search: ConformerSearchConfig | None = None,
) -> str:
    """Convert canonical SMILES to an optimized XYZ string.

    Args:
        canonical_smiles: RDKit canonical SMILES for the molecular graph.
        charge: Formal charge in elementary-charge units. The graph SMILES itself
            carries atom-level charge; this value is accepted to keep geometry
            generation aligned with engine request signatures.
        conformer_search: Override for the conformer-search setting; defaults to the module-active
            config (single deterministic conformer unless ``conformer_search_active`` is in effect).

    Returns:
        XYZ-format geometry in angstrom.
    """

    config = conformer_search if conformer_search is not None else _ACTIVE_CONFORMER_SEARCH
    if config.enabled:
        searched = _mmff94_multi_conformer_search(canonical_smiles, config.n_conformers)
        if searched is not None:
            return _xyz_from_mol(searched, canonical_smiles, charge)
        # Non-MMFF-typable or search failed: fall through to the hardened single-conformer path.

    mol = _embed(canonical_smiles)

    if AllChem.MMFFHasAllMoleculeParams(mol):
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
    elif AllChem.UFFHasAllMoleculeParams(mol):
        AllChem.UFFOptimizeMolecule(mol, maxIters=500)
    else:
        # No classical force field can type every atom (e.g. Se in EDOS: both MMFF and
        # UFF report "Unrecognized atom type: Se2+2"). Running UFF anyway collapses the
        # ETKDG geometry into an atom-clashing structure (~0.26 A min distance), making
        # xTB abort geometry optimization ("|grad| > 500, something is totally wrong!").
        # Hand the clean ETKDG embedding to xTB instead; its GFN2 optimizer handles Se.
        pass

    return _xyz_from_mol(mol, canonical_smiles, charge)

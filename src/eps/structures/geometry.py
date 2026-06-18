"""Deterministic RDKit 3D geometry generation for xTB input."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

ETKDG_RANDOM_SEED = 61453
# Fallback seeds tried (with random starting coordinates) when the deterministic embed fails;
# large/floppy oligomers (e.g. the dioctylfluorene hexamer) often need random coordinates.
ETKDG_FALLBACK_SEEDS = (0xC0FFEE, 1, 7, 42, 2024)
ETKDG_MAX_ITERATIONS = 2000


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


def smiles_to_xyz(canonical_smiles: str, charge: int = 0) -> str:
    """Convert canonical SMILES to an optimized XYZ string.

    Args:
        canonical_smiles: RDKit canonical SMILES for the molecular graph.
        charge: Formal charge in elementary-charge units. The graph SMILES itself
            carries atom-level charge; this value is accepted to keep geometry
            generation aligned with engine request signatures.

    Returns:
        XYZ-format geometry in angstrom.
    """

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

    conformer = mol.GetConformer()
    lines = [str(mol.GetNumAtoms()), f"generated from {canonical_smiles}; charge={charge}"]
    for atom in mol.GetAtoms():
        pos = conformer.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {pos.x:.8f} {pos.y:.8f} {pos.z:.8f}")
    return "\n".join(lines) + "\n"

"""Deterministic RDKit 3D geometry generation for xTB input."""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

ETKDG_RANDOM_SEED = 61453


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

    mol = Chem.MolFromSmiles(canonical_smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES for geometry generation: {canonical_smiles}")
    mol = Chem.AddHs(mol)

    params = AllChem.ETKDGv3()
    params.randomSeed = ETKDG_RANDOM_SEED
    params.useRandomCoords = False
    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        raise ValueError(f"RDKit failed to embed SMILES: {canonical_smiles}")

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

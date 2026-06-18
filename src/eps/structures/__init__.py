"""Structure generation utilities."""

from eps.structures.geometry import smiles_to_xyz
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    DIMER_N,
    PolymerizationSpec,
    alpha_building_block_smiles,
    assemble_oligomer,
    detect_alpha_carbons,
    load_polymerization_specs,
    oligomer_smiles,
    write_building_block_artifact,
)

__all__ = [
    "DEFAULT_OLIGOMER_N",
    "DIMER_N",
    "PolymerizationSpec",
    "alpha_building_block_smiles",
    "assemble_oligomer",
    "detect_alpha_carbons",
    "load_polymerization_specs",
    "oligomer_smiles",
    "smiles_to_xyz",
    "write_building_block_artifact",
]

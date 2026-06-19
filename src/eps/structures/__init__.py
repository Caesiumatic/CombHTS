"""Structure generation utilities."""

from eps.structures.geometry import (
    ConformerSearchConfig,
    conformer_method_suffix,
    conformer_search_active,
    smiles_to_xyz,
)
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    DIMER_N,
    PolymerizationSpec,
    alpha_building_block_smiles,
    assemble_oligomer,
    detect_alpha_carbons,
    load_polymerization_specs,
    oligomer_smiles,
    truncate_inert_alkyl_to_methyl,
    write_building_block_artifact,
)

__all__ = [
    "ConformerSearchConfig",
    "DEFAULT_OLIGOMER_N",
    "DIMER_N",
    "PolymerizationSpec",
    "conformer_method_suffix",
    "conformer_search_active",
    "alpha_building_block_smiles",
    "assemble_oligomer",
    "detect_alpha_carbons",
    "load_polymerization_specs",
    "oligomer_smiles",
    "smiles_to_xyz",
    "truncate_inert_alkyl_to_methyl",
    "write_building_block_artifact",
]

"""Property conversions and calculators built on engine results."""

from eps.properties.calculators import (
    anion_oxidation_potential,
    dimerization_dG,
    monomer_eox_vs_AgAgCl,
    monomer_solvation,
    polymer_optical_gap,
    solvent_anodic_limit,
    solvent_cathodic_limit,
)
from eps.properties.redox import (
    ABS_SHE_V,
    AGAGCL_SHIFT_V,
    ip_eV_to_potential_vs_AgAgCl,
    potential_vs_AgAgCl_to_ip_eV,
)

__all__ = [
    "ABS_SHE_V",
    "AGAGCL_SHIFT_V",
    "anion_oxidation_potential",
    "dimerization_dG",
    "ip_eV_to_potential_vs_AgAgCl",
    "monomer_eox_vs_AgAgCl",
    "monomer_solvation",
    "potential_vs_AgAgCl_to_ip_eV",
    "polymer_optical_gap",
    "solvent_anodic_limit",
    "solvent_cathodic_limit",
]

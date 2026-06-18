"""Property conversions and calculators built on engine results."""

from eps.properties.calculators import (
    anion_oxidation_potential,
    dimerization_dG,
    monomer_eox_vs_AgAgCl,
    monomer_solvation,
    oligomer_eox_raw_eV,
    oligomer_eox_sidechain_truncated,
    optical_gap_oligomer,
    polymer_optical_gap,
    polymer_optical_gap_method,
    solvent_anodic_limit,
    solvent_anodic_limit_csv,
    solvent_cathodic_limit,
    solvent_cathodic_limit_csv,
)
from eps.properties.oligomer_series import (
    DEFAULT_EOX_OLIGOMER_LENGTHS,
    compute_oligomer_eox_series,
    extrapolate_infinite_chain,
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
    "DEFAULT_EOX_OLIGOMER_LENGTHS",
    "anion_oxidation_potential",
    "compute_oligomer_eox_series",
    "extrapolate_infinite_chain",
    "dimerization_dG",
    "ip_eV_to_potential_vs_AgAgCl",
    "monomer_eox_vs_AgAgCl",
    "monomer_solvation",
    "oligomer_eox_raw_eV",
    "oligomer_eox_sidechain_truncated",
    "optical_gap_oligomer",
    "potential_vs_AgAgCl_to_ip_eV",
    "polymer_optical_gap",
    "polymer_optical_gap_method",
    "solvent_anodic_limit",
    "solvent_anodic_limit_csv",
    "solvent_cathodic_limit",
    "solvent_cathodic_limit_csv",
]

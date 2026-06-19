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
    extrapolate_infinite_chain_poly2,
)
from eps.properties.optical_convergence import (
    DEFAULT_CONVERGENCE_LENGTHS,
    DEFAULT_CONVERGENCE_THRESHOLD_EV,
    compute_optical_gap_convergence,
)
from eps.properties.redox import (
    ABS_SHE_V,
    AGAGCL_SHIFT_V,
    ip_eV_to_potential_vs_AgAgCl,
    potential_vs_AgAgCl_to_ip_eV,
)
from eps.properties.secondary_descriptors import (
    anion_vdw_volume_descriptors,
    cation_reduction_descriptors,
    ionpair_descriptors,
    monomer_secondary_descriptors,
    solvent_secondary_descriptors,
)

__all__ = [
    "ABS_SHE_V",
    "AGAGCL_SHIFT_V",
    "DEFAULT_CONVERGENCE_LENGTHS",
    "DEFAULT_CONVERGENCE_THRESHOLD_EV",
    "DEFAULT_EOX_OLIGOMER_LENGTHS",
    "anion_oxidation_potential",
    "compute_optical_gap_convergence",
    "anion_vdw_volume_descriptors",
    "cation_reduction_descriptors",
    "ionpair_descriptors",
    "monomer_secondary_descriptors",
    "solvent_secondary_descriptors",
    "compute_oligomer_eox_series",
    "extrapolate_infinite_chain",
    "extrapolate_infinite_chain_poly2",
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

"""Redox potential conversions for monomer oxidation potentials.

The project spec pins the absolute SHE potential as 4.28 V and the Ag/AgCl
reference shift as -0.197 V. Because 1 eV per elementary charge maps to 1 V,
an adiabatic IP in eV is converted as:

    E(vs SHE) = IP_eV - ABS_SHE_V
    E(vs Ag/AgCl) = E(vs SHE) + AGAGCL_SHIFT_V
"""

ABS_SHE_V = 4.28
"""Absolute standard hydrogen electrode potential in V from the project spec."""

AGAGCL_SHIFT_V = -0.197
"""Ag/AgCl reference shift in V from the project spec."""


def ip_eV_to_potential_vs_AgAgCl(ip_eV: float) -> float:
    """Convert adiabatic ionization potential to oxidation potential.

    Args:
        ip_eV: Adiabatic ionization potential in eV.

    Returns:
        Oxidation potential in V vs Ag/AgCl.
    """

    return ip_eV - ABS_SHE_V + AGAGCL_SHIFT_V


def potential_vs_AgAgCl_to_ip_eV(potential_V: float) -> float:
    """Convert oxidation potential vs Ag/AgCl back to ionization potential.

    Args:
        potential_V: Oxidation potential in V vs Ag/AgCl.

    Returns:
        Adiabatic ionization potential in eV.
    """

    return potential_V + ABS_SHE_V - AGAGCL_SHIFT_V

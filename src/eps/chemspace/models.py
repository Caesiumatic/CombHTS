"""Pydantic models for versioned chemical-space records."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Monomer(BaseModel):
    """A polymerizable monomer precursor with neutral canonical SMILES."""

    name: str
    monomer_class: str
    smiles: str
    canonical_smiles: str
    notes: str = ""


class Solvent(BaseModel):
    """A solvent with dielectric constant and electrochemical stability window.

    Attributes:
        eps_r: Relative dielectric constant, dimensionless.
        esw_anodic_V: Approximate anodic stability limit in V on potential_reference.
        esw_cathodic_V: Approximate cathodic stability limit in V on potential_reference.
        potential_reference: Reference electrode for ESW limits, default V vs Ag/AgCl.
        xtb_gbsa_name: xTB ALPB solvent keyword or versioned proxy keyword.
        orca_smd_name: ORCA SMD solvent keyword for the §4.2 Tier-2 DFT redox (CPCM SMDsolvent).
            None -> ORCA Tier-2 runs this solvent in gas phase (no built-in SMD parametrization).
    """

    name: str
    smiles: str
    canonical_smiles: str
    eps_r: float = Field(gt=0)
    esw_anodic_V: float
    esw_cathodic_V: float
    potential_reference: str = "Ag/AgCl"
    xtb_gbsa_name: Optional[str] = None
    orca_smd_name: Optional[str] = None
    notes: str = ""


class Electrolyte(BaseModel):
    """An electrolyte salt with separately canonicalized cation and anion SMILES."""

    salt: str
    cation_smiles: str
    canonical_cation_smiles: str
    anion_smiles: str
    canonical_anion_smiles: str
    salt_class: str
    electrolyte_role: Literal["supporting", "reference_only", "acid", "other"]
    supporting_electrolyte_ok: bool
    electrolyte_role_justification: str
    notes: str = ""

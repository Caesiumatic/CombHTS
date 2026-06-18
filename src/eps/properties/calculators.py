"""Per-species property calculators that route engine calls through the cache."""

from __future__ import annotations

from eps.chemspace.models import Electrolyte, Monomer, Solvent
from eps.engines.base import CalcRequest, Engine, SpeciesSpec
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage.cache import SQLiteCache, cached_run
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    DIMER_N,
    PolymerizationSpec,
    oligomer_smiles,
)

DEFAULT_METHOD = "mock-gfn2"

EV_TO_KCAL_MOL = 23.060547830619
PROTON_GIBBS_EV = 0.0
"""Reference free energy of the released proton, in eV.

The α,α′ coupling 2 M⁺• → [M–M]²⁺ + 2 H⁺ loses exactly two protons for EVERY monomer, so
this constant cancels in the cross-monomer comparison and in the min–max normalization that
feeds the composite (same "constant cancels" logic as THINK T11). It is fixed at the free-
proton reference (0 eV) here: the ABSOLUTE ΔG is therefore screening-grade up to this proton
convention, while the RELATIVE ordering across monomers — which is what the w4 score uses — is
robust. Overridable per call for testing the invariance."""


def monomer_eox_vs_AgAgCl(
    monomer: Monomer,
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Return monomer oxidation potential in V vs Ag/AgCl for a solvent dielectric."""

    req = CalcRequest(
        species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=solvent.eps_r,
        quantity="adiabatic_ip",
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    result = cached_run(cache, engine, req, solvent.name)
    return ip_eV_to_potential_vs_AgAgCl(result.value)


def solvent_anodic_limit(
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Adiabatic ΔSCF oxidation potential of the solvent molecule in its own implicit
    solvent, in V vs Ag/AgCl (spec §3.2). Raw, uncalibrated, screening-grade."""

    req = CalcRequest(
        species=SpeciesSpec(solvent.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=solvent.eps_r,
        quantity="adiabatic_ip",
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    result = cached_run(cache, engine, req, solvent.name)
    return ip_eV_to_potential_vs_AgAgCl(result.value)


def solvent_cathodic_limit(
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Adiabatic ΔSCF reduction potential of the solvent molecule in its own implicit
    solvent, in V vs Ag/AgCl (spec §3.2). Raw, uncalibrated, screening-grade.

    The engine returns the adiabatic EA in eV (E(neutral) − E(anion)); the
    solvent/solvent⁻ reduction potential projects to V vs Ag/AgCl through the SAME
    function used for IP: E(vs Ag/AgCl) = EA − 4.28 − 0.197.

    Computed solvent EA via GFN2-xTB is unreliable for closed-shell solvents
    (unbound anions); this cathodic value is informational only and is NOT used in any
    Tier-1 filter.
    """

    req = CalcRequest(
        species=SpeciesSpec(solvent.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=solvent.eps_r,
        quantity="adiabatic_ea",
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    result = cached_run(cache, engine, req, solvent.name)
    return ip_eV_to_potential_vs_AgAgCl(result.value)


def solvent_anodic_limit_csv(solvent: Solvent) -> float:
    """Return the stopgap CSV anodic limit in V vs Ag/AgCl, kept as a fallback."""

    return solvent.esw_anodic_V


def solvent_cathodic_limit_csv(solvent: Solvent) -> float:
    """Return the stopgap CSV cathodic limit in V vs Ag/AgCl, kept as a fallback."""

    return solvent.esw_cathodic_V


def anion_oxidation_potential(
    electrolyte: Electrolyte,
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Return electrolyte anion oxidation potential in V vs Ag/AgCl."""

    req = CalcRequest(
        species=SpeciesSpec(electrolyte.canonical_anion_smiles, charge=-1, multiplicity=1),
        method=method,
        solvent_eps_r=solvent.eps_r,
        quantity="adiabatic_ip",
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    result = cached_run(cache, engine, req, solvent.name)
    return ip_eV_to_potential_vs_AgAgCl(result.value)


def monomer_solvation(
    monomer: Monomer,
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Return monomer solvation free energy in kcal/mol."""

    req = CalcRequest(
        species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=solvent.eps_r,
        quantity="solvation_free_energy",
        xtb_gbsa_name=solvent.xtb_gbsa_name,
    )
    return cached_run(cache, engine, req, solvent.name).value


def _optical_gap_request(monomer: Monomer, spec: PolymerizationSpec, method: str, n: int) -> CalcRequest:
    oligo_smiles = oligomer_smiles(monomer.canonical_smiles, spec, n)
    return CalcRequest(
        species=SpeciesSpec(oligo_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=None,
        quantity="optical_gap",
    )


def polymer_optical_gap(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
    *,
    spec: PolymerizationSpec,
    n: int = DEFAULT_OLIGOMER_N,
) -> float:
    """Optical (band) gap in eV from the assembled n-mer oligomer (directive §3.1/§4.1).

    The engine returns the sTDA-xTB lowest singlet excitation when ``stda`` is available, or
    the oligomer GFN2-xTB HOMO–LUMO gap as a clearly-labeled screening proxy otherwise. This
    is a per-MONOMER property (one oligomer calc per monomer), cached by the oligomer SMILES.
    Raw/uncalibrated vs TD-DFT (Step-2 calibration hook), screening-grade.
    """

    req = _optical_gap_request(monomer, spec, method, n)
    return cached_run(cache, engine, req, solvent_name=None).value


def polymer_optical_gap_method(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
    *,
    spec: PolymerizationSpec,
    n: int = DEFAULT_OLIGOMER_N,
) -> str:
    """Return which method produced the cached optical gap (stda-xtb / HOMO–LUMO proxy / mock)."""

    req = _optical_gap_request(monomer, spec, method, n)
    result = cached_run(cache, engine, req, solvent_name=None)
    return str(result.raw.get("optical_gap_method", "unknown"))


def _gas_energy_eV(
    engine: Engine,
    cache: SQLiteCache,
    smiles: str,
    *,
    charge: int,
    multiplicity: int,
    method: str,
) -> float:
    req = CalcRequest(
        species=SpeciesSpec(smiles, charge=charge, multiplicity=multiplicity),
        method=method,
        solvent_eps_r=None,
        quantity="gas_energy",
    )
    return cached_run(cache, engine, req, solvent_name=None).value


def dimerization_dG(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
    *,
    spec: PolymerizationSpec,
    dimer_n: int = DIMER_N,
    proton_gibbs_eV: float = PROTON_GIBBS_EV,
) -> float:
    """Radical–radical coupling free energy in kcal/mol (directive §3.1/§4.2).

    Reaction: 2 M⁺• → [M–M]²⁺ + 2 H⁺. The xTB-level
    ΔG = G([M–M]²⁺) + 2·G(H⁺) − 2·G(M⁺•), with each G taken as the GFN2-xTB energy of that
    species (reusing the redox energy path) and G(H⁺) the fixed proton convention
    (``proton_gibbs_eV``). The dimer is the α,α′ neutral n=2 oligomer evaluated in the +2
    charge state (closed-shell singlet); the monomer radical cation is +1, doublet.

    Per-MONOMER property (cached). The proton constant cancels across monomers, so the
    ABSOLUTE value is screening-grade but the RELATIVE ordering the score uses is sound. This
    is NOT a hard Tier-1 filter — it feeds the w4 composite term only.
    """

    dimer_smiles = oligomer_smiles(monomer.canonical_smiles, spec, dimer_n)
    g_dimer_dication = _gas_energy_eV(
        engine, cache, dimer_smiles, charge=2, multiplicity=1, method=method
    )
    g_monomer_cation = _gas_energy_eV(
        engine, cache, monomer.canonical_smiles, charge=1, multiplicity=2, method=method
    )
    delta_eV = g_dimer_dication + 2.0 * proton_gibbs_eV - 2.0 * g_monomer_cation
    return delta_eV * EV_TO_KCAL_MOL

"""Per-species property calculators that route engine calls through the cache."""

from __future__ import annotations

from eps.chemspace.models import Electrolyte, Monomer, Solvent
from eps.engines.base import CalcRequest, Engine, SpeciesSpec
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage.cache import SQLiteCache, cached_run

DEFAULT_METHOD = "mock-gfn2"


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


def solvent_anodic_limit(solvent: Solvent, engine: Engine | None = None) -> float:
    """Return solvent anodic stability limit in V vs Ag/AgCl from the CSV library."""

    return solvent.esw_anodic_V


def solvent_cathodic_limit(solvent: Solvent, engine: Engine | None = None) -> float:
    """Return solvent cathodic stability limit in V vs Ag/AgCl from the CSV library."""

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


def polymer_optical_gap(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Return polymer optical gap proxy in eV, using monomer as the current placeholder."""

    req = CalcRequest(
        species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=None,
        quantity="optical_gap",
    )
    return cached_run(cache, engine, req, solvent_name=None).value


def dimerization_dG(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
) -> float:
    """Return mock dimerization free energy in kcal/mol.

    The first skeleton uses monomer gas energy as a deterministic placeholder
    signal, then rescales it to a chemically plausible -12 to +12 kcal/mol range.
    Later structure-aware dimer calculations can replace this without changing
    workflow callers.
    """

    req = CalcRequest(
        species=SpeciesSpec(monomer.canonical_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=None,
        quantity="gas_energy",
    )
    gas_energy_eV = cached_run(cache, engine, req, solvent_name=None).value
    fraction = (gas_energy_eV + 650.0) / 600.0
    return -12.0 + fraction * 24.0

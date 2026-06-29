"""Per-species property calculators that route engine calls through the cache."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

from eps.chemspace.models import Electrolyte, Monomer, Solvent
from eps.engines.base import CalcRequest, Engine, SpeciesSpec
from eps.engines.mock import MockEngine
from eps.engines.xtb import XTBEngine
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage.cache import SQLiteCache, cached_run
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    DIMER_N,
    PolymerizationSpec,
    oligomer_smiles,
    truncate_inert_alkyl_to_methyl,
)

DEFAULT_METHOD = "mock-gfn2"
OPTICAL_GAP_METHOD_REVISION = "+optgap-optgeom-v2"
"""Cache-key-only revision for optical gaps that consume optimized xTB geometry."""
OPTICAL_GAP_BACKEND_STDA = "+backend-stda"
OPTICAL_GAP_BACKEND_HL_FALLBACK = "+backend-hl-fallback"
OPTICAL_GAP_BACKEND_MOCK = "+backend-mock"
OPTICAL_GAP_BACKEND_GENERIC = "+backend-generic"
OPTICAL_GAP_BACKEND_TAGS = (
    OPTICAL_GAP_BACKEND_STDA,
    OPTICAL_GAP_BACKEND_HL_FALLBACK,
    OPTICAL_GAP_BACKEND_MOCK,
    OPTICAL_GAP_BACKEND_GENERIC,
)

EV_TO_KCAL_MOL = 23.060547830619
PROTON_GIBBS_EV = 0.0
"""Electronic-energy reference of the released proton, in eV.

The oxidative coupling 2 M⁺• → M–M(neutral) + 2 H⁺ is charge- AND electron-balanced (both
sides carry 2·Z_M − 2 electrons), and a bare proton has no electrons, so its electronic energy
is rigorously 0 on the same GFN2-xTB scale as the other species. The proton term is therefore
0 by construction (not an arbitrary cancel-constant): the resulting ΔG = E(M–M) − 2·E(M⁺•) is
the physically interpretable, self-contained screening-grade coupling energy (dG < 0 ⇒
favorable coupling). The screening-grade caveats are the missing thermal/ZPE corrections and
proton solvation, and that these are GFN2-xTB electronic energies (the DFT-grade version is
Step-2). Overridable per call for testing the cross-monomer invariance."""


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
        quantity="ipea_ip",
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
        quantity="ipea_ip",
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
        quantity="ipea_ea",
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


def load_cosmors_solvation_table(path: str | Path) -> dict[tuple[str, str], float]:
    """Load the precomputed decoupled openCOSMO-RS ΔGsolv table (directive §4.1, COSMO-RS).

    Keyed by ``(monomer_canonical_smiles, solvent_name)`` → ΔGsolv (kcal/mol). The Tier-1 screen
    reads this cosmors-first and falls back to the ALPB ΔGsolv proxy when a pair is absent (the same
    measured-first discipline used for the ESW window gate). Returns ``{}`` if the file is missing.
    """

    path = Path(path)
    if not path.exists():
        return {}
    table: dict[tuple[str, str], float] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            try:
                key = (row["monomer_canonical_smiles"].strip(), row["solvent_name"].strip())
                table[key] = float(row["dGsolv_kcal_mol"])
            except (KeyError, ValueError):
                continue
    return table


def optical_gap_oligomer(monomer: Monomer, spec: PolymerizationSpec, n: int) -> tuple[str, bool]:
    """Return the (possibly side-chain-truncated) optical-gap oligomer SMILES + truncated flag.

    Long inert saturated side chains are truncated to methyl for the OPTICAL-GAP oligomer only
    (they are electronically innocent for the conjugated-backbone gap and otherwise make large
    hexamers — e.g. dioctylfluorene — fail 3D embedding). The monomer Eox / solvation /
    dimerization paths keep the full side chains.
    """

    oligo_smiles = oligomer_smiles(monomer.canonical_smiles, spec, n)
    return truncate_inert_alkyl_to_methyl(oligo_smiles)


def _optical_gap_request(
    monomer: Monomer,
    spec: PolymerizationSpec,
    method: str,
    n: int,
    engine: Engine,
) -> CalcRequest:
    oligo_smiles, _ = optical_gap_oligomer(monomer, spec, n)
    return CalcRequest(
        species=SpeciesSpec(oligo_smiles, charge=0, multiplicity=1),
        method=_optical_gap_cache_method(method, engine),
        solvent_eps_r=None,
        quantity="optical_gap",
    )


def _optical_gap_cache_method(method: str, engine: Engine) -> str:
    base_method = _strip_optical_gap_cache_suffix(method)
    return f"{base_method}{OPTICAL_GAP_METHOD_REVISION}{_optical_gap_backend_tag(engine)}"


def _strip_optical_gap_cache_suffix(method: str) -> str:
    for backend_tag in OPTICAL_GAP_BACKEND_TAGS:
        suffix = f"{OPTICAL_GAP_METHOD_REVISION}{backend_tag}"
        if method.endswith(suffix):
            return method[: -len(suffix)]
    if method.endswith(OPTICAL_GAP_METHOD_REVISION):
        return method[: -len(OPTICAL_GAP_METHOD_REVISION)]
    return method


def _optical_gap_backend_tag(engine: Engine) -> str:
    if isinstance(engine, XTBEngine):
        if shutil.which(engine.stda_binary) is not None:
            return OPTICAL_GAP_BACKEND_STDA
        return OPTICAL_GAP_BACKEND_HL_FALLBACK
    if isinstance(engine, MockEngine):
        return OPTICAL_GAP_BACKEND_MOCK
    return OPTICAL_GAP_BACKEND_GENERIC


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

    req = _optical_gap_request(monomer, spec, method, n, engine)
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

    req = _optical_gap_request(monomer, spec, method, n, engine)
    result = cached_run(cache, engine, req, solvent_name=None)
    return str(result.raw.get("optical_gap_method", "unknown"))


def oligomer_eox_raw_eV(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
    *,
    spec: PolymerizationSpec,
    n: int,
) -> float:
    """RAW xTB adiabatic ionization energy (eV) of the assembled n-mer, gas phase.

    Reuses the SAME side-chain-truncated oligomer as the optical gap (``optical_gap_oligomer``;
    long inert alkyl chains are trimmed to methyl for embedding safety) and the SAME adiabatic
    redox convention as the rest of the code (neutral singlet -> radical cation, ``adiabatic_ip``).
    The value is RAW (not projected to V vs Ag/AgCl, not calibrated). Per-monomer, gas-phase,
    cached by the oligomer SMILES so the 1/n series is phase-consistent across n.

    n=1 is the length-1 oligomer (the monomer itself, truncated identically), used as the
    classic monomer anchor of the 1/n extrapolation.
    """

    oligo_smiles, _ = optical_gap_oligomer(monomer, spec, n)
    req = CalcRequest(
        species=SpeciesSpec(oligo_smiles, charge=0, multiplicity=1),
        method=method,
        solvent_eps_r=None,
        quantity="adiabatic_ip",
    )
    return cached_run(cache, engine, req, solvent_name=None).value


def oligomer_eox_sidechain_truncated(monomer: Monomer, spec: PolymerizationSpec, n: int) -> bool:
    """Whether the n-mer's inert side chains were trimmed to methyl (mirrors the optical gap)."""

    _, truncated = optical_gap_oligomer(monomer, spec, n)
    return bool(truncated)


def _gas_energy_eV(
    engine: Engine,
    cache: SQLiteCache,
    smiles: str,
    *,
    charge: int,
    multiplicity: int,
    method: str,
    solvent_model_name: str | None = None,
    solvent_name: str | None = None,
    solvent_eps_r: float | None = None,
) -> float:
    req = CalcRequest(
        species=SpeciesSpec(smiles, charge=charge, multiplicity=multiplicity),
        method=method,
        solvent_eps_r=solvent_eps_r,
        solvent_model_name=solvent_model_name,
        quantity="gas_energy",
    )
    return cached_run(cache, engine, req, solvent_name=solvent_name).value


def dimerization_dG(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    method: str = DEFAULT_METHOD,
    *,
    spec: PolymerizationSpec,
    dimer_n: int = DIMER_N,
    proton_gibbs_eV: float = PROTON_GIBBS_EV,
    solvent_model_name: str | None = None,
    solvent_name: str | None = None,
    solvent_eps_r: float | None = None,
) -> float:
    """Radical–radical coupling free energy in kcal/mol (directive §3.1/§4.2).

    Reaction (charge- and electron-balanced): 2 M⁺• → M–M(neutral) + 2 H⁺. The xTB-level
    ΔG = G(M–M neutral) + 2·G(H⁺) − 2·G(M⁺•), with each G taken as the GFN2-xTB energy of that
    species (reusing the redox energy path). The dimer is the SAME α,α′-coupled n=2 oligomer,
    now evaluated NEUTRAL (closed-shell singlet) — two radical cations couple and the
    rearomatized dimer is neutral, having lost 2 H⁺. The monomer radical cation is +1, doublet.
    Using the +2 dication (the earlier code) double-counted oxidation and made every monomer
    look strongly endothermic (~+650 kcal/mol); the neutral dimer fixes that.

    The proton's electronic energy is rigorously 0 (a bare proton has no electrons; see
    ``PROTON_GIBBS_EV``), so ΔG is the physically interpretable, self-contained coupling energy
    (dG < 0 ⇒ favorable). Per-MONOMER property (cached). Screening-grade (no thermal/ZPE/solvation
    corrections; GFN2-xTB electronic energies — DFT-grade is Step-2). NOT a hard Tier-1 filter —
    it feeds the w4 composite term only.
    """

    dimer_smiles = oligomer_smiles(monomer.canonical_smiles, spec, dimer_n)
    solvent_kwargs = {
        "solvent_model_name": solvent_model_name,
        "solvent_name": solvent_name,
        "solvent_eps_r": solvent_eps_r,
    }
    g_dimer_neutral = _gas_energy_eV(
        engine, cache, dimer_smiles, charge=0, multiplicity=1, method=method, **solvent_kwargs
    )
    g_monomer_cation = _gas_energy_eV(
        engine, cache, monomer.canonical_smiles, charge=1, multiplicity=2, method=method,
        **solvent_kwargs
    )
    delta_eV = g_dimer_neutral + 2.0 * proton_gibbs_eV - 2.0 * g_monomer_cation
    return delta_eV * EV_TO_KCAL_MOL

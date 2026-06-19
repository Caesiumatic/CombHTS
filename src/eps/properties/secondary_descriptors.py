"""Directive §3 secondary descriptors — additive, reported-only, screening-grade.

These per-species quantities (monomer frontier orbitals / radical-cation spin / reorganization
energy; solvent oxidation/reduction reorganization; electrolyte cation reduction, anion volume,
ion-pair dissociation) are computed through the SAME cached Engine as the Tier-1 axes and joined
into the harvest. They are PURELY REPORTED: none enters a hard filter or the composite score.
Every value is failure-tolerant (a bad calc yields NaN + a status/error, never an abort) and is
RAW/uncalibrated screening-grade. Mock-first: MockEngine returns deterministic plausible values
so the whole module is exercisable without xtb.
"""

from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import AllChem

from eps.chemspace.models import Electrolyte, Monomer, Solvent
from eps.engines.base import CalcRequest, Engine, SpeciesSpec
from eps.properties.calculators import EV_TO_KCAL_MOL, _gas_energy_eV
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage.cache import SQLiteCache, cached_run
from eps.structures.oligomer import detect_alpha_carbons

DEFAULT_METHOD = "mock-gfn2"
IONPAIR_METHOD = "alpb_contact_pair_approx"

# Bondi van der Waals radii (Å) for the additive-volume fallback used when RDKit cannot embed a
# 3D conformer (e.g. octahedral PF6⁻, which distance geometry cannot place). Additive spheres
# OVERESTIMATE the molecular volume (they ignore bond overlap), so it is a clearly-flagged proxy.
_BONDI_RADII_A = {
    "H": 1.20, "B": 1.92, "C": 1.70, "N": 1.55, "O": 1.52, "F": 1.47, "P": 1.80,
    "S": 1.80, "Cl": 1.75, "Se": 1.90, "Br": 1.85, "I": 1.98, "Li": 1.82, "Na": 2.27,
    "K": 2.75,
}
_DEFAULT_BONDI_RADIUS_A = 1.70


def _bondi_additive_volume_A3(mol: Chem.Mol) -> float:
    """Sum of per-atom Bondi vdW spheres (Å³), a robust fallback when 3D embedding fails."""

    from math import pi

    total = 0.0
    for atom in mol.GetAtoms():
        radius = _BONDI_RADII_A.get(atom.GetSymbol(), _DEFAULT_BONDI_RADIUS_A)
        total += (4.0 / 3.0) * pi * radius**3
    return total


def _concise(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:240]


def _scalar(
    engine: Engine,
    cache: SQLiteCache,
    *,
    smiles: str,
    charge: int,
    multiplicity: int,
    quantity: str,
    method: str,
    solvent_eps_r: float | None,
    xtb_gbsa_name: str | None,
    solvent_name: str | None,
) -> float:
    """Cached scalar engine value for one (species, quantity)."""

    req = CalcRequest(
        species=SpeciesSpec(smiles, charge=charge, multiplicity=multiplicity),
        method=method,
        solvent_eps_r=solvent_eps_r,
        quantity=quantity,
        xtb_gbsa_name=xtb_gbsa_name,
    )
    return cached_run(cache, engine, req, solvent_name).value


# --- §3.1 monomer ------------------------------------------------------------------------


def monomer_secondary_descriptors(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str = DEFAULT_METHOD,
) -> dict[str, object]:
    """Per-monomer §3.1 frontier orbitals, radical-cation spin, vertical IP + reorganization.

    All gas phase (no solvent). HOMO/LUMO/gap (eV); radical-cation (+1, doublet) Mulliken spin
    density → max value, its atom index, whether that atom is an α coupling site, and the summed
    spin on the α coupling atoms; vertical IP (eV), the REUSED adiabatic IP (eV), and
    lambda_ox = vertical − adiabatic. Reported-only, screening-grade.
    """

    smiles = monomer.canonical_smiles
    errors: list[str] = []

    def safe(label: str, fn):
        try:
            return float(fn()), True
        except Exception as exc:  # noqa: BLE001 - reported descriptor must never abort the row.
            errors.append(f"{label}: {_concise(exc)}")
            return float("nan"), False

    homo, _ = safe("homo", lambda: _scalar(
        engine, cache, smiles=smiles, charge=0, multiplicity=1, quantity="homo",
        method=method, solvent_eps_r=None, xtb_gbsa_name=None, solvent_name=None))
    lumo, lumo_ok = safe("lumo", lambda: _scalar(
        engine, cache, smiles=smiles, charge=0, multiplicity=1, quantity="lumo",
        method=method, solvent_eps_r=None, xtb_gbsa_name=None, solvent_name=None))
    hl_gap = (lumo - homo) if (lumo_ok and homo == homo) else float("nan")  # noqa: PLR0124

    adiabatic_ip, _ = safe("adiabatic_ip", lambda: _scalar(
        engine, cache, smiles=smiles, charge=0, multiplicity=1, quantity="adiabatic_ip",
        method=method, solvent_eps_r=None, xtb_gbsa_name=None, solvent_name=None))
    vertical_ip, _ = safe("vertical_ip", lambda: _scalar(
        engine, cache, smiles=smiles, charge=0, multiplicity=1, quantity="vertical_ip",
        method=method, solvent_eps_r=None, xtb_gbsa_name=None, solvent_name=None))
    lambda_ox = vertical_ip - adiabatic_ip

    spin = _cation_spin_descriptors(monomer, engine, cache, method=method, errors=errors)

    status = "ok" if not errors else "failed"
    return {
        "monomer_HOMO_eV": homo,
        "monomer_LUMO_eV": lumo,
        "monomer_HL_gap_eV": hl_gap,
        "monomer_vertical_IP_eV": vertical_ip,
        "monomer_adiabatic_IP_eV": adiabatic_ip,
        "monomer_lambda_ox_eV": lambda_ox,
        **spin,
        "secondary_monomer_calc_status": status,
        "secondary_monomer_calc_error": "; ".join(errors),
    }


def _cation_spin_descriptors(
    monomer: Monomer,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str,
    errors: list[str],
) -> dict[str, object]:
    """Radical-cation Mulliken spin: max spin, its atom, α-membership, α-spin sum."""

    blank = {
        "monomer_cation_max_spin": float("nan"),
        "monomer_cation_max_spin_atom_idx": "",
        "monomer_cation_max_spin_is_alpha": "",
        "monomer_cation_alpha_spin_sum": float("nan"),
    }
    try:
        req = CalcRequest(
            species=SpeciesSpec(monomer.canonical_smiles, charge=1, multiplicity=2),
            method=method,
            solvent_eps_r=None,
            quantity="spin_density",
        )
        result = cached_run(cache, engine, req, solvent_name=None)
        spins = [float(s) for s in result.raw.get("atomic_spin_density", [])]
        if not spins:
            errors.append("spin_density: empty atomic_spin_density")
            return blank
        max_idx = max(range(len(spins)), key=lambda i: spins[i])
        mol = Chem.MolFromSmiles(monomer.canonical_smiles)
        alpha = set(detect_alpha_carbons(mol)) if mol is not None else set()
        alpha_sum = float(sum(spins[i] for i in alpha if i < len(spins)))
        return {
            "monomer_cation_max_spin": float(spins[max_idx]),
            "monomer_cation_max_spin_atom_idx": int(max_idx),
            "monomer_cation_max_spin_is_alpha": bool(max_idx in alpha),
            "monomer_cation_alpha_spin_sum": alpha_sum,
        }
    except Exception as exc:  # noqa: BLE001
        errors.append(f"spin_density: {_concise(exc)}")
        return blank


# --- §3.2 solvent ------------------------------------------------------------------------


def solvent_secondary_descriptors(
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str = DEFAULT_METHOD,
) -> dict[str, object]:
    """Per-solvent §3.2 oxidation/reduction reorganization energies, in implicit self-solvent.

    lambda_ox = vertical IP − adiabatic IP; lambda_red = vertical EA − adiabatic EA (eV).
    Reuses the adiabatic IP/EA the anodic/cathodic limits already compute (same cache key) and
    only ADDS the vertical points. Reported-only, screening-grade.
    """

    errors: list[str] = []

    def safe(label: str, quantity: str):
        try:
            return float(_scalar(
                engine, cache, smiles=solvent.canonical_smiles, charge=0, multiplicity=1,
                quantity=quantity, method=method, solvent_eps_r=solvent.eps_r,
                xtb_gbsa_name=solvent.xtb_gbsa_name, solvent_name=solvent.name))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label}: {_concise(exc)}")
            return float("nan")

    adiabatic_ip = safe("adiabatic_ip", "adiabatic_ip")
    vertical_ip = safe("vertical_ip", "vertical_ip")
    adiabatic_ea = safe("adiabatic_ea", "adiabatic_ea")
    vertical_ea = safe("vertical_ea", "vertical_ea")

    status = "ok" if not errors else "failed"
    return {
        "solvent_adiabatic_IP_eV": adiabatic_ip,
        "solvent_vertical_IP_eV": vertical_ip,
        "solvent_lambda_ox_eV": vertical_ip - adiabatic_ip,
        "solvent_adiabatic_EA_eV": adiabatic_ea,
        "solvent_vertical_EA_eV": vertical_ea,
        "solvent_lambda_red_eV": vertical_ea - adiabatic_ea,
        "secondary_solvent_calc_status": status,
        "secondary_solvent_calc_error": "; ".join(errors),
    }


# --- §3.3 electrolyte --------------------------------------------------------------------


def anion_vdw_volume_descriptors(electrolyte: Electrolyte) -> dict[str, object]:
    """Per-anion van der Waals volume (Å³), RDKit grid volume on a 3D conformer when embeddable.

    Falls back to an additive Bondi-sphere estimate (clearly flagged via ``anion_volume_method``)
    for anions distance geometry cannot place — e.g. octahedral PF6⁻. No engine. Reported-only.
    """

    try:
        mol = Chem.MolFromSmiles(electrolyte.canonical_anion_smiles)
        if mol is None:
            raise ValueError(f"unparseable anion SMILES: {electrolyte.canonical_anion_smiles}")
        mol = Chem.AddHs(mol)
        embedded = False
        for seed in (0xC0FFEE, 1, 7, 42, 2024):
            params = AllChem.ETKDGv3()
            params.randomSeed = seed
            params.useRandomCoords = True
            params.maxIterations = 2000
            if AllChem.EmbedMolecule(mol, params) == 0:
                embedded = True
                break
        if embedded:
            return {
                "anion_vdw_volume_A3": float(AllChem.ComputeMolVolume(mol)),
                "anion_volume_method": "rdkit_3d_grid",
                "anion_volume_calc_status": "ok",
                "anion_volume_calc_error": "",
            }
        return {
            "anion_vdw_volume_A3": _bondi_additive_volume_A3(mol),
            "anion_volume_method": "bondi_additive_fallback",
            "anion_volume_calc_status": "ok",
            "anion_volume_calc_error": "3D embed failed; additive Bondi-sphere proxy (overestimate)",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "anion_vdw_volume_A3": float("nan"),
            "anion_volume_method": "none",
            "anion_volume_calc_status": "failed",
            "anion_volume_calc_error": _concise(exc),
        }


def cation_reduction_descriptors(
    electrolyte: Electrolyte,
    solvent: Solvent,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str = DEFAULT_METHOD,
) -> dict[str, object]:
    """Per-(cation, solvent) cation reduction potential, RAW V vs Ag/AgCl.

    Adiabatic ΔSCF reduction of the cation (+1 → neutral radical) in implicit solvent, projected
    through the pinned redox function. RAW — a REDUCTION potential, deliberately NOT put on the
    monomer oxidation calibration (T11). Reported-only, screening-grade.
    """

    try:
        ea_eV = _scalar(
            engine, cache, smiles=electrolyte.canonical_cation_smiles, charge=1, multiplicity=1,
            quantity="adiabatic_ea", method=method, solvent_eps_r=solvent.eps_r,
            xtb_gbsa_name=solvent.xtb_gbsa_name, solvent_name=solvent.name)
        return {
            "cation_reduction_raw_V_vs_AgAgCl": ip_eV_to_potential_vs_AgAgCl(ea_eV),
            "cation_reduction_calc_status": "ok",
            "cation_reduction_calc_error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "cation_reduction_raw_V_vs_AgAgCl": float("nan"),
            "cation_reduction_calc_status": "failed",
            "cation_reduction_calc_error": _concise(exc),
        }


def ionpair_descriptors(
    electrolyte: Electrolyte,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str = DEFAULT_METHOD,
) -> dict[str, object]:
    """Per-salt ion-pair dissociation ΔG (kcal/mol), ALPB-proxy APPROXIMATE.

    ΔG = E(cation) + E(anion) − E(contact pair), with the contact pair the multi-fragment SMILES
    ``cation.anion`` (net charge 0), each species' energy from the cached engine (GFN2 proxy).
    dG > 0 ⇒ the pair is bound (energy is needed to separate it). If the contact pair cannot be
    assembled the status is ``skipped`` (never guessed). Reported-only, screening-grade.
    """

    cation = electrolyte.canonical_cation_smiles
    anion = electrolyte.canonical_anion_smiles
    pair_smiles = f"{cation}.{anion}"
    if Chem.MolFromSmiles(pair_smiles) is None:
        return {
            "ionpair_dissociation_dG_kcal": float("nan"),
            "ionpair_method": IONPAIR_METHOD,
            "ionpair_calc_status": "skipped",
            "ionpair_calc_error": f"could not assemble contact pair from {pair_smiles!r}",
        }
    try:
        e_pair = _gas_energy_eV(engine, cache, pair_smiles, charge=0, multiplicity=1, method=method)
        e_cat = _gas_energy_eV(engine, cache, cation, charge=1, multiplicity=1, method=method)
        e_an = _gas_energy_eV(engine, cache, anion, charge=-1, multiplicity=1, method=method)
        dg_kcal = (e_cat + e_an - e_pair) * EV_TO_KCAL_MOL
        return {
            "ionpair_dissociation_dG_kcal": dg_kcal,
            "ionpair_method": IONPAIR_METHOD,
            "ionpair_calc_status": "ok",
            "ionpair_calc_error": "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ionpair_dissociation_dG_kcal": float("nan"),
            "ionpair_method": IONPAIR_METHOD,
            "ionpair_calc_status": "failed",
            "ionpair_calc_error": _concise(exc),
        }

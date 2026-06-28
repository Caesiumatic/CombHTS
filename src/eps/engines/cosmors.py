"""Decoupled openCOSMO-RS solvation free energy (directive §4.1 COSMO-RS).

ORCA 6.1 computes a molecule's σ-profile (a ``.orcacosmo`` file) once via a COSMO calculation; the
bundled standalone ``openCOSMORS`` binary then combines any (solute, solvent) pair from two ``.orcacosmo``
files via a small JSON in milliseconds, with no further DFT. This module exploits that to DECOUPLE the
expensive part (one σ-profile per species) from the free pairwise ΔGsolv combination, so the full
monomer × solvent grid costs ``N_monomers + N_solvents`` σ-profiles, not ``N_pairs`` DFT calls.

Validated 2026-06-28: combining a solute σ-profile with a solvent σ-profile generated in a SEPARATE ORCA
run reproduces the integrated per-pair dGsolv to the digit (thiophene/MeCN = −4.132111549377441 kcal/mol).
See ``docs/research/opencosmors_decoupling_20260628.md``.

Per-species DFT cost (BP86/def2-TZVPD COSMO, 1 core): ~2 min for a 5-heavy-atom monomer, ~45 min for a
25-heavy-atom monomer. σ-profile generation is run on Lop via SGE; the combination step is cheap.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path

from rdkit import Chem

from eps.structures import smiles_to_xyz

# openCOSMO-RS 24a parametrisation — fixed constants taken VERBATIM from ORCA's own generated input JSON
# (a validated thiophene/MeCN run). The only per-pair fields are the solute's dGsolv_E_gas and
# dGsolv_numberOfAtomsInRing plus componentPaths/calculations, filled in by ``dgsolv_kcal_mol``.
COSMORS_24A_PARAMS: dict[str, object] = {
    "Aeff": 5.925,
    "ln_alpha": 0.202,
    "ln_CHB": 0.166,
    "CHBT": 1.5,
    "SigmaHB": 0.009611,
    "Rav": 0.5,
    "fCorr": 2.4,
    "RavCorr": 1.0,
    "comb_SG_A_std": 41.624,
    "comb_SG_z_coord": 10.0,
    "dGsolv_eta": -4.448,
    "dGsolv_omega_ring": 0.263,
    "dGsolv_tau": {
        "1": 0.02934, "6": 0.02288, "7": 0.0007008, "8": 0.003545, "9": 0.005609,
        "14": 0.004216, "15": 0.003608, "16": 0.03499, "17": 0.03414, "35": 0.04085, "53": 0.213,
    },
}

DEFAULT_REF_SOLVENT = "water"  # σ-profile is solvent-independent; the ref only drives ORCA to emit it.


def _opencosmors_binary() -> str:
    """Locate the standalone openCOSMORS binary bundled with ORCA."""
    found = shutil.which("openCOSMORS")
    if found:
        return found
    orca_home = os.environ.get("ORCA_HOME")
    if orca_home:
        candidate = Path(orca_home) / "openCOSMORS"
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "openCOSMORS binary not found (not on PATH and ORCA_HOME unset). Load the ORCA module."
    )


def _species_key(canonical_smiles: str) -> str:
    return sha1(canonical_smiles.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class SigmaProfile:
    """A cached, reusable σ-profile for one species (role- and solvent-independent)."""

    canonical_smiles: str
    orcacosmo_path: Path
    e_gas: list[float]            # dGsolv_E_gas (solute-specific)
    n_atoms_in_ring: list[int]    # dGsolv_numberOfAtomsInRing (solute-specific)

    def fields_path(self) -> Path:
        return self.orcacosmo_path.with_suffix(".fields.json")


def _cached(cache_dir: Path, canonical_smiles: str) -> SigmaProfile | None:
    key = _species_key(canonical_smiles)
    orcacosmo = cache_dir / f"{key}.orcacosmo"
    fields = cache_dir / f"{key}.fields.json"
    if orcacosmo.exists() and fields.exists():
        data = json.loads(fields.read_text(encoding="utf-8"))
        return SigmaProfile(canonical_smiles, orcacosmo, data["e_gas"], data["n_atoms_in_ring"])
    return None


def generate_sigma_profile(
    smiles: str,
    *,
    cache_dir: str | Path,
    orca_binary: str = "orca",
    ref_solvent: str = DEFAULT_REF_SOLVENT,
    nprocs: int = 1,
    maxcore_mb: int = 2000,
) -> SigmaProfile:
    """Generate (or load from cache) the σ-profile of ``smiles`` via one ORCA COSMORS run.

    Runs ``! COSMORS(ref_solvent)`` on the species as solute; ORCA emits the species' own σ-profile
    (``*.solute.orcacosmo``) and a JSON carrying its ``dGsolv_E_gas`` / ``dGsolv_numberOfAtomsInRing``.
    Those are cached and reused for any later pairing (the ref solvent is irrelevant to the σ-profile).
    """

    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        raise ValueError(f"Invalid SMILES for σ-profile: {smiles!r}")
    canonical = Chem.MolToSmiles(mol, canonical=True)

    cached = _cached(cache_dir, canonical)
    if cached is not None:
        return cached

    xyz_lines = smiles_to_xyz(canonical, charge=0).splitlines()
    if len(xyz_lines) < 3:
        raise ValueError(f"Generated XYZ has no coordinates for {smiles!r}")
    coords = "\n".join(xyz_lines[2:])  # drop .xyz count+comment header; ORCA `* xyz` wants atom lines only
    inp = (
        f"! COSMORS({ref_solvent}) TightSCF\n"
        f"%pal nprocs {nprocs} end\n"
        f"%maxcore {maxcore_mb}\n"
        f"* xyz 0 1\n{coords}\n*\n"
    )
    with tempfile.TemporaryDirectory(prefix="eps-cosmors-") as tmp:
        run_dir = Path(tmp)
        (run_dir / "job.inp").write_text(inp, encoding="utf-8")
        completed = subprocess.run(
            [orca_binary, str(run_dir / "job.inp")],
            cwd=run_dir, check=False, capture_output=True, text=True,
        )
        out = completed.stdout + "\n" + completed.stderr
        if completed.returncode != 0 or "ORCA TERMINATED NORMALLY" not in out:
            tail = "\n".join(out.splitlines()[-30:])
            raise RuntimeError(f"ORCA COSMORS σ-profile run failed for {smiles!r}:\n{tail}")
        solute_profiles = list(run_dir.glob("*.solute.orcacosmo"))
        job_jsons = [p for p in run_dir.glob("*.json") if not p.name.endswith("_out.json")]
        if not solute_profiles or not job_jsons:
            raise RuntimeError(f"ORCA produced no .orcacosmo/.json for {smiles!r}")
        job_json = json.loads(job_jsons[0].read_text(encoding="utf-8"))
        key = _species_key(canonical)
        dest = cache_dir / f"{key}.orcacosmo"
        shutil.copyfile(solute_profiles[0], dest)
        fields = {
            "smiles": canonical,
            "e_gas": job_json["dGsolv_E_gas"],
            "n_atoms_in_ring": job_json["dGsolv_numberOfAtomsInRing"],
        }
        (cache_dir / f"{key}.fields.json").write_text(json.dumps(fields), encoding="utf-8")
    return SigmaProfile(canonical, dest, fields["e_gas"], fields["n_atoms_in_ring"])


def build_combine_payload(
    solute: SigmaProfile, solvent: SigmaProfile, *, temperature: float = 298.15
) -> dict:
    """Assemble the openCOSMORS input JSON: fixed 24a params + solute fields + the two σ-profiles."""
    payload = dict(COSMORS_24A_PARAMS)
    payload["dGsolv_E_gas"] = solute.e_gas
    payload["dGsolv_numberOfAtomsInRing"] = solute.n_atoms_in_ring
    payload["componentPaths"] = [str(solute.orcacosmo_path), str(solvent.orcacosmo_path)]
    payload["calculations"] = [
        {
            "concentrations": [[0.0, 1.0]],
            "temperatures": [temperature],
            "reference_state_types": [4],
            "component_indices": [0, 1],
        }
    ]
    return payload


def dgsolv_kcal_mol(
    solute: SigmaProfile,
    solvent: SigmaProfile,
    *,
    opencosmors_binary: str | None = None,
    temperature: float = 298.15,
) -> float:
    """Solvation free energy of ``solute`` in ``solvent`` (kcal/mol) by combining two cached σ-profiles.

    Pure statistical-mechanics integration over the stored σ-profiles — no DFT, milliseconds.
    """
    binary = opencosmors_binary or _opencosmors_binary()
    payload = build_combine_payload(solute, solvent, temperature=temperature)
    with tempfile.TemporaryDirectory(prefix="eps-cosmors-comb-") as tmp:
        in_json = Path(tmp) / "combine.json"
        out_json = Path(tmp) / "combine_out.json"
        in_json.write_text(json.dumps(payload), encoding="utf-8")
        completed = subprocess.run(
            [binary, str(in_json), str(out_json)],
            check=False, capture_output=True, text=True,
        )
        if completed.returncode != 0 or not out_json.exists():
            raise RuntimeError(
                f"openCOSMORS combine failed (exit {completed.returncode}):\n{completed.stdout}\n{completed.stderr}"
            )
        result = json.loads(out_json.read_text(encoding="utf-8"))
    return float(result["dGsolv"][0][0][0])

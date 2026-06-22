#!/usr/bin/env python3
"""Prepare or run the six-anchor ORCA dimer optical calibration.

This is a diagnostic calibration artifact. It does not update scoring, weights, or
calibration profiles. Optical energies are neutral-dimer lowest singlet excitations in eV.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rdkit import Chem

from eps.chemspace import load_monomers
from eps.engines import CalcRequest, SpeciesSpec
from eps.storage import SQLiteCache
from eps.storage.cache import cached_run
from eps.structures.oligomer import (
    PolymerizationSpec,
    load_polymerization_specs,
    oligomer_smiles,
)
from eps.workflow.orca_pilots import (
    build_mock_orca_pilot_engines,
    build_real_orca_pilot_engines,
    load_orca_pilot_config,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANCHORS = PROJECT_ROOT / "data" / "lit_curation" / "optical_anchors_selected.csv"
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "orca_pilots.yaml"
DEFAULT_OUTDIR = PROJECT_ROOT / "outputs" / "optical_calibration_n6"
DEFAULT_PILOT_CACHE = (
    PROJECT_ROOT / "outputs" / "orca_optical_pilot_corrected" / "cache.sqlite"
)


@dataclass(frozen=True)
class AnchorRequest:
    """One staging-derived polymer anchor represented by a neutral oligomer."""

    polymer: str
    monomer_smiles: str
    monomer_class: str
    experimental_gap_eV: float
    gap_method: str
    source_doi: str
    citation: str
    selected_reason: str
    anchor_confidence: str
    monomer_name: str
    oligomer_n: int
    oligomer_smiles: str
    polymerization_approximate: bool
    polymerization_notes: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("mock", "orca"), default="mock")
    parser.add_argument("--anchors", type=Path, default=DEFAULT_ANCHORS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument(
        "--pilot-cache",
        type=Path,
        default=DEFAULT_PILOT_CACHE,
        help="Read-only source for exact-key cache reuse; the source is never modified.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate anchors/methods and print cache status without running an engine.",
    )
    return parser.parse_args()


def _canonical(smiles: str) -> str:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES in optical anchors: {smiles}")
    return Chem.MolToSmiles(mol)


def load_anchor_requests(anchor_path: Path, config_path: Path) -> list[AnchorRequest]:
    """Load exactly six HIGH staging anchors and construct the pilot's neutral dimers."""

    frame = pd.read_csv(anchor_path)
    high = frame[frame["anchor_confidence"].str.lower().eq("high")].copy()
    if len(high) != 6:
        raise ValueError(f"Expected exactly 6 HIGH anchors in {anchor_path}, found {len(high)}")

    optical = load_orca_pilot_config(config_path)["optical"]
    oligomer_n = int(optical["oligomer_n"])
    if oligomer_n != 2:
        raise ValueError(
            "This diagnostic must reproduce the pilot dimer model (oligomer_n=2); "
            f"{config_path} requests n={oligomer_n}"
        )
    if int(optical["nprocs"]) != 1:
        raise ValueError("Lop ORCA optical calibration must remain serial (nprocs=1)")

    monomers = {_canonical(m.canonical_smiles): m for m in load_monomers()}
    specs = load_polymerization_specs()
    requests: list[AnchorRequest] = []
    for row in high.to_dict(orient="records"):
        monomer_smiles = str(row["monomer_smiles"])
        canonical = _canonical(monomer_smiles)
        monomer = monomers.get(canonical)
        if monomer is None:
            # PProDOP is selected staging data but is not in the 36-row library. Its clean
            # five-membered heteroaromatic has the same data-documented alpha coupling rule.
            monomer_name = "ProDOP (staging anchor)"
            spec = PolymerizationSpec(
                monomer_name=monomer_name,
                coupling_mode="alpha",
                building_block_smiles="",
                approximate=False,
                notes="2,5-alpha coupling auto-derived for the staging-only ProDOP anchor",
            )
        else:
            monomer_name = monomer.name
            spec = specs[monomer.name]
        dimer = oligomer_smiles(canonical, spec, oligomer_n)
        requests.append(
            AnchorRequest(
                polymer=str(row["polymer"]),
                monomer_smiles=monomer_smiles,
                monomer_class=str(row["monomer_class"]),
                experimental_gap_eV=float(row["optical_gap_eV"]),
                gap_method=str(row["gap_method"]),
                source_doi=str(row["source_doi"]),
                citation=str(row["citation"]),
                selected_reason=str(row["selected_reason"]),
                anchor_confidence=str(row["anchor_confidence"]),
                monomer_name=monomer_name,
                oligomer_n=oligomer_n,
                oligomer_smiles=dimer,
                polymerization_approximate=spec.approximate,
                polymerization_notes=spec.notes,
            )
        )
    return requests


def _cache_key_rows(
    requests: list[AnchorRequest], stda_method: str, tddft_method: str, solvent_name: str
) -> list[tuple[str, int, str, str, str]]:
    return [
        (anchor.oligomer_smiles, 0, method, solvent_name, "optical_gap")
        for anchor in requests
        for method in (stda_method, tddft_method)
    ]


def _existing_keys(path: Path) -> set[tuple[str, int, str, str, str]]:
    if not path.exists():
        return set()
    with sqlite3.connect(path) as connection:
        rows = connection.execute(
            "SELECT canonical_smiles, charge, method, solvent_name, quantity FROM results"
        ).fetchall()
    return {tuple(row) for row in rows}


def seed_exact_cache_hits(source: Path, target: Path, wanted: set[tuple]) -> int:
    """Copy exact requested rows into a distinct cache without modifying the pilot cache."""

    if not source.exists() or source.resolve() == target.resolve():
        return 0
    SQLiteCache(target)  # Ensure the target schema exists.
    copied = 0
    with sqlite3.connect(source) as source_db, sqlite3.connect(target) as target_db:
        for row in source_db.execute("SELECT * FROM results"):
            key = (row[0], row[1], row[2], row[3], row[4])
            if key not in wanted:
                continue
            before = target_db.total_changes
            target_db.execute(
                "INSERT OR IGNORE INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row
            )
            copied += target_db.total_changes - before
        target_db.commit()
    return copied


def _run_one(cache: SQLiteCache, engine, species: SpeciesSpec, method: str, solvent: str):
    request = CalcRequest(
        species=species, method=method, solvent_eps_r=None, quantity="optical_gap"
    )
    try:
        result = cached_run(cache, engine, request, solvent)
        return float(result.value), "ok", ""
    except Exception as exc:  # noqa: BLE001 - preserve every per-anchor failure.
        message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
        return float("nan"), "failed", f"{exc.__class__.__name__}: {message}"[:500]


def main() -> int:
    args = parse_args()
    outdir = args.outdir.resolve()
    cache_path = (args.cache or (outdir / "cache.sqlite")).resolve()
    requests = load_anchor_requests(args.anchors.resolve(), args.config.resolve())
    engines = (
        build_mock_orca_pilot_engines()
        if args.engine == "mock"
        else build_real_orca_pilot_engines(args.config.resolve())
    )
    stda_engine, stda_method = engines[2], engines[3]
    tddft_engine, tddft_method = engines[4], engines[5]
    optical = load_orca_pilot_config(args.config.resolve())["optical"]
    solvent = str(optical["solvent_name"])
    wanted = set(_cache_key_rows(requests, stda_method, tddft_method, solvent))
    pilot_hits = wanted.intersection(_existing_keys(args.pilot_cache.resolve()))
    target_hits = wanted.intersection(_existing_keys(cache_path))

    print(f"Engine: {args.engine}")
    print(f"Method: {stda_method} + {tddft_method}")
    print("Oligomer model: neutral dimers (n=2), matching the corrected ORCA pilot")
    print(f"Output directory: {outdir}")
    print(f"Fresh/resumable cache: {cache_path}")
    print(f"Read-only pilot cache: {args.pilot_cache.resolve()}")
    print(f"Exact pilot-cache request hits: {len(pilot_hits)}/{len(wanted)}")
    print(f"Existing target-cache request hits: {len(target_hits)}/{len(wanted)}")
    for anchor in requests:
        methods_cached = sum(
            (
                anchor.oligomer_smiles,
                0,
                method,
                solvent,
                "optical_gap",
            )
            in (pilot_hits | target_hits)
            for method in (stda_method, tddft_method)
        )
        print(
            f"- {anchor.monomer_name}: dimer; cached {methods_cached}/2; "
            f"needed {2 - methods_cached}/2"
        )
    if args.preflight_only:
        return 0

    outdir.mkdir(parents=True, exist_ok=True)
    copied = seed_exact_cache_hits(args.pilot_cache.resolve(), cache_path, wanted)
    cache = SQLiteCache(cache_path)
    rows: list[dict[str, object]] = []
    for anchor in requests:
        species = SpeciesSpec(anchor.oligomer_smiles, charge=0, multiplicity=1)
        stda_value, stda_status, stda_error = _run_one(
            cache, stda_engine, species, stda_method, solvent
        )
        tddft_value, tddft_status, tddft_error = _run_one(
            cache, tddft_engine, species, tddft_method, solvent
        )
        rows.append(
            {
                **anchor.__dict__,
                "stda_gap_eV": stda_value,
                "stda_calc_status": stda_status,
                "stda_calc_error": stda_error,
                "tddft_gap_eV": tddft_value,
                "tddft_calc_status": tddft_status,
                "tddft_calc_error": tddft_error,
                "stda_method": stda_method,
                "tddft_method": tddft_method,
                "solvent_name": solvent,
                "engine": args.engine,
                "anchor_source_csv": str(args.anchors.resolve()),
            }
        )
    points = pd.DataFrame(rows)
    points_path = outdir / "optical_n6_points.csv"
    points.to_csv(points_path, index=False)
    provenance = {
        "status": "diagnostic_only_not_production_calibration",
        "engine": args.engine,
        "anchor_count": len(requests),
        "oligomer_n": 2,
        "stda_method": stda_method,
        "tddft_method": tddft_method,
        "pilot_cache": str(args.pilot_cache.resolve()),
        "target_cache": str(cache_path),
        "pilot_rows_copied": copied,
        "points_csv": str(points_path),
        "scoring_changed": False,
    }
    (outdir / "run_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    failures = int(
        ((points["stda_calc_status"] != "ok") | (points["tddft_calc_status"] != "ok")).sum()
    )
    print(f"Copied exact pilot-cache rows into fresh cache: {copied}")
    print(f"Wrote anchor/computed points: {points_path}")
    print(f"Paired anchors: {len(points) - failures}/6; failed anchors: {failures}")
    if args.engine == "mock":
        print("NOTE: mock values are non-physical pre-flight data and are not scientific results.")
    return 0 if failures == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

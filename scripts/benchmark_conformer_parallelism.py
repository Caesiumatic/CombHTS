#!/usr/bin/env python
"""Local RDKit-only conformer parallelism benchmark.

This utility is an engineering diagnostic. It does not call xTB, sTDA, ORCA,
Gaussian, the network, the cluster, or production workflow outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rdkit import Chem, rdBase
from rdkit.Chem import AllChem

from eps.chemspace import load_monomers
from eps.structures.geometry import ETKDG_MAX_ITERATIONS, ETKDG_RANDOM_SEED
from eps.structures.oligomer import load_polymerization_specs, oligomer_smiles

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RDKit-only conformer threading benchmark for CombHTS engineering diagnostics."
    )
    parser.add_argument("--monomer", required=True, help="Monomer name from data/monomers.csv.")
    parser.add_argument("--oligomer-length", type=int, default=2, help="Oligomer length n.")
    parser.add_argument("--conformers", type=int, default=20, help="Number of conformers to embed.")
    parser.add_argument(
        "--threads",
        default="1,2,4",
        help="Comma-separated RDKit thread counts to test, for example 1,2,4.",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Repeat count per thread setting.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to /tmp/combhts_conformer_parallelism_<timestamp>.json.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        threads = _parse_threads(args.threads)
        if args.oligomer_length < 1:
            raise ValueError("--oligomer-length must be >= 1")
        if args.conformers < 1:
            raise ValueError("--conformers must be >= 1")
        if args.repeats < 1:
            raise ValueError("--repeats must be >= 1")
        output_path = _output_path(args.output_json)
        smiles = _resolve_smiles(args.monomer, args.oligomer_length)
    except ValueError as exc:
        parser.error(str(exc))

    records: list[dict[str, Any]] = []
    for thread_count in threads:
        for repeat_index in range(args.repeats):
            records.append(
                _run_once(
                    smiles=smiles,
                    conformers=args.conformers,
                    threads=thread_count,
                    repeat_index=repeat_index,
                )
            )

    successful = [record for record in records if record["embedding_success"]]
    result = {
        "label": "local engineering diagnostic; not a production or scientific result",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "monomer": args.monomer,
        "oligomer_length": args.oligomer_length,
        "smiles": smiles,
        "conformer_count_requested": args.conformers,
        "thread_counts": threads,
        "repeats": args.repeats,
        "environment": _environment(),
        "rdkit_thread_parameter_supported": _rdkit_thread_parameter_supported(),
        "runs": records,
        "summary": _summarize(records),
    }
    result["thread_support_appears_effective"] = _thread_support_appears_effective(result["summary"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote local engineering diagnostic JSON: {output_path}")
    print(f"Successful runs: {len(successful)}/{len(records)}")
    return 0 if successful else 2


def _parse_threads(raw: str) -> list[int]:
    try:
        values = [int(item.strip()) for item in raw.split(",") if item.strip()]
    except ValueError as exc:
        raise ValueError("--threads must be a comma-separated list of positive integers") from exc
    if not values or any(value < 1 for value in values):
        raise ValueError("--threads must contain at least one positive integer")
    return sorted(dict.fromkeys(values))


def _output_path(path: Path | None) -> Path:
    if path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return Path(tempfile.gettempdir()) / f"combhts_conformer_parallelism_{stamp}.json"
    output = path
    if not output.is_absolute():
        output = Path.cwd() / output
    resolved = output.resolve()
    forbidden_roots = [PROJECT_ROOT / "outputs", PROJECT_ROOT / "data", PROJECT_ROOT / "configs"]
    for forbidden in forbidden_roots:
        try:
            resolved.relative_to(forbidden.resolve())
        except ValueError:
            continue
        raise ValueError(f"output JSON must not be written under {forbidden}")
    return resolved


def _resolve_smiles(monomer_name: str, oligomer_length: int) -> str:
    monomers = {monomer.name: monomer for monomer in load_monomers()}
    if monomer_name not in monomers:
        known = ", ".join(sorted(monomers))
        raise ValueError(f"unknown monomer {monomer_name!r}; known monomers: {known}")
    monomer = monomers[monomer_name]
    if oligomer_length == 1:
        return monomer.canonical_smiles
    specs = load_polymerization_specs()
    spec = specs.get(monomer.name)
    if spec is None:
        raise ValueError(f"monomer {monomer_name!r} has no polymerization spec for n={oligomer_length}")
    return oligomer_smiles(monomer.canonical_smiles, spec, oligomer_length)


def _run_once(
    *,
    smiles: str,
    conformers: int,
    threads: int,
    repeat_index: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    record: dict[str, Any] = {
        "mode": "serial" if threads == 1 else "threaded",
        "threads": threads,
        "repeat_index": repeat_index,
        "conformer_count_requested": conformers,
    }
    try:
        mol = Chem.MolFromSmiles(smiles, sanitize=True)
        if mol is None:
            raise ValueError(f"invalid SMILES: {smiles}")
        mol = Chem.AddHs(mol)
        if not AllChem.MMFFHasAllMoleculeParams(mol):
            raise ValueError("MMFF94 cannot type every atom")
        params = AllChem.ETKDGv3()
        params.randomSeed = ETKDG_RANDOM_SEED + repeat_index
        params.useRandomCoords = True
        params.maxIterations = ETKDG_MAX_ITERATIONS
        if hasattr(params, "numThreads"):
            params.numThreads = threads
        conf_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=conformers, params=params))
        if not conf_ids:
            raise ValueError("RDKit returned zero conformers")
        opt_results = AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=threads, maxIters=500)
        energies = [float(energy) for _status, energy in opt_results]
        best_index = min(range(len(energies)), key=lambda index: energies[index])
        best_conf_id = int(conf_ids[best_index])
        record.update(
            {
                "embedding_success": True,
                "conformer_count_embedded": len(conf_ids),
                "mmff_converged_count": sum(1 for status, _energy in opt_results if int(status) == 0),
                "minimum_mmff_energy": float(energies[best_index]),
                "selected_conformer_id": best_conf_id,
                "geometry_digest": _geometry_digest(mol, best_conf_id),
                "error": "",
            }
        )
    except Exception as exc:  # noqa: BLE001 - one setting failure is part of the benchmark record.
        record.update(
            {
                "embedding_success": False,
                "conformer_count_embedded": 0,
                "mmff_converged_count": 0,
                "minimum_mmff_energy": None,
                "selected_conformer_id": None,
                "geometry_digest": "",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    record["wall_time_s"] = time.perf_counter() - started
    return record


def _geometry_digest(mol: Chem.Mol, conf_id: int) -> str:
    conformer = mol.GetConformer(conf_id)
    chunks: list[str] = []
    for atom in mol.GetAtoms():
        pos = conformer.GetAtomPosition(atom.GetIdx())
        chunks.append(f"{atom.GetSymbol()}:{pos.x:.6f}:{pos.y:.6f}:{pos.z:.6f}")
    return hashlib.sha256("|".join(chunks).encode("utf-8")).hexdigest()


def _environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "rdkit_version": rdBase.rdkitVersion,
    }


def _rdkit_thread_parameter_supported() -> bool:
    params = AllChem.ETKDGv3()
    return hasattr(params, "numThreads")


def _summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for threads in sorted({int(record["threads"]) for record in records}):
        group = [record for record in records if int(record["threads"]) == threads]
        successes = [record for record in group if record["embedding_success"]]
        times = [float(record["wall_time_s"]) for record in successes]
        energies = [
            float(record["minimum_mmff_energy"])
            for record in successes
            if record["minimum_mmff_energy"] is not None
        ]
        digests = {record["geometry_digest"] for record in successes if record["geometry_digest"]}
        summary[str(threads)] = {
            "mode": "serial" if threads == 1 else "threaded",
            "n_runs": len(group),
            "n_success": len(successes),
            "median_wall_time_s": statistics.median(times) if times else None,
            "min_wall_time_s": min(times) if times else None,
            "max_wall_time_s": max(times) if times else None,
            "minimum_mmff_energy_min": min(energies) if energies else None,
            "minimum_mmff_energy_max": max(energies) if energies else None,
            "unique_geometry_digests": len(digests),
        }
    baseline = summary.get("1", {}).get("median_wall_time_s")
    if baseline:
        for item in summary.values():
            median = item.get("median_wall_time_s")
            item["speedup_vs_threads_1"] = (baseline / median) if median else None
    return summary


def _thread_support_appears_effective(summary: dict[str, Any]) -> bool:
    baseline = summary.get("1", {}).get("median_wall_time_s")
    if not baseline:
        return False
    for key, item in summary.items():
        if key == "1":
            continue
        speedup = item.get("speedup_vs_threads_1")
        if speedup is not None and speedup >= 1.05:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())

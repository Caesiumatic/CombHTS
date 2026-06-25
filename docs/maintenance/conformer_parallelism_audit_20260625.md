# Conformer Parallelism Audit - 2026-06-25

## Purpose

Prepare a safe acceleration decision for RDKit conformer generation without changing production
geometry generation tonight. This audit is a local engineering diagnostic, not a scientific result.

No xTB, sTDA, ORCA, Gaussian, network, cluster, production cache, or production output path was
used.

## Code Inspection

- `src/eps/structures/geometry.py` currently embeds multiple ETKDGv3 conformers through
  `AllChem.EmbedMultipleConfs(...)`.
- The current production path does not pass `params.numThreads`.
- It currently optimizes conformers through `AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=500)`.
- The current production path does not pass `numThreads` to MMFF optimization.
- `scripts/run_tier1.sge` and `scripts/run_oligomer.sge` set `OMP_NUM_THREADS` from `NSLOTS`, but
  RDKit conformer embedding/optimization does not automatically use all scheduler slots unless
  RDKit thread parameters are set in code.
- No `MKL_NUM_THREADS` policy is present in current SGE templates.
- Tier-1 Python orchestration is serial at the stage level: monomer, monomer-solvent,
  solvent, anion-solvent, cation-solvent, and ion-pair tables are built in Python loops before
  the no-engine triad join.
- A single 24-core serial job can leave most cores idle if the active stage does not use
  thread-aware kernels.
- Process-level parallelism must not share one multi-writer SQLite cache unless that access pattern
  is proven safe. Task-local caches plus no-engine harvest are the safer design pattern.

## Benchmark Utility

Added:

```text
scripts/benchmark_conformer_parallelism.py
```

The utility:

- uses RDKit only;
- accepts monomer name, oligomer length, conformer count, thread counts, repeats, and output JSON;
- writes JSON under a user-supplied path or `/tmp` by default;
- rejects output paths under repository `outputs/`, `data/`, or `configs/`;
- records conformer counts, embed success, MMFF convergence count, minimum MMFF energy, selected
  conformer id, geometry digest, and wall time;
- records Python, platform, RDKit version, and whether the RDKit ETKDG parameter exposes
  `numThreads`;
- exits nonzero only for malformed input or complete benchmark failure.

Smoke test:

```text
tests/test_conformer_benchmark_script.py
```

## Measured Environment

| Item | Value |
| --- | --- |
| Platform | macOS-26.3.1-arm64-arm-64bit |
| Python | 3.11.15 |
| RDKit | 2022.09.5 |
| RDKit ETKDG `numThreads` parameter | present |

Raw JSON artifacts:

- `/private/tmp/combhts_conformer_thiophene_n2_20.json`
- `/private/tmp/combhts_conformer_thiophene_n6_50.json`
- `/private/tmp/combhts_conformer_edot_n2_20.json`

## Results

All runs succeeded: 9/9 for each case.

| Case | Threads | Median wall time (s) | Speedup vs 1 thread | Min energy range | Unique geometry digests |
| --- | ---: | ---: | ---: | --- | ---: |
| thiophene n=2, 20 confs | 1 | 0.0586 | 1.00x | 15.7530564872-15.7530564877 | 3 |
| thiophene n=2, 20 confs | 2 | 0.0313 | 1.87x | 15.7530564872-15.7530564877 | 3 |
| thiophene n=2, 20 confs | 4 | 0.0173 | 3.39x | 15.7530564872-15.7530564877 | 3 |
| thiophene n=6, 50 confs | 1 | 2.6774 | 1.00x | 53.4652500618-54.3883142965 | 3 |
| thiophene n=6, 50 confs | 2 | 1.3731 | 1.95x | 53.4652500618-54.3883142965 | 3 |
| thiophene n=6, 50 confs | 4 | 0.7318 | 3.66x | 53.4652500618-54.3883142965 | 3 |
| EDOT n=2, 20 confs | 1 | 0.2860 | 1.00x | 62.5417452533-62.5417452834 | 3 |
| EDOT n=2, 20 confs | 2 | 0.1475 | 1.94x | 62.5417452533-62.5417452834 | 3 |
| EDOT n=2, 20 confs | 4 | 0.0782 | 3.66x | 62.5417452533-62.5417452834 | 3 |

## Reproducibility

The benchmark intentionally varies the seed by repeat. Therefore each case has three unique
geometry digests across three repeats.

For each fixed repeat/seed, all thread counts produced identical selected geometry digests and
identical minimum MMFF energies:

- thiophene n=2: repeat 0/1/2 each had 1 unique digest and 1 unique energy across threads 1/2/4.
- thiophene n=6: repeat 0/1/2 each had 1 unique digest and 1 unique energy across threads 1/2/4.
- EDOT n=2: repeat 0/1/2 each had 1 unique digest and 1 unique energy across threads 1/2/4.

This bounded evidence establishes cross-thread deterministic equivalence for the tested molecules,
seed policy, conformer counts, and RDKit version.

## Interpretation

- RDKit threading appears effective in this local environment.
- Speedup is close to linear up to four threads for the tested MMFF-heavy cases.
- Merely requesting 16-24 scheduler slots does not accelerate the current production path unless
  the code passes thread counts into RDKit or splits work across safe independent tasks.
- The current Tier-1 orchestration remains mostly serial Python around per-species work.
- Shared SQLite could become a bottleneck or correctness risk under process-level parallelism.

## Future Patch Safety

Threaded conformer generation is safe enough to consider for a future reviewed patch because fixed
seeds produced identical selected geometries and energies across 1, 2, and 4 RDKit threads in this
bounded matrix.

A future production patch must still:

- preserve the conformer-search cache-key suffix;
- add tests for fixed-seed cross-thread equivalence;
- prove behavior on non-MMFF-typable species still falls back cleanly;
- benchmark on Lop with the actual scheduler environment;
- decide how thread counts are configured and recorded in provenance;
- avoid shared-cache multi-writer patterns.

No threaded production conformer generation was implemented in this work unit.

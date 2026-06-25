# Tier-1 Parallelization Plan - 2026-06-25

## Goal

Design a scheduler-safe Tier-1 parallelization path without implementing it in this work unit.
The design preserves the central architecture: expensive calculations are per species or
per species-solvent, never per triad. Triad construction and scoring remain no-engine joins.

## Current Scale

| Quantity | Count |
| --- | ---: |
| Monomers | 36 |
| Solvents | 13 |
| Electrolytes | 16 |
| Triads | 7,488 |
| Unique anions | 9 |
| Unique cations | 7 |
| Monomer-solvent tasks | 468 |
| Anion-solvent tasks | 117 |
| Cation-solvent tasks | 91 |

## Non-Negotiable Invariants

- Never run an engine per triad.
- Never duplicate expensive work for salts that share an ion.
- Keep mock-first behavior for every stage.
- Use task-local failure isolation.
- Make every task resumable.
- Record engine, method, config/data hashes, and task identity.
- Reject stale or hash-mismatched results.
- Do not use one concurrently written SQLite file unless a specific implementation proves it safe.
- Keep scientific thresholds, weights, coefficients, and method policy in data/config surfaces.

## Proposed Scheduler DAG

### Stage A - Plan And Validate

No engine calls.

Responsibilities:

- load production CSV libraries;
- load configs;
- canonicalize species identities;
- compute data/config/method hashes;
- write task manifests for stages B-E;
- record expected task counts;
- fail before scheduling if libraries or configs are invalid.

### Stage B - Monomer-Only Tasks

One task per unique monomer and method/config identity.

Current count: 36 tasks.

Quantities:

- optical gap/convergence descriptors;
- dimerization/radical-coupling descriptor;
- oligomer Eox series;
- frontier orbitals, radical-cation spin, reorganization, and other monomer secondary descriptors.

Threading:

- 1 thread for small mock/local smoke;
- 4 threads as the first real conformer-search candidate;
- 8 threads only after Lop benchmark proof.

### Stage C - Monomer-Solvent Tasks

One task per `(monomer_canonical_smiles, solvent_name, method/config identity)`.

Current count: 36 x 13 = 468 tasks.

Quantities:

- monomer Eox in solvent;
- monomer solvation-affinity proxy in solvent.

Threading:

- likely 1-4 threads per task;
- prefer more array tasks over one 24-core serial job unless a stage-specific benchmark proves
  scaling.

### Stage D - Solvent Tasks

One task per solvent and any explicit solvent-condition identity.

Current count: 13 solvent-only tasks.

Quantities:

- solvent anodic descriptor;
- solvent cathodic descriptor;
- solvent oxidation/reduction reorganization descriptors;
- measured-window selection remains a no-engine join over CSV rows.

Threading:

- usually 1 thread per solvent task is enough;
- solvent-condition tasks are cheap enough to schedule as separate jobs if needed.

### Stage E - Ion Tasks

Task families:

- anion-solvent: 9 x 13 = 117 tasks;
- cation-solvent: 7 x 13 = 91 tasks;
- ion-pair: one per salt identity = 16 tasks when enabled.

Quantities:

- anion oxidation;
- anion volume descriptors;
- cation reduction descriptors;
- ion-pair dissociation descriptors.

Threading:

- 1-4 threads depending on engine quantity;
- keep anion/cation identity deduplicated across salts.

### Stage F - No-Engine Harvest, Join, Score, Report

No engine calls.

Responsibilities:

- validate every expected result or record explicit missing/failed state;
- reject duplicate task results;
- reject hash mismatches;
- merge task-local outputs into per-species tables;
- apply measured-first solvent-window policy;
- join all monomer x solvent x electrolyte triads;
- apply hard filters;
- score survivors;
- emit ranked CSV, all-triads audit CSV, descriptor artifacts, and provenance.

## Task Manifest Columns

Each manifest row should include:

- `task_id`
- `stage`
- `quantity_family`
- `species_role`
- `canonical_smiles`
- `charge_state`
- `multiplicity`
- `solvent_name`
- `solvent_eps_r`
- `xtb_gbsa_name`
- `monomer_name`, `salt`, or ion label where applicable
- `method_label`
- `engine_name`
- `config_hash`
- `data_hash`
- `method_hash`
- `cache_key_preview`
- `result_dir`
- `status_path`
- `result_json_path`
- `failure_json_path`
- `created_at_utc`

## Task-Local Layout

Recommended per-task directory:

```text
outputs/tier1_tasks/<stage>/<task_id>/
  manifest_row.json
  result.json
  failure.json
  status.txt
  done.ok
  cache.sqlite
  raw/
```

`done.ok` is written atomically only after `result.json` validates. Failures write
`failure.json` and `status.txt` without creating `done.ok`.

## Completion And Failure Semantics

- `success`: `done.ok` exists, result schema validates, hashes match.
- `failed`: `failure.json` exists; harvest carries status/error, no fabricated values.
- `missing`: no terminal marker; harvest fails or records partial status depending on command mode.
- `duplicate`: more than one terminal success for same task identity; harvest blocks.
- `stale`: config/data/method hash mismatch; harvest blocks.
- `identity_mismatch`: result claims a different species/solvent/method than the manifest; harvest
  blocks.

## Cache Strategy

Preferred first implementation:

- one SQLite cache per task;
- no concurrent multi-writer access;
- harvest reads result JSON, not SQLite, as the public contract;
- optional later cache merge happens after all tasks finish and never controls scientific output.

Alternative later implementation:

- read-only shared seed cache plus task-local write caches;
- explicit cache export/import tool;
- no direct concurrent writes until SQLite locking and failure behavior are tested on Lop.

## SGE Array Mapping

Each stage gets a manifest and one SGE array template:

```text
SGE_TASK_ID -> manifest row number -> task_id -> result directory
```

The runner must:

- read exactly one manifest row;
- run exactly one task;
- write exactly one terminal status;
- never submit child jobs;
- never compute a triad-level quantity;
- return nonzero on malformed input or task failure.

## Scaling Toward Directive Target

For an eventual approximate 100 x 30 x 25 library:

- monomer-only: about 100 tasks;
- monomer-solvent: about 3,000 tasks;
- solvent-only: about 30 tasks;
- anion-solvent: about unique-anions x 30, likely hundreds not tens of thousands;
- cation-solvent: about unique-cations x 30;
- triads: about 75,000 no-engine join rows if using 100 x 30 x 25.

The engine task count grows with species combinations, not full triads. That is the central reason
array parallelization is viable.

## Why One 24-Core Serial Job Is Usually Worse

- Current Python orchestration loops serially across species families.
- RDKit only uses multiple cores when thread parameters are supplied.
- xTB/Gaussian/ORCA scaling is quantity- and system-dependent.
- One large job has poor failure isolation: one bad species can waste a long allocation.
- Many smaller array tasks improve queue backfill and resumability.
- Task-local caches prevent multi-writer SQLite contention.

## Migration Path From Tier-2 Patterns

Reuse the established Tier-2 plan/run/harvest shape:

1. `tier1-plan-tasks` writes manifests and provenance.
2. `tier1-run-task` executes one manifest row with mock or real engine.
3. `tier1-harvest-tasks` validates task results and writes per-species tables.
4. Existing `run_tier1` join/scoring logic consumes harvested tables.

Compatibility shims should keep the current `eps run-tier1` behavior available while the array path
is tested.

## Required Tests Before Implementation

- mock plan count tests for 36 x 13 x 16 current library;
- deduplication tests for shared anions/cations;
- one-task mock success and failure tests;
- task-local cache path tests;
- result hash mismatch rejection;
- duplicate result rejection;
- stale config/data/method rejection;
- no-engine harvest tests;
- full mock array mini-fixture across all stages;
- CLI contract tests for new commands;
- output schema tests proving harvested tables match current Tier-1 contracts;
- no-triad-engine-call test.

## Proposed Future PR Sequence

1. Add manifest dataclasses, task identity hashing, and plan-only command.
2. Add mock-only one-task runner for Stage B and harvest validation.
3. Extend runner/harvest to Stage C.
4. Extend runner/harvest to Stages D and E.
5. Add no-engine final join/scoring command consuming harvested tables.
6. Add SGE templates for mock smoke arrays.
7. Run a small real xTB array on Lop with task-local caches.
8. Compare harvested output against serial Tier-1 for a fixed mini-library.
9. Only then consider replacing or augmenting the production Tier-1 run path.

No implementation was performed in this work unit.

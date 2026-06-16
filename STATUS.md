# Project Status
_Last updated: 2026-06-16_

## Current phase
Engineering scaffold complete and real xTB validation has run successfully on the SCS
cluster. First-pass benchmark provenance cleanup is in place, but primary-source
curation remains the scientific bottleneck before any calibrated xTB MAE is trusted.

## What works and is verified
- Per-species architecture, SQLite caching (idempotent), Engine abstraction, mock-first.
- redox -> V vs Ag/AgCl conversion: single tested function, constants pinned (ABS_SHE=4.28, AgAgCl shift=-0.197).
- Tier-1 funnel: per-species calc -> triad JOIN -> hard filters -> composite score + Pareto, end-to-end on MockEngine.
- Calibration + benchmark validation harness (gates trust; PerfectEoxEngine proves plumbing).
- Benchmark CSV now has full provenance columns: native value/reference, potential type,
  conversion constant/source, medium, citation, reliability tier, and notes.
- Benchmark methods memo exists at `docs/benchmark_methods_memo.md` with conversion
  constants, aqueous/nonaqueous caveats, potential-type mismatch, accuracy expectation,
  and deliberate exclusions.
- XTBEngine: wired, fixture-tested locally; physics correct (IP/EA charge/multiplicity/sign, solvated adiabatic redox via --alpb <name>, xtbout.json parsing).
- SCS cluster validation: Grid Engine (`qsub`/`qstat`) confirmed; `xtb/6.4.1` confirmed; `--alpb`, `--gbsa`, and `--json` confirmed; real thiophene xTB run produced `xtbout.json` with expected fields.
- Cluster CombHTS runs: `eps run-tier1 --engine mock` completed; `eps validate --engine xtb` completed on 12 benchmark rows (MAE before calibration = 5.398 V; after in-sample calibration = 0.145 V; Tier-1 target PASS; calibration y = 0.572*x - 2.584, R^2 = 0.643).

## Placeholders / not yet validated (do not treat as real)
- optical_gap = HOMO-LUMO gap on an MMFF geometry (not an optical gap, not an oligomer).
- dimerization_dG = rescaled gas energy (fake signal).
- benchmark.csv is no longer an unstructured seed, but it is still not a primary
  calibration set: current rows = 3 Tier B, 10 Tier C, 0 Tier A.
- Many benchmark values remain review-level or condition-incomplete sanity checks.
- solvent anodic limits are seed approximations, not literature-verified.

## Open debts (priority order)
1. (P0 science) Recover primary CV tables/traces for benchmark rows and promote only
   explicit-source rows to Tier A/B. Current table is auditable but mostly Tier C;
   do not use it to claim scientifically meaningful calibration accuracy.
2. (P0 science) Replace solvent anodic limits with measured values vs Ag/AgCl; current values are stopgap = cathodic + spec ESW width (every row flagged TODO).
3. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
4. Get professor sign-off on the 4 ALPB proxy solvents (PC->dmso, GBL->acetonitrile, sulfolane->dmso, NMP->dmf), or move to ddCOSMO with manual epsilon.
5. In XTBEngine._run_xtb, check subprocess returncode BEFORE parsing xtbout.json.
6. Switch calibration MAE to leave-one-out CV (currently in-sample, optimistic).
7. Write queue-safe SGE job scripts for `eps validate --engine xtb` and `eps run-tier1 --engine xtb`; avoid running production calculations in interactive sessions.
8. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
9. Not yet built: Tier-2 DFT adapter, analysis/plots, expand libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
For `data/benchmark.csv`, recover primary CV values for EDOT/ProDOT/EDOP, pyrrole,
aniline, carbazole/fluorene/CPDT, furan, and selenophene; keep nonaqueous calibration
on an Fc/Fc+ master scale where possible.

## Architecture invariants
See AGENTS.md (per-species not per-triad; mock-first; data in CSV, thresholds in YAML; SQLite cache; single pinned redox function). Do not restate them here to avoid drift.

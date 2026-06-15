# Project Status
_Last updated: 2026-06-15_

## Current phase
Engineering scaffold complete (mock-first pipeline + real xTB engine wired and locally
testable). Next phase = first real xTB run on the cluster + experimental-data curation.

## What works and is verified (mock/local)
- Per-species architecture, SQLite caching (idempotent), Engine abstraction, mock-first.
- redox -> V vs Ag/AgCl conversion: single tested function, constants pinned (ABS_SHE=4.28, AgAgCl shift=-0.197).
- Tier-1 funnel: per-species calc -> triad JOIN -> hard filters -> composite score + Pareto, end-to-end on MockEngine.
- Calibration + benchmark validation harness (gates trust; PerfectEoxEngine proves plumbing).
- XTBEngine: wired, fixture-tested locally; physics correct (IP/EA charge/multiplicity/sign, solvated adiabatic redox via --alpb <name>, xtbout.json parsing). Not yet run on real xtb.

## Placeholders / not yet validated (do not treat as real)
- optical_gap = HOMO-LUMO gap on an MMFF geometry (not an optical gap, not an oligomer).
- dimerization_dG = rescaled gas energy (fake signal).
- benchmark.csv and solvent anodic limits are seed approximations, not literature-verified.

## Open debts (priority order)
1. (P0 science) benchmark.csv reference-electrode cleanup: currently mixes SCE/Ag-AgCl and aqueous/nonaqueous; will poison calibration. If first real MAE >> 0.30 V, look here first.
2. (P0 science) Replace solvent anodic limits with measured values vs Ag/AgCl; current values are stopgap = cathodic + spec ESW width (every row flagged TODO).
3. Confirm installed xtb's solvent list and --json behavior on the cluster; capture a REAL xtbout.json as a fixture (current fixture is hand-written).
4. Get professor sign-off on the 4 ALPB proxy solvents (PC->dmso, GBL->acetonitrile, sulfolane->dmso, NMP->dmf), or move to ddCOSMO with manual epsilon.
5. In XTBEngine._run_xtb, check subprocess returncode BEFORE parsing xtbout.json.
6. Switch calibration MAE to leave-one-out CV (currently in-sample, optimistic).
7. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
8. Not yet built: Tier-2 DFT adapter, analysis/plots, expand libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
On the cluster: `xtb --help` (confirm solvent list + --json) -> capture a real xtbout.json -> `eps validate --engine xtb` for the first real MAE (validates reference frame / benchmark / anodic limits simultaneously).

## Architecture invariants
See AGENTS.md (per-species not per-triad; mock-first; data in CSV, thresholds in YAML; SQLite cache; single pinned redox function). Do not restate them here to avoid drift.

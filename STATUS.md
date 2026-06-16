# Project Status
_Last updated: 2026-06-16_

## Current phase
Deep-research benchmark nucleus installed; medium/tier/LOO-aware validation.

## What works and is verified
- Per-species architecture, SQLite caching (idempotent), Engine abstraction, mock-first.
- redox -> V vs Ag/AgCl conversion: single tested function, constants pinned (ABS_SHE=4.28, AgAgCl shift=-0.197).
- Tier-1 funnel: per-species calc -> triad JOIN -> hard filters -> composite score + Pareto, end-to-end on MockEngine.
- Calibration + benchmark validation harness: medium/tier filters, duplicate collapse by (monomer, solvent), full-row reporting, leave-one-out CV headline metric, within-group spread noise floor, and integrity guards for SMILES, library SMILES matches, and native+conversion consistency.
- Benchmark CSV provenance schema is complete. Current nucleus = 11 rows from 4 source families: 2 Tier A aqueous EDOT, 8 Tier B nonaqueous rows, 1 Tier C downgraded 3-hexylthiophene. Default calibration set = nonaqueous Tier A/B -> 8 rows -> 5 collapsed points across 4 families.
- XTBEngine: wired, fixture-tested locally; physics correct (IP/EA charge/multiplicity/sign, solvated adiabatic redox via --alpb <name>, xtbout.json parsing).
- SCS cluster validation: Grid Engine (`qsub`/`qstat`) confirmed; `xtb/6.4.1` confirmed; `--alpb`, `--gbsa`, and `--json` confirmed; real thiophene xTB run produced `xtbout.json` with expected fields.
- Cluster CombHTS runs: `eps run-tier1 --engine mock` completed; earlier `eps validate --engine xtb` completed on the old 12-row benchmark, but that result is superseded by the new validation definition.

## Placeholders / not yet validated (do not treat as real)
- optical_gap = HOMO-LUMO gap on an MMFF geometry (not an optical gap, not an oligomer).
- dimerization_dG = rescaled gas energy (fake signal).
- Solvent anodic limits are seed approximations, not literature-verified.
- Real cluster `eps validate --engine xtb` LOO-CV MAE has not yet been rerun on the new nucleus.

## Open debts (priority order)
1. (P0 science) Run and record real cluster `eps validate --engine xtb` with the new medium/tier/LOO-aware validation harness; do not compare new LOO-CV numbers to the superseded in-sample result.
2. (P0 science) Expand benchmark to >=30 rows across missing families: pyrrole, aniline, furan, ProDOT, EDOP, fluorene, CPDT, bithiophene, terthiophene, and D-A thiophene-benzothiadiazole units.
3. Verify the Pavlishchuk-Addison conversion DOI and all per-row source DOIs; keep row-level caveats until every source is rechecked.
4. Evaluate migrating the nonaqueous master scale to Fc/Fc+ rather than aqueous Ag/AgCl.
5. Replace solvent anodic limits with measured values vs the chosen reference scale; current values are stopgap = cathodic + spec ESW width.
6. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
7. Get professor sign-off on the 4 ALPB proxy solvents (PC->dmso, GBL->acetonitrile, sulfolane->dmso, NMP->dmf), or move to ddCOSMO with manual epsilon.
8. In XTBEngine._run_xtb, check subprocess returncode BEFORE parsing xtbout.json.
9. Write queue-safe SGE job scripts for `eps validate --engine xtb` and `eps run-tier1 --engine xtb`; avoid running production calculations in interactive sessions.
10. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
11. Not yet built: Tier-2 DFT adapter, analysis/plots, expand libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
Run `pytest -q`, then run `eps validate --engine mock` to inspect the new report columns and CLI output before scheduling real xTB validation on the cluster.

## Architecture invariants
See AGENTS.md (per-species not per-triad; mock-first; data in CSV, thresholds in YAML; SQLite cache; single pinned redox function). Do not restate them here to avoid drift.

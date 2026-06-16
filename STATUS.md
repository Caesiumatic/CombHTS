# Project Status
_Last updated: 2026-06-16_

## Current phase
Tier-1 smoke auditability and per-property failure capture complete under MockEngine; rerun xTB smoke to audit the selenium geometry failure without aborting the screen.

## What works and is verified
- Per-species architecture, SQLite caching (idempotent), Engine abstraction, mock-first.
- redox -> V vs Ag/AgCl conversion: single tested function, constants pinned (ABS_SHE=4.28, AgAgCl shift=-0.197).
- Benchmark validation harness: medium/tier filters, duplicate collapse by (monomer, solvent), full-row reporting, leave-one-out CV headline metric, within-group spread noise floor, and integrity guards for SMILES, library SMILES matches, and native+conversion consistency.
- Latest cluster xTB validation completed on the current nucleus: calibration y = 0.623*x - 2.872, LOO-CV MAE after calibration = 0.079 V, Tier-1 gate PASS (PROVISIONAL).
- Tier-1 workflow now preserves raw monomer xTB Eox, computes provisional calibrated monomer Eox from `configs/tier1.yaml`, exposes the exact filter Eox, and keeps `monomer_Eox_V` only as a backward-compatible alias.
- Tier-1 now writes a survivor ranked CSV plus an all-triads audit CSV with hard-filter booleans and semicolon-separated failure reasons.
- Tier-1 now records per-property calculation failures (`*_calc_status`, `*_calc_error`) as NaN-valued audit rows instead of aborting the full screen; failed required calculations are excluded from ranked survivors.
- Mock Tier-1 CLI verified after the refactor: 1650 total triads, 1540 survivors, audit CSV written with all 1650 rows.
- XTBEngine: wired, fixture-tested locally; physics correct (IP/EA charge/multiplicity/sign, solvated adiabatic redox via --alpb <name>, xtbout.json parsing).
- SCS cluster environment previously confirmed: Grid Engine (`qsub`/`qstat`), `xtb/6.4.1`, `--alpb`, `--gbsa`, and `--json`.

## Placeholders / not yet validated (do not treat as real)
- optical_gap = HOMO-LUMO gap on an MMFF geometry (not an optical gap, not an oligomer).
- dimerization_dG = rescaled gas energy (fake signal).
- Solvent anodic limits are seed approximations, not literature-verified.
- Monomer Eox calibration in Tier-1 is provisional and monomer-only; anion_Eox_V is not calibrated.
- Latest xTB Tier-1 smoke reached real xTB on a compute node but aborted on a selenium geometry optimization failure before this failure-capture patch; rerun it to produce `outputs/tier1_xtb_smoke_all.csv`.

## Open debts (priority order)
1. (P0 science) Rerun the same SGE `eps run-tier1 --engine xtb` smoke with the new failure-capture audit output; confirm `outputs/tier1_xtb_smoke_all.csv` has 8 rows and selenium failures are explicit.
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
On the cluster, rerun the xTB Tier-1 smoke job with `--output outputs/tier1_xtb_smoke_ranked.csv`; verify the inferred audit file `outputs/tier1_xtb_smoke_all.csv`.

## Architecture invariants
See AGENTS.md (per-species not per-triad; mock-first; data in CSV, thresholds in YAML; SQLite cache; single pinned redox function). Do not restate them here to avoid drift.

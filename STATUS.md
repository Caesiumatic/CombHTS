# Project Status
_Last updated: 2026-06-16_

## Current phase
Tier-1 xTB smoke auditability and per-property failure capture verified on Lop with real xTB.

## What works and is verified
- Per-species architecture, SQLite caching (idempotent), Engine abstraction, mock-first.
- redox -> V vs Ag/AgCl conversion: single tested function, constants pinned (ABS_SHE=4.28, AgAgCl shift=-0.197).
- Benchmark validation harness: medium/tier filters, duplicate collapse by (monomer, solvent), full-row reporting, leave-one-out CV headline metric, within-group spread noise floor, and integrity guards for SMILES, library SMILES matches, and native+conversion consistency.
- Latest cluster xTB validation completed on the current nucleus: calibration y = 0.623*x - 2.872, LOO-CV MAE after calibration = 0.079 V, Tier-1 gate PASS (PROVISIONAL).
- Tier-1 workflow preserves raw monomer xTB Eox, computes provisional calibrated monomer Eox from `configs/tier1.yaml`, exposes the exact filter Eox, and keeps `monomer_Eox_V` only as a backward-compatible alias.
- Tier-1 writes a survivor ranked CSV plus an all-triads audit CSV with hard-filter booleans, per-property `*_calc_status` / `*_calc_error`, and semicolon-separated failure reasons.
- xTB Tier-1 smoke completed on Lop through Grid Engine/qsub using real xTB.
- `outputs/tier1_xtb_smoke_all.csv`: 1650 attempted triads.
- `outputs/tier1_xtb_smoke_ranked.csv`: 1273 ranked survivors; survival fraction = 0.7715151515.
- 152 calculation-failure rows were captured as audit rows instead of aborting.
- EDOS monomer_Eox and dimerization failures were captured across 110 triads.
- TBAPF6/PF6 anion_Eox failures were captured in propylene carbonate, DMSO, and sulfolane across 45 triads.
- Solvation failures = 0; optical_gap failures = 0.
- XTBEngine: wired, fixture-tested locally; physics correct (IP/EA charge/multiplicity/sign, solvated adiabatic redox via --alpb <name>, xtbout.json parsing).

## Scientific caution
- This is an engineering/pipeline milestone, not a final scientific ranking.
- Do not interpret ranked xTB smoke candidates as recommendations while optical_gap, dimerization_dG, solvent limits, and calibration remain provisional/placeholders.
- Keep label ontology strict: monomer oxidation potential, electropolymerization growth/onset potential, and polymer doping onset are different quantities and must not be mixed.

## Placeholders / not yet validated (do not treat as real)
- optical_gap = HOMO-LUMO gap on an MMFF geometry (not an optical gap, not an oligomer).
- dimerization_dG = rescaled gas energy (fake signal).
- Solvent anodic limits are seed approximations, not literature-verified.
- Monomer Eox calibration in Tier-1 is provisional and monomer-only.
- anion_Eox_V is not calibrated.

## Open debts (priority order)
1. (P0 science) Expand benchmark to >=30 clean experimental monomer oxidation potentials across missing families: pyrrole, aniline, furan, ProDOT, EDOP, fluorene, CPDT, bithiophene, terthiophene, and D-A thiophene-benzothiadiazole units.
2. Verify the Pavlishchuk-Addison conversion DOI and all per-row source DOIs; keep row-level caveats until every source is rechecked.
3. Evaluate migrating the nonaqueous master scale to Fc/Fc+ rather than aqueous Ag/AgCl.
4. Replace solvent anodic limits with measured values vs the chosen reference scale; current values are stopgap = cathodic + spec ESW width.
5. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
6. Get professor sign-off on the 4 ALPB proxy solvents (PC->dmso, GBL->acetonitrile, sulfolane->dmso, NMP->dmf), or move to ddCOSMO with manual epsilon.
7. In XTBEngine._run_xtb, check subprocess returncode BEFORE parsing xtbout.json.
8. Write queue-safe SGE job script templates for `eps validate --engine xtb` and `eps run-tier1 --engine xtb`; avoid running production calculations in interactive sessions.
9. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
10. Not yet built: Tier-2 DFT adapter, analysis/plots, expand libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
Curate and verify more clean experimental monomer oxidation benchmark rows; keep Tier-1 ranked smoke output as an audit artifact only.

## Architecture invariants
See AGENTS.md (per-species not per-triad; mock-first; data in CSV, thresholds in YAML; SQLite cache; single pinned redox function). Do not restate them here to avoid drift.

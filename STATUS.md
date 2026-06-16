# Project Status
_Last updated: 2026-06-16_

## Current phase
Strict benchmark v1 is integrated: 14 calibration-eligible raw rows, 14 collapsed calibration groups under `monomer_smiles + solvent_name + label_type`, and demoted/unresolved provenance separated into `data/benchmark_candidates.csv`.

Tier-1 xTB smoke auditability and per-property failure capture are verified on Lop with real xTB.

## What works and is verified
- Per-species architecture, SQLite caching, Engine abstraction, and mock-first tests.
- Redox -> V vs Ag/AgCl conversion is a single tested function with pinned constants.
- Benchmark validation now enforces explicit label ontology before calibration: `label_type`, `calibration_eligible`, exclusion reason, reported/converted references, conversion method, source reference/locator/confidence, and `medium_class`.
- Default calibration uses only eligible monomer oxidation labels from `data/benchmark.csv`; `data/benchmark_candidates.csv` is provenance-only.
- Strict benchmark v1 has 14 rows, 14 calibration-eligible rows, and 14 collapsed groups: 10 `monomer_oxidation_onset`, 4 `monomer_oxidation_peak`, all `nonaqueous`.
- Thiophene/acetonitrile peak-like and onset-like rows remain separate groups and are not averaged.
- xTB Tier-1 smoke completed on Lop through Grid Engine/qsub using real xTB.
- `outputs/tier1_xtb_smoke_all.csv`: 1650 attempted triads.
- `outputs/tier1_xtb_smoke_ranked.csv`: 1273 ranked survivors; survival fraction = 0.7715151515.
- 152 calculation-failure rows were captured as audit rows instead of aborting.
- EDOS monomer_Eox and dimerization failures were captured across 110 triads.
- TBAPF6/PF6 anion_Eox failures were captured in propylene carbonate, DMSO, and sulfolane across 45 triads.
- Solvation failures = 0; optical_gap failures = 0.

## Scientific caution
- This is an engineering/pipeline milestone, not a final scientific ranking.
- Strict benchmark v1 did not meet the professor's original >=30 clean-group target.
- Do not interpret ranked xTB smoke candidates as recommendations while optical_gap, dimerization_dG, solvent limits, and calibration remain provisional/placeholders.
- Keep label ontology strict: monomer oxidation potential, electropolymerization growth/onset potential, polymer doping onset, irreversible polymer-film redox, and ambiguous reference-electrode values must not be mixed.

## Placeholders / not yet validated
- optical_gap = HOMO-LUMO gap on an MMFF geometry, not an optical gap or oligomer result.
- dimerization_dG = rescaled gas energy and still a fake signal.
- Solvent anodic limits are provisional seed approximations.
- Monomer Eox calibration is provisional and tied to a small strict benchmark.
- anion_Eox_V is uncalibrated.

## Open debts
1. (P0 science) Expand benchmark to >=30 clean experimental monomer oxidation potential groups using `docs/benchmark_curation_protocol.md`; future promotion requires PI policy decision or source-level recovery.
2. Resolve or re-audit candidate/provenance rows in `data/benchmark_candidates.csv`, especially EDOT current rows, nonaqueous SCE/Ag/Ag+/pseudo-reference conversions, mixed solvents, and missing source locators.
3. Evaluate migrating the nonaqueous master scale to Fc/Fc+ rather than aqueous Ag/AgCl.
4. Replace solvent anodic limits with measured values vs the chosen reference scale.
5. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
6. Get professor sign-off on the 4 ALPB proxy solvents, or move to ddCOSMO with manual epsilon.
7. In `XTBEngine._run_xtb`, check subprocess return code before parsing `xtbout.json`.
8. Write queue-safe SGE job script templates for xTB validation/Tier-1 runs; avoid running production calculations in interactive sessions.
9. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
10. Not yet built: Tier-2 DFT adapter, analysis/plots, expanded libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
Curate and verify more clean experimental monomer oxidation benchmark groups toward >=30, without promoting incompatible label types or unresolved reference conversions.

## Architecture invariants
See AGENTS.md: compute per-species, not per-triad; mock-first; data in CSV and thresholds in YAML; SQLite cache; one pinned redox function.

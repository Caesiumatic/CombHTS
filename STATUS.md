# Project Status
_Last updated: 2026-06-17_

## Current phase
Strict benchmark v2 is integrated: 20 calibration-eligible raw rows and 20 collapsed groups under canonical SMILES + `solvent_name + label_type`. Calibration is profile-driven by `reference_frame`, `label_type`, tier, and medium.

Tier-1 xTB smoke auditability and per-property failure capture are verified on Lop with real xTB.

## What works and is verified
- Per-species architecture, SQLite caching, Engine abstraction, and mock-first tests.
- Redox -> V vs Ag/AgCl conversion is a single tested function with pinned constants.
- Benchmark validation enforces explicit label ontology before calibration: `label_type`, `calibration_eligible`, exclusion reason, reported/converted references, conversion method, source reference/locator/confidence, `medium_class`, and `reference_frame`.
- `configs/calibration_profiles.yaml` defines independent Ag/AgCl peak, Ag/AgCl onset, and placeholder Fc/Fc+ profiles. Profiles never pool different reference frames or co-fit peak and onset labels.
- `eps validate` runs the default screening profile; `eps validate --all-profiles` writes a profile comparison CSV and skips profiles with fewer than two collapsed points.
- Strict benchmark v2 has 20 rows, 20 calibration-eligible rows, and 20 collapsed groups: 10 `monomer_oxidation_peak`, 10 `monomer_oxidation_onset`, all `nonaqueous`, all `reference_frame=agagcl`.
- `agagcl_peak_relaxed` and `agagcl_onset_relaxed` each have 10 points and are fit separately. The Fc/Fc+ profiles remain empty and skipped pending PI approval.
- `configs/tier1.yaml` monomer Eox calibration is refit from `agagcl_peak_relaxed`: slope 0.051941, intercept 1.345652, LOO-CV MAE 0.466255 V.
- OSeO and FSeF share the same canonical SMILES but remain distinct calibration groups because their solvents differ.
- xTB Tier-1 smoke completed on Lop through Grid Engine/qsub using real xTB: 1650 attempted triads, 1273 ranked survivors, and 152 calculation-failure audit rows captured instead of aborting.

## Scientific caution
- This is an engineering/pipeline milestone, not a final scientific ranking.
- Strict benchmark v2 still does not meet the professor's original >=30 clean-group target.
- The default screening profile remains provisional and needs PI sign-off on peak vs onset anchoring.
- Do not interpret ranked xTB smoke candidates as recommendations while optical_gap, dimerization_dG, solvent limits, and calibration remain provisional/placeholders.
- Keep label ontology strict: monomer oxidation potential, electropolymerization growth/onset potential, polymer doping onset, irreversible polymer-film redox, and ambiguous reference-electrode values must not be mixed.

## Placeholders / not yet validated
- optical_gap = HOMO-LUMO gap on an MMFF geometry, not an optical gap or oligomer result.
- dimerization_dG = rescaled gas energy and still a fake signal.
- Solvent anodic limits are provisional seed approximations.
- Monomer Eox calibration is provisional and tied to a small strict benchmark.
- Fc/Fc+ profiles are empty placeholders until PI approval and clean native-Fc rows exist.
- anion_Eox_V is uncalibrated.

## Open debts
1. (P0 science) Expand benchmark to >=30 clean experimental monomer oxidation potential groups using `docs/benchmark_curation_protocol.md`; future promotion requires PI policy decision or source-level recovery.
2. Decide whether peak or onset should be the screening anchor; the current default is `agagcl_peak_relaxed`.
3. Decide whether to fund a separate Fc/Fc+ track; do not force-convert incompatible Ag/Ag+, SCE, or polymer-onset rows to fill it.
4. Resolve or re-audit candidate/provenance rows in `data/benchmark_candidates.csv`, especially EDOT current rows, nonaqueous SCE/Ag/Ag+/pseudo-reference conversions, mixed solvents, and missing source locators.
5. Replace solvent anodic limits with measured values vs the chosen reference scale.
6. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
7. Get professor sign-off on the 4 ALPB proxy solvents, or move to ddCOSMO with manual epsilon.
8. In `XTBEngine._run_xtb`, check subprocess return code before parsing `xtbout.json`.
9. Write queue-safe SGE job script templates for xTB validation/Tier-1 runs; avoid running production calculations in interactive sessions.
10. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
11. Not yet built: Tier-2 DFT adapter, analysis/plots, expanded libraries toward ~100x30x25, HPC orchestration.

## Immediate next action
Get PI sign-off on the default screening calibration profile and decide whether to launch the separate Fc/Fc+ retrieval track.

## Architecture invariants
See AGENTS.md: compute per-species, not per-triad; mock-first; data in CSV and thresholds/profiles in YAML; SQLite cache; one pinned redox function.

# Project Status
_Last updated: 2026-06-17_

## Current phase
Strict benchmark v3 is integrated: 32 calibration-eligible raw rows and 32 collapsed groups under canonical SMILES + `solvent_name + label_type`. Calibration is profile-driven by `reference_frame`, `label_type`, tier, and medium.

Tier-1 xTB smoke auditability and per-property failure capture are verified on Lop with real xTB.

## What works and is verified
- Per-species architecture, SQLite caching, Engine abstraction, and mock-first tests.
- Redox -> V vs Ag/AgCl conversion is a single tested function with pinned constants.
- Benchmark validation enforces explicit label ontology before calibration: `label_type`, `calibration_eligible`, exclusion reason, reported/converted references, conversion method, source reference/locator/confidence, `medium_class`, and `reference_frame`.
- `configs/calibration_profiles.yaml` defines independent Ag/AgCl peak, Ag/AgCl onset, and placeholder Fc/Fc+ profiles. Profiles never pool different reference frames or co-fit peak and onset labels.
- `eps validate` runs the default screening profile; `eps validate --all-profiles` writes a profile comparison CSV and skips profiles with fewer than two collapsed points.
- Strict benchmark v3 has 32 rows, 32 calibration-eligible rows, and 32 collapsed groups: 19 `monomer_oxidation_peak`, 13 `monomer_oxidation_onset`, all `nonaqueous`, all `reference_frame=agagcl`.
- Profile point counts: `agagcl_peak_relaxed` = 19, `agagcl_onset_relaxed` = 13, `agagcl_peak_strict` = 9. The Fc/Fc+ profiles remain empty and skipped pending PI approval.
- New v3 sources: Cakal/Cihaner/Onal 2020 (10.1016/j.jelechem.2020.114000) FTPF/TTPT/STPS peak+onset rows in DCM; Oguzturk/Tirkes/Onal 2015 (10.1016/j.jelechem.2015.04.041) carbazole M1-M4 peak rows in MeCN from the journal, resolving the former M3 thesis conflict with published value 0.98 V; Algi et al. 2017 (10.1007/s10895-016-1978-x) pyridazinedione compounds 5/6 peak rows in MeCN.
- Asil/Cihaner/Onal 2009 TTT-Lum remains excluded in `data/benchmark_candidates.csv` because it was measured in 0.1 M LiClO4/MeCN + 5% BF3-Et2O, a Lewis-acid-modified medium rather than clean acetonitrile.
- `configs/tier1.yaml` monomer Eox calibration now comes from a real GFN2-xTB `eps validate --all-profiles` run on strict benchmark v3, using `agagcl_peak_strict`: slope 0.725837, intercept -3.145372, R^2 0.889, LOO-CV MAE 0.197 V.
- SeSeSe (DCM) hit a GFN2-xTB SCF non-convergence and was dropped from the `agagcl_peak_relaxed` fit; it is tier B and does not affect the chosen tier-A strict anchor.
- OSeO and FSeF share the same canonical SMILES but remain distinct calibration groups because their solvents differ.
- xTB Tier-1 smoke completed on Lop through Grid Engine/qsub using real xTB: 1650 attempted triads, 1273 ranked survivors, and 152 calculation-failure audit rows captured instead of aborting.

## Scientific caution
- This is an engineering/pipeline milestone, not a final scientific ranking.
- Strict benchmark v3 meets the professor's original >=30 clean-group target under strict native-Ag/AgCl rules.
- The default screening profile remains provisional and needs PI sign-off on peak vs onset anchoring.
- Do not interpret ranked xTB smoke candidates as recommendations while optical_gap, dimerization_dG, solvent limits, and calibration remain provisional/placeholders.
- Keep label ontology strict: monomer oxidation potential, electropolymerization growth/onset potential, polymer doping onset, irreversible polymer-film redox, and ambiguous reference-electrode values must not be mixed.

## Placeholders / not yet validated
- optical_gap = HOMO-LUMO gap on an MMFF geometry, not an optical gap or oligomer result.
- dimerization_dG = rescaled gas energy and still a fake signal.
- Solvent anodic/cathodic limits are COMPUTED per spec §3.2 (adiabatic ΔSCF oxidation/reduction of the solvent molecule in implicit self-solvent, projected to V vs Ag/AgCl through the pinned redox function). The ANODIC limit is now on the shared oxidation calibration (T11 decided), so it sits on the same calibrated scale as monomer Eox; absolute calibrated values are screening-grade extrapolations (fit on monomer data) pending a solvent benchmark. The CATHODIC limit (via EA) stays raw/informational and is NOT used in any Tier-1 filter. The stopgap CSV `esw_*_V` values are retained as an explicit per-solvent fallback when the calc fails (CSV values are never calibrated).
- Monomer Eox calibration in `configs/tier1.yaml` is refit from real xTB on strict v3 (`agagcl_peak_strict`); it is still provisional and screening-grade. This single oxidation calibration is now shared by monomer Eox, solvent anodic limit, and anion Eox (T11).
- Fc/Fc+ profiles are empty placeholders until PI approval and clean native-Fc rows exist.
- Anion Eox is now on the shared oxidation calibration (T11), so the anion-stability filter is LIVE; absolute calibrated anion values are screening-grade extrapolations pending an anion benchmark.
- The window and anion-stability filters are now LIVE on one calibrated oxidation scale; previously they were effectively no-ops because the anion (and solvent) limits were raw while monomer Eox was calibrated (a raw-vs-calibrated scale mismatch).

## Open debts
1. (P0 science, MET) The >=30 clean experimental monomer oxidation group target is met by strict benchmark v3; future promotion still requires PI policy decision or source-level recovery.
2. DONE: `configs/tier1.yaml` now uses a real GFN2-xTB `eps validate --all-profiles` run on strict benchmark v3, profile `agagcl_peak_strict`.
3. Decide whether peak or onset should be the screening anchor; the current recommendation is `agagcl_peak_strict` pending PI sign-off.
4. Decide whether to fund a separate Fc/Fc+ track; do not force-convert incompatible Ag/Ag+, SCE, or polymer-onset rows to fill it.
5. Resolve or re-audit candidate/provenance rows in `data/benchmark_candidates.csv`, especially EDOT current rows, nonaqueous SCE/Ag/Ag+/pseudo-reference conversions, mixed solvents, Lewis-acid-modified media, and missing source locators.
6. Solvent anodic/cathodic limits are computed per spec §3.2 (adiabatic ΔSCF on the solvent molecule), with CSV as fallback; the anodic limit and anion Eox now share the monomer oxidation calibration (THINK T11 decided). Remaining future work is to validate the calibrated solvent/anion values against a measured solvent/anion benchmark (the calibration is currently a monomer-fit extrapolation).
7. Replace the hand-written xtbout.json fixture with a captured real cluster `xtbout.json`; keep checking full ALPB solvent availability for the proxy list.
8. Get professor sign-off on the 4 ALPB proxy solvents, or move to ddCOSMO with manual epsilon.
9. In `XTBEngine._run_xtb`, check subprocess return code before parsing `xtbout.json`.
10. Write queue-safe SGE job script templates for xTB validation/Tier-1 runs; avoid running production calculations in interactive sessions.
11. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
12. Not yet built: Tier-2 DFT adapter, analysis/plots, expanded libraries toward ~100x30x25, HPC orchestration.
13. Reconcile the calibration-anchor mismatch between `configs/tier1.yaml` (`agagcl_peak_strict`) and `configs/calibration_profiles.yaml` default screening profile (`agagcl_peak_relaxed`).

## Immediate next action
Get PI sign-off on using `agagcl_peak_strict` as the screening calibration anchor.

## Architecture invariants
See AGENTS.md: compute per-species, not per-triad; mock-first; data in CSV and thresholds/profiles in YAML; SQLite cache; one pinned redox function.

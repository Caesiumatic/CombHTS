# Changelog

## 2026-06-17
- Integrated strict benchmark v3: appended 12 verified native-Ag/AgCl monomer-oxidation
  rows to `data/benchmark.csv`, bringing the benchmark to 32 calibration-eligible rows
  and 32 collapsed groups.
- Recorded the v3 label/profile split: 19 `monomer_oxidation_peak`, 13
  `monomer_oxidation_onset`, `agagcl_peak_relaxed=19`, `agagcl_onset_relaxed=13`,
  `agagcl_peak_strict=9`, and empty/skipped Fc/Fc+ profiles.
- Added Cakal/Cihaner/Onal 2020 FTPF/TTPT/STPS DCM peak+onset rows, Oguzturk/Tirkes/Onal
  2015 journal carbazole M1-M4 MeCN peak rows with the M3 value resolved to 0.98 V, and
  Algi et al. 2017 pyridazinedione compounds 5/6 MeCN peak rows.
- Reconciled `data/benchmark_candidates.csv` from 21 to 19 rows by removing four promoted
  Oguzturk 2013 MSc-thesis carbazole candidates and adding two parked rows, including
  Asil/Cihaner/Onal 2009 TTT-Lum excluded for Lewis-acid-modified MeCN + 5% BF3-Et2O.
- Left `configs/tier1.yaml` unchanged and documented that its mock-derived calibration is
  stale relative to strict benchmark v3 pending a real xTB `eps validate --engine xtb
  --all-profiles` refit.
- Updated validation tests and benchmark curation/status docs for strict benchmark v3 and
  the now-met >=30 clean-group target.
- Integrated six verified native-Ag/AgCl monomer-oxidation peak rows into
  `data/benchmark.csv`, moving the strict benchmark from 14 to 20 calibration-eligible
  collapsed groups while keeping `data/benchmark_candidates.csv` at 21 provenance rows.
- Preserved the source-level corrections from the curation report: FSeF is 1.06 V and FSF
  is 1.16 V, and the OSeO/SSeS/SeSeSe source is `J. Electroanal. Chem.` rather than
  `Organic Electronics`.
- Refit `configs/tier1.yaml` from `agagcl_peak_relaxed` with n_points=10:
  slope=0.051941, intercept=1.345652, LOO-CV MAE=0.466255 V.
- Added a regression test showing OSeO and FSeF share canonical SMILES but remain distinct
  calibration groups because their solvents differ.
- Updated `STATUS.md` and the benchmark curation protocol for strict benchmark v2.
- Added profile-driven benchmark calibration with `configs/calibration_profiles.yaml`.
  Profiles now fit independently by `reference_frame`, `label_type`, tier, and medium,
  preventing Ag/AgCl vs Fc/Fc+ pooling and peak/onset co-fitting.
- Added `reference_frame` as the final `data/benchmark.csv` column and set all 14 strict-v1
  rows to `agagcl`; loaders default missing or blank values to `agagcl` for backward
  compatibility.
- Extended validation with optional `label_types` and `reference_frames` filters,
  `run_calibration_profile()`, and `run_all_calibration_profiles()`; empty Fc profiles are
  reported as `skipped_insufficient_points` instead of raising.
- Changed `eps validate` to run the default screening profile by default and added
  `--profile` / `--all-profiles` CLI modes with a profile comparison CSV.
- Added regression tests for reference-frame defaulting, disjoint peak/onset profile group
  sets, profile fit separation, and all-profile skip/report behavior.
- Documented calibration profiles in the benchmark curation protocol and updated
  `STATUS.md` for the profile-driven calibration phase.

## 2026-06-16
- Archived the final benchmark curation report at
  `docs/literature/deep_research_benchmark_finalization_20260616.md` and linked it from
  the status/protocol docs as the provenance basis for strict benchmark v1.
- Changed strict benchmark duplicate group IDs from raw `monomer_smiles + solvent_name +
  label_type` to canonical SMILES + `solvent_name + label_type`, with a regression test
  showing equivalent SMILES collapse into one calibration group.
- Tightened the benchmark protocol's SCE example to require source-internal,
  source-calibrated, or explicitly PI-approved nonaqueous SCE -> Ag/AgCl conversions.
- Implemented strict benchmark v1 from the final curation report: replaced
  `data/benchmark.csv` with 14 benchmark-ready calibration rows and added
  `data/benchmark_candidates.csv` with 21 demoted/excluded/unresolved provenance rows.
- Changed benchmark duplicate collapse to group by canonical SMILES + `solvent_name +
  label_type`, keeping thiophene/acetonitrile peak-like and onset-like labels separate.
- Relaxed source metadata validation so `source_doi` may be blank only when
  `source_doi_or_ref` and `source_locator` are populated; calibration still requires
  explicit reference-conversion metadata.
- Added validation reporting fields for raw rows, calibration-eligible rows, collapsed
  groups, label-type counts, medium-class counts, and a warning when strict groups are
  below the >=30 target.
- Added tests for the 14-row strict benchmark, identity Ag/AgCl conversions, source DOI
  fallback, label-aware grouping, thiophene peak/onset separation, and provenance-file
  exclusion from default calibration.
- Documented "Strict benchmark v1 status" in `docs/benchmark_curation_protocol.md`,
  including the 14-group current state, the unmet >=30 target, candidate-file policy,
  and the rule that onset and peak labels must not be averaged.
- Added explicit benchmark label ontology columns to `data/benchmark.csv` so monomer
  oxidation labels, electropolymerization setpoints, polymer-film labels, and unknown/mixed
  rows cannot be silently blended.
- Strengthened benchmark validation: calibration now requires `calibration_eligible=true`,
  a monomer oxidation `label_type`, converted potential values, and reference-conversion
  metadata; excluded rows remain in reports with `calibration_exclusion_reason`.
- Added `docs/benchmark_curation_protocol.md` with rules and examples for clean monomer
  oxidation benchmarks, reference-electrode conversion metadata, low-confidence rows, and
  unacceptable calibration labels.
- Added validation tests for growth-setpoint exclusion, required exclusion reasons,
  source DOI/locator confidence rules, and eligible-only calibration point counts.
- Recorded the successful Lop/Grid Engine xTB Tier-1 smoke milestone: 1650 audit rows,
  1273 ranked survivors, 152 calculation-failure audit rows, EDOS monomer_Eox/dimerization
  failures across 110 triads, and PF6 anion_Eox failures across 45 triads.
- Removed the brittle wall-clock assertion from the Tier-1 smoke/cache test; functional
  cache and output assertions remain.
- Added `.gitignore` coverage for common scheduler logs, cluster job scripts, and
  `.last_*_jobid` files while keeping generated outputs ignored.
- Made Tier-1 robust to per-property xTB failures: monomer Eox, solvation, optical gap,
  dimerization, and anion Eox exceptions now produce NaN values plus `*_calc_status` and
  `*_calc_error` audit columns instead of aborting the whole screen.
- Tier-1 hard-filter annotation now marks calculation failures as non-survivors with
  `calculation_failed` plus specific reasons such as `monomer_eox_failed`,
  `solvation_failed`, or `anion_eox_failed`; ranked output excludes failed required
  properties while all-triads audit output remains complete.
- Made Tier-1 smoke auditable and calibration-explicit: raw monomer xTB Eox is preserved,
  provisional calibrated monomer Eox is loaded from `configs/tier1.yaml`, the exact filter
  Eox is exposed, and the old `monomer_Eox_V` column is now a backward-compatible alias.
- Added all-triads audit output for Tier-1 runs, including hard-filter booleans,
  `failed_filter_reasons`, raw/calibrated/filter Eox columns, and a zero-survivor CLI
  warning pointing to the audit CSV.
- Refactored Tier-1 hard filters to use `monomer_Eox_filter_V_vs_AgAgCl` for solvent-window
  and anion-stability margins; anion oxidation remains explicitly uncalibrated pending a
  separate benchmark.
- Added Tier-1 audit tests for calibration math, margin source, failure reasons, zero-survivor
  audit behavior, and the backward-compatible `monomer_Eox_V` alias.
- Replaced the conservative seed re-curation with the provided deep-research benchmark
  nucleus verbatim, preserving the superseded CSV as
  `data/benchmark_superseded_codex_v1.csv`.
- Added medium/tier filtering, duplicate collapsing by (monomer, solvent), leave-one-out
  CV, within-group spread reporting, and integrity guards for SMILES parsing, library
  SMILES cross-checks, and native+conversion consistency.
- Changed the Tier-1 PASS/FAIL validation gate to use LOO-CV instead of in-sample MAE,
  while keeping the in-sample metrics for continuity.
- Dropped the EDOT/methanol row to avoid touching the solvent library and retained the
  VNUHCM 2023 3-hexylthiophene row only as Tier C because of source-condition concerns.
- Replaced the old approximate benchmark seed with a full provenance CSV schema for
  monomer oxidation potentials: native potential/reference, potential type, conversion
  constant/source, standardized V vs Ag/AgCl value, medium, conditions, DOI/citation,
  reliability tier, and row-level caveats. Current curated state is deliberately
  conservative: 13 traceable rows, 3 Tier B, 10 Tier C, and 0 Tier A.
- Added `docs/benchmark_methods_memo.md` documenting electrode conversion constants,
  the nonaqueous liquid-junction caveat, the recommendation to migrate nonaqueous
  calibration to Fc/Fc+, the xTB thermodynamic-vs-onset/Epa mismatch, realistic MAE
  expectations, and deliberately excluded monomer families.
- Updated project status to make primary CV recovery, not more mock/xTB plumbing, the
  next benchmark-critical action.
- Recorded the first real cluster xTB validation milestone: SCS Lop/Grid Engine environment confirmed, `xtb/6.4.1` with `--json` and `--alpb <name>` verified on a compute node, `eps run-tier1 --engine mock` completed on the cluster, and `eps validate --engine xtb` completed with MAE 5.398 V before calibration and 0.145 V after in-sample calibration.
- Updated the living project status to make benchmark curation and queue-safe real xTB Tier-1 execution the next priorities.

## 2026-06-15
Back-filled on 2026-06-15 from session history; exact per-milestone dates not recorded.

- M7 — xTB solvent fix + robust JSON parsing: --alpb takes solvent NAMES (removed the invalid numeric-dielectric path); filled xtb_gbsa_name for all solvents incl. nitromethane + 4 nearest-dielectric ALPB proxies; switched energy/gap parsing to xtbout.json with last-match regex fallback; added xtbout.json fixture.
- M6 — Real GFN2-xTB engine: XTBEngine via subprocess (RDKit ETKDG->xyz, adiabatic IP/EA with q/multiplicity rule, solvated redox, GBSA/ALPB solvation), fixture-tested + skipif live test; added structures/geometry.py and xtb_gbsa_name column; CLI --engine {mock,xtb}.
- M5 — Corrected solvent anodic limits: previous derivation reused a stale column and corrupted 6 solvents; replaced with cathodic + spec ESW width (CombHTS table 2.2), all flagged TODO for measured values.
- M4 — Calibration + validation harness: benchmark.csv (seed CV Eox), linear xTB->reference calibration, validation runner reporting MAE before/after vs targets in validation.yaml; `eps validate`.
- M3 — Data/reference fixes: solvent ESW semantics corrected (anodic limit vs width), added potential_reference column + loader warning, water eps_r 80.1, rdkit-pypi -> rdkit.
- M2 — Tier-1 driver + SQLite cache + composite scoring + Pareto + end-to-end mock smoke test (`eps run-tier1`).
- M1 — Engine interface + deterministic MockEngine + pinned redox conversion.
- M0 — Project brief (AGENTS.md), repo scaffold, chemical-space data layer (monomers/solvents/electrolytes CSVs, pydantic models, RDKit-validating loaders).

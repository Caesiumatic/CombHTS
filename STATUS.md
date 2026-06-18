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
- The 152 real-xTB failures are now explained AND resolved (THINK T10 decided): 110 were EDOS-only `monomer_eox`/`dimerization` failures from RDKit force-field geometry corruption (MMFF/UFF cannot type Se, so UFF collapsed the geometry into a ~0.26 Å atom clash and xTB aborted geometry optimization) — fixed in `src/eps/structures/geometry.py` by skipping FF pre-optimization when no classical FF can type every atom and handing the clean ETKDG geometry (~1.0 Å min distance) to xTB. The remaining anion failures are gone: the harvest with `--iterations 500 --etemp 400` shows 0 `anion_eox` failures, so no ddCOSMO move is needed.
- First fully-clean real-xTB Tier-1 harvest completed on the SCS Lop cluster (GFN2-xTB, EDOS/Se geometry fix in place, cache rebuilt from scratch so every value reflects the fixed geometry path): 1650 triads (15 monomers × 11 solvents × 10 salts), ZERO calculation failures across all seven per-property stages (`monomer_Eox`, `solvation`, `optical_gap`, `dimerization`, `solvent_anodic_limit`, `solvent_cathodic_limit`, `anion_Eox`), and 1007 surviving triads. EDOS now computes (calibrated Eox ~1.47 V). This is the first complete, reproducible real-physics per-species descriptor harvest, produced with the shared oxidation calibration (T11). It is an engineering + real-physics milestone, not a final scientific ranking (see Scientific caution).
- Every primary CLI output (`run-tier1`/`validate`/`memo`/`analyze`) writes a
  `<output>.provenance.json` sidecar (timestamp, git commit+dirty, eps version, engine/method,
  config SHA-256, library sizes) — best-effort, never crashes the command. CI (`pytest`+`ruff`)
  runs on push/PR; `ruff check` is clean.
- The Tier-1 all-triads CSV now carries the scoring columns (composite_score/pareto_front/band_gap_deviation_eV/norm_*) joined from the ranked survivors by triad identity (survivors identical, non-survivors NaN/False), so `eps analyze` produces every §8 output (incl. Pareto + shortlist) from the single all-triads file.
- `eps analyze` (directive §8, read-only) turns a Tier-1 harvest CSV into `summary.csv` (total/surviving/retention overall + by monomer/solvent/salt_class + per-property failure counts), real-axis distribution PNGs, a Pareto PNG, a Morgan-fingerprint+descriptor chemical-space map (PCA→t-SNE, PCA(2) fallback for n<10), and a SCREENING-GRADE `shortlist.csv`. Any output touching `optical_gap`/`dimerization_dG`/`band_gap_deviation_eV`/`composite_score`/`pareto_front` is labeled screening-grade (real but uncalibrated/proton-referenced; not validated). Degrades gracefully if matplotlib/scikit-learn are absent or if the harvest lacks scoring columns (the all-triads audit currently does — point analyze at a scored CSV for the Pareto/shortlist). `matplotlib`+`scikit-learn` added as deps.
- Validation metrics extended (directive §7): `eps validate` now also reports Spearman ρ, residual std, the worst-5 predicted monomers, and MAE-by-chemical-family (RDKit substructure, no scipy); new `eps sanity` runs directional monomer-Eox checks within one solvent on the Tier-1 harvest; new `eps memo` writes `docs/validation_memo_<date>.md`. The two §7 metrics that cannot be computed yet (solvent ESW MAE → no solvent benchmark; yes/no feasibility >85% → no binary labels) are marked not-computable, never fabricated. Real numbers come from the cluster xTB run.

## Scientific caution
- This is an engineering/pipeline milestone, not a final scientific ranking.
- Strict benchmark v3 meets the professor's original >=30 clean-group target under strict native-Ag/AgCl rules.
- The default screening profile remains provisional and needs PI sign-off on peak vs onset anchoring.
- The composite ranking is now SCREENING-GRADE (all five axes real physics), NOT placeholder-contaminated and NOT validated. Remaining honesty caveats: `optical_gap` is the sTDA-xTB (or HOMO-LUMO proxy) oligomer gap, UNCALIBRATED vs TD-DFT (Step-2); `dimerization_dG`'s ABSOLUTE value is set up to a fixed proton constant (relative ordering is sound); the anion/solvent oxidation values are monomer-fit calibration extrapolations (T11); and several coupling regiochemistries are approximate (aniline N-para, the D-A simplification, and the dioxy monomers whose stored SMILES are 2,3- not 3,4-dioxy). A produced value is not a validated value.
- Keep label ontology strict: monomer oxidation potential, electropolymerization growth/onset potential, polymer doping onset, irreversible polymer-film redox, and ambiguous reference-electrode values must not be mixed.

## Placeholders / not yet validated
- optical_gap is now REAL (no longer a placeholder): the sTDA-xTB lowest singlet excitation of the assembled n=6 oligomer, or the oligomer GFN2-xTB HOMO-LUMO gap as a clearly-labeled proxy (`optical_gap_method = homo_lumo_hexamer_fallback`) when `stda` is absent. Screening-grade, UNCALIBRATED vs TD-DFT (Step-2 hook). Open items: confirm `stda` availability on Lop; calibrate vs a TD-DFT reference.
- dimerization_dG is now REAL (no longer a placeholder): the xTB radical-radical coupling ΔG (2 M+. -> [M-M]2+ + 2 H+) from the dimer dication and monomer radical cation. The proton free energy is one fixed convention that cancels across monomers, so the ABSOLUTE ΔG is screening-grade and the RELATIVE ordering the w4 score uses is sound. NOT used as a hard filter.
- Oligomer assembly uses RDKit α-coupling (documented substitution for `stk`, which is unavailable in the env). Coupling regiochemistry is in `data/polymerization.csv` (human-reviewable; `eps run-tier1` also writes `outputs/oligomer_buildingblocks.csv`). APPROXIMATE coupling flagged for aniline (N-para) and the benzothiadiazole-thiophene D-A; and DATA-CURATION item: the stored monomers.csv canonical SMILES for EDOT/ProDOT/EDOP/EDOS encode the 2,3-dioxy isomer (one α blocked), so those couple at the free α + an adjacent C — out of scope to fix monomers.csv here.
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
7. ADDRESSED (fixture): `tests/fixtures/xtbout.json` is now schema-faithful (mirrors real `xtb --json` keys/nesting); still worth replacing with a captured real cluster dump when convenient, and keep checking full ALPB solvent availability for the proxy list.
8. Get professor sign-off on the 4 ALPB proxy solvents. (The ddCOSMO alternative is no longer needed on convergence grounds — T10 decided: 0 anion failures in the clean harvest — but PI sign-off on the ALPB proxies is still outstanding.)
9. DONE: `XTBEngine._run_xtb` now checks the subprocess return code and raises before parsing `xtbout.json`, so a garbage JSON cannot mask a real xTB failure (regression test added).
10. DONE (templates): version-controlled SGE templates live in `scripts/` (`run_tier1`, `run_validate`, `run_memo`, `run_analyze`) with a `#$ -S /bin/bash` first directive and the known-good module/conda/OMP preamble; see `scripts/README.md`. Submit via `qsub`, not interactively.
11. Upgrade placeholders: real oligomer assembly -> band gap; real dimer calculation.
12. PARTIAL: analysis/plots now exist (`eps analyze`, directive §8) and the Tier-2 DFT adapter is scaffolded build-only (`GaussianEngine`, B3LYP/6-31G(d,p), fixture-tested, never run; optional `eps tier2 --dry-run` writes .gjf inputs). Still not built: actually running Tier-2 at scale (PI/T8 decision), expanded libraries toward ~100x30x25, HPC orchestration.
13. Reconcile the calibration-anchor mismatch between `configs/tier1.yaml` (`agagcl_peak_strict`) and `configs/calibration_profiles.yaml` default screening profile (`agagcl_peak_relaxed`).

## Immediate next action
Get PI sign-off on using `agagcl_peak_strict` as the screening calibration anchor.

## Architecture invariants
See AGENTS.md: compute per-species, not per-triad; mock-first; data in CSV and thresholds/profiles in YAML; SQLite cache; one pinned redox function.

# Project Status
_Last updated: 2026-06-23 (Directive section-7 validation package completed; SGE 417671)_

## Current phase

Directive section-7 validation is now a reproducible, machine-readable workflow. The command
`eps validate-directive --engine xtb --harvest <salt-fixed-tier1-all.csv> --cache <sqlite>
--outdir <dir>` gathers the existing calculators into one package without changing scoring
weights, thresholds, calibration coefficients, redox constants, production CSVs, or the optical
policy. Mock mode remains a deterministic, explicitly NON-PHYSICAL smoke path.

The authoritative real run is SGE **417671** on Lop, executed from the isolated clone
`/home/shic4/CombHTS_section7_e023a1c` at git commit
`e023a1c6bba0b60f22a6afb3a649f45308234122`. It used real `gfn2-xtb+conf-mmff94-n100`, read the
salt-role-fixed harvest at `/home/shic4/CombHTS/outputs/tier1_real_7488_salt_fixed/tier1_all.csv`,
and wrote the validation package under
`/home/shic4/CombHTS_section7_e023a1c/outputs/directive_section7_validation/`. `qacct` reports
exit 0, failed 0, `intel24@compute-3-16.local`, 4 slots, and 398 s wall time.

Headline section-7 status:

- Tier-1 monomer Eox active production profile `agagcl_peak_strict`: LOO-CV MAE **0.186 V** over
  **9** collapsed groups, PASS versus the directive `<0.30 V` gate. This is above the hard
  0.15 V reference/measurement floor; do not claim tighter accuracy.
- Other configured Ag/AgCl profiles are reported for comparison: `agagcl_peak_relaxed`
  LOO-CV MAE **0.169 V** over 23 groups, and `agagcl_onset_relaxed` LOO-CV MAE **0.087 V** over
  16 onset groups. The onset value is not promoted as sub-reference-floor accuracy. Fc profiles
  skipped because no clean native-Fc calibration rows exist.
- Eox applicability domain for the active profile spans raw acetonitrile descriptors
  **5.694-7.412 V**. The 36-monomer library has **3/36** out-of-domain monomers (8.3%):
  two halothiophenes and one heteroaromatic.
- Raw solvent molecular DeltaSCF descriptor accuracy fails the practical ESW target:
  anodic MAE **5.409 V** and cathodic MAE **3.755 V** over 6 matched solvent benchmark rows.
  This confirms the isolated-solvent descriptor is not a universal electrochemical stability
  window calibration.
- Production ESW gate safety passes the correctness invariant: **0 unsafe widenings** across
  **5,760** comparable measured rows. Exact formulation coverage is **252/7,488** (3.37%),
  solvent-only measured coverage **5,508/7,488** (73.56%), and computed/CSV fallback coverage
  **1,728/7,488** (23.08%). Mean conservatism is **0.354 V**, max conservatism **2.508 V**.
- Qualitative electropolymerization feasibility remains **NOT_YET_TESTABLE**. The current labels
  are 34 total (18 YES / 16 NO), with 20 in scope and 12 matched to the salt-fixed harvest
  (6 exact-anion, 6 generic-electrolyte). Confusion matrix: TP=5, FN=3, TN=2, FP=2; balanced
  accuracy **56.25%** with stratified bootstrap 95% interval **25.0-87.5%**. Do not claim the
  directive `>85%` target from this small matched set.

No PI escalation was triggered. The work stayed inside Directive_CombHTS, used normal project-scale
CPU resources, did not change scoring/config policy, and did not create a new scope commitment.

Soft-axis interpretation is unchanged. Optical job **417587** remains a completed diagnostic
negative/weak baseline: six neutral-dimer ORCA anchors finished, but sTDA/TDA fits to experimental
neutral-polymer gaps are weak (R2 about 0.15-0.17; LOO-CV MAE about 0.45 eV), so the 15% optical
axis remains diagnostic. Dimerization is ranking-safe only because its proton-reference offset is
one common additive constant that min-max normalization cancels. The former solubility axis remains
documented as solvation affinity (`dGsolv` proxy), not measured solubility.

The corrected real-harvest ranking state is unchanged: CSV-only SGE 417569 applied the salt-role
gate to the existing real-xTB harvest without rerunning xTB, changing capped-ESW survivors
2,938 -> 2,143 (795 dropped, zero gained), with retained scores unchanged. Read-only analysis
417571 produced 1,127 exact score classes and a distinct diagnostic top-30 of 19 PC / 6 MeCN /
3 nitromethane / 2 NMP.

## What works

- Architecture invariants remain intact: expensive work is per species, triad scoring is a cheap
  join/arithmetic layer, all engines go through the Engine interface, results are SQLite-cached by
  species/method/solvent, and library/configuration data remain CSV/YAML.
- `eps validate-directive` writes all required artifacts:
  `validation_summary.json`, `validation_report.md`, `eox_profile_summary.csv`, `eox_points.csv`,
  `esw_descriptor_points.csv`, `esw_gate_diagnostics.csv`, `feasibility_matches.csv`, and
  `provenance.json`.
- `scripts/run_validate_directive.sge` is an xTB-only SGE template with an absolute scheduler log
  path and `COMBHTS_ROOT` override for isolated cluster clones/worktrees.
- The validation package records active-vs-configured Eox profiles, deterministic bootstrap
  intervals, worst residuals/influence diagnostics, library applicability-domain calls, raw ESW
  descriptor points, measured-first production-gate safety diagnostics, feasibility matches, and
  provenance/hashes.
- The measured-first conservative ESW gate is validated as one-way safe on the salt-fixed real
  harvest: measured literature can tighten the hard gate, not admit rows by widening a sparse
  generic window.
- Real Tier-1 job 417538, re-score 417569, analysis 417571, optical diagnostic 417587, and
  directive validation 417671 all have run manifests or manifest updates in version control.

## Open scientific and engineering debt

1. ESW descriptor physics is the largest validated failure. The raw isolated-solvent molecular
   DeltaSCF descriptors are off by multiple volts versus practical ESW measurements. They should
   remain audited priors/caps, not standalone solvent-window calibrations.
2. Exact ESW formulation coverage is sparse. The safety invariant passes, but exact `(solvent,salt)`
   coverage is only 3.37% of the salt-fixed harvest rows. PC/NMP/sulfolane and common supporting
   salts need condition-relevant curation before any experimental recommendation.
3. Feasibility labels are not yet enough for the directive `>85%` claim. Add condition-relevant
   negatives and exact-anion labels, especially in baseline nonaqueous media, until at least a
   defensible matched validation set exists.
4. Tier-2 held-out DFT validation remains out of scope for the section-7 package. The old 0.119 V
   DFT number is in-sample and must not be reported as a held-out Tier-2 pass.
5. The composite's diagnostic half remains data-limited: optical, dimerization absolute scale, and
   solvation-affinity/true-solubility calibration are reference-only until better anchors exist.
6. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, cation deposition, and condition-specific anion
   limits are not calibrated.
7. The library is still 36 x 13 x 16, not the requested roughly 80-150 x 25-35 x 20-30. The vetted
   expansion proposal remains gated on stable ESW, solvation/solubility, and optical evidence.

## Immediate next actions

1. Expand section-7 evidence coverage, not weights: add exact ESW formulation rows and
   condition-relevant feasibility labels, then rerun `eps validate-directive` on the same
   salt-fixed harvest.
2. Keep the section-7 package as the authoritative validation report for the current 7,488-triad
   screen. Use the JSON/CSVs in the Lop output directory for group-update tables.
3. Treat any next Tier-2 DFT validation or full library expansion as a separate resource-planning
   work unit.

## Verification

- Target branch: `feat/section7-validation-closure`, based on
  `origin/main` `e7e8c3967d9bf5fefb0e191722197ed0af136b41`.
- Local verification before first commit: targeted pytest `23 passed`; full pytest
  `224 passed, 5 skipped, 2 warnings`; `ruff check src tests` passed; `git diff --check` clean;
  mock `validate-directive` smoke wrote all required artifacts.
- Lop verification: SGE 417671 completed with exit 0 and wrote the real section-7 artifact package.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

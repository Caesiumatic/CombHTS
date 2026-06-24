# Project Status
_Last updated: 2026-06-24 (R11-R21 primary-PDF staging correction)_

## Current phase

Directive Section 7 validation is now a reproducible, machine-readable workflow. The command
`eps validate-directive --engine xtb --harvest <salt-fixed-tier1-all.csv> --cache <sqlite>
--outdir <dir>` gathers the existing calculators into one package without changing scoring
weights, thresholds, calibration coefficients, redox constants, production CSVs, or the optical
policy. Mock mode remains a deterministic, explicitly NON-PHYSICAL smoke path.

The authoritative real validation run is SGE **417671** on Lop, executed from isolated clone
`/home/shic4/CombHTS_section7_e023a1c` at git commit
`e023a1c6bba0b60f22a6afb3a649f45308234122`. It used real `gfn2-xtb+conf-mmff94-n100`, read the
salt-role-fixed harvest at `/home/shic4/CombHTS/outputs/tier1_real_7488_salt_fixed/tier1_all.csv`,
and wrote the validation package under
`/home/shic4/CombHTS_section7_e023a1c/outputs/directive_section7_validation/`. `qacct` reports
exit 0, failed 0, `intel24@compute-3-16.local`, 4 slots, and 398 s wall time.

Headline Section 7 status:

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

Section 7 staging-data audit and targeted gap curation is **COMPLETE** at review/staging scope.
The new audit artifacts under `data/lit_curation/` and
`docs/research/section7_staging_audit_20260623.md` cover existing solvent ESW, polymerization,
optical-anchor, solubility, and optical/doping staging rows. All audited staging schemas pass and
all 127 SMILES-bearing staging rows RDKit-parse; no production CSV, config, scoring code, or optical
policy changed. The audit produced compact review tables for Eox gapfill candidates, ESW promotion
candidates, ESW remaining gaps, polymerizability promotion candidates, and Wave-A library readiness.
The top blockers before production ingest are exact PC/MeCN-TBAPF6 ESW evidence, nitromethane
primary-source reconciliation, NMP/nitrobenzene ESW coverage, and a small set of Eox/polymerization
rows needing source or reference checks.

The R11-R21 Eox rescue package remains **review-only staging**, not production ingest. A primary-PDF
correction memo now records six thiophene attachment fixes (R12, R13, R14, R15, R16, R21) plus
source-internal reference/condition conflicts in the R14-R21 papers. The normalized source
transcription lives at `data/lit_curation/eox_r11_r21_source_candidates.csv`, the generated review
table at `data/lit_curation/eox_r11_r21_rescue_review.csv`, the regenerated report at
`docs/research/eox_r11_r21_staging_rescue_20260624.md`, and the correction memo at
`docs/research/eox_r11_r21_primary_pdf_correction_20260624.md`. All 11 rows RDKit-parse, all
working Ag-wire/SCE-to-Ag/AgCl transcriptions numerically reproduce, R14-R17 formulae match RDKit
formulae, and no row duplicates the production benchmark. Only R11-R13 remain
`PROMOTE_NOW_CANDIDATE`; R14-R21 are fail-closed as `NEEDS_REFERENCE_CHECK` because 8 rows carry
reference-source conflicts and R18-R21 also carry condition-source conflicts. The projected
onset-only union is now 19 groups, peak remains 23, and the combined experimental-combination
inventory is 42 only when onset and peak are counted together; this does **not** close the
Directive `>=30` benchmark question by raw row count.

The Tier-2 monomer-Eox pilot workflow is implemented as a **mock-first, array-safe scaffold**.
`eps tier2-plan` validates a selection CSV and emits one task per unique `(monomer, solvent,
method config)` identity; repeated salts/cations are deduplicated before any Engine call.
`eps tier2-run-task` executes one manifest task with a task-local SQLite cache, atomic
`result.json`, persistent Gaussian input/log retention, Normal-termination checks, SCF/Gibbs energy
selection metadata, and frequency-quality metadata. `eps tier2-harvest` is a no-engine combiner
that rejects missing/failed/duplicate/hash-mismatched results and never fills Tier-2 gaps with
Tier-1 values. SGE templates exist for the array run and the separate harvest step. No real
Gaussian task was submitted in this work unit, and no scoring/config/production CSV value changed.

No PI escalation was triggered by these merged work units. They stayed inside Directive_CombHTS,
used normal project-scale resources, did not change scoring/config policy, and did not create a new
scope commitment.

A post-integration codebase map and safe-hygiene review now document package layout, workflow
ownership, data/config boundaries, engine/cache contracts, scientific axes, and no-touch items in
`docs/code_structure.md` and `docs/maintenance/codebase_review_20260623.md`. This review is
documentation-only and does not change scoring, filters, calibration, production data, redox
constants, cache keys, output schemas, or optical policy.

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
- `docs/code_structure.md` is the current maintainer map for source/package layout, public
  workflows, data/config ownership, scientific axes, run-manifest practice, onboarding, and
  no-touch boundaries.
- `eps validate-directive` writes all required artifacts:
  `validation_summary.json`, `validation_report.md`, `eox_profile_summary.csv`, `eox_points.csv`,
  `esw_descriptor_points.csv`, `esw_gate_diagnostics.csv`, `feasibility_matches.csv`, and
  `provenance.json`.
- `scripts/run_validate_directive.sge` is an xTB-only SGE template with an absolute scheduler log
  path and `COMBHTS_ROOT` override for isolated cluster clones/worktrees.
- The Section 7 staging audit validates staging schemas, RDKit-parses known SMILES fields,
  canonicalizes structures, detects internal and production duplicates, and writes review tables
  without touching production data.
- The R11-R21 Eox rescue workflow loads only the manually normalized source-candidate CSV, audits
  structures/conversions/source conflicts/duplicates, refuses production CSV outputs, and writes
  deterministic review-only artifacts. Source-conflicted rows cannot be
  `PROMOTE_NOW_CANDIDATE`.
- Tier-2 pilot orchestration is split into plan / one-task run / harvest commands. Planning is
  schema-validated and monomer-solvent aware; task execution is mock-first and cache-separated by
  default; harvest preserves raw energy fields and emits a standard per-monomer-solvent Eox CSV
  consumable by `eps tier2-screen`.
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
   coverage is only 3.37% of the salt-fixed harvest rows. The staging audit now pinpoints priority
   review targets: exact PC BF4/PF6/ClO4/TFSI rows, MeCN/TBAPF6, nitromethane primary-source
   reconciliation, NMP, and nitrobenzene.
3. Feasibility labels are not yet enough for the directive `>85%` claim. Add condition-relevant
   negatives and exact-anion labels, especially in baseline nonaqueous media, until at least a
   defensible matched validation set exists.
4. Tier-2 held-out DFT validation remains out of scope for the Section 7 package. The old 0.119 V
   DFT number is in-sample and must not be reported as a held-out Tier-2 pass. The pilot
   orchestration is ready, but no real Gaussian array has been submitted and no completed Tier-2
   scientific values exist yet.
5. The composite's diagnostic half remains data-limited: optical, dimerization absolute scale, and
   solvation-affinity/true-solubility calibration are reference-only until better anchors exist.
6. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, cation deposition, and condition-specific anion
   limits are not calibrated.
7. The library is still 36 x 13 x 16, not the requested roughly 80-150 x 25-35 x 20-30. The vetted
   expansion proposal remains gated on stable ESW, solvation/solubility, and optical evidence.

## Immediate next actions

1. Review the Section 7 staging-audit outputs, source-check the flagged Eox/ESW/polymerization rows,
   and promote only approved rows through a separate production-ingest task.
2. For R11-R21, source-check only R11-R13 as still-promotable review candidates. Resolve or exclude
   the R14-R21 source-internal reference/condition conflicts before any separate benchmark-promotion
   task.
3. Expand Section 7 evidence coverage, not weights: add exact ESW formulation rows and
   condition-relevant feasibility labels, then rerun `eps validate-directive` on the same
   salt-fixed harvest.
4. Keep the Section 7 package as the authoritative validation report for the current 7,488-triad
   screen. Use the JSON/CSVs in the Lop output directory for group-update tables.
5. Prepare/review the concrete Tier-2 pilot selection CSV, run `eps tier2-plan`, execute a mock
   array smoke, and only then schedule a separate reviewed real-Gaussian cluster work unit.

## Verification

- Section 7 validation branch verification before first code commit: targeted pytest `23 passed`;
  full pytest `224 passed, 5 skipped, 2 warnings`; `ruff check src tests` passed;
  `git diff --check` clean; mock `validate-directive` smoke wrote all required artifacts.
- Staging-audit branch verification: `.venv/bin/python -m pytest -q` reported `238 passed,
  5 skipped, 2 warnings`; `.venv/bin/ruff check src tests` passed; `git diff --check` passed.
- Tier-2 branch verification: targeted Tier-2/Gaussian/DFT tests `39 passed, 2 skipped`; tracked
  tests plus new Tier-2 pilot tests `227 passed, 5 skipped`; tracked-Python ruff passed;
  `bash -n` passed for new SGE templates; `git diff --check` passed.
- Integration verification: full pytest `238 passed, 5 skipped, 2 warnings`; ruff passed;
  `git diff --check` passed; SGE `bash -n` passed for the new validation/Tier-2 templates;
  no-real-engine CLI smoke passed; conflict-marker scan clean. Details are in
  `docs/maintenance/pre_cleanup_merge_report_20260623.md`.
- Codebase-map/hygiene verification: full pytest `238 passed, 5 skipped, 2 warnings`; ruff passed;
  `git diff --check` passed; `eps doctor` reported 0 FAIL and the expected four local
  cluster-binary WARNs; no-real-engine CLI smoke passed, including mock `eps validate`.
- R11-R21 primary-PDF correction verification: `.venv/bin/ruff check .` passed;
  `tests/test_eox_rescue.py` reported `51 passed`; `tests/test_lit_curation_audit.py` reported
  `4 passed`; validation/directive target tests reported `28 passed`; full pytest reported
  `290 passed, 5 skipped, 2 warnings`; `git diff --check` passed; `eps doctor` reported
  21 checks, 0 FAIL, and the expected four local cluster-binary WARNs.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

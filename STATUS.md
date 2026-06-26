# Project Status
_Last updated: 2026-06-25 (director autonomous run — Phase 1B: B1 criterion, §1–§9 audit, scale guard)_

## Director autonomous run (2026-06-25) — current state

**Read `DECISIONS_PENDING.md` first** for the human/PI checklist (3 decision gates + B1/λ/calibration/
reconcile + freeze + §0 no-go's). What this run changed (all committed + pushed to `main`):

- **Feasibility source of truth fixed.** Ingested the canonical 36-row set (19 YES / 17 NO) at
  `data/lit_curation/feasibility_labels_canonical_36row.csv`; production `polymerizability_labels.csv`
  (34) is superseded and has 3 **wrong carbazole SMILES** (pos 2/4, not 3,6 — corrected interpretation
  in `docs/research/feasibility_reconcile_20260625.md`).
- **§1–§9 code audit** (`docs/research/directive_section_audit_20260625.md`): hard gates + 5 composite
  terms are live/correct; selenophene `[se]`, optical `*`-SMILES, benchmark≥30, peak/onset split, pinned
  redox constant are already done. Net-new gaps: **λ computed-but-unused** (T16), **no scale guardrail**
  (now fixed), calibration strict/relaxed inconsistency, sTDA/COSMO-RS external blockers.
- **Scale guardrail implemented** (commit `6aca1be`): `run-tier1` blocks >12k triads and `tier2-plan`
  blocks >500 tasks unless `--allow-large-scale` — protects the directive §0 forbidden full-scale actions.
  Full suite **326 passed, 5 skipped**; ruff clean.
- **B1 coupling-feasibility criterion — DECIDED (THINK T15; `docs/research/b1_coupling_feasibility_results_20260625.md`)**:
  via the size-matched real-xTB batch (SGE 417846/417848), only the per-class coupling-SITE-availability
  signal separates intrinsic NO from YES, and only for **position-blocked** monomers. Size-matched
  dimerization ΔG does NOT separate the electronic (3-thiophenecarboxaldehyde −21.2 ≈ thiophene) or
  β-steric (3,4-dibutylthiophene +36.6 ≈ 3-hexylthiophene) NOs; α-spin is unavailable at xtb screening
  level. **B2** soft `coupling_risk_flag` implemented (`src/eps/properties/coupling_risk.py`, config in
  `tier1.yaml`, reported-only). **B3**: catches 3/7 intrinsic NOs with 0/11 false positives on simple
  YES → balanced accuracy 0.50→0.71; 4/7 are Tier-2 blind spots. **B4** (hard reject) → PI.
- **THINK T16** (λ wiring) and **T17** (two-tier freeze-readiness recommendation) added.
- Targeted lit-gapfill (`docs/research/lit_gapfill_20260625.md`): DMSO ESW, pyrrole+EDOT Epa,
  PFO/poly(2,7-carbazole)/polyfuran optical newly web-sourced (screening-grade, needs verification);
  NMP/nitrobenzene/THF/sulfolane + 3-methylthiophene Epa + neutral PPy optical still open.
- **No production scoring weight / threshold / calibration coefficient / redox constant / cache key /
  filter / library / harvest was changed.** Nothing frozen; no §0 full-scale action launched.

**Immediate next (for the PI / next session):** see `DECISIONS_PENDING.md`. Key calls: strict-vs-relaxed
calibration reconcile (data-gated on DFT 417442) + freeze tier-1 hard-constraint methods (T17); whether
to wire `coupling_risk_flag` into the harvest/feasibility report (needs the feasibility-anchor monomers
in the library — the library-expansion/promote decision); λ soft-term diagnostic (T16). No method frozen
and no §0 full-scale action launched by this run.

## Current phase

Directive Section 7 validation is now a reproducible, machine-readable workflow. The command
`eps validate-directive --engine xtb --harvest <salt-fixed-tier1-all.csv> --cache <sqlite>
--outdir <dir>` gathers the existing calculators into one package without changing scoring
weights, thresholds, calibration coefficients, redox constants, production CSVs, or the optical
policy. Mock mode remains a deterministic, explicitly NON-PHYSICAL smoke path.

### Post-review repository state (2026-06-25)

The independent repository review concluded that the architecture is healthy and the repository is
not broken: expensive work is still organized per species, triad scoring remains a join/arithmetic
layer, engines go through the shared interface/cache boundary, and scientific data/configuration
stay in CSV/YAML surfaces.

Review-reported evidence from baseline `d79a944410e1e98ab99c53b4399cde126890e241`: local
`main`/`origin/main` at `d79a944`, clean worktree, full pytest `313 passed, 5 skipped, 2 warnings`,
`ruff check .` passed, `eps doctor` reported 21 checks, 0 FAIL, and 4 expected cluster-binary WARNs.
Those test/tool results are review-reported here unless explicitly rerun in a later work unit. The
current production library is **36 x 13 x 16 = 7,488 triads**; this is the current validated
iteration scale, below the eventual directive target but not a failed run. No branch deletion or
large refactor should occur in this documentation-only work unit.

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

The G1.2 Eox master closure audit is now complete at **review-only** scope. External evidence was
prepared outside the repo under `$HOME/CombHTS_evidence/G1_2/`; committed repo artifacts contain
only canonical filenames, hashes, statuses, and normalized review tables. The generated package is
`data/lit_curation/eox_g1_2_source_manifest.csv`,
`data/lit_curation/eox_g1_2_master_evidence.csv`,
`data/lit_curation/eox_g1_2_combination_summary.csv`,
`data/lit_curation/eox_g1_2_production_change_proposal.csv`, and
`docs/research/eox_g1_2_master_closure_audit_20260624.md`. It reviews 39 production rows,
11 R11-R21 staging rows, and 36 external evidence/provenance rows. The audit finds **31**
directive-eligible combinations in the review/proposal basis (PASS versus `>=30`) while keeping
onset/peak model groups separate. It also identifies **10** current production Camarada rows as
non-CV steady-state polarization evidence, not clean CV onset; they are proposed only for a future
calibration/ontology correction, not edited in production.

The R11-R21 Eox rescue package remains **review-only staging**, not production ingest. A primary-PDF
correction memo records six thiophene attachment fixes (R12, R13, R14, R15, R16, R21) plus
source-internal reference/condition conflicts in the R14-R21 papers. The normalized source
transcription lives at `data/lit_curation/eox_r11_r21_source_candidates.csv`, the generated review
table at `data/lit_curation/eox_r11_r21_rescue_review.csv`, the regenerated report at
`docs/research/eox_r11_r21_staging_rescue_20260624.md`, and the correction memo at
`docs/research/eox_r11_r21_primary_pdf_correction_20260624.md`. All 11 rows RDKit-parse, all
working Ag-wire/SCE-to-Ag/AgCl transcriptions numerically reproduce, R14-R17 formulae match RDKit
formulae, and no row duplicates the production benchmark. In the master audit, R11-R13 are parked as
mixed-solvent pseudo-reference rows, and R14-R21 stay fail-closed because their source-internal
reference/condition conflicts are unresolved.

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

### Optical-gap correctness state (2026-06-25)

The optical-gap correctness fix is committed and pushed on `main`/`origin/main` as
`b6d9ae957cb2cb779847b3e857a5098c19e483a8` (`Fix optical gap sTDA cache key and geometry path`).
The code now captures optimized `xtbopt.xyz`, passes that captured optimized geometry into the sTDA
preparation calculation, records structured sTDA/fallback metadata in `CalcResult.raw`, and uses a
backend-aware optical cache key:
`base_method + "+optgap-optgeom-v2" + backend_tag`, where backend tags are `+backend-stda`,
`+backend-hl-fallback`, `+backend-mock`, and `+backend-generic`. Public raw result labels remain
`stda-xtb` and `homo_lumo_hexamer_fallback`.

Local targeted verification before the commit was
`.venv/bin/python -m pytest -q tests/test_xtb.py tests/test_oligomer.py`, reporting
`36 passed, 1 skipped`. The Lop real-backend smoke was prepared only in the isolated clone
`/home/shic4/CombHTS_optgap_smoke_20260624_235245/source`, checked out at the same commit; relative
to base `fae6bbabce52c216ad2d89febcf44c05fff42558`, only the four expected code/test files changed.
No SGE job was submitted, and no production run result was produced.

**Lop blocker wording:** real optimized-geometry sTDA smoke is **BLOCKED, not PASS**: `module avail
xtb` shows `xtb/6.4.1`, `module avail anaconda` shows `anaconda/3-2023.09`, but `module avail stda`
has no output, `module load stda` fails with `ERROR:105: Unable to locate a modulefile for 'stda'`,
and `command -v stda` is empty. A HOMO-LUMO fallback must not be accepted as a successful sTDA
smoke. The next operational blocker is locating, installing, or configuring a usable `stda` /
`xtb4stda` binary/module on Lop.

No production Lop checkout change occurred: `$HOME/CombHTS` remained on
`calib/solubility-cosmors` at `06b7e1dde6e66cf65d88300ba7809915b5d45d3f`; existing untracked files
remained unchanged, and the production stash was empty.

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
- The G1.2 Eox master audit builds deterministic source-manifest, master-evidence,
  combination-summary, and production-change-proposal tables from normalized CSV inputs plus the
  external manifest. It refuses production CSV/config/scoring/redox/validation destinations,
  canonicalizes SMILES with RDKit, keeps onset/peak model groups separate, and never parses PDFs at
  production runtime.
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

1. **RESOLVED 2026-06-25 (binary + engine level).** Real-backend optical-gap sTDA is now operational on
   Lop: `stda` (prebuilt v1.6.3) installed and `xtb4stda` built from source (`meson -Dla_backend=openblas`)
   in `$HOME/bin`; the eps engine fix (`src/eps/engines/xtb.py`, commit c5dce3a) now calls `xtb4stda`
   (writes `wfn.xtb`) instead of plain `xtb` — the prior code could never produce real sTDA. End-to-end
   eps smoke SGE 417865 returned `optical_gap_method="stda-xtb"` (value 5.354 eV, thiophene), not the
   fallback (manifest `docs/runs/2026-06-25_optical-stda-unblock-417865.md`). Runtime needs
   `PATH=$HOME/bin` + `XTB4STDAHOME=$HOME/xtb4stda_src`. **Production re-harvest DONE** (SGE 417866,
   `docs/runs/2026-06-26_optical-reharvest-417866.md`): all 36 monomers now have real
   `optical_gap_method=stda-xtb` (0 NaN; sane hexamer gaps), replacing the HOMO-LUMO fallback, and the
   new `oligomer_Eox_monotonic_status` is monotonic_decreasing for all 36. **Remaining:** per-class
   optical calibration (T6) — the 15% axis stays DIAGNOSTIC until then; the real sTDA descriptors it
   would consume now exist.
2. Calibration operational truth needs better visibility. Production Tier-1 uses the
   `agagcl_peak_strict` coefficients in `configs/tier1.yaml`, while default `eps validate` uses
   `agagcl_peak_relaxed` from `configs/calibration_profiles.yaml`. Add an active-calibration
   manifest and explicit CLI disclosure before revisiting strict-vs-relaxed scientifically.
3. Current-operating-state documentation and stale terminology need a concise cleanup. Add a short
   current-state/reader entrypoint and align outdated "placeholder" wording with the current
   "screening-grade/diagnostic" reality without changing scientific conclusions.
4. Interface/schema locking should precede large-module decomposition. Lock public CLI defaults/help
   and generated CSV/JSON schemas before splitting `eps.cli`, directive validation, or curation
   modules.
5. ESW descriptor physics is the largest validated failure. The raw isolated-solvent molecular
   DeltaSCF descriptors are off by multiple volts versus practical ESW measurements. They should
   remain audited priors/caps, not standalone solvent-window calibrations.
6. Exact ESW formulation coverage is sparse. The safety invariant passes, but exact `(solvent,salt)`
   coverage is only 3.37% of the salt-fixed harvest rows. The staging audit now pinpoints priority
   review targets: exact PC BF4/PF6/ClO4/TFSI rows, MeCN/TBAPF6, nitromethane primary-source
   reconciliation, NMP, and nitrobenzene.
7. Feasibility labels are not yet enough for the directive `>85%` claim. Add condition-relevant
   negatives and exact-anion labels, especially in baseline nonaqueous media, until at least a
   defensible matched validation set exists.
8. Tier-2 held-out DFT validation remains out of scope for the Section 7 package. The old 0.119 V
   DFT number is in-sample and must not be reported as a held-out Tier-2 pass. The pilot
   orchestration is ready, but no real Gaussian array has been submitted and no completed Tier-2
   scientific values exist yet.
9. The composite's diagnostic half remains data-limited: optical, dimerization absolute scale, and
   solvation-affinity/true-solubility calibration are reference-only until better anchors exist.
10. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, cation deposition, and condition-specific anion
   limits are not calibrated.
11. The current validated iteration scale is 36 x 13 x 16 = 7,488 triads, below the eventual
   directive target of roughly 80-150 x 25-35 x 20-30 but not a failed run. The vetted expansion
   proposal remains gated on stable ESW, solvation/solubility, and optical evidence.

## Immediate next actions

1. Locate, install, or configure a usable Lop `stda` / `xtb4stda` binary/module, then rerun the
   isolated real optimized-geometry sTDA smoke against
   `b6d9ae957cb2cb779847b3e857a5098c19e483a8`. Do not accept HOMO-LUMO fallback as a successful
   sTDA smoke.
2. Add an active-calibration manifest plus explicit CLI disclosure so users can distinguish
   production Tier-1 coefficients from validation-profile fits. Do not choose strict vs relaxed or
   alter coefficients in that operational-visibility task.
3. Add a concise current-operating-state entrypoint and clean stale terminology only where it
   reduces confusion. Do not delete branches or start a large refactor in this work unit.
4. Lock CLI/interface defaults and output schemas before decomposing large modules such as
   `eps.cli`, `eps.validation.directive`, or curation audit builders.
5. Review the G1.2 master audit proposal table before any production ingest. Treat the 10 Camarada
   rows as a separate production-correction task, and treat the 5 clean external Ag/AgCl onset rows
   as separate add-candidate rows that still need human sign-off.
6. Resolve or exclude the R11-R21 mixed-solvent/source-conflict blockers before any separate
   benchmark-promotion task.
7. Review the Section 7 staging-audit outputs, source-check the flagged ESW/polymerization rows,
   and promote only approved rows through a separate production-ingest task.
8. Expand Section 7 evidence coverage, not weights: add exact ESW formulation rows and
   condition-relevant feasibility labels, then rerun `eps validate-directive` on the same
   salt-fixed harvest.
9. Keep the Section 7 package as the authoritative validation report for the current 7,488-triad
   screen. Use the JSON/CSVs in the Lop output directory for group-update tables.
10. Prepare/review the concrete Tier-2 pilot selection CSV, run `eps tier2-plan`, execute a mock
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
- G1.2 Eox master-audit targeted verification: `tests/test_eox_master_audit.py` reported
  `23 passed`; targeted ruff on the new module, wrapper, exports, and tests passed; full pytest
  reported `313 passed, 5 skipped, 2 warnings`; `git diff --check` passed; `eps doctor` reported
  21 checks, 0 FAIL, and the expected four local cluster-binary WARNs.
- Optical-gap correctness verification before commit `b6d9ae957cb2cb779847b3e857a5098c19e483a8`:
  `.venv/bin/python -m pytest -q tests/test_xtb.py tests/test_oligomer.py` reported
  `36 passed, 1 skipped`; the Lop real-backend smoke stopped before submission at the missing
  `stda` module/binary preflight.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

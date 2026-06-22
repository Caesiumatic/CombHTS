# Project Status
_Last updated: 2026-06-22 (n=6 optical calibration prepared; awaiting human qsub submission)_

## Current phase

Directive items 2 and 3 have reached the pilot/implementation milestone.

- Tier-1 now uses a **condition-aware, measured-first/conservative solvent-window gate** after
  the cheap solvent+electrolyte join. Water, MeCN, DCM, DMF, and DMSO controls are tested; the
  hard gate is the minimum across selected conditioned measurement, curated CSV, and computed
  prior, so a wider generic formulation can never relax an existing conservative bound.
- A mock-first ORCA 6.1 Engine, CLI workflows, SQLite caching, raw-output retention, and SGE
  templates now cover openCOSMO-RS solvation and paired sTDA/TDA optical pilots.
- Real openCOSMO-RS job 417544 completed 3/3 points. Corrected optical job 417557 completed 3/3
  sTDA recalculations plus 3/3 TDA cache hits; its standard CSV/JSON now reproduce the raw spectra.
- The six-HIGH-anchor computed-to-experiment optical workflow is prepared on
  `calib/optical-n6`: serial ORCA sTDA+TDA dimers, a distinct resumable cache/output directory,
  staging-row provenance, and post-run slope/intercept/R2/LOO-CV/per-class/leverage analysis.
  It has **not been submitted** and has no real n=6 result yet. The corrected pilot cache has
  0/12 exact-key overlaps, so all six anchor dimers need both real methods.
- The expanded real GFN2-xTB Tier-1 job 417538 completed with zero failures in all seven core/
  scored stages. CSV-only job 417553 produced 2,961/7,488 survivors, but its shortlist exposed that
  uncapped generic GBL evidence (5.2 V) dominated all top-20 rows. It is retained as a diagnostic,
  not the final corrected ranking. Final capped job 417562 produced **2,938/7,488 survivors** with
  zero gains relative to the old gate; its survivor set is a strict subset of the old set.

The corrected Tier-1 descriptor/ranking pipeline is in the **shortlist-audit / validation phase, and
the per-row shortlist audit is now COMPLETE** (merged to main at bee31d3). Read-only analysis 417564
produced a standards-compliant 30-row diagnostic shortlist (raw **24 PC / 6 MeCN**). The completed
audit ([docs/audits/shortlist_audit_417564.md](docs/audits/shortlist_audit_417564.md)) found that a
**salt-permutation score degeneracy** is the top artifact: the composite ignores the cation
(`window_margin` is solvent-only, `anion_stability` anion-only, solubility/dimerization/band_gap
monomer-only), so each (monomer, solvent, anion) chemistry appears up to 5x at a byte-identical
score. Collapsing that degeneracy and removing artifact salts reduces the list to **14 distinct
chemistries (8 PC / 6 MeCN, ~57% PC)** — the raw 80% PC headline is largely a permutation artifact,
**not** ESW inflation (the measured-first min-of-evidence cap held: PC 3.6 V -> 2.947 V). Audit
verdicts: **KEEP 2 / CAVEAT 12 / PARK 10 / REMOVE 6** (REMOVE = all AgClO4 reference-salt rows + all
HClO4 acid rows). The audit's gate fix is now merged on `main`: versioned role metadata excludes every acid and
reference-only salt behind a reversible YAML toggle, while ranked/shortlist views collapse exact
cation-only score permutations and retain `salts_tied`/`n_tied`. `tier1_all.csv` still retains and
scores every passing per-salt row for audit. This is a presentation correction for a known model
limitation, not invented cation physics.

The fix has now been applied to the existing real-xTB harvest without rerunning xTB. CSV-only SGE
417569 completed in 21 s: capped-ESW survivors changed **2,938 -> 2,143** (795 dropped, zero gained),
all common-row scores were unchanged, and zero acid/reference-only row passed. The full survivor
audit collapses to **1,127 exact score-classes** in the ranked view. Read-only analysis 417571
completed in 44 s; its distinct diagnostic top-30 is **19 PC / 6 MeCN / 3 nitromethane / 2 NMP**
(PC 63.3%, down from the raw 80%). AgClO4 and HClO4 are absent both as representatives and inside
`salts_tied`. The old shortlist's 14 distinct classes all remain: its 8 PC / 6 MeCN (~57%) estimate
is reproduced in the leading 14, while the expanded distinct top-30 adds 16 lower-ranked classes.

Three analysis/proposal artifacts are now merged to main (bee31d3), all **analysis/proposal ONLY** —
none changed scoring, config, or production data: the 417564 shortlist audit
([docs/audits/shortlist_audit_417564.md](docs/audits/shortlist_audit_417564.md)); the optical-anchor
selection + calibration plan ([data/lit_curation/optical_anchors_selected.csv](data/lit_curation/optical_anchors_selected.csv)
+ [docs/lit_curation/optical_calibration_plan.md](docs/lit_curation/optical_calibration_plan.md),
6 high-confidence + 3 medium neutral-polymer anchors, n=6 primary target, replacing the n=3 sTDA/TDA
pilot — the 15% optical axis stays DIAGNOSTIC until that calibration is executed and reviewed); and
the library-expansion proposal ([docs/research/library_expansion_proposal.md](docs/research/library_expansion_proposal.md),
+76 monomers / +27 solvents / +25 salts, RDKit-verified, proposal only, gated on stable
ESW/solubility/optical gates before any wiring).

Code verification is green: **214 passed, 5 skipped**; `ruff check .` and `git diff --check`
pass. This remains a screening/route-validation milestone, not an experimental recommendation.

## What works

- Architecture invariants remain intact: expensive work is per species, triads are cheap joins,
  all engines share the Engine interface, results are cache-keyed by species/method/solvent, and
  libraries/configuration are versioned CSV/YAML.
- `data/solvent_windows.csv` records anodic/cathodic limits in V vs Ag/AgCl with salt,
  electrolyte, electrode, reference, cutoff, source, tier, and electrolyte-limited metadata.
  Evidence selection is exact `(solvent,salt)` measurement then conservative solvent-only evidence;
  the hard gate is capped by `min(measurement, curated CSV, computed descriptor)` and every raw
  measurement/cap/source/cap-applied decision remains audited.
- The mandatory ESW controls retain their conditioned measurements as auditable evidence
  (water/KCl 1.145 V, MeCN/TBABF4 3.245 V, DCM/TBAClO4 1.845 V, DMF/TBAClO4 1.745 V, and
  DMSO/TBAPF6 1.045 V vs Ag/AgCl) while using the minimum of measurement/CSV/computed as the gate.
- Real ORCA/openCOSMO-RS dGsolv in MeCN (kcal/mol): thiophene -4.132112, EDOT -7.908007,
  pyrrole -6.982100. These validate the route only; dGsolv is not solubility.
- Real ORCA corrected dimer pairs `(sTDA, TDA)` in eV: thiophene (4.870360, 4.396), EDOT
  (4.869517, 4.687), pyrrole (5.488049, 5.004). The three-point diagnostic fit is slope 0.747765,
  intercept 0.900028 eV, R2 0.7701, MAE 0.0973 eV; it is too small and ill-conditioned for scoring.
- Lop ORCA 6.1/openCOSMO-RS and built-in sTDA/TDA work serially. Four-core attempts 417540-543
  exposed an OpenMPI 4.1.8/hwloc topology segfault on older nodes; no failed value was cached.
- Real Tier-1 job 417538 completed in 10 h 54 m 54 s. Core stages had zero failed triad rows.
  Report-only failures remain fully audited: spin-density secondary monomer rows 7,488; water
  cathodic/secondary-solvent rows 576 each; ion-pair rows 3,744.
- Diagnostic re-score 417553 used no Engine and completed in 31 s. It removed 1,140 old survivors
  and admitted 23, but its top-20 were all GBL because the first policy did not cap a wide generic
  measurement. That evidence directly motivated the stricter minimum-of-all-evidence hard gate.
- Final capped re-score 417562 completed with 2,938 survivors, exactly 1,140 fewer than the old gate
  and **zero newly admitted triads**. Its survivor set is a strict subset of the old set; water and
  DMSO remain at zero. Final analysis 417564 removed GBL domination and produced a complete
  standards-compliant 30-row PC/MeCN-led diagnostic shortlist.
- `data/electrolytes.csv` now classifies supporting/reference-only/acid roles additively. The live
  role gate excludes AgClO4 and all four acid entries without aborting or deleting audit rows.
  Exact cation-degenerate score classes are represented once in ranked/shortlist outputs with
  deterministic tied-salt metadata; the unchanged full per-salt score table remains in
  `tier1_all.csv`.
- Real-harvest verification 417569/417571 proves the gate behaves as designed: 2,143 per-salt
  survivors, 1,127 ranked score-classes, zero non-supporting passes, and no score change among the
  2,143 retained rows. The representative salt is only a deterministic label, not a cation claim.

## Open scientific and engineering debt

1. The condition table is still sparse. Exact-salt/electrode coverage and quantitative ESW error
   analysis must expand; a conditioned formulation limit is not a universal solvent constant.
2. **Salt-permutation score degeneracy (417564 audit — presentation/gate guard IMPLEMENTED; cation
   physics still absent).** The composite ignores the cation — `window_margin` is solvent-only,
   `anion_stability` anion-only, and solubility/dimerization/band_gap monomer-only — so each
   (monomer, solvent, anion) chemistry appears up to 5x at a byte-identical score. This inflates the
   apparent PC dominance (raw 80% -> ~57% over 14 distinct chemistries: 8 PC / 6 MeCN). Ranked and
   shortlist views now collapse only exact score classes and expose every tied salt; the full audit
   remains per-salt. A separate config-driven role gate excludes reference-only and acid rows.
   Remaining debt is a validated cation/salt-compatibility model, not further tie-breaking.
3. The corrected three-dimer optical fit is route evidence only. The six-anchor/per-class
   expansion is prepared but awaiting human submission; no real n=6 regression exists yet.
4. Solubility remains a dGsolv proxy without lattice/fusion, concentration, aggregation,
   protonation, or salt-compatibility terms. openCOSMO-RS improves the descriptor, not the claim.
5. Optical calibration still needs completion of the prepared six-anchor run plus longer-chain/
   geometry sensitivity and review. The prepared n=6 baseline deliberately uses pilot-matched
   dimers and therefore does not satisfy the polymer-limit gate. The 15% axis remains diagnostic.
6. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, and condition-specific anion limits are sparse.
7. Dimerization has an unknown proton-reference offset; polymer doping onset is reported but not
   calibrated; Tier-2 production still lacks the full solvent-/ion-specific execution matrix.
8. Validation coverage remains below directive gates, and the library is 36x13x16 versus the
   requested roughly 80-150 x 25-35 x 20-30. The vetted +76/+27/+25 library-expansion proposal
   (`docs/research/library_expansion_proposal.md`, merged bee31d3) is PROPOSAL ONLY and stays gated
   on stable ESW/solubility/optical gates before any wiring.
9. **`cation_reduction_below_solvent_cathodic` does not model metal deposition (417564 audit).** It
   does not model Ag+ plating as metal, so a passing flag must not be read as plating/compatibility
   protection. The role gate now blocks the known reference-only/acid misuse, but it is only a
   guard: a calibrated cation/deposition model remains open scientific debt.

## Immediate next actions

1. Audit salt solubility/conductivity/ion pairing for the 30 distinct classes, prioritizing the
   19 PC rows and remembering that alphabetic Li representatives are not cation recommendations.
2. Expand exact-formulation ESW and solubility anchors, then run the six-anchor/per-class optical
   calibration before considering any production score change.
3. Use those error analyses to choose the next 10-20 monomer Tier-2 pilot. Full-scale Tier-2 and
   expansion to ~100x30x25 remain the genuine PI/group resource-planning decision.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

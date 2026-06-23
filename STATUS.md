# Project Status
_Last updated: 2026-06-22 (soft-axis review complete; §7 validation next)_

## Current phase

Soft-axis calibration review is **COMPLETE** as of 2026-06-22. Dimerization's unknown
proton-reference offset is confirmed to be one constant across monomers by code inspection,
test assertions, and harvested value distribution; min-max normalization cancels that constant, so
the 15% dimerization axis is **ranking-safe** as implemented. It remains diagnostic, not calibrated:
absolute solution thermochemistry and monomer-dependent chemistry errors are unvalidated.

The 20% "solubility" score component is now documented honestly as **solvation affinity
(dGsolv proxy)**. It is min-max(-dGsolv), not measured solubility. The missing lattice/fusion term is
primary, and calibration is blocked by two data facts: no quantitative solubility data exist for
the key process solvents PC and NMP in the current library, and Lop's ORCA/openCOSMO-RS built-in
solvent database contains only acetonitrile, nitromethane, and water. Because the corrected
distinct top-30 is 63% PC, the axis cannot be properly evaluated for most survivors. The formula,
weight, and scoring config are unchanged.

Optical calibration has moved from prepared to **submitted and RUNNING** as SGE job **417587** on
Lop (reported/unverified; no output inspected in this repo). Even when it completes, it is a
diagnostic baseline only: neutral dimer (n=2) excitations are being compared to neutral-polymer
experimental gaps, so the chain-length, geometry-sensitivity, phase-matching, per-class residual,
and leverage gates remain unsatisfied. The 15% optical axis stays diagnostic until the full review is
complete and accepted by a human.

Composite interpretation is now explicit. The reliable half, weight **0.50**, is
`window_margin` (0.30) plus `anion_stability` (0.20), backed by calibrated/two-stage-validated Eox,
measured-first conservative ESW, and the salt-role hard gate. This half drives trustworthy pass/fail
and coarse ranking. The diagnostic half, weight **0.50**, is optical + dimerization + solvation
affinity; all three are data-gated and reference-only for now. The shortlist is therefore a
hard-gate-driven **chemical-feasibility shortlist**, not a full OMIEC performance ranking or an
experimental recommendation.

The next highest-ROI work is **§7 Tier-1 validation**, not continued soft-axis calibration: report
Eox calibration MAE in the honest 0.20-0.35 V band, ESW MAE against `data/solvent_benchmark.csv`,
and polymerization yes/no accuracy using `data/polymerizability_labels.csv`. Soft-axis absolute
calibration is deferred as future/opportunistic work.

The corrected real-harvest state is unchanged: CSV-only SGE 417569 applied the salt-role gate to
the existing real-xTB harvest without rerunning xTB, changing capped-ESW survivors
**2,938 -> 2,143** (795 dropped, zero gained), with all retained scores unchanged and zero
acid/reference-only passes. Read-only analysis 417571 produced **1,127 exact score-classes** and a
distinct diagnostic top-30 of **19 PC / 6 MeCN / 3 nitromethane / 2 NMP**. AgClO4 and HClO4 are
absent as representatives and inside `salts_tied`.

Docs-sync verification is green: `.venv/bin/python -m pytest -q` reports **216 passed, 5 skipped**
with 2 warnings. The known ruff I001 import-ordering debt in `tests/test_orca_pilots.py` is not fixed
in this docs-only work unit.

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
  pyrrole -6.982100. These validate the route only; the 20% axis is solvation affinity
  (dGsolv proxy), not measured solubility.
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
   `anion_stability` anion-only, and solvation-affinity/dimerization/band_gap monomer-only — so each
   (monomer, solvent, anion) chemistry appears up to 5x at a byte-identical score. This inflates the
   apparent PC dominance (raw 80% -> ~57% over 14 distinct chemistries: 8 PC / 6 MeCN). Ranked and
   shortlist views now collapse only exact score classes and expose every tied salt; the full audit
   remains per-salt. A separate config-driven role gate excludes reference-only and acid rows.
   Remaining debt is a validated cation/salt-compatibility model, not further tie-breaking.
3. The corrected three-dimer optical fit is route evidence only. The six-anchor/per-class
   expansion is now submitted as SGE **417587** and RUNNING on Lop (reported/unverified); no real
   n=6 regression result is known yet.
4. The former "solubility" label is a **solvation affinity (dGsolv proxy)** score. It lacks
   lattice/fusion, concentration, aggregation, protonation, and salt-compatibility terms. PC/NMP
   calibration is blocked because quantitative process-solvent solubility data are absent and Lop's
   built-in openCOSMO-RS solvent profiles cover only MeCN, nitromethane, and water.
5. Optical calibration still needs 417587 completion plus per-class residuals, leverage analysis,
   comparison to the n=3 pilot, longer-chain/geometry sensitivity, and human review. The submitted
   baseline deliberately uses pilot-matched dimers and therefore does not satisfy the polymer-limit
   gate. The 15% axis remains diagnostic.
6. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, and condition-specific anion limits are sparse.
7. Dimerization's proton-reference ambiguity is resolved for ranking: the offset is one common
   additive intercept and cancels exactly from the min-max 15% term. Absolute calibration remains
   deferred until exact-reaction equilibrium/Hess-cycle data exist; kinetics/onsets are not anchors.
   Optional cosmetic debt: rename output/docs from "dimerization" to "radical-coupling energy" where
   doing so does not imply a formula, weight, or config change.
8. §7 validation is the next active item: Eox MAE, ESW MAE, and polymerization yes/no accuracy
   should be reported before further soft-axis chasing. Use `data/polymerizability_labels.csv` for
   the yes/no metric and never claim MAE < 0.15 V.
9. `tests/test_orca_pilots.py` has ruff I001 import-ordering debt. Fix it on the next src-touching
   PR; it does not affect test results.
10. Validation coverage remains below directive gates, and the library is 36x13x16 versus the
   requested roughly 80-150 x 25-35 x 20-30. The vetted +76/+27/+25 library-expansion proposal
   (`docs/research/library_expansion_proposal.md`, merged bee31d3) is PROPOSAL ONLY and stays gated
   on stable ESW, solvation-affinity/true-solubility, and optical gates before any wiring.
11. **`cation_reduction_below_solvent_cathodic` does not model metal deposition (417564 audit).** It
   does not model Ag+ plating as metal, so a passing flag must not be read as plating/compatibility
   protection. The role gate now blocks the known reference-only/acid misuse, but it is only a
   guard: a calibrated cation/deposition model remains open scientific debt.

## Immediate next actions

1. Run §7 Tier-1 validation: report Eox calibration MAE (honest 0.20-0.35 V band), ESW MAE vs
   `data/solvent_benchmark.csv`, and polymerization yes/no accuracy using
   `data/polymerizability_labels.csv`.
2. Await 417587 optical result, then fit n=6, inspect per-class residuals and leverage, and compare
   to the n=3 pilot. Do **not** wire it into the composite until reviewed.
3. Fix ruff I001 in `tests/test_orca_pilots.py` on the next src-touching PR.
4. Tier-2 pilot selection (10-20 stratified monomers from the corrected ranking) and library
   expansion remain PI/resource decisions for the June-30 group meeting.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

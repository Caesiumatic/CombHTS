# Project Status
_Last updated: 2026-06-22 08:18 CDT_

## Current phase

The first expanded-library **REAL GFN2-xTB Tier-1 harvest** is running on Lop as SGE job
**417538** (36 monomers x 13 solvents x 16 salts = 7,488 triads; ib2; 4 slots; 72 h wall).
Direct SSH verification at 08:18 CDT found the job active and the resumable SQLite cache at
**856 successful per-species results** (~39% of the 2,223 no-failure calls in the equivalent
mock run). No final `tier1_ranked.csv` or `tier1_all.csv` exists yet, so survivor and failure
counts are still unknown.

The codebase is healthy: local `.venv/bin/pytest -q` reports **191 passed, 4 skipped** and
`.venv/bin/ruff check .` passes. This is an engineering milestone, not yet a validated
scientific ranking.

## What works

- Architecture invariants are implemented: per-species computation followed by cheap triad
  joins; deterministic MockEngine; SQLite caching; CSV libraries; YAML thresholds/weights;
  one tested redox-reference conversion function.
- Tier 1 computes all five composite axes with real GFN2-xTB routes: calibrated monomer Eox,
  monomer-solvent solvation free energy, solvent/anion oxidation descriptors, n=6 oligomer gap,
  and oxidative-coupling energy. Failures are audited without aborting the harvest.
- The interim library is valid and parseable at **36 x 13 x 16 = 7,488 triads**. It is still
  well below the directive target of roughly 80-150 x 25-35 x 20-30.
- The real gas-phase B3LYP/6-31G(d,p) calibration batch 417442 completed 22/22 monomers. Its
  composed xTB->DFT->experiment line agrees with the pinned Tier-1 line within 0.087 V over
  the calibration range, but this does not validate solvent windows, solubility, optical gaps,
  or polymerization outcomes.
- `eps analyze` can produce retention summaries, failure counts, distributions, Pareto plots,
  chemical-space maps, and a diagnostic shortlist. `eps validate` supports separate peak/onset
  profiles, a solvent-window benchmark, and a balanced-accuracy feasibility diagnostic.
- Tier-2/Tier-3 Gaussian input generation is config-driven and cache-safe. The completed Tier-2
  batch is only a monomer gas-phase calibration; the production refinement workflow remains a
  dry-run/scaffold.

## Verified Lop facts

- Job 417538: running since 2026-06-21 22:44:48 CDT on `ib2@compute-2-16.local`, 4 slots.
- Cache snapshot: 325 `adiabatic_ip`, 167 `solvation_free_energy`, 184 `optical_gap`, 72
  `gas_energy`, and 36 each of `homo`, `lumo`, and `vertical_ip` (856 total). Final CSVs pending.
- Modules: xtb 6.4.1, Gaussian g16, and ORCA 4.2.1-6.1.0 are available.
- Standalone `stda`/`std2` and a standalone COSMO-RS module are absent. However, the installed
  ORCA 6.1 tree **does contain an executable `openCOSMORS`**, and ORCA 6.1 supports openCOSMO-RS
  and built-in sTDA/sTD-DFT. The solvation/optical calibration routes are therefore no longer
  wholly blocked on a Help Desk installation; they need a small verified pilot and backend code.

## Scientific gaps that block an experimental recommendation

1. **Solvent ESW is not validated and is presently the highest-risk axis.** The primary value is
   an isolated-solvent xTB oxidation descriptor passed through a monomer calibration. The old
   real-xTB shortlist consequently ranked EDOP/water highly while assigning water an anodic
   limit of ~3.77 V vs Ag/AgCl; the library's own experimental fallback is 0.77 V. Matching
   numerical scales does not make a molecular IP an experimental, electrode/electrolyte-specific
   electrochemical window. Until fixed, constraint (i) is not trustworthy.
2. **Solubility is a solvation proxy, not solubility.** `DeltaG_solv < -3 kcal/mol` ignores the
   solute lattice/fusion term, concentration, temperature, aggregation, protonation, surfactants,
   and salt compatibility. Constraint (iii) is therefore only a weak ranking proxy.
3. **Electrolyte compatibility is partial.** Anion oxidation is computed, but its calibration is
   extrapolated from monomers; salt solubility/conductivity, ion pairing, acid/base speciation,
   and condition-specific anion limits are unvalidated. Cation reduction and ion-pair descriptors
   are reported-only.
4. **Optical gap is real but uncalibrated.** The active run uses an n=6 GFN2-xTB HOMO-LUMO
   fallback because external sTDA-xTB is absent. The target is an optical excitation, so this
   cannot yet support the 15% band-gap score or a material-quality claim.
5. **Dimerization is relative-only.** The xTB coupling energy carries an unknown proton reference
   offset; absolute exothermicity and the directive's `DeltaG < -10 kcal/mol` interpretation are
   not available.
6. **Polymer doping onset is not delivered.** Oligomer Eox-vs-length and a 1/n extrapolation are
   reported, but they are not calibrated to polymer-film doping onset and do not enter ranking.
7. **Tier 2 is incomplete.** Production Tier 2 currently writes neutral/cation monomer inputs and
   can merge a per-monomer Eox CSV. It does not yet execute solvent-specific DFT for monomers,
   solvents, anions/cations, spin density, dimerization, reorganization, or TD-DFT convergence.
8. **Validation coverage is below directive gates.** The frozen clean peak calibration has 9
   points (relaxed peak 23, onset 16); the solvent benchmark has 6 rows and several are
   electrolyte-limited; the binary feasibility set is 18 YES/16 NO but only a small in-library
   subset matches. The >=30 clean-group, solvent-MAE, and >85% feasibility goals are not met.
9. **No expanded real shortlist exists yet.** The running harvest must finish, pass its per-species
   failure audit, and be re-analyzed before any 20-50 candidate list can be generated.

## Immediate next actions

1. Let 417538 finish (or resume from the same cache after a wall kill), then update the run
   manifest with final survivor/failure counts before running `eps analyze`.
2. Treat the coming composite ranking as a diagnostic only. First replace the solvent-window
   gate with a condition-aware measured-first/conservative hybrid and test the water/MeCN/DCM/
   DMF/DMSO controls.
3. Run two small ORCA pilots now: openCOSMO-RS on a representative monomer-solvent matrix, and
   sTDA/TD-DFT on the existing six polymer optical-gap anchors. Add them through Engine interfaces
   and cache them per species; do not launch the full production matrix first.
4. Expand experimental anchors: solvent windows with electrode/electrolyte/reference metadata;
   quantitative or threshold monomer solubilities; baseline-condition polymerization negatives;
   and polymer optical/doping-onset data.
5. Complete Tier-2 execution per species for a stratified 10-20 monomer pilot, then use the error
   analysis to decide which axes deserve full-scale DFT. The full ~100 x 30 x 25 production spend
   remains the genuine PI/group resource-planning decision.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

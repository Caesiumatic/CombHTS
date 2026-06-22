# Project Status
_Last updated: 2026-06-22 11:00 CDT_

## Current phase

Directive items 2 and 3 have reached the pilot/implementation milestone.

- Tier-1 now uses a **condition-aware, measured-first/conservative solvent-window gate** after
  the cheap solvent+electrolyte join. Water, MeCN, DCM, DMF, and DMSO controls are tested; the
  computed solvent oxidation descriptor remains in the audit but cannot override a measurement.
- A mock-first ORCA 6.1 Engine, CLI workflows, SQLite caching, raw-output retention, and SGE
  templates now cover openCOSMO-RS solvation and paired sTDA/TDA optical pilots.
- Real openCOSMO-RS job 417544 completed 3/3 points. Real optical job 417545 completed all six
  ORCA calculations; corrected raw values prove the route, but the submitted sTDA postprocessor
  misread an unrelated numeric table. The parser is fixed and regression-tested locally; the
  cluster CSV/cache is explicitly invalid until a corrected sTDA-only rerun.
- The expanded real GFN2-xTB Tier-1 job 417538 completed with zero failures in all seven core/
  scored stages. CSV-only job 417553 has now superseded its old gate: **2,961/7,488 survivors
  (39.5%)**, down from 4,078/7,488. The new and old top-50 lists overlap 0/50, so the old shortlist
  must not be used. Directive-§8 analysis of the corrected harvest is next.

Local verification is green: **205 passed, 5 skipped**; `ruff check .` and `git diff --check`
pass. This remains a screening/route-validation milestone, not an experimental recommendation.

## What works

- Architecture invariants remain intact: expensive work is per species, triads are cheap joins,
  all engines share the Engine interface, results are cache-keyed by species/method/solvent, and
  libraries/configuration are versioned CSV/YAML.
- `data/solvent_windows.csv` records anodic/cathodic limits in V vs Ag/AgCl with salt,
  electrolyte, electrode, reference, cutoff, source, tier, and electrolyte-limited metadata.
  Selection order is exact `(solvent,salt)` conservative measurement, conservative solvent-only
  measurement, then `min(curated CSV, computed descriptor)` as a flagged fallback.
- The mandatory ESW controls select measured values: water/KCl 1.145 V, MeCN/TBABF4 3.245 V,
  DCM/TBAClO4 1.845 V, DMF/TBAClO4 1.745 V, and DMSO/TBAPF6 1.045 V vs Ag/AgCl.
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
- Measured-first re-score 417553 used no Engine and completed in 31 s. It removed 1,140 old
  survivors and admitted 23 (net -1,117); window-pass rows fell 6,352 -> 4,244 while anion and
  solvation pass counts were unchanged. DMSO and water now have zero survivors.

## Open scientific and engineering debt

1. The condition table is still sparse. Exact-salt/electrode coverage and quantitative ESW error
   analysis must expand; a conditioned formulation limit is not a universal solvent constant.
2. The 23 newly admitted PC/GBL triads come from generic measured formulation windows that exceed
   the old prior; audit them and the zero-overlap top-50 before any experimental recommendation.
3. Job 417545's ORCA calculations are valid, but its generated sTDA CSV/cache values are not.
   Sync the fixed absorption-block parser, delete only the three invalid sTDA cache rows, and rerun;
   the three valid TDA cache rows should be reused.
4. Solubility remains a dGsolv proxy without lattice/fusion, concentration, aggregation,
   protonation, or salt-compatibility terms. openCOSMO-RS improves the descriptor, not the claim.
5. Optical calibration needs the six experimental neutral-polymer anchors, longer-chain/geometry
   sensitivity, and per-class validation. The three-dimer pilot must not change the 15% score axis.
6. Electrolyte compatibility remains partial. Anion oxidation is scored, but salt solubility,
   conductivity, ion pairing, acid/base speciation, and condition-specific anion limits are sparse.
7. Dimerization has an unknown proton-reference offset; polymer doping onset is reported but not
   calibrated; Tier-2 production still lacks the full solvent-/ion-specific execution matrix.
8. Validation coverage remains below directive gates, and the library is 36x13x16 versus the
   requested roughly 80-150 x 25-35 x 20-30.

## Immediate next actions

1. Run `eps analyze` on `outputs/tier1_real_7488_measured_esw/tier1_all.csv`; inspect the corrected
   shortlist/Pareto set and explicitly audit the 23 PC/GBL gains.
2. Re-run only the invalid ORCA sTDA cache entries with the fixed parser; verify the standard
   CSV/JSON reproduce the raw-output values and diagnostic fit recorded above.
3. Expand exact-formulation ESW and solubility anchors, then run the six-anchor/per-class optical
   calibration before considering any production score change.
4. Use those error analyses to choose the next 10-20 monomer Tier-2 pilot. Full-scale Tier-2 and
   expansion to ~100x30x25 remain the genuine PI/group resource-planning decision.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

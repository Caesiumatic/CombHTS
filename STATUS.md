# Project Status
_Last updated: 2026-06-22 11:27 CDT_

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
- The expanded real GFN2-xTB Tier-1 job 417538 completed with zero failures in all seven core/
  scored stages. CSV-only job 417553 produced 2,961/7,488 survivors, but its shortlist exposed that
  uncapped generic GBL evidence (5.2 V) dominated all top-20 rows. It is retained as a diagnostic,
  not the final corrected ranking. Final capped job 417562 produced **2,938/7,488 survivors** with
  zero gains relative to the old gate; its survivor set is a strict subset of the old set.

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
  DMSO remain at zero. Analysis 417563 removed GBL domination and produced PC/MeCN-led candidates;
  a standard-CSV serialization fix is pending one read-only rerun.

## Open scientific and engineering debt

1. The condition table is still sparse. Exact-salt/electrode coverage and quantitative ESW error
   analysis must expand; a conditioned formulation limit is not a universal solvent constant.
2. Regenerate analysis once with the standard-CSV shortlist fix; then inspect the 30 complete
   PC/MeCN-led triads without using an unsafe `comment='#'` parser.
3. The corrected three-dimer optical fit is route evidence only; it remains too small and
   ill-conditioned for scoring and needs the six experimental anchors/per-class expansion.
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

1. Re-run `eps analyze` on capped output with the standard-CSV fix and inspect shortlist/Pareto
   composition before recommendation.
2. Expand exact-formulation ESW and solubility anchors, then run the six-anchor/per-class optical
   calibration before considering any production score change.
3. Use those error analyses to choose the next 10-20 monomer Tier-2 pilot. Full-scale Tier-2 and
   expansion to ~100x30x25 remain the genuine PI/group resource-planning decision.

## Architecture invariants

See `AGENTS.md`: compute per species, never per triad; mock-first; CSV/YAML configuration;
SQLite cache; explicit units; run manifests for every run; mock results are never scientific data.

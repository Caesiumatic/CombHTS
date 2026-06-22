# Run: 2026-06-22 — openCOSMO-RS dGsolv expansion pilot (monomer × solvent grid)
- run_id: 2026-06-22_solvation-cosmors-pilot
- date: 2026-06-22
- command: `python -m eps.cli orca-pilot-solvation-grid --engine orca` (via `qsub scripts/run_solvation_cosmors_pilot.sge`)
- engine / method: ORCA 6.1/openCOSMO-RS 24a, BP86/def2-TZVPD; serial (nprocs 1)
- status: **prepared — awaiting submission** (human submits; this run was NOT submitted)
- scope: stratified 12-monomer × computable-solvent grid for **descriptor validation** of dGsolv,
  extending the 3-molecule MeCN pilot ([2026-06-22_orca-solvation-real-417544](2026-06-22_orca-solvation-real-417544.md)).
  - monomers (12, stratified by chemistry): thiophene, pyrrole, furan, selenophene, EDOT, EDOP,
    3-hexylthiophene, bithiophene, aniline, carbazole, CPDT, 3-methoxythiophene
  - solvents COMPUTED (ORCA built-in openCOSMO-RS): acetonitrile, nitromethane, water (control)
  - solvents DEFERRED (no built-in COSMORS profile in ORCA 6.1.0-418; need custom solvent
    sigma-profile): propylene carbonate, NMP
- computed-vs-cached-vs-needed (pre-flight plan):
  - cached (reused from pilot, MeCN): 3 — thiophene, EDOT, pyrrole
  - to-compute: 33 = (12 × 3 built-in solvents) − 3 cached
  - deferred / needed but not computable here: 24 = 12 × {propylene carbonate, NMP}
  - total grid intent: 60 (monomer × solvent) points
- config: [`configs/solvation_cosmors_pilot.yaml`](../../configs/solvation_cosmors_pilot.yaml)
- SGE script: [`scripts/run_solvation_cosmors_pilot.sge`](../../scripts/run_solvation_cosmors_pilot.sge)
  (serial; seeds a fresh cache by copying the pilot cache so the 3 MeCN points are reused and the
  pilot artifacts stay untouched)
- analysis script: [`scripts/analyze_solvation_cosmors_pilot.py`](../../scripts/analyze_solvation_cosmors_pilot.py)
- output artifacts (paths, NOT committed): Lop `$HOME/CombHTS/outputs/solvation_cosmors_pilot/`
  — `solvation_grid_points.csv`, `solvation_grid_plan.csv`, `cache.sqlite`, `raw/`,
  and (post-analysis) `solvation_grid_pivot.csv` + `solvation_grid_summary.{json,md}`
- cache path: `$HOME/CombHTS/outputs/solvation_cosmors_pilot/cache.sqlite`
  (seeded from `$HOME/CombHTS_pilot_work/outputs/orca_solvation_pilot/cache.sqlite`)
- qsub command (human submits; NOT submitted here):
  `cd $HOME/CombHTS && git checkout calib/solubility-cosmors && qsub scripts/run_solvation_cosmors_pilot.sge`
- provenance: branch `calib/solubility-cosmors`; ORCA module `6.1.0-418`; serial fallback
- caveats: **descriptor-validation pilot, NOT a solubility calibration.** dGsolv is a solvation
  free energy; it omits lattice/fusion, concentration, aggregation, protonation, and salt
  compatibility (see [solubility_descriptor_status.md](../lit_curation/solubility_descriptor_status.md)).
  **The Tier-1 20% solubility axis is UNCHANGED** by this work; the docs note recommends only.
- supersedes / superseded_by: extends `2026-06-22_orca-solvation-real-417544` (does not supersede it)

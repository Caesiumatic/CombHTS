# Run: 2026-06-22 — analyze salt-role-fixed Tier-1 ranking (none)

- run_id: `2026-06-22_analyze-salt-fixed-417571`
- date: 2026-06-22 14:57 CDT
- command: `HARVEST=outputs/tier1_real_7488_salt_fixed/tier1_all.csv ANALYSIS_OUTDIR=outputs/tier1_real_7488_salt_fixed/analysis qsub scripts/run_analyze.sge` (absolute SGE log path supplied at submission)
- engine / method: none; read-only analysis
- scope: 7,488 triads / 2,143 full per-salt survivors / 1,127 ranked score-classes
- cluster job: SGE 417571; `compute-0-11.local`; wall 44 s; exit 0
- status: completed
- headline results: diagnostic top-30 contains 30 distinct `(monomer, solvent, anion, exact-score)` classes: 19 propylene carbonate (63.3%), 6 MeCN (20.0%), 3 nitromethane (10.0%), and 2 NMP (6.7%). AgClO4 and HClO4 occur neither as representatives nor inside `salts_tied`. The old raw shortlist was 24 PC / 6 MeCN (80% PC) but only 14 distinct classes; all 14 remain in the new top-30 (the leading 14 are 8 PC / 6 MeCN), followed by 16 newly visible lower-ranked classes. Thus the audit's ~57% PC estimate applies exactly to the old 14-class subset; the realized distinct top-30 is 63.3% PC after extending to 30 classes.
- per-property failures: read-only carry-through; no new calculations. Report-only source failures remain secondary monomer 7,488, ion pair 3,744, solvent cathodic/secondary solvent 576 each.
- output artifacts (paths, NOT committed): `outputs/tier1_real_7488_salt_fixed/analysis/summary.csv`, `shortlist.csv`, six PNGs, provenance JSON, `analyze.sge.log`
- provenance: git commit `f41459dd7075d8cec489f59ea27268d033c3d771`; same config hashes as run 417569. Provenance dirty flag is from pre-existing untracked Lop files, not tracked-code drift.
- caveats: representative salt names are deterministic presentation labels (eligible supporting row, then alphabetic salt), not a learned cation preference. The shortlist remains screening-grade and is not an experimental order list.
- supersedes / superseded_by: supersedes the salt-permutation presentation in `2026-06-22_analyze-capped-esw-standard-417564`; —

## Distinct diagnostic top-30

| rank | monomer | solvent | anion | representative | salts tied | n | score |
| ---: | --- | --- | --- | --- | --- | ---: | ---: |
| 1 | terfuran | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.684005 |
| 2 | terfuran | PC | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.648628 |
| 3 | o-methoxyaniline | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.647676 |
| 4 | terfuran | PC | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.642396 |
| 5 | terthiophene | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.631062 |
| 6 | fluorene 9,9-dioctyl | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.624229 |
| 7 | diphenylamine | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.610910 |
| 8 | bifuran | MeCN | BF4 | TBABF4 | TBABF4 | 1 | 0.609075 |
| 9 | fluorene 9,9-dioctyl | PC | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.596284 |
| 10 | terthiophene | PC | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.590318 |
| 11 | fluorene 9,9-dioctyl | PC | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.590052 |
| 12 | terthiophene | PC | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.584086 |
| 13 | terfuran | PC | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.576085 |
| 14 | bifuran | PC | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.570522 |
| 15 | bifuran | PC | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.564290 |
| 16 | benzothiadiazole-thiophene D-A | PC | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.558928 |
| 17 | benzothiadiazole-thiophene D-A | PC | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.552696 |
| 18 | terfuran | PC | OTf | TBAOTf | TBAOTf | 1 | 0.552692 |
| 19 | fluorene 9,9-dioctyl | nitromethane | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.552650 |
| 20 | fluorene 9,9-dioctyl | nitromethane | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.547423 |
| 21 | fluorene 9,9-dioctyl | PC | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.523741 |
| 22 | terthiophene | PC | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.517776 |
| 23 | fluorene 9,9-dioctyl | PC | OTf | TBAOTf | TBAOTf | 1 | 0.500348 |
| 24 | bifuran | PC | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.497980 |
| 25 | terthiophene | PC | OTf | TBAOTf | TBAOTf | 1 | 0.494382 |
| 26 | benzothiadiazole-thiophene D-A | PC | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.486385 |
| 27 | terfuran | NMP | BF4 | LiBF4 | LiBF4; TBABF4 | 2 | 0.482281 |
| 28 | fluorene 9,9-dioctyl | nitromethane | TFSI | LiTFSI | LiTFSI; TBATFSI | 2 | 0.478512 |
| 29 | terfuran | NMP | ClO4 | LiClO4 | LiClO4; NaClO4; TBAClO4 | 3 | 0.476400 |
| 30 | bifuran | PC | OTf | TBAOTf | TBAOTf | 1 | 0.474586 |

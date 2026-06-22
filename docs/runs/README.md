# Run manifests

`outputs/` is gitignored, so run artifacts (harvest CSVs, calibration reports, plots, caches) never enter the repo and heavy files stay on the cluster. These manifests carry the **facts** of each run — engine, scope, job id, status, headline numbers, output paths, provenance, caveats — into version control so the run history is reviewable without the artifacts. One file per run, from [TEMPLATE.md](TEMPLATE.md); always state the engine explicitly (mock vs real) and never present a mock smoke as a scientific result.

| date | label | engine | scope | status | headline | manifest |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-22 | sTDA/TDA serial pilot | ORCA 6.1 real | 3 dimers x 2 methods | completed ORCA / invalid initial sTDA postprocess | SGE 417545 exit 0; corrected raw fit R2=.770/MAE=.097 eV; parser fixed locally, cluster rerun pending | [link](2026-06-22_orca-optical-real-417545.md) |
| 2026-06-22 | openCOSMO-RS serial pilot | ORCA 6.1 real | 3 monomers in MeCN | completed | SGE 417544; 3/3; dGsolv -4.13/-7.91/-6.98 kcal/mol | [link](2026-06-22_orca-solvation-real-417544.md) |
| 2026-06-22 | openCOSMO-RS parallel diagnostic | ORCA 6.1 real | 3 monomers in MeCN | failed | SGE 417542; OpenMPI/hwloc crash; 0 values cached | [link](2026-06-22_orca-solvation-real-417542.md) |
| 2026-06-22 | sTDA/TDA parallel diagnostic | ORCA 6.1 real | 3 dimers x 2 methods | failed | SGE 417543; OpenMPI/hwloc crash; 0 values cached | [link](2026-06-22_orca-optical-real-417543.md) |
| 2026-06-22 | openCOSMO-RS first attempt | ORCA 6.1 real | 3 monomers in MeCN | failed | SGE 417540; 0/3; raw-output retention added next | [link](2026-06-22_orca-solvation-real-417540.md) |
| 2026-06-22 | sTDA/TDA first attempt | ORCA 6.1 real | 3 dimers x 2 methods | failed | SGE 417541; ORCA exit 139; raw-output retention added next | [link](2026-06-22_orca-optical-real-417541.md) |
| 2026-06-22 | openCOSMO-RS route smoke | mock | 3 monomers in MeCN | completed | 3/3 mock-trivial; NON-PHYSICAL | [link](2026-06-22_orca-solvation-mock-smoke.md) |
| 2026-06-22 | sTDA/TDA route smoke | mock | 3 dimers x 2 methods | completed | 3/3 mock-trivial; NON-PHYSICAL | [link](2026-06-22_orca-optical-mock-smoke.md) |
| 2026-06-21 | Tier-1 harvest (REAL xTB) | gfn2-xtb | 36×13×16 = 7,488 | completed | SGE 417538 exit 0; 4,078/7,488 pre-new-ESW survivors; core stages 0 failures; must re-score with measured-first gate | [link](2026-06-21_tier1-harvest-real-7488.md) |
| 2026-06-19 | DFT calibration (gas-phase v1) | b3lyp/6-31G(d,p) gas | 22-monomer cal set | completed (exit 0) | SGE 417442, 49.3h wall; Fit-1 R²0.918/MAE0.14eV, Fit-2 R²0.854/MAE0.119V, composed 0.657/−2.720 V (≤0.087 V vs pinned); thiophene flag | [link](2026-06-19_dftcal-417442-gasphase.md) |
| 2026-06-19 | Tier-1 harvest (MOCK) | mock-gfn2 | 36×13×16 = 7,488 | completed | 509 survivors; 0 failures (mock-trivial) — SMOKE ONLY | [link](2026-06-19_tier1-harvest-mock-7488.md) |
| 2026-06-18 | DFT calibration (SMD+Freq) | b3lyp/6-31G(d,p) SMD+Freq | ~22-monomer cal set | killed@wall | SGE 417297, exit 137 @24h after ~10 pts; no output | [link](2026-06-18_dftcal-417297-smd-freq.md) |
| 2026-06-18 | analyze §8 | n/a (read-only) | real-xTB harvest | completed (reported) | summary/shortlist/dist+Pareto PNGs; t-SNE skipped | [link](2026-06-18_analyze-s8.md) |
| 2026-06-16 | Tier-1 smoke (real xTB) | gfn2-xtb | 15×11×10 = 1,650 | completed | 1,273→1,007 survivors; 152 failures later resolved | [link](2026-06-16_tier1-smoke-xtb.md) |

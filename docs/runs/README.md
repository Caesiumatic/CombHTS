# Run manifests

`outputs/` is gitignored, so run artifacts (harvest CSVs, calibration reports, plots, caches) never enter the repo and heavy files stay on the cluster. These manifests carry the **facts** of each run — engine, scope, job id, status, headline numbers, output paths, provenance, caveats — into version control so the run history is reviewable without the artifacts. One file per run, from [TEMPLATE.md](TEMPLATE.md); always state the engine explicitly (mock vs real) and never present a mock smoke as a scientific result.

| date | label | engine | scope | status | headline | manifest |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-06-21 | Tier-1 harvest (REAL xTB) | gfn2-xtb | 36×13×16 = 7,488 | running | SGE 417538, Lop ib2, started 22:44; survivors/failures TBD; validated pinned agagcl_peak_strict_v3 | [link](2026-06-21_tier1-harvest-real-7488.md) |
| 2026-06-19 | DFT calibration (gas-phase v1) | b3lyp/6-31G(d,p) gas | 22-monomer cal set | completed (exit 0) | SGE 417442, 49.3h wall; Fit-1 R²0.918/MAE0.14eV, Fit-2 R²0.854/MAE0.119V, composed 0.657/−2.720 V (≤0.087 V vs pinned); thiophene flag | [link](2026-06-19_dftcal-417442-gasphase.md) |
| 2026-06-19 | Tier-1 harvest (MOCK) | mock-gfn2 | 36×13×16 = 7,488 | completed | 509 survivors; 0 failures (mock-trivial) — SMOKE ONLY | [link](2026-06-19_tier1-harvest-mock-7488.md) |
| 2026-06-18 | DFT calibration (SMD+Freq) | b3lyp/6-31G(d,p) SMD+Freq | ~22-monomer cal set | killed@wall | SGE 417297, exit 137 @24h after ~10 pts; no output | [link](2026-06-18_dftcal-417297-smd-freq.md) |
| 2026-06-18 | analyze §8 | n/a (read-only) | real-xTB harvest | completed (reported) | summary/shortlist/dist+Pareto PNGs; t-SNE skipped | [link](2026-06-18_analyze-s8.md) |
| 2026-06-16 | Tier-1 smoke (real xTB) | gfn2-xtb | 15×11×10 = 1,650 | completed | 1,273→1,007 survivors; 152 failures later resolved | [link](2026-06-16_tier1-smoke-xtb.md) |

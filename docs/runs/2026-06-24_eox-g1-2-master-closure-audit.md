# Run: 2026-06-24 - Eox G1.2 master closure audit (none / no-engine curation)

- run_id: 2026-06-24_eox-g1-2-master-closure-audit
- date: 2026-06-24
- command: `.venv/bin/python scripts/build_eox_g1_2_master_audit.py`
- engine / method: none; no chemistry engine, no mock engine, no xTB, no DFT, no quantum chemistry
- scope: review-only G1.2 Eox master closure audit across current production, R11-R21 staging, and prepared external evidence manifest
- cluster job: local only; no Lop access; no qsub/qstat/qacct
- status: completed
- headline results: 31 source-manifest rows; 86 master evidence rows; 83 directive-combination rows; 57 proposal rows; 31 directive-eligible combinations PASS vs >=30; 5 clean external Ag/AgCl onset additions proposed; 10 current Camarada production rows marked non-CV steady-state polarization evidence for future correction
- per-property failures: n/a
- output artifacts: `data/lit_curation/eox_g1_2_source_manifest.csv`; `data/lit_curation/eox_g1_2_master_evidence.csv`; `data/lit_curation/eox_g1_2_combination_summary.csv`; `data/lit_curation/eox_g1_2_production_change_proposal.csv`; `docs/research/eox_g1_2_master_closure_audit_20260624.md`
- provenance: git commit `87f62157e16a1e33baa73ff4504efed1e2863784` at preflight; external manifest hash `3698c8fae7dd7ffc0e85ad50dd73aaa352964ce4952551374decf4056e004075`; benchmark hash `572ecd8e4339fcd1e7bb31834f90ee5b4f7bf3690550e3f53ad2044d9b2fa6fe`; R11-R21 review hash `ed72def28074d34bee8db5fe16923fb3a2e1894654e8206d54ca20b06883ca2a`
- caveats: review-only closure audit; no row was promoted into `data/benchmark.csv`; PDFs/zips/extracted text remain outside git; no production scoring, thresholds, calibration coefficients, redox constants, production libraries, benchmark rows, cache keys, public schemas, Tier-1/Tier-2 settings, validation workflow, or optical policy changed
- supersedes / superseded_by: supersedes the R11-R21-only count basis for G1.2 closure review; superseded_by: -

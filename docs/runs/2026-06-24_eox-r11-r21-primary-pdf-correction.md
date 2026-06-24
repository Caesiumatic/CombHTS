# Run: 2026-06-24 - Eox R11-R21 primary-PDF staging correction (none / no-engine curation)

- run_id: 2026-06-24_eox-r11-r21-primary-pdf-correction
- date: 2026-06-24
- command: `.venv/bin/python scripts/build_eox_r11_r21_staging.py`
- engine / method: none; no chemistry engine, no mock engine, no xTB, no DFT, no quantum chemistry
- scope: primary-PDF staging correction for review-only R11-R21 Eox candidates
- cluster job: local only; no Lop access; no qsub/qstat
- status: completed
- headline results: 11 source rows loaded; 11/11 RDKit parsed; 11/11 conversion checks passed as working transcriptions; 3 PROMOTE_NOW_CANDIDATE; 8 NEEDS_REFERENCE_CHECK; 8 reference-source conflicts; 4 condition-source conflicts; 0 internal duplicates; 0 production benchmark duplicates
- per-property failures: n/a
- output artifacts: `data/lit_curation/eox_r11_r21_source_candidates.csv`; `data/lit_curation/eox_r11_r21_rescue_review.csv`; `docs/research/eox_r11_r21_staging_rescue_20260624.md`; `docs/research/eox_r11_r21_primary_pdf_correction_20260624.md`
- provenance: local main pre-change SHA `a5ae41b972bbc05a5ff41a9f59150a41b520b154`; normalized source CSV hash recorded in the regenerated staging report
- caveats: review-only staging correction; no source-internal conflict was resolved; no row was promoted into `data/benchmark.csv`; no production scoring, thresholds, calibration coefficients, redox constants, production libraries, benchmark rows, cache keys, public schemas, Tier-1/Tier-2 settings, or optical policy changed
- supersedes / superseded_by: supersedes the pre-primary-PDF-conflict R11-R21 staging-rescue disposition for ingest readiness; superseded_by: -

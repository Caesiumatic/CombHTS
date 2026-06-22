# Run: 2026-06-22 — salt-role Tier-1 re-score (none)

- run_id: `2026-06-22_tier1-rescore-salt-fixed-417569`
- date: 2026-06-22 14:56 CDT
- command: `RESCORE_INPUT=outputs/tier1_real_7488/tier1_all.csv RESCORE_OUTDIR=outputs/tier1_real_7488_salt_fixed qsub scripts/run_tier1_rescore.sge` (absolute SGE log path supplied at submission)
- engine / method: none; CSV-only measured-first/conservative ESW + supporting-electrolyte role gate + unchanged composite
- scope: existing real-GFN2-xTB 36 x 13 x 16 = 7,488-triad harvest; no Engine or SQLite cache opened
- cluster job: SGE 417569; `compute-1-12.local`; wall 21 s; exit 0
- status: completed
- headline results: 2,143/7,488 full per-salt survivors (28.619%), versus 2,938 under capped ESW alone; exactly 795 dropped and zero gained. Dropped prior survivors were HClO4 262, AgClO4 262, H2SO4 255, and pTSA 16 (CSA already had zero). All 2,143 common surviving rows retained byte-equivalent composite values (max absolute score change 0). The ranked presentation contains 1,127 exact score-classes; `n_tied` sums back to 2,143 (`n_tied=1`: 373 classes; 2: 492; 3: 262).
- per-property failures: core/scored failures unchanged from source; role gate passed zero acid/reference-only rows. Existing report-only failures remain source-harvest facts.
- output artifacts (paths, NOT committed): `outputs/tier1_real_7488_salt_fixed/tier1_ranked.csv`, `outputs/tier1_real_7488_salt_fixed/tier1_all.csv`, provenance JSON, `rescore.sge.log`
- provenance: git commit `f41459dd7075d8cec489f59ea27268d033c3d771`; `configs/tier1.yaml` SHA-256 `abfb074087cd057cdfb24b2d0c38af7d537ff71b468d9af192334c6491bb9c45`; `configs/scoring.yaml` SHA-256 `223fbb899b12b14b2db6050129117eca5de7329468ec8d296033b336c2875dee`. Provenance says dirty only because the Lop checkout had pre-existing untracked user files; tracked files were at the recorded commit.
- caveats: this reuses the existing real-xTB descriptors and changes only gate/presentation policy. It does not validate cation deposition, salt solubility, conductivity, ion pairing, or the uncalibrated composite axes.
- supersedes / superseded_by: applies the 417564 audit fix after `2026-06-22_tier1-rescore-capped-esw-417562`; analyzed by `2026-06-22_analyze-salt-fixed-417571`

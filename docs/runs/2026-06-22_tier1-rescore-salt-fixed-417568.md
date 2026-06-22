# Run: 2026-06-22 — salt-role Tier-1 re-score first submission (none)

- run_id: `2026-06-22_tier1-rescore-salt-fixed-417568`
- date: 2026-06-22 14:56 CDT
- command: `qsub -o outputs/tier1_real_7488_salt_fixed/rescore.sge.log -v RESCORE_INPUT=outputs/tier1_real_7488/tier1_all.csv,RESCORE_OUTDIR=outputs/tier1_real_7488_salt_fixed scripts/run_tier1_rescore.sge`
- engine / method: none; CSV-only re-score was requested but the script never started
- scope: intended existing real-GFN2-xTB 36 x 13 x 16 = 7,488-triad harvest
- cluster job: SGE 417568; no execution host/start time; wall 0 s
- status: failed before execution (`failed 26: opening input/output file`)
- headline results: no calculation or output; SGE resolved the relative `-o` path under `$HOME`, where the requested directory did not exist
- per-property failures: n/a; script never executed
- output artifacts (paths, NOT committed): none
- provenance: intended git commit `f41459d`; no program process started
- caveats: scheduler/log-path setup failure only; no result was generated or overwritten
- supersedes / superseded_by: superseded by `2026-06-22_tier1-rescore-salt-fixed-417569`

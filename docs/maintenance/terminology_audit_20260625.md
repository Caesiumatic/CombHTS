# Terminology Audit - 2026-06-25

## Scope

Command used:

```bash
rg -n -i 'placeholder|placeholder-contaminated|50k|50,000|dimer dication|dimer dications|all five axes|mock Tier-1|production-grade' README.md docs scripts src tests
```

Goal: update objectively stale current-state language while preserving historical records,
review-only curation wording, genuine mock/Tier-3 placeholder language, and no-touch optical
patch files.

## Fixed Current-State Hits

| File | Previous wording class | Action |
| --- | --- | --- |
| `src/eps/analysis/summary.py` | Current code docstring described analysis outputs as placeholder-contaminated. | Reworded to screening-grade / diagnostic-only soft-axis language. |
| `src/eps/analysis/summary.py` | Diagnostic note said "all five composite axes are now real physics." | Reworded to "all five composite axes now have real descriptor implementations" to avoid overclaiming. |
| `src/eps/analysis/plots.py` | Plotting docstring and comments referred to placeholder axes/warnings. | Reworded to diagnostic soft-axis language. |
| `src/eps/analysis/plots.py` and `tests/test_invariants.py` | Internal label constant used the stale placeholder name. | Renamed to `DIAGNOSTIC_LABEL` and updated tests. |
| `src/eps/cli.py` | `run-tier1` help implied the command was only a mock Tier-1 workflow. | Reworded help to say mock is the default and xTB is the real-run path. |
| `scripts/run_oligomer.sge` | Current scheduler-template comment referred to dimer dications. | Reworded to radical-coupling descriptors. |
| `src/eps/workflow/tier1.py` | Current docstring said the axes were no longer single-monomer placeholders. | Reworded to "single-monomer proxy" language. |

## Intentionally Retained Hits

| File or family | Classification | Reason retained |
| --- | --- | --- |
| `docs/overnight_report_20260618.md`, `docs/overnight_report_20260618_batch2.md`, `docs/step1_real_bandgap_dimerization_report.md` | Historical record | These documents record earlier work and should not be rewritten to newer terminology. |
| `docs/literature/deep_research_benchmark_finalization_20260616.md` | Historical/source-curation record | "Placeholder locator" describes curation state at that time. |
| `docs/research/eox_benchmark_finalization_review.md`, `docs/research/eox_benchmark_intermediate_review.md` | Review-only curation record | "Review placeholder" marks unresolved evidence and prevents silent back-fill. |
| `docs/research/section7_staging_audit_20260623.md` | Review/staging diagnostic | "Unconverted primary placeholder" identifies an unresolved staging row. |
| `docs/research/library_expansion_proposal.md` | Future directive scale planning | `~50k` refers to the eventual target-scale proposal, not the current 7,488-triad library. |
| `docs/research/solvent_windows_and_solvation_reference.md` | Scientific caveat | "Placeholder" correctly describes crude continuum/Abraham estimates or staging descriptors. |
| `src/eps/validation/memo.py` | Mock-output honesty language | Mock calibration numbers are still nonphysical placeholders by design. |
| `src/eps/workflow/tier3.py` | Optional hook language | Tier-3 optional methods remain documented placeholders that do not run. |
| `docs/code_structure.md` | Current architecture map | Tier-3 optional hooks are correctly described as placeholders to avoid production-readiness claims. |
| `src/eps/engines/xtb.py` | Excluded no-touch optical patch file | This work unit explicitly forbids editing `src/eps/engines/xtb.py`; the hit is recorded for the separate optical correctness task. |

## Ambiguous Or Deferred

No additional ambiguous hits required scientific review in this pass. The only source hit that
would normally merit current-code cleanup was in `src/eps/engines/xtb.py`, and it was deferred
solely because that file is part of the active no-touch optical patch surface.

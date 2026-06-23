# Pre-Cleanup Merge Report — 2026-06-23

## Summary

- Base SHA observed before integration: `e7e8c3967d9bf5fefb0e191722197ed0af136b41`
- `origin/main` SHA after `git fetch origin --prune`: `e7e8c3967d9bf5fefb0e191722197ed0af136b41`
- Integration branch: `integration/pre-cleanup-merge-20260623`
- Last source-branch merge commit before this report: `e3626d925199b2d7c4c01576f7ed6e755c250b05`
- Main updated: no. Only the integration branch was prepared.

## Branches Discovered

| branch | local | remote | pre-merge classification | result |
| --- | --- | --- | --- | --- |
| `feat/section7-validation-closure` | yes | `origin/feat/section7-validation-closure` | `MERGE_NOW` | merged |
| `research/section7-staging-audit` | yes | `origin/research/section7-staging-audit` | `MERGE_NOW` | merged |
| `feat/tier2-pilot-orchestration` | yes | `origin/feat/tier2-pilot-orchestration` | `MERGE_NOW` | merged |

Related-name discovery for `section7`, `validation`, `staging`, `tier2`, `orchestration`,
`hygiene`, and `codebase` found no additional completed candidate branches beyond the three above.
After integration, all three candidate branches are contained in `HEAD`.

## Branch Inspection

- `feat/section7-validation-closure`: two commits. Added `eps validate-directive`, an xTB-only SGE
  template, directive validation outputs/reporting code, tests, and run manifest
  `docs/runs/2026-06-23_directive-section7-validation-417671.md`. No production data/config/scoring
  policy changes.
- `research/section7-staging-audit`: one commit. Added review-only staging audit scripts, tests,
  report, and `data/lit_curation/` audit/review tables. It did not promote staging rows into
  production CSVs.
- `feat/tier2-pilot-orchestration`: one commit. Added mock-first Tier-2 plan/run-task/harvest
  orchestration, SGE templates, Gaussian-engine robustness metadata, and tests. No real Gaussian
  job submission and no Tier-2 scientific values.

## Conflicts

- `feat/section7-validation-closure`: no conflicts.
- `research/section7-staging-audit`: conflicts in `CHANGELOG.md` and `STATUS.md`.
  Resolution preserved the 417587 diagnostic-only conclusion and 417671 validation facts, added
  staging-audit facts as review/staging-only, and did not promote production data.
- `feat/tier2-pilot-orchestration`: conflicts in `CHANGELOG.md`, `STATUS.md`, and
  `scripts/README.md`; `src/eps/cli.py` auto-merged. Resolution preserved all CLI commands,
  including `validate-directive`, `tier2-plan`, `tier2-run-task`, `tier2-harvest`, and
  `tier2-screen`; `scripts/README.md` keeps both validation and Tier-2 template notes.
- Pre-existing staged duplicate staging-audit state on `feat/tier2-pilot-orchestration` was saved
  as `stash@{0}` before creating the integration branch. The integrated branch history used the
  actual `research/section7-staging-audit` branch, not that stash.

## Files Changed By Category

- Current-state docs: `STATUS.md`, `CHANGELOG.md`, `THINK.md`.
- Run records: `docs/runs/README.md`,
  `docs/runs/2026-06-23_directive-section7-validation-417671.md`.
- Maintenance/research docs: `docs/maintenance/pre_cleanup_merge_report_20260623.md`,
  `docs/research/section7_staging_audit_20260623.md`, `scripts/README.md`.
- Staging/review data only: `data/lit_curation/eox_gapfill_candidates.csv`,
  `data/lit_curation/esw_promotion_candidates.csv`,
  `data/lit_curation/esw_remaining_gap_matrix.csv`,
  `data/lit_curation/library_waveA_readiness_candidates.csv`,
  `data/lit_curation/polymerizability_promotion_candidates.csv`,
  `data/lit_curation/staging_audit_issues.csv`,
  `data/lit_curation/staging_audit_summary.csv`.
- Scripts/templates: `scripts/audit_lit_curation_staging.py`,
  `scripts/run_validate_directive.sge`, `scripts/run_tier2_pilot_array.sge`,
  `scripts/run_tier2_pilot_harvest.sge`.
- Source code: `src/eps/cli.py`, `src/eps/engines/gaussian.py`,
  `src/eps/validation/__init__.py`, `src/eps/validation/directive.py`,
  `src/eps/validation/feasibility.py`, `src/eps/workflow/tier2.py`.
- Tests: `tests/test_gaussian.py`, `tests/test_lit_curation_audit.py`,
  `tests/test_tier2_pilot.py`, `tests/test_validate_directive.py`.

## Forbidden-File Audit

No unexpected forbidden files changed. Explicit audit of these paths returned no diffs:

- `configs/scoring.yaml`
- `configs/tier1.yaml`
- `configs/calibration_profiles.yaml`
- `data/benchmark.csv`
- `data/solvent_windows.csv`
- `data/polymerizability_labels.csv`
- `data/monomers.csv`
- `data/solvents.csv`
- `data/electrolytes.csv`
- `src/eps/redox.py`

No scoring weights, Tier-1 thresholds, calibration coefficients, redox constants, optical policy,
output schemas, production CSVs, or cache-key semantics were changed by the integration.

## Verification

After merging `feat/section7-validation-closure`:

- `.venv/bin/python -m pytest -q`: `224 passed, 5 skipped, 2 warnings`
- `.venv/bin/ruff check src tests`: passed
- `git diff --check`: passed

After merging `research/section7-staging-audit`:

- `.venv/bin/python -m pytest -q`: `227 passed, 5 skipped, 2 warnings`
- `.venv/bin/ruff check src tests`: passed
- `git diff --check`: passed

After merging `feat/tier2-pilot-orchestration`:

- `.venv/bin/python -m pytest -q`: `238 passed, 5 skipped, 2 warnings`
- `.venv/bin/ruff check src tests`: passed
- `git diff --check`: passed
- `bash -n scripts/run_validate_directive.sge scripts/run_tier2_pilot_array.sge scripts/run_tier2_pilot_harvest.sge`: passed

No-real-engine CLI smoke:

- `.venv/bin/python -m eps.cli --help`: passed
- `.venv/bin/python -m eps.cli validate --engine mock`: passed; mock output is non-scientific
- `.venv/bin/python -m eps.cli analyze --help`: passed
- `.venv/bin/python -m eps.cli tier2-plan --help`: passed
- `.venv/bin/python -m eps.cli validate-directive --help`: passed
- `.venv/bin/python -m eps.cli doctor`: passed with 0 FAIL and 4 expected local WARNs for
  cluster-only binaries (`xtb`, `g16`, `orca`, Tier-2 `g16`)

Final pre-commit verification after report/documentation/governance sync:

- `.venv/bin/python -m pytest -q`: `238 passed, 5 skipped, 2 warnings`
- `.venv/bin/ruff check src tests`: passed
- `git diff --check`: passed
- Conflict-marker scan over merge-touched docs and `src/eps/cli.py`: clean

## Remaining Issues

- No unresolved merge issue remains.
- Scientific debts remain as recorded in `STATUS.md`: sparse exact ESW formulation coverage,
  underpowered feasibility labels, diagnostic-only optical/dimerization/solvation-affinity axes,
  no held-out Tier-2 DFT validation, and library size below directive scale.
- No item in this merge meets `ESCALATE_PI`. The only retained PI/group item is future resource
  planning for large shared-cluster Tier-2/full-scale work.

## Cleanup Recommendation

Proceed to codebase cleanup from this integration branch after the final report/docs commit and
push. Cleanup should not alter scoring/config/calibration/production data unless opened as a
separate reviewed task.

Explicit negative controls for this merge:

- No quantum engines were run.
- No Lop jobs were submitted.
- No heavy outputs, caches, or raw quantum logs were inspected or committed.
- 417587 remains diagnostic-only.

# Codebase Review and Safe Hygiene Report - 2026-06-23

## Scope

This was a no-engine static review and low-risk hygiene/documentation pass starting from
`integration/pre-cleanup-merge-20260623` at
`16ff3ec0b826682a7ccbe57357d68116a95aa722`. The work reviewed the integrated Section 7
validation, staging-audit, and Tier-2 pilot orchestration state; added a maintainer-facing code
structure map; and synchronized project status/history documentation. It did not inspect Lop,
submit jobs, run xTB/Gaussian/ORCA/openCOSMO-RS, or reinterpret optical job 417587.

## Repo State

| Item | Observed value |
| --- | --- |
| Working branch | `chore/codebase-map-and-hygiene` |
| Cleanup base SHA | `16ff3ec0b826682a7ccbe57357d68116a95aa722` |
| `origin/main` SHA | `e7e8c3967d9bf5fefb0e191722197ed0af136b41` |
| `origin/integration/pre-cleanup-merge-20260623` SHA | `16ff3ec0b826682a7ccbe57357d68116a95aa722` |
| Current branch HEAD before this pass | `16ff3ec0b826682a7ccbe57357d68116a95aa722` |
| `stash@{0}` | Present: `On feat/tier2-pilot-orchestration: pre-cleanup-duplicate-staging-audit-staged-state` |
| Merged work present | Yes: Section 7 validation closure, Section 7 staging audit, and Tier-2 pilot orchestration are visible in docs, source, scripts, and tests. |

The checkout was clean before edits. `stash@{0}` was not popped, applied, dropped, or overwritten.

## Findings Table

| ID | Area | Severity | Type | Finding | Evidence | Action taken | Recommended follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CBR-001 | Repository map | MEDIUM | docs | The integrated repo now has enough workflows that a maintainer map is needed to prevent accidental policy/schema drift. | `src/eps/cli.py` exposes Tier-1, validation, ORCA pilots, Tier-2, Tier-3, analysis, and doctor commands; docs/run records are spread across several directories. | Added `docs/code_structure.md`. | Keep the map current when adding public workflows or changing data/config ownership. |
| CBR-002 | Python hygiene | INFO | maintainability | The previously reported `ruff` I001 import-ordering debt in `tests/test_orca_pilots.py` is already fixed on the integrated branch. | `tests/test_orca_pilots.py` imports are sorted; `.venv/bin/ruff check src tests` passed before edits. | No Python change needed. | None for I001; continue running ruff before commits. |
| CBR-003 | CLI organization | MEDIUM | maintainability | `src/eps/cli.py` is large and mixes parser setup, dispatch, and text formatting. | Function scan shows all command parsers and dispatch in one file, with command handling through roughly line 1100. | Deferred; splitting CLI is outside this pass and could accidentally change public command behavior. | Later split into command modules with compatibility tests for command names/defaults/help text. |
| CBR-004 | Validation modules | LOW | maintainability | `eps.validation.directive` is broad because it now owns Section 7 metric generation, rendering, bootstrap helpers, and provenance shaping. | The file contains `run_directive_validation` plus many helpers for Eox, ESW, feasibility, reports, JSON, and provenance. | Deferred; documented as engineering debt. | Extract pure table/render/bootstrap helpers after adding report-shape tests. |
| CBR-005 | Run/provenance records | LOW | docs | Run facts are well recorded but manually maintained, so future drift is possible. | `docs/runs/README.md` indexes many real/mock runs with varied caveat detail. | Documented the run-manifest convention in `docs/code_structure.md`. | Add a lightweight manifest lint/check script. |
| CBR-006 | Scientific no-touch | INFO | scientific-risk | Current scientific conclusions must remain stable: 417587 is diagnostic-only; no scoring/config/calibration/production-data change is authorized. | `STATUS.md`, `docs/runs/README.md`, and the pre-cleanup merge report all record this state. | No scientific files or formulas were edited. | Keep scientific policy edits in separate reviewed tasks. |
| CBR-007 | Staging audit | LOW | docs | Staging curation is integrated and useful but must stay distinct from production data. | `data/lit_curation/*` contains review tables; production CSVs remain separate. | Documented staging vs production ownership. | Future production ingest should have its own source-check and forbidden-file audit. |
| CBR-008 | Tier-2 pilot | LOW | tests | Tier-2 orchestration has strong unit coverage, but a future no-engine fixture smoke across plan/run/harvest would lower regression risk. | `tests/test_tier2_pilot.py` exists; plan/run/harvest are now public CLI commands. | Deferred; no behavior change needed. | Add a small CLI-level smoke using mock tasks and temporary output roots. |

## Safe Fixes Applied

| File | Change | Why behavior-preserving |
| --- | --- | --- |
| `docs/code_structure.md` | Added maintainer map for package layout, workflows, data/config ownership, engine/cache contract, scientific axes, and no-touch boundaries. | Documentation only. |
| `docs/maintenance/codebase_review_20260623.md` | Added this review report with repo state, findings, deferred refactors, no-touch items, and follow-up recommendations. | Documentation only. |
| `README.md` | Added a concise link to the new code-structure map and removed one stale trailing space in references. | Documentation only. |
| `STATUS.md` | Synchronized the current snapshot to mention the new maintainer map/review and that ruff I001 is closed. | Documentation only; scientific status preserved. |
| `CHANGELOG.md` | Prepended a concise entry for the codebase map and low-risk hygiene pass. | Documentation only; append-only history preserved by prepending. |

No Python source, tests, production CSVs, scoring/config YAML values, redox constants, cache logic,
output schemas, or optical policy were changed.

## Deferred Refactors

- Split `src/eps/cli.py` into subcommand modules while preserving public CLI names, defaults, and
  help text.
- Reorganize workflow modules only where it removes real duplication; preserve existing imports and
  output schemas.
- Consolidate data/schema documentation for CSV inputs and generated output CSVs.
- Extract directive-validation utility helpers for rendering, bootstrap intervals, JSON safety, and
  provenance records after adding report-shape tests.
- Package reusable audit/code-generation helpers currently living in `scripts/`.
- Add a run-manifest linter for engine/scope/status/qacct/provenance/caveat completeness.
- Add CLI-level no-engine fixture tests for Tier-2 plan/run/harvest and directive-validation help
  or report shape.

## Scientific No-Touch Items

Intentionally not touched:

- scoring weights and component directions;
- Tier-1 thresholds and calibration coefficients;
- calibration profile definitions;
- filters and measured-first solvent gate policy;
- production data CSVs;
- benchmark CSVs;
- redox constants and conversion formulas;
- cache keys and generated output schemas;
- optical-axis policy and the diagnostic-only conclusion for 417587;
- solvent gate policy and salt-role gate behavior.

## Suggested Next Cleanup Tasks

1. Add a no-engine CLI smoke test for Tier-2 plan/run-task/harvest using a tiny temporary selection
   and mock task result.
2. Add a manifest lint/check script for `docs/runs/` and wire it into documentation hygiene checks.
3. Split `src/eps/cli.py` into parser/dispatch modules with golden help-text or parser-default
   regression tests.
4. Extract pure helpers from `eps.validation.directive` after locking report/JSON schemas in tests.
5. Create a concise output-schema/data-dictionary doc for Tier-1, directive validation, Tier-2, and
   analysis artifacts.
6. Add a `docs/maintenance/README.md` index once there are multiple maintenance reports.
7. Move reusable staging-audit logic into importable helper modules while keeping the script entry
   point stable.
8. Add a production-ingest checklist template for future staged data promotion tasks.

## Validation

Validation was run after edits:

- `.venv/bin/python -m pytest -q`: `238 passed, 5 skipped, 2 warnings`.
- `.venv/bin/ruff check src tests`: passed.
- `git diff --check`: passed.
- `.venv/bin/python -m eps.cli doctor`: `21 checks, 0 FAIL, 4 WARN`; the warnings are the
  expected local cluster-only binary warnings for `xtb`, `g16`, `orca`, and Tier-2 `g16`.
- `.venv/bin/python -m eps.cli --help`: passed.
- `.venv/bin/python -m eps.cli validate --engine mock`: passed and wrote the expected gitignored
  mock validation report/provenance under `outputs/`; this is non-physical smoke evidence only.
- `.venv/bin/python -m eps.cli validate-directive --help`: passed.
- `.venv/bin/python -m eps.cli analyze --help`: passed.
- `.venv/bin/python -m eps.cli tier2-plan --help`: passed.
- `.venv/bin/python -m eps.cli tier2-harvest --help`: passed.

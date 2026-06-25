# Module Decomposition Plan - 2026-06-25

This is a plan only. No module movement, import-path change, or command split was implemented in
this work unit. Future extraction depends on the contract tests added for CLI behavior, Tier-1
schemas, and Section-7 artifacts.

## Current Line Counts

| Module | Lines |
| --- | ---: |
| `src/eps/cli.py` | 1,199 |
| `src/eps/validation/directive.py` | 1,409 |
| `src/eps/curation/eox_master_audit.py` | 1,947 |

## Shared Extraction Rules

- Preserve public CLI command names, defaults, required arguments, and return codes.
- Preserve required artifact filenames and column families in `docs/output_contracts.md`.
- Add compatibility shims before moving imports.
- Extract pure helpers before orchestration.
- Keep scientific policy in CSV/YAML/data, not hidden in new orchestration modules.
- Every PR must pass ruff, contract tests, targeted workflow tests, full pytest, doctor, and
  `git diff --check`.
- Rollback must be a simple revert of the extraction PR without data/config migration.

## `src/eps/cli.py`

### Current Public Entry Points

- `build_parser()`
- `main(argv=None)`

### Internal Groups

- engine builders: `_engine_from_name`, `_dft_calibration_engines`;
- provenance/disclosure printing: `_stamp_provenance`, `_print_calibration_disclosure`;
- parser construction for all subcommands;
- dispatch branches for Tier-1, rescore, validation, directive validation, DFT calibration, ORCA
  pilots, sanity, memo, analyze, Tier-2, Tier-3, and doctor;
- formatting helpers for validation output.

### Practical Dependency Graph

`main` depends on parser args, engine builders, workflow functions, validation functions, doctor,
provenance, and output formatting helpers. The parser and dispatch are currently coupled because
the command strings in `build_parser()` must match the `if args.command == ...` branches.

### Shared State And Constants

Most defaults are imported from workflow/validation modules. `DEFAULT_ANALYSIS_OUTDIR` is defined
locally. Parser command names are public interface state.

### Output Schemas

CLI output is terminal text plus files written by downstream workflow modules. `eps validate`
also now prints calibration operational disclosure before metrics.

### Existing Tests

- `tests/test_cli_contracts.py` locks subcommand set, required args, critical defaults, invalid
  command behavior, and help availability.
- Workflow-specific tests cover downstream functions called by dispatch branches.
- `tests/test_calibration_operational.py` covers validation disclosure for `eps validate`.

### Missing Contract Tests

- CLI no-engine smoke for every command that can run without external artifacts.
- Exact return-code tests for file-missing branches.
- Tier-2 plan/run/harvest end-to-end CLI fixture.
- ORCA pilot help/default contract tests.

### Low-Risk Boundaries

1. Move formatting helpers into `eps.cli_format`.
2. Move engine builder helpers into `eps.cli_engines`.
3. Move parser construction into `eps.cli_parser` while keeping `eps.cli.build_parser` as a shim.
4. Move command handlers one family at a time into `eps.commands.<family>`.

### High-Risk Boundaries

- Splitting parser and dispatch without tests for every command identity.
- Changing imported default constants or default path objects.
- Rewording operational disclosure in a way tests/users cannot recognize.
- Moving validation/doctor logic into CLI-only modules.

### Proposed Target Layout

```text
eps/cli.py                 # build_parser/main shims only
eps/cli_parser.py          # parser construction
eps/cli_format.py          # terminal formatting helpers
eps/cli_engines.py         # engine builders
eps/commands/tier1.py
eps/commands/validation.py
eps/commands/orca_pilots.py
eps/commands/tier2.py
eps/commands/tier3.py
eps/commands/doctor.py
```

### Staged PR Order

1. Extract formatting helpers.
2. Extract engine builders.
3. Extract parser construction with shim.
4. Extract `doctor` handler.
5. Extract `validate` / `validate-directive` handlers.
6. Extract Tier-2 handlers.
7. Extract remaining workflow handlers.

### Rollback

Each PR should leave `eps.cli.main` and `eps.cli.build_parser` intact. Rollback is reverting the
single extraction PR.

## `src/eps/validation/directive.py`

### Current Public Entry Points

- `DirectiveValidationResult`
- `run_directive_validation(...)`

### Internal Groups

- orchestration and artifact writing;
- Eox profile execution and point construction;
- applicability-domain audit;
- ESW descriptor comparison;
- ESW gate diagnostics;
- feasibility matching and bootstrap intervals;
- directive metric table;
- Markdown rendering;
- profile summary row builders;
- stats helpers: LOO, linear influence, bootstrap, coverage, finite/format helpers;
- provenance and JSON helpers.

### Practical Dependency Graph

`run_directive_validation` coordinates all sections, then delegates to Eox, ESW, feasibility,
metric-table, provenance, JSON, and report-render helpers. It imports benchmark validation,
solvent benchmark loading, feasibility metric code, Tier-1 conformer config, provenance helpers,
and production library loaders.

### Shared State And Constants

Constants include default output/cache paths, bootstrap seed/replicates, reference floor, numeric
tolerance, feasibility minimum matched count, and status labels. These are reporting/validation
contract state and must be carried forward unchanged unless explicitly reviewed.

### Output Schemas

Required artifacts:

- `validation_summary.json`
- `validation_report.md`
- `eox_profile_summary.csv`
- `eox_points.csv`
- `esw_descriptor_points.csv`
- `esw_gate_diagnostics.csv`
- `feasibility_matches.csv`
- `provenance.json`

Column and top-level JSON contracts are documented in `docs/output_contracts.md` and covered by
`tests/test_output_contracts.py`.

### Existing Tests

- `tests/test_validate_directive.py` covers deterministic output, missing harvest behavior,
  feasibility matching, applicability-domain boundaries, ESW safety, bootstrap reproducibility, and
  solvent descriptor behavior.
- `tests/test_output_contracts.py` locks required artifact filenames and required columns.

### Missing Contract Tests

- Empty solvent benchmark path with real artifact shape.
- Active profile source mismatch in directive context.
- Markdown report section-order smoke.
- Provenance hash-missing behavior for optional paths.

### Low-Risk Boundaries

1. Extract pure numeric/stat helpers into `eps.validation.stats`.
2. Extract JSON/provenance helpers into `eps.validation.directive_provenance`.
3. Extract Markdown rendering into `eps.validation.directive_report`.
4. Extract ESW gate diagnostics into `eps.validation.directive_esw`.
5. Extract feasibility packaging into `eps.validation.directive_feasibility`.
6. Extract Eox profile packaging into `eps.validation.directive_eox`.

### High-Risk Boundaries

- Moving `run_directive_validation` orchestration before artifact contracts are locked.
- Changing profile active/default semantics.
- Changing bootstrap seeds or reference-floor wording.
- Changing CSV column names or JSON top-level keys.

### Proposed Target Layout

```text
eps/validation/directive.py              # public dataclass + orchestration shim
eps/validation/directive_eox.py
eps/validation/directive_esw.py
eps/validation/directive_feasibility.py
eps/validation/directive_report.py
eps/validation/directive_provenance.py
eps/validation/stats.py
```

### Staged PR Order

1. Extract stats helpers with direct unit tests.
2. Extract report rendering with golden section smoke tests.
3. Extract provenance/JSON helpers.
4. Extract ESW diagnostics.
5. Extract feasibility packaging.
6. Extract Eox profile packaging.
7. Leave `run_directive_validation` as the stable top-level orchestrator until all consumers are
   updated.

### Rollback

Keep imports re-exported from `eps.validation.directive`. Rollback is a PR revert because no data
or config migration should be involved.

## `src/eps/curation/eox_master_audit.py`

### Current Public Entry Points

- `EoxMasterAuditResult`
- `build_eox_g1_2_master_audit(...)`
- `load_external_manifest(...)`
- `build_source_manifest(...)`
- `build_master_evidence(...)`
- `validate_master_evidence_schema(...)`
- `validate_master_enums(...)`
- `build_combination_summary(...)`
- `build_production_change_proposal(...)`
- `summarize_master_audit(...)`
- `render_closure_report(...)`
- `main()`

### Internal Groups

- constants defining output columns and enums;
- top-level orchestration and output refusal;
- source manifest construction;
- master evidence materialization;
- production, R11-R21, and external row builders;
- hard-coded external evidence row blocks;
- schema/enum/strict boolean validation;
- combination summary and proposal generation;
- report rendering;
- source-id lookup and citation helpers;
- low-level cleanup, hashing, git SHA, path-safety, sorting, and parsing helpers.

### Practical Dependency Graph

The top-level builder loads repository CSVs and an external manifest, builds a source manifest,
then builds master evidence rows from production, staging, and external evidence blocks. Summary,
proposal, and report all depend on the master evidence schema. The script entry point is a wrapper
around the top-level builder.

### Shared State And Constants

The column tuples and enum tuples are schema contracts for review-only artifacts. Default output
paths intentionally point to `data/lit_curation/` and `docs/research/`, not production ingest
surfaces. Path-refusal helpers protect production/config/scoring outputs.

### Output Schemas

- `eox_g1_2_source_manifest.csv`
- `eox_g1_2_master_evidence.csv`
- `eox_g1_2_combination_summary.csv`
- `eox_g1_2_production_change_proposal.csv`
- `eox_g1_2_master_closure_audit_20260624.md`

These are review-only schemas. Production CSV ingest remains out of scope.

### Existing Tests

Search-targeted curation tests should protect schema validation, forbidden output refusal,
deterministic row counts, and generated review artifacts. Contract coverage is less complete than
for CLI and directive validation.

### Missing Contract Tests

- Explicit required-column tests for every output table.
- Forbidden-output tests for production CSV/config/scoring destinations.
- Deterministic source-id ordering tests.
- Row-block fixture tests for each external evidence family.
- Report section smoke tests.
- Source-conflict fail-close proposal tests.

### Low-Risk Boundaries

1. Extract constants and schemas into `eps.curation.eox_master_schema`.
2. Extract generic helpers into `eps.curation.eox_master_utils`.
3. Extract report rendering into `eps.curation.eox_master_report`.
4. Extract source manifest logic into `eps.curation.eox_master_sources`.
5. Extract row materialization helpers into `eps.curation.eox_master_rows`.

### High-Risk Boundaries

- Moving hard-coded evidence row blocks before row-level fixture tests exist.
- Weakening forbidden-output checks.
- Mixing review-only proposal artifacts with production ingest.
- Changing onset/peak grouping semantics.
- Silently resolving source conflicts while refactoring.

### Proposed Target Layout

```text
eps/curation/eox_master_audit.py        # public orchestration shim + main
eps/curation/eox_master_schema.py       # column/enums/dataclasses
eps/curation/eox_master_sources.py      # source manifest/loaders
eps/curation/eox_master_rows.py         # production/staging/external row materialization
eps/curation/eox_master_summary.py      # combination/proposal/summary logic
eps/curation/eox_master_report.py       # Markdown rendering
eps/curation/eox_master_utils.py        # hashing/path/sort/clean helpers
```

### Staged PR Order

1. Add missing schema/forbidden-output/report tests.
2. Extract constants and dataclasses only.
3. Extract low-level pure helpers.
4. Extract report rendering.
5. Extract source manifest logic.
6. Extract row materialization by source family after fixture tests exist.
7. Keep the top-level `build_eox_g1_2_master_audit` signature unchanged.

### Rollback

The top-level shim must keep all current public function names until downstream scripts are
updated. Rollback is reverting the extraction PR; no generated review CSV should require migration.

## Verification Gate For Every Future PR

Minimum:

```bash
python -m pytest -q tests/test_cli_contracts.py tests/test_output_contracts.py tests/test_validate_directive.py
python -m pytest -q
python -m eps.cli doctor
ruff check .
git diff --check
```

Add curation-specific tests before any `eox_master_audit` extraction. Add no-engine CLI smoke
fixtures before command-handler movement. Add artifact-schema tests before any directive-output
movement.

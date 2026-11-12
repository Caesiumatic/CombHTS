# CombHTS status

## Current state

Commit metadata maintenance is complete on the existing remote branches and tag.
File trees, human authors, timestamps, and commit topology were verified against
the backup. The README, supporting documentation, and reviewed source cleanup are ready for publication.
The overview has been shortened to a technical repository introduction.

The repository revision adds a method/result README and a project map
linking the screening, calibration, full-space, and surrogate workspaces.
Calculation methods, data libraries, calibration, thresholds, and ranking logic
are unchanged.

The README describes the method, recorded results, and documentation entry points. Local setup
and detailed screening counts are collected in `docs/code_structure.md`, with
links to the existing calculation and validation records. This follow-up changes
documentation only; no calculations or package tests were rerun.

The recorded CombHTS screen covers 7,488 triads. The salt-role-corrected ranking
has 2,143 per-salt survivors and 1,127 score classes. The oxidation validation,
solvent-window policy, and optical diagnostics are documented in
[the code/workflow map](docs/code_structure.md) and `docs/runs/`.

## Verification — 2026-11-12

The publication check identified 38 existing Ruff errors. Import ordering and
plotting statement formatting have been corrected; Ruff now passes.
The full suite completed with 386 passed, 5 skipped, and 2 existing warnings.

## Previous verification — 2026-11-11

The existing test suite completed with 386 passed, 5 skipped, and 2 warnings
(local core-count detection and a mixed-type CSV column). No cluster calculation
or new scientific experiment was started.

## Remaining work

Scientific issues and unfinished calculation work remain as recorded in
[the previous status snapshot](docs/history/status-before-2026-11-11.md) and
`THINK.md`. This revision does not resume those runs.

Source consolidation with the later full-space implementation needs a defined
schema/interface migration; [the project map](docs/project-map.md) describes the
boundary. Next action: review the local documentation and verification results
after publication.

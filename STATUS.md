# CombHTS status

## Current state

CombHTS provides cached per-species calculations, calibration, compatibility
filters, and ranking for monomer–solvent–electrolyte combinations. Its recorded
June 2026 screen covers 7,488 triads; the salt-role-corrected ranking has 2,143
per-salt survivors and 1,127 score classes.

The [workflow guide](docs/code_structure.md) connects the implementation to
screening and validation records. The [calibration manifest](configs/CALIBRATION_ACTIVE.md)
tracks subsequent engine and calibration revisions, and the
[project map](docs/project-map.md) distinguishes later full-space studies from
this screen. The workflow guide also links the June 29 partial Tier-2 ORCA
harvest and refined screen. Optical diagnostics and open scientific questions remain recorded
in `docs/runs/` and `THINK.md`.

## Documentation verification — 2026-11-13

- Focused the README on descriptor reuse and screening results; attributed the
  0.186 V calibration metric to its June 23 validation record.
- Clarified workflow, engine, diagnostic, and optional-method docstrings,
  including IPEA request types already used by the property calculators.
- Checked Python syntax trees with docstrings removed and token streams with
  comments/docstrings removed; executable code and runtime strings are unchanged.
- Checked local links and `git diff --check`. Calculation settings, data,
  thresholds, and recorded results are unchanged; no calculations were run.

## Recorded verification — 2026-11-12

Ruff passed after import-ordering and plotting-format corrections. The full
suite completed with 386 passed, 5 skipped, and 2 existing warnings.

## Earlier verification — 2026-11-11

The existing test suite completed with 386 passed, 5 skipped, and 2 warnings
(local core-count detection and a mixed-type CSV column). No cluster calculation
or new scientific experiment was started.

## Remaining work

Scientific issues and unfinished calculations are recorded in
[the earlier status snapshot](docs/history/status-before-2026-11-11.md) and
[THINK.md](THINK.md). Source consolidation with the later full-space implementation
requires an agreed schema and package interface; the project map identifies that
boundary. The next engineering step is to review that interface before moving
source between workspaces.

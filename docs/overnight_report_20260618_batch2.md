# Overnight /goal #2 report — 2026-06-18 (rigor & reproducibility)

Second autonomous batch: all six tasks (0, A, B, C, D, E) completed, each committed separately
on `main` and pushed. Code-only, additive, no PI/curation, no pinned configs/data changed.

## Result at a glance

| Task | Status | Commit |
| --- | --- | --- |
| 0 — track `scripts/*.sge` (un-ignore) | DONE | `724bc00` |
| A — scoring columns on Tier-1 all-triads | DONE | `a1a2554` |
| B — CI (pytest) + ruff linting | DONE | `b215e99` |
| C — native provenance sidecars | DONE | `3c8ce66` |
| D — scientific-invariant regression tests | DONE | `e873530` |
| E — `eps doctor` readiness check (optional) | DONE | `c677a96` |

Baseline at start: `79 passed, 3 skipped`. Final: **`94 passed, 3 skipped`** (+15 tests).
**`ruff check`: clean.** `pytest -q` was green after each commit. The 3 skips are the
`xtb`/`g16` live smokes (skip when the binary is absent, by design). No changes to
`configs/tier1.yaml`, `configs/scoring.yaml`, `configs/calibration_profiles.yaml`,
`configs/validation.yaml`, the redox conversion, or any `data/*.csv`.

## Task 0 — track the SGE templates — DONE
- `.gitignore`: added `!scripts/*.sge` (root-level ad-hoc `*.sge` stays ignored; the templates
  under `scripts/` are now tracked). The four `scripts/run_*.sge` already existed on disk from
  batch 1 (they had been silently excluded by the `*.sge` ignore) and are now committed.

## Task A — scoring columns on the all-triads output — DONE
- `run_tier1` now left-joins the survivors' scoring columns (`composite_score`, `pareto_front`,
  `band_gap_deviation_eV`, `norm_*`) from `ranked` onto `all_triads` by triad identity
  (`monomer_name, solvent_name, salt`) with a `one_to_one` merge. Survivor rows carry IDENTICAL
  values to the ranked CSV; non-survivors are NaN (`pareto_front` False). Nothing is recomputed —
  `add_composite_score`, the weights, and the Pareto front are untouched.
- Net effect (closes batch-1 TODO #1): `eps analyze --harvest <all.csv>` now produces every §8
  output (Pareto + shortlist included) from the single all-triads file.
- Tests: `tests/test_tier1_audit.py` (columns present, survivor values match ranked exactly,
  non-survivors NaN/False, total count unchanged, and `eps analyze` on the all-CSV emits the
  Pareto PNG + shortlist with no skip notes).

## Task B — CI + ruff — DONE
- `.github/workflows/ci.yml`: on push and pull_request, Python 3.11 & 3.12, `pip install -e .[dev]`,
  then `ruff check .` and `pytest -q`. xtb/g16 absent in CI → live smokes skip, not fail.
- `[tool.ruff]` in `pyproject.toml` (select E, F, I; ignore E501; line-length 110) and a `dev`
  optional-dependency group (`ruff`). Ran `ruff --fix` (import sorting + removed two genuinely
  unused imports). `ruff check` is clean locally.
- NOTE: I could not exercise the GitHub Actions runner from here; the workflow is written to the
  standard pattern but its first real run happens when GitHub picks it up (see TODO #1).

## Task C — native provenance sidecars — DONE
- `src/eps/provenance.py`: `write_provenance(output_path, *, engine, method, extra)` writes
  `<output>.provenance.json` capturing a UTC timestamp, git commit short+long + dirty flag,
  `eps` version, engine/method, SHA-256 of the four pinned configs, and the library CSV row
  counts. Pure stdlib + pandas; degrades to `"unknown"`/`"missing"` outside a repo / when files
  are absent, never raising.
- Hooked best-effort into the `run-tier1`, `validate`, `memo`, and `analyze` CLI handlers — a
  provenance failure warns, never crashes the command. Replaces the by-hand MANIFEST.
- Tests: `tests/test_provenance.py` (sidecar keys, config-hash stability across calls, the
  not-a-git-repo and missing-config degradation paths).

## Task D — scientific-invariant regression tests — DONE
- `tests/test_invariants.py` (mock engine + synthetic data, no real runs):
  - redox→V conversion reproduces its pinned constants (4.28 / −0.197), is monotonic in energy,
    and round-trips through the inverse;
  - the single `tier1.yaml` oxidation calibration (slope 0.725837 / intercept −3.145372) is
    applied with the IDENTICAL slope/intercept transform to monomer Eox, the solvent anodic
    limit, and anion Eox (T11);
  - `eps sanity` is not a no-op: forcing EDOT's Eox ABOVE thiophene's yields FAIL, while the
    clean directional ordering (EDOT<thiophene, EDOP<pyrrole, EDOS<selenophene,
    bithiophene<thiophene) passes;
  - honesty: the memo always marks both unmeasurable §7 metrics "not computable" (never a
    number), and `eps analyze`'s placeholder/diagnostic labels are present.

## Task E — `eps doctor` — DONE
- `src/eps/doctor.py` + `eps doctor`: no-compute readiness check reporting PASS/WARN/FAIL for
  Python version, `xtb`/`g16` on PATH (WARN if absent — cluster-only), importability of
  rdkit/pandas/numpy (FAIL) and matplotlib/sklearn (WARN), and existence + parseability of the
  pinned configs and expected `data/*.csv`. No network; no subprocess beyond `shutil.which`.
  Locally: 16 checks, 0 FAIL, 2 WARN (xtb/g16). Tests in `tests/test_doctor.py`.

## Environment note
`ruff` was not installed in the local `.venv`; I installed it (and added it to the `dev`
optional-dependency group). `matplotlib`/`scikit-learn` were installed in batch 1.

## TODOs for human follow-up
1. **Confirm CI goes green on GitHub.** The workflow installs `rdkit`, `matplotlib`,
   `scikit-learn` from PyPI on 3.11 & 3.12 — watch the first run for any wheel-availability
   surprise (esp. `numpy<2` + py3.12). If a dep is slow/unavailable, pin or cache it.
2. **Provenance on cluster runs:** real `eps run-tier1 --engine xtb` etc. will now drop
   `*.provenance.json` next to each primary output; archive these alongside the CSVs.
3. **`eps analyze` against the real harvest:** with Task A, a single
   `outputs/tier1_all_xtb.csv` now yields all §8 outputs — re-run `qsub scripts/run_analyze.sge`.
4. Out of scope tonight, untouched per guardrails: band-gap/dimerization realism (T6), library
   expansion (T8), peak-vs-onset anchor (T1), and experimental-data curation.

## Definition of done
Six focused commits on `main` (one per task), `pytest -q` green after each
(`94 passed, 3 skipped`), `ruff check` clean, no pinned configs/data changed, this report
written.

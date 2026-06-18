# Overnight /goal report — 2026-06-18

Three-task overnight run: harden engineering, build `eps analyze` (§8), scaffold the Tier-2
DFT (Gaussian) adapter. All three completed, each committed separately on `main` and pushed.

## Result at a glance

| Task | Status | Commit | Pushed |
| --- | --- | --- | :---: |
| 1 — xTB hardening + SGE templates | DONE | `72f11a3` | yes |
| 2 — `eps analyze` (directive §8) | DONE | `d45a447` | yes |
| 3 — Gaussian Tier-2 scaffold (build-only) | DONE | `fa9d68f` | yes |

Baseline at start: `64 passed, 2 skipped`. Final: **`79 passed, 3 skipped`** (+15 tests; the 3
skips are the live `xtb`/`g16` smokes that skip when the binary is absent — by design). Full
`pytest -q` was green after each commit. No pinned config/data changed
(`configs/tier1.yaml`, `scoring.yaml`, `calibration_profiles.yaml`, `validation.yaml`,
`redox.py`, `data/*.csv` untouched). New deps added: `matplotlib`, `scikit-learn`.

## Task 1 — engineering hardening (STATUS debts #7, #9, #10) — DONE

- **1a** `src/eps/engines/xtb.py` `_run_xtb`: the subprocess return code is now checked and
  raises the xTB-exit `RuntimeError` BEFORE `xtbout.json` is parsed, so a present-but-garbage
  JSON can no longer mask a real failure with a `ValueError`. Success path is byte-identical.
- **1b** `tests/fixtures/xtbout.json`: replaced with a synthetic-but-schema-faithful fixture
  mirroring real `xtb --json` keys/nesting; the parser keys (`total energy`,
  `HOMO-LUMO gap/eV`) and existing tests are unchanged.
- **1c** `scripts/`: version-controlled SGE templates `run_tier1.sge`, `run_validate.sge`,
  `run_memo.sge`, `run_analyze.sge` (each leads with `#$ -S /bin/bash`, known-good
  modules/conda/OMP preamble; `run_analyze` omits the xtb module) + `scripts/README.md`.
- Files added: `scripts/*.sge`, `scripts/README.md`. Modified: `xtb.py`, `tests/test_xtb.py`,
  `tests/fixtures/xtbout.json`, STATUS, CHANGELOG.
- Tests added: `test_run_xtb_nonzero_exit_raises_before_json_parse`.

## Task 2 — `eps analyze` (directive §8) — DONE

- New read-only module `src/eps/analysis/` (`summary.py` + `plots.py`); new CLI
  `eps analyze --harvest <csv> --outdir <dir>`. Never recomputes/rescores — only reads.
- Produces: `summary.csv` (total/surviving/retention overall + by monomer/solvent/salt_class +
  per-property `*_calc_status` failure counts); real-axis distribution PNGs; a Pareto PNG
  (existing `pareto_front` flag, size ~ `-band_gap_deviation_eV`); a chemical-space map
  (per-triad Morgan fp r2/1024 → PCA(~50) + normalized descriptors → t-SNE, PCA(2) for n<10),
  colored by `monomer_class` and `passes_all_tier1_filters`; and a `shortlist.csv` (top-30
  Pareto by composite).
- Honesty guardrail honored: every output touching `optical_gap`/`dimerization_dG`/
  `band_gap_deviation_eV`/`composite_score`/`pareto_front` is labeled
  "PLACEHOLDER-CONTAMINATED / DIAGNOSTIC ONLY"; the shortlist carries the diagnostic note.
- Graceful degradation: missing matplotlib → skip figures; missing scikit-learn → skip only
  the chemical-space map; harvest without scoring columns → skip Pareto/shortlist; each with a
  note, never a crash.
- Files added: `src/eps/analysis/{__init__,summary,plots}.py`, `tests/test_analysis.py`.
  Modified: `cli.py`, `pyproject.toml`, STATUS, CHANGELOG.

## Task 3 — Gaussian 16 Tier-2 DFT scaffold (BUILD ONLY) — DONE

- `src/eps/engines/gaussian.py`: `GaussianEngine` (`gas_energy`, `adiabatic_ip`,
  `adiabatic_ea`) mirroring `XTBEngine` and the same charge/multiplicity convention
  (oxidation → charge+1, multiplicity+1; ΔG = G(cation) − G(neutral), preferring the thermally
  corrected Gibbs free energy). Return-code-first ordering (Task-1a lesson); raises clearly when
  `g16` is absent and NEVER fabricates a value. `build_gaussian_input(...)` →
  `#p B3LYP/6-31G(d,p) Opt SCF=Tight` (+ optional `SCRF=(SMD,Solvent=...)`), charge/multiplicity,
  Cartesian coords from `smiles_to_xyz`. `parse_gaussian_log(...)` → final `SCF Done` energy +
  optional `Sum of electronic and thermal Free Energies`, Hartree→eV.
- Registered `"gaussian"` in the CLI engine factory (`b3lyp-6-31g(d,p)-smd`); NOT wired into any
  production workflow run.
- Optional sub-item DONE: experimental `eps tier2 --dry-run --survivors <csv> --outdir <dir>`
  (`src/eps/workflow/tier2.py`) writes neutral+cation `.gjf` per unique survivor monomer and a
  rough CPU-hour estimate; never runs g16 (a test asserts no subprocess launches).
- Files added: `gaussian.py`, `workflow/tier2.py`, `tests/fixtures/gaussian_scf.log`,
  `tests/test_gaussian.py`. Modified: `engines/__init__.py`, `cli.py`, STATUS, CHANGELOG.

## Environment note

`matplotlib` and `scikit-learn` were not present in the local `.venv` at start; I installed
them (also added to `pyproject.toml`). The analysis code imports them lazily and degrades
gracefully, and the matplotlib/sklearn-dependent tests use `importorskip`, so the suite stays
green even where those libs are absent.

## Git note

`origin/main` had advanced by one human commit (`576a230`, the first real-xTB validation memo)
that shared a parent with my work. I rebased the Task-1 commit onto it (disjoint files, clean
rebase), then pushed; Tasks 2 and 3 fast-forwarded normally. All three commits are on
`origin/main`.

## TODOs for human follow-up

1. **Run `eps analyze` against the real cluster harvest.** Build it on Lop via
   `qsub scripts/run_analyze.sge` (→ `outputs/analysis/`). NOTE: the Tier-1 all-triads audit CSV
   (`tier1_all_xtb.csv`) does **not** carry `composite_score`/`pareto_front`/`band_gap_deviation_eV`
   (those live only on the ranked survivors). `eps analyze` skips the Pareto PNG and the
   shortlist with a note when they're absent. To get (iii)+(v), point `--harvest` at a scored
   CSV (the ranked survivors, or a harvest joined with the ranked columns). Decide whether to
   teach the Tier-1 all-output to also emit the scoring columns (would be a small additive
   change, deferred — not done tonight to avoid touching the scoring path).
2. **Tier-2:** inspect `eps tier2 --dry-run` outputs, then decide (PI / T8) whether to launch a
   bounded Tier-2 batch. The g16 path is untested against a real run — the live smoke test skips
   without `g16`; run it on the cluster once to confirm `SCF Done`/Gibbs parsing against a real
   log, and replace `tests/fixtures/gaussian_scf.log` with a captured real (trimmed) log.
3. **SGE templates** are templates — review resource requests (`-pe smp`, `-l h_rt`) before
   `qsub`.
4. Out of scope tonight (left untouched, per guardrails): band-gap/dimerization realism (T6),
   library expansion (T8), peak-vs-onset anchor (T1).

## Definition of done

Three focused commits on `main`, full `pytest -q` green after each (`79 passed, 3 skipped`), no
pinned configs/data changed, this report written.

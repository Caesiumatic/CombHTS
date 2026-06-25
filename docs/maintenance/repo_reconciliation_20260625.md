# Repository reconciliation — 2026-06-25

Non-destructive git hygiene pass across three locations (Mac, Lop HPC, GitHub).
Scope was **git metadata + one fresh clone only** — no chemistry, no compute, no
edits to scientific code or data. No `main` history was modified, rebased, reset,
or force-pushed; no branch was deleted; no stash was touched; no merge into `main`
was performed.

GitHub remote: `https://github.com/Caesiumatic/CombHTS` (branch `main`).

---

## 1. Verified three-way state

| Location | Path | Branch | Commit | Role |
| --- | --- | --- | --- | --- |
| **Mac** | `/Users/shichen/GitHub/CombHTS` | `main` | `7249d81` | Primary working checkout; in sync with `origin/main`. |
| **GitHub** | `origin` | `main` | `7249d81` | Single source of truth. |
| **Lop** | `$HOME/CombHTS` | `calib/solubility-cosmors` | `06b7e1d` | **Frozen data archive.** Holds real harvest data under `outputs/` + untracked local data (`analysis/`, `logs/`, `*.tar.gz`, smoke `.sge` scripts). Left fully untouched — read-only inspection only. Zero local-only commits, empty stash. |
| **Lop** | `$HOME/CombHTS-main` | `main` | `7249d81` | **NEW clean main-tracking code checkout.** Created this pass via fresh `git clone`. This is the checkout future Phase-1B cluster compute should use. |

**Alignment confirmed:** Mac `main`, GitHub `main`, and Lop `$HOME/CombHTS-main`
are all at `7249d81` ("docs: update STATUS and THINK notes").

Lop intentionally now has **two** checkouts: the old `$HOME/CombHTS` stays as the
frozen data archive (`06b7e1d`), and the new `$HOME/CombHTS-main` is the clean
code checkout. They are independent working trees of the same GitHub repo.

> Note on `$HOME/CombHTS` being "17 behind origin/main": this is expected and
> harmless. It is a frozen archive parked on `calib/solubility-cosmors @ 06b7e1d`
> for its data, not a checkout meant to track `main`. It was deliberately not
> updated. Compute on Lop should use `$HOME/CombHTS-main` instead.

---

## 2. What was preserved (additive, non-destructive)

### 2a. Archive tag for the one local-only commit
The only commit that existed locally on Mac but on no remote was `e8e571e`
("Record optical calibration submission 417587") on branch `calib/optical-n6`
(upstream `[gone]`).

- Created annotated tag **`archive/optical-417587-e8e571e`** at `e8e571e`
  (message: `archived "Record optical calibration submission 417587" commit`).
- Pushed the tag to `origin`. The commit is now durably preserved on GitHub.
- `calib/optical-n6` was **not** deleted.

### 2b. Overnight worktree work committed onto its own branch
The overnight worktree (see §3) contained **real uncommitted work**. It was
committed onto its branch so it finally carries its own commit, then pushed:

- Branch: **`chore/operational-hardening-20260624_234902`**
- New commit: **`1d4b254`** — "chore: operational-hardening overnight work
  (calibration disclosure + terminology audit)"
- Pushed to `origin/chore/operational-hardening-20260624_234902`.
- **Not merged into `main`.** Held for review/comparison against `main`.

---

## 3. Overnight worktree diagnosis

Worktree: `/Users/shichen/GitHub/CombHTS_overnight_20260624_234902`
(branch `chore/operational-hardening-20260624_234902`, was at `fae6bba`, which is
already inside `main`'s history — the branch had zero commits of its own).

**Verdict: category (a) — contains real, substantial uncommitted work.** Not a
phantom. Diagnosed read-only before any action:

- **9 modified tracked files** (+207 / −39): `README.md`,
  `scripts/run_oligomer.sge`, `src/eps/analysis/plots.py`,
  `src/eps/analysis/summary.py`, `src/eps/cli.py`, `src/eps/doctor.py`,
  `src/eps/workflow/tier1.py`, `tests/test_doctor.py`, `tests/test_invariants.py`.
- **13 untracked files (~124 KB)**: a new operational-calibration subsystem
  (`src/eps/calibration/operational.py`, `configs/calibration_operational.yaml`,
  `tests/test_calibration_operational.py`), `tests/test_cli_contracts.py`,
  `tests/test_output_contracts.py`, `tests/test_conformer_benchmark_script.py`,
  `scripts/benchmark_conformer_parallelism.py`, `docs/output_contracts.md`,
  `docs/current_state.md`, and four `docs/maintenance/*_20260625.md` planning/audit
  notes.

**Themes of the change set** (for later comparison against `main`):
1. New **operational-calibration disclosure** subsystem — declares Tier-1
   production profile (`agagcl_peak_strict`) vs validation default
   (`agagcl_peak_relaxed`) as intentionally divergent; wired into `doctor` and the
   `validate` CLI output. No production coefficients or scientific policy changed.
2. **Terminology refactor**: `placeholder` → `diagnostic` / `soft-axis` across
   analysis/plots/summary/workflow and invariant tests (label + symbol renames,
   e.g. `PLACEHOLDER_LABEL` → `DIAGNOSTIC_LABEL`).
3. **README rewrite** (operating-state + truth map) and new planning/contract docs.

This work is preserved on its branch (§2b) and **paused for confirmation** — no
merge, no worktree removal, pending review.

---

## 4. RECOMMENDED prune list (NOT executed — for approval)

Nothing below was deleted. Recommendations only. **Every `recover/*` branch is
explicitly excluded** (intentional safety archives — never prune).

### 4a. Safe to prune — git-verified fully integrated

**Local branches with `[gone]` upstream whose tips are ancestors of `main`:**

| Branch | Commit | Why safe |
| --- | --- | --- |
| `track/library-proposal` | `0347096` | tip is an ancestor of `main` |
| `track/optical-anchors` | `2717218` | tip is an ancestor of `main` |
| `track/shortlist-audit` | `2717218` | tip is an ancestor of `main` |

**Local `[gone]` branches whose tips are NOT in `main` but are preserved elsewhere:**

| Branch | Commit | Preserved by |
| --- | --- | --- |
| `calib/optical-n6` | `e8e571e` | tag `archive/optical-417587-e8e571e` (pushed) |
| `calib/solubility-cosmors` | `06b7e1d` | `recover/optical-06b7e1d` + Lop `$HOME/CombHTS` archive |
| `calib/dimerization-anchor` | `c72afbf` | `recover/solubility-c72afbf` |

**Remote branches that are true ancestors of `origin/main`:**

| Remote branch | Why safe |
| --- | --- |
| `origin/feat/eox-r11-r21-staging-rescue` | ancestor of `origin/main` (`--merged`) |
| `origin/fix/salt-degeneracy-and-electrolyte-role` | ancestor of `origin/main` (`--merged`) |

### 4b. DO NOT prune yet — task premise NOT git-verified (DISCREPANCY)

The task brief assumed the merged `feat/*`, `chore/*`, `integration/*`,
`research/*` remote branches were already in `main` and safe to remove. **Git does
not confirm this.** Each branch below is neither an ancestor of `origin/main` nor
patch-equivalent to it (`git cherry origin/main <branch>` reports every commit as
still `+`/unmerged). Deleting them could lose work, which violates the
"lose nothing" goal — so they are **excluded** from the safe list and flagged for
manual review before any prune:

| Remote branch | Unmerged commits (per `git cherry`) |
| --- | --- |
| `origin/chore/codebase-map-and-hygiene` | 7 / 7 |
| `origin/chore/repo-simplification-only` | 3 / 3 |
| `origin/feat/section7-validation-closure` | 2 / 2 — note: brief claimed "already merged into main"; `2ef21f6` is **not** an ancestor of `origin/main`. Its worktree lives at the ephemeral `/private/tmp/CombHTS_section7_validation`. |
| `origin/feat/tier2-pilot-orchestration` | 1 / 1 |
| `origin/integration/pre-cleanup-merge-20260623` | 5 / 5 |
| `origin/research/section7-staging-audit` | 1 / 1 |

### 4c. Never prune (excluded by guardrail)

`recover/dimerization-3d871a5`, `recover/optical-06b7e1d`,
`recover/solubility-c72afbf` (and `origin/recover/*`) — intentional safety
archives. Excluded from all prune recommendations.

---

## 5. Worktrees still present on Mac (not removed)

| Worktree | Branch | Note |
| --- | --- | --- |
| `/Users/shichen/GitHub/CombHTS` | `main @ 7249d81` | primary |
| `/private/tmp/CombHTS_section7_validation` | `feat/section7-validation-closure @ 2ef21f6` | ephemeral `/tmp` location; branch NOT verified-merged (see §4b) |
| `/Users/shichen/GitHub/CombHTS_overnight_20260624_234902` | `chore/operational-hardening-20260624_234902 @ 1d4b254` | now carries the committed overnight work; retained pending review |

Stash `stash@{0}` ("On feat/tier2-pilot-orchestration:
pre-cleanup-duplicate-staging-audit-staged-state") was left untouched.

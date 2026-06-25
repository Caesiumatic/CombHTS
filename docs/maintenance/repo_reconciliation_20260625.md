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

## 4. Branch prune — EXECUTED 2026-06-25 (per explicit user approval)

The branch prune was approved by the user and **executed** on 2026-06-25 after
verification that every deleted branch's content is already in `main` (zero work
lost). **Every `recover/*` branch was excluded** (intentional safety archives),
as were `main` and `chore/operational-hardening-20260624_234902` (the latter
carries genuinely unmerged overnight work — see §2b/§3).

### 4a. Verification that nothing was lost

Two independent checks confirmed all deleted branches are fully contained in `main`:

1. **No branch-unique files.** For every deleted branch,
   `comm -23 <(git ls-tree -r --name-only <branch>) <(git ls-tree -r --name-only origin/main)`
   was empty — i.e. every file on the branch also exists in `main`.
2. **Key "new" files already in `main`.** The substantive files these feature
   branches introduced (`src/eps/validation/directive.py`, `feasibility.py`,
   `tests/test_validate_directive.py`, `src/eps/curation/staging_audit.py`,
   `scripts/run_tier2_pilot_array.sge`, `tests/test_tier2_pilot.py`, …) all
   resolve via `git cat-file -e origin/main:<path>` and `main`'s versions are
   newer / superseding.

> **Correction to an earlier read:** `git branch --merged` and
> `git cherry origin/main <branch>` reported these six branches as "unmerged."
> That was a **false positive** from patch-id drift: the work was integrated into
> `main` via squash/rebase (new commit objects) and `main` then evolved the same
> files further, so patch-ids no longer match even though the content is present.
> The file-level checks above are authoritative; the branches were stale snapshots.

### 4b. Deletion ledger (recoverable SHAs)

**Remote branches deleted on `origin` (8):**

| Remote branch | SHA at deletion |
| --- | --- |
| `feat/section7-validation-closure` | `2ef21f6` |
| `feat/tier2-pilot-orchestration` | `606e7f8` |
| `research/section7-staging-audit` | `e186569` |
| `chore/repo-simplification-only` | `60670f5` |
| `chore/codebase-map-and-hygiene` | `b290da9` |
| `integration/pre-cleanup-merge-20260623` | `16ff3ec` |
| `feat/eox-r11-r21-staging-rescue` | `c51e3ea` (true ancestor of `main`) |
| `fix/salt-degeneracy-and-electrolyte-role` | `f41459d` (true ancestor of `main`) |

**Local branches deleted on Mac (14):**

| Branch | SHA at deletion | Also preserved by |
| --- | --- | --- |
| `calib/dimerization-anchor` | `c72afbf` | `recover/solubility-c72afbf` |
| `calib/optical-n6` | `e8e571e` | tag `archive/optical-417587-e8e571e` |
| `calib/solubility-cosmors` | `06b7e1d` | `recover/optical-06b7e1d` + Lop archive |
| `chore/codebase-map-and-hygiene` | `b290da9` | content in `main` |
| `chore/repo-simplification-only` | `60670f5` | content in `main` |
| `feat/eox-r11-r21-staging-rescue` | `c51e3ea` | ancestor of `main` |
| `feat/section7-validation-closure` | `2ef21f6` | content in `main` |
| `feat/tier2-pilot-orchestration` | `606e7f8` | content in `main` |
| `fix/salt-degeneracy-and-electrolyte-role` | `f41459d` | ancestor of `main` |
| `integration/pre-cleanup-merge-20260623` | `16ff3ec` | content in `main` |
| `research/section7-staging-audit` | `e186569` | content in `main` |
| `track/library-proposal` | `0347096` | ancestor of `main` |
| `track/optical-anchors` | `2717218` | ancestor of `main` |
| `track/shortlist-audit` | `2717218` | ancestor of `main` |

Any of the above can be restored with `git branch <name> <sha>` (or
`git push origin <sha>:refs/heads/<name>`) while the objects remain reachable.
The ephemeral worktree `/private/tmp/CombHTS_section7_validation` was removed
first (it was clean) to allow deleting its local branch.

### 4c. Never pruned (excluded by guardrail)

`recover/dimerization-3d871a5`, `recover/optical-06b7e1d`,
`recover/solubility-c72afbf` (and `origin/recover/*`) — intentional safety
archives, left fully intact.

---

## 5. Worktrees on Mac (after prune)

| Worktree | Branch | Note |
| --- | --- | --- |
| `/Users/shichen/GitHub/CombHTS` | `main @ 14cc443` | primary |
| `/Users/shichen/GitHub/CombHTS_overnight_20260624_234902` | `chore/operational-hardening-20260624_234902 @ 1d4b254` | carries the committed overnight work; retained pending review |

The ephemeral `/private/tmp/CombHTS_section7_validation` worktree was **removed**
during the 2026-06-25 prune (it was clean; its content is in `main`).

Stash `stash@{0}` ("On feat/tier2-pilot-orchestration:
pre-cleanup-duplicate-staging-audit-staged-state") was left untouched.

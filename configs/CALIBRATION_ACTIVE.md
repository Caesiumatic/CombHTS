# Active calibration manifest

_Created 2026-06-25 (director run). Resolves the audit/T1 visibility gap: production Tier-1 and
`eps validate` resolve their Eox calibration from two config files. This manifest is the single
statement of which calibration is live where._

_**Updated 2026-06-26:** the strict-vs-relaxed tiebreaker (T1) has resolved to **STRICT**
(`docs/research/eox_strict_vs_relaxed_loocv_20260626.md`, SGE 417876 on the current benchmark).
`default_screening_profile` flipped `agagcl_peak_relaxed → agagcl_peak_strict`, so the validate-default
now matches the already-pinned production line. No coefficient changed; production Tier-1 was already
strict. This is a reporting-default/label realignment, not a scoring change._

## What converts the screen's xTB Eox

| context | profile / source | slope | intercept (V) | n groups | metrics | where pinned |
|---|---|---|---|---|---|---|
| **Production Tier-1 harvest** (the 50k-bound screen; constraint-① window filter + 0.30 composite axis) | `agagcl_peak_strict_2026_06_17_xtb_v3` | **0.725837** | **−3.145372** | 9 | R²=0.889; in-sample MAE 0.144 V; **LOO-CV 0.197 V** | `configs/tier1.yaml` → `calibration.monomer_eox` (pinned constants) |
| **`eps validate` default report** | `agagcl_peak_strict` (fit at runtime; **= production line**, since 2026-06-26) | runtime fit (≈0.7258) | runtime fit (≈−3.1454) | 9 | R²=0.889; **LOO-CV 0.197 V** (SGE 417876, current benchmark) | `configs/calibration_profiles.yaml` → `default_screening_profile` |
| _(superseded)_ relaxed comparator | `agagcl_peak_relaxed` (kept for out-of-sample monitoring, not the fit) | runtime fit | runtime fit | 23 | LOO-CV **0.232 V** (SGE 417876) — loses to strict on every metric | comparison CSV only |
| Onset screening-filter track (reported, not the calibration anchor) | `agagcl_onset_relaxed` | runtime fit | runtime fit | 16 | LOO-CV 0.087 V (separate onset subset; **not** a sub-floor production claim) | `configs/calibration_profiles.yaml` |

Notes:
- `configs/calibration_profiles.yaml` defines profiles by **selection** (reference_frame / label_type /
  tier / media); the slope/intercept are **fit at runtime** from `data/benchmark.csv`. Only the
  production Tier-1 line carries **pinned** constants (in `tier1.yaml`), self-labeled *provisional*.
- The single oxidation calibration is applied (per `THINK` T11) to all computed oxidation potentials
  (monomer Eox, solvent **anodic** limit, anion Eox) — the intercept cancels in every margin, so the
  hard filters are governed by raw IP differences. The solvent **cathodic** limit stays raw.
- Accuracy language (per `THINK` T3): honest band **0.20–0.35 V**, hard floor **0.15 V**; never claim
  < 0.15 V. Report peak- and onset-anchored MAEs separately.

## Resolved decision (2026-06-26): STRICT

Strict (`agagcl_peak_strict`, n=9, tier-A native-Ag/AgCl peak) vs relaxed (`agagcl_peak_relaxed`,
n=23, tier A+B peak) was re-run on the **current** benchmark with real GFN2-xTB (SGE 417876, cache
seeded). Strict wins on every metric: LOO-CV 0.197 V vs 0.232 V, R² 0.889 vs 0.508, Spearman ρ
0.833 vs 0.663. Adding the tier-B D–A peak rows flattens the slope (0.73→0.45) without adding
calibration information. The DFT 417442 composed line corroborates strict (max |Δ| 0.087 V). Both
configs now resolve to strict; the earlier "leans toward relaxed on conditioning grounds" note is
retired — the live LOO-CV is the decider and it favors strict. See `THINK` T1 and
`docs/research/eox_strict_vs_relaxed_loocv_20260626.md`. Tier-B rows remain in `benchmark.csv`
(calibration_eligible) for out-of-sample monitoring.

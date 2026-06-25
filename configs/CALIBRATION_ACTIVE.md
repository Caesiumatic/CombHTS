# Active calibration manifest

_Created 2026-06-25 (director run). Resolves the audit/T1 visibility gap: production Tier-1 and
`eps validate` resolve **different** Eox calibrations, and that was only discoverable by reading two
config files. This manifest is the single statement of which calibration is live where. It does **not**
choose strict-vs-relaxed (that is `THINK` T1, data-gated on the DFT 417442 Fit-2 LOO-CV) and changes
no coefficient._

## What converts the screen's xTB Eox

| context | profile / source | slope | intercept (V) | n groups | metrics | where pinned |
|---|---|---|---|---|---|---|
| **Production Tier-1 harvest** (the 50k-bound screen; constraint-① window filter + 0.30 composite axis) | `agagcl_peak_strict_2026_06_17_xtb_v3` | **0.725837** | **−3.145372** | 9 | R²=0.889; in-sample MAE 0.144 V; **LOO-CV 0.197 V** | `configs/tier1.yaml` → `calibration.monomer_eox` (pinned constants) |
| **`eps validate` default report** | `agagcl_peak_relaxed` (fit at runtime from `data/benchmark.csv`) | runtime fit | runtime fit | 23 | LOO-CV **0.169 V** (per SGE 417671) | `configs/calibration_profiles.yaml` → `default_screening_profile` |
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

## Open decision (do NOT resolve here)

Strict (`agagcl_peak_strict`, n=9, tier-A native-Ag/AgCl peak) vs relaxed (`agagcl_peak_relaxed`,
n=23, tier A+B peak): decide from the recorded **DFT batch 417442** Fit-2 LOO-CV comparison, then
reconcile `tier1.yaml` + `calibration_profiles.yaml` onto the chosen profile and update this manifest.
The +37% in-sample→LOO jump on n=9 strict currently leans toward relaxed on conditioning grounds.
See `THINK` T1 and `DECISIONS_PENDING.md` B3.

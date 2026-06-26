# T1 — Eox calibration strict-vs-relaxed LOO-CV on the current benchmark (2026-06-26)

Status: **decide-and-report.** Production scoring line is UNCHANGED (it is already the strict line).
This resolves the "pending the live DFT LOO-CV tiebreaker" note in `configs/calibration_profiles.yaml`.

## What was run
Real GFN2-xTB benchmark validation over the **current committed `data/benchmark.csv`** (not the stale
2026-06-17 snapshot), all calibration profiles, on Lop — **SGE 417876**, cache seeded from the
2026-06-17 real-xTB validation cache so only newly-added benchmark monomers recomputed.
Output: `outputs/validation_current/calibration_profile_comparison.csv` (cluster).

## Results

| profile | track | n_points | slope | intercept (V) | R² | MAE_after (V) | **LOO-CV MAE (V)** | Spearman ρ | resid σ (V) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **agagcl_peak_strict** (tier A) | calibration | 9 | 0.7258 | −3.1454 | **0.889** | 0.144 | **0.197** | 0.833 | 0.158 |
| agagcl_peak_relaxed (tier A+B) | calibration | 23 | 0.4457 | −1.5361 | 0.508 | 0.191 | 0.232 | 0.663 | 0.283 |
| agagcl_onset_relaxed (tier A+B) | screening-filter | 16 | 0.2694 | −0.6101 | 0.618 | 0.121 | 0.149 | 0.871 | 0.160 |
| fc_peak_strict / fc_onset_relaxed | — | 0 | — | — | — | — | — | — | skipped (no Fc rows) |

(Strict and relaxed are the two competing **calibration** PEAK tracks; the onset profile is the
separate screening-filter track and is not a strict-vs-relaxed competitor — listed for completeness.)

## Verdict — STRICT generalizes better on every metric

Adding the 14 tier-B peak rows (23 vs 9) does **not** help calibration; it hurts it:
- **LOO-CV MAE**: strict **0.197 V** < relaxed 0.232 V — strict predicts held-out points better.
- **R²**: strict **0.889** vs relaxed 0.508 — relaxed loses nearly half its explained variance.
- **Spearman ρ**: strict **0.833** vs relaxed 0.663 — strict preserves rank order (what screening needs) far better.
- **Slope**: strict **0.726** vs relaxed **0.446**. The tier-B D–A peak rows (TPD/BTD/carbazole–furan
  D–A–D monomers, DTP, arylamines) cluster in a narrow ~0.9–1.6 V experimental band while their xTB
  adiabatic-IP descriptors span a wider range, so the OLS slope flattens toward 0.45 and the line tilts
  away from the thermodynamic ~0.7 V/eV relationship. They contribute *quantity* but not calibration
  *information*; they are more valuable as out-of-sample validation than as fit anchors.

### Independent DFT cross-check (SGE 417442, gas-phase ΔSCF)
The composed xTB→DFT→experiment line is slope 0.657 / intercept −2.720 V, which agrees with the
pinned strict line (0.7258 / −3.1454) to **max |Δ| = 0.087 V** over the calibration descriptor range
(5.45–7.41 eV) — within the ~0.1 V reference-scale floor. Two independent routes (direct xTB→exp strict
fit, and xTB→DFT→exp composition) converge on the same production line. This corroborates strict.

## Decisions

1. **Production screening line is correct and UNCHANGED.** `configs/tier1.yaml` already pins
   slope 0.725837 / intercept −3.145372 — i.e. the strict line. No edit needed; this analysis confirms it.

2. **Recommended (PI calibration-freeze action — flagged, NOT executed here):** flip
   `configs/calibration_profiles.yaml` `default_screening_profile: agagcl_peak_relaxed →
   agagcl_peak_strict` so the named validate-default matches both the already-pinned production
   coefficients and the LOO-CV winner. The current relaxed default is a latent inconsistency
   (documented in `configs/CALIBRATION_ACTIVE.md` as "production strict vs validate-default relaxed");
   the tiebreaker has now landed on strict. Left to the PI because changing the default calibration
   profile is a calibration-freeze decision under the directive, even though it only realigns the label
   with the line production already uses.

3. **Honest-MAE band stands.** Strict LOO-CV MAE 0.197 V sits in the 0.20–0.35 V honest floor; do not
   claim sub-0.15 V precision. The tier-B relaxed rows remain in `benchmark.csv` (calibration_eligible)
   for out-of-sample monitoring; this decision only governs which set FITS the line.

Resolves the `calibration_profiles.yaml` "strict-vs-relaxed (peak) choice ... pending the live DFT
LOO-CV tiebreaker" note: **strict.**

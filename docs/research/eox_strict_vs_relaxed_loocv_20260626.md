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

---

## UPDATE 2026-06-26 — re-fit on the EXPANDED benchmark (SGE 417945)

The benchmark was expanded with 6 clean convertible canonical-monomer PEAK anchors
(EDOT 1.485 / EDOS 1.225 / pyrrole 1.245 / pyrrole 1.302 / N-methylpyrrole 1.185 / carbazole 1.205 V vs
Ag/AgCl; all tier-B; the strict tier-A set is untouched at n=9 — see `eox_gapfill_deepresearch_20260626.md`).
The strict↔relaxed verdict was re-run on this expanded set to test a specific hypothesis: **does adding
clean, canonical, chemically-diverse monomers to the relaxed (A|B) set rescue it?** Run on Lop, all
profiles, cache warm so only the new monomers recomputed. Output:
`outputs/calibration_profile_comparison.csv` (cluster).

| profile | track | n | slope | intercept (V) | R² | MAE_after (V) | **LOO-CV (V)** | Spearman ρ | resid σ (V) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **agagcl_peak_strict** (tier A) | calibration | 9 | 0.7258 | −3.1454 | **0.889** | 0.144 | **0.197** | 0.833 | 0.158 |
| agagcl_peak_relaxed (A+B) | calibration | **28** | 0.4181 | −1.3869 | 0.475 | 0.184 | 0.211 | 0.711 | 0.267 |
| agagcl_onset_relaxed (A+B) | screening-filter | 16 | 0.2694 | −0.6101 | 0.618 | 0.121 | 0.149 | 0.871 | 0.160 |
| fc_peak_strict / fc_onset_relaxed | — | 0 | — | — | — | — | — | — | skipped (no Fc-scale Eox rows) |

**Hypothesis FALSIFIED — and the falsification is the result.** I predicted the clean canonical anchors
would pull the relaxed slope *up* toward the thermodynamic ~0.7 V/eV. They did not: slope moved the wrong
way (0.446 → **0.418**), R² stayed poor (0.508 → 0.475), and although LOO-CV improved marginally
(0.232 → **0.211 V**) with the larger, more stable set, **relaxed still loses to strict** (0.211 > 0.197).
Strict is unchanged to the digit (its tier-A set didn't move) and remains the winner on every metric.

The scientific upgrade: this rules out **small-sample instability** as the reason relaxed underperforms.
Going 9→23→28 points and adding the cleanest possible canonical monomers did *not* fix the slope. The
deficit is therefore **structural / data-quality**, not quantity: the tier-B rows carry a genuinely noisier
xTB-adiabatic-IP ↔ experimental-Eox relationship (heterogeneous measurement conditions; D–A push–pull
monomers whose peak potential decouples from a single-molecule adiabatic IP), so they flatten the line no
matter how many clean points sit alongside them. They are **out-of-sample validation material, not fit
anchors** — exactly the role they now play (`calibration_eligible`, but not in the production strict fit).

**Decisions (post-expansion):**
- **Production line UNCHANGED and re-confirmed.** `configs/tier1.yaml` strict coefficients
  (0.725837 / −3.145372) are byte-identical to this re-fit's strict row. No edit.
- **Decision #2 above is now DONE, not pending.** `default_screening_profile` was flipped
  relaxed→strict in commit `1d59349` and `configs/CALIBRATION_ACTIVE.md` reconciled. The expanded re-fit
  retroactively strengthens that flip.
- No new action required; the only remaining freeze action is the PI-level calibration freeze itself
  (THINK T17 layer-1), which this analysis clears for the Eox axis.

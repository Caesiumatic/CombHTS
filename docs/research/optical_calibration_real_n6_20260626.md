# T6 — Per-class optical calibration of REAL sTDA-xTB hexamer gaps (2026-06-26)

Status: **DIAGNOSTIC ONLY. No change to the 15% optical scoring axis, weights, or filters.**
Decide-and-report. This is the data-gated follow-up promised by the optical re-harvest
(`docs/runs/2026-06-26_optical-reharvest-417866.md`): now that all 36 monomers carry a *real*
sTDA-xTB optical series (n1..n6), can the optical axis graduate from diagnostic to a calibrated
screening axis?

## Inputs
- **Computed**: real sTDA-xTB on neutral hexamers (n=6), SGE 417866 — `data/lit_curation/optical_n6_real_stda_36monomers.csv` (provenance copy of the per-monomer optical series).
- **Experimental anchors**: `data/lit_curation/optical_anchors_selected.csv` (curated neutral-polymer optical-gap anchors mapped to library monomers) + the ~30-row anchor table in `docs/research/external_reports_20260625/03_optical_bandgap_anchors.md`.
- **Analysis**: `scripts/analyze_optical_calibration_real_n6.py` → `outputs/optical_calibration_real_n6/{optical_real_n6_points.csv, optical_real_n6_fit.json}`.

Relationship fit: `exp_polymer_gap_eV = slope · sTDA_xTB_n6_eV + intercept`.

## Matched anchor set (8 of 9; PProDOP excluded — its monomer is not in the 36-row library)

| polymer | class | exp (eV) | sTDA n6 (eV) | raw bias n6−exp (eV) | global resid (eV) | LOO resid (eV) | n6 converged | conf. |
|---|---|---:|---:|---:|---:|---:|:--:|:--:|
| PEDOS (electrodeposited) | alkylenedioxyselenophene | 1.38 | 2.849 | +1.469 | −0.609 | +0.697 | no | high |
| P[T1] thieno[3,4-b]pyrazine terthienyl | donor–acceptor | 1.46 | 2.090 | +0.630 | −0.005 | +0.009 | yes | med |
| p-AlkyneDTP (dithienopyrrole) | fused donor | 1.76 | 2.685 | +0.925 | −0.116 | +0.135 | yes | high |
| PEDOP | alkylenedioxypyrrole | 2.00 | 3.160 | +1.160 | −0.203 | +0.240 | no | high |
| Polyterthiophene PT3 | oligothiophene | 2.02 | 2.559 | +0.539 | +0.231 | −0.280 | yes | med |
| P3HT (solution, L43) | alkylthiophene | 2.31 | 2.802 | +0.492 | +0.354 | −0.406 | no | high |
| Polyfuran (P1) | heteroaromatic (furan) | 2.31 | 2.927 | +0.617 | +0.267 | −0.306 | no | med |
| PFO (poly-9,9-dioctylfluorene) | fluorene | 2.95 | 4.126 | +1.176 | +0.081 | −0.324 | yes | high |

## Fit results

| fit | n | slope | intercept (eV) | R² | in-sample MAE (eV) | **LOO-CV MAE (eV)** |
|---|---:|---:|---:|---:|---:|---:|
| Global (all 8) | 8 | 0.690 | +0.024 | 0.626 | 0.233 | **0.299** |
| High-confidence only | 5 | 0.819 | −0.478 | 0.656 | 0.233 | **0.442** |

Raw hexamer bias (n6 − exp): **mean +0.876 eV, std 0.361 eV**. Hexamer convergence: **4 / 8** anchors converged at n=6.

## Verdict — the optical axis does NOT graduate; stays 15% diagnostic

Four independent blockers, each sufficient on its own:

1. **Generalization error exceeds the anchor accuracy floor.** Global LOO-CV MAE is **0.299 eV** (high-conf-only is *worse*, 0.442 eV, because dropping points raises leverage at n=5). Report 03 places the *experimental* anchor accuracy at ±0.1–0.2 eV. A calibrated axis whose own cross-validated error (~0.3 eV) is larger than the data it is calibrated against would inject noise, not information, into the 15% band-gap term. It must remain a soft diagnostic, not a scored predictor.

2. **Per-class offsets are not estimable — every class is a singleton.** The 8 anchors fall into 8 distinct chemical classes (1 anchor each). Report 03's own Stage-1 recommendation requires **≥3 anchors per class** before fitting a per-class offset. With n=1 per class, the "per-class offset" is just that anchor's residual; it cannot be distinguished from noise and cannot be transferred to the other library members of its class. **The per-class calibration the task set out to fit is structurally impossible with the current anchor mapping.**

3. **The oligomer→polymer extrapolation is unconverged and conflated with the fit.** Only 4/8 hexamers converged at n=6; the other half (PEDOS, PEDOP, P3HT, polyfuran) are still descending the 1/n curve, so their n6 gap is not the polymer-limit value the experimental anchor reports. The +0.876 eV mean raw bias is *not constant* (std 0.36 eV), so a single global intercept cannot absorb it — and the unconverged points are exactly the largest-residual ones.

4. **Documented-weak low-gap regime confirmed.** The largest miss is PEDOS (the 1.38 eV selenophene end-member): residual −0.61 eV, LOO residual +0.70 eV. This reproduces the report-03 warning that sTDA-xTB is weakest below ~1.7 eV on D–A / low-gap chromophores — precisely the OMIEC-relevant regime.

**Decision (within directive authority):** keep the optical/band-gap axis at its current **15% weight, diagnostic, uncalibrated** role. Do not adopt a global or per-class optical→experiment map into scoring. The HL-gap fallback is fully retired (all 36 are real sTDA), which was the actual deliverable of the re-harvest; the *graduation* decision is gated on data, and the data says not yet.

## Path to graduation (data-gap closure, future work — not executed here)

The blocker is anchor *density per class*, not method capability. Report 03 already lists ≥3 high/med anchors for polythiophenes, dioxythiophenes (PEDOT family), dioxypyrroles, selenophenes, and D–A — but `optical_anchors_selected.csv` mapped only ONE to a library monomer per class. To make per-class offsets estimable:

- **Expand the anchor CSV to ≥3 anchors per well-anchored class**, mapping report-03 rows onto library monomers: e.g. polythiophene class → unsubstituted PT (2.0), P3HT film (1.9), P3OT (1.92) all onto `3-hexylthiophene`/`thiophene`; PEDOT family → neutral PEDOT (1.55), PProDOT-Me2 (1.7) onto `EDOT`/`ProDOT`; dioxypyrrole → PEDOP (2.0), PProDOP (2.2) onto `EDOP`.
- **Re-fit per class** once ≥3 points exist, and re-check LOO-CV against the ±0.2 eV floor.
- **Threshold to revise** (report 03): refit a class separately if any new primary anchor deviates >0.2 eV from the class mean.
- Only if a class achieves LOO-CV MAE ≲ 0.2 eV should that class's optical term move from diagnostic to calibrated.

This is a curation task (literature → CSV), not a compute task; the real sTDA-xTB descriptors it would consume now exist for all 36 monomers.

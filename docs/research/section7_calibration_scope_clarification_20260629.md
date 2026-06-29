# §7 calibration: what the directive says vs what we actually do (clarification)

**Date:** 2026-06-29. Written to stop a recurring misstatement (incl. by the assistant) about the
§7 calibration. Two precise corrections.

## Directive §7 calibration protocol (verbatim intent)
> "Following Zwijnenburg et al., fit linear models (slope, intercept) **mapping xTB properties to DFT
> values** using the benchmark set. Apply these corrections to **all** Tier-1 results before
> filtering. Re-fit if new functional groups outside the training domain are introduced."

So the directive's **calibration = xTB → DFT** (a linear map), applied to the Tier-1 properties.
DFT → Ag/AgCl is then a **physical conversion** (absolute reference potential 4.28 V SHE − 0.197 V),
**not a fit**; comparison to experimental CV is **validation** (the MAE targets), not calibration.

## What the repo actually does — TWO documented deviations

### Deviation 1 — we fit xTB → EXPERIMENT, not xTB → DFT
Production calibration is a **direct xTB → experiment (Ag/AgCl)** linear fit (the IPEA strict line
slope 0.931164 / intercept −0.083599). This **collapses** the directive's two steps
(xTB→DFT fit, then DFT→Ag/AgCl conversion) into one empirical line, because full-scale Tier-2 DFT
was not available when the line was pinned (THINK **T4**). It is justified, not arbitrary: the
directive-style composed path (xTB→DFT Fit-1 R²0.91, then DFT→exp) agrees with the direct line to
**≤ 0.087 V** (SGE 417442, GFN2-era pilot). The **DFT→experiment fit is an added cross-check, NOT a
directive step.** Once the running Tier-2 DFT batch lands, the calibration can be redone the
directive way (xTB→DFT) with the current IPEA method.

### Deviation 2 — we calibrate the OXIDATION axis only, not "all xTB properties"
`configs/tier1.yaml` `calibration.monomer_eox.scope = all_computed_oxidation` (THINK **T11**):
**one** oxidation calibration line is applied to **all computed oxidation potentials** — monomer
Eox, solvent **anodic** limit, anion Eox. It is **fit on monomer peak data only**, so the solvent
and anion absolute values are screening-grade extrapolations (the intercept cancels in every
margin, so the filters are unaffected).

**Not calibrated** (reported-only / declined):
- solvent **cathodic** / reduction (EA) limit — left raw (it is a reduction, not on the oxidation line);
- **optical gap** — a separate sTDA→TD-DFT/exp calibration was fit and **declined for cause**
  (R²≈0.15, descriptor degenerate within class; kept a 15 % diagnostic axis, THINK T6);
- HOMO/LUMO, dimerization ΔG, reorganization energy λ — reported-only.

So vs the directive's "fit … mapping xTB properties to DFT … apply to all Tier-1 results", we
calibrate the one property that drives the hard constraint-① filter (oxidation Eox), decline optical
on rigor grounds, and leave the rest reported-only. We do **not** calibrate every xTB property.

## How to state it (presentation / PI)
- "Directive calibration is xTB→DFT; we currently use an equivalent direct xTB→experiment line
  (≤0.087 V agreement, documented collapse) and calibrate the **oxidation axis only**."
- Do **not** claim a DFT→experiment fit is a directive step, and do **not** claim all xTB properties
  are calibrated.

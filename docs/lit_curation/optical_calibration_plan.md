# Optical-gap calibration PLAN — per-class neutral-polymer anchors

> **PLAN ONLY — nothing here is executed and nothing changes scoring.** This document
> selects experimental anchors and specifies how a future calibration *would* be run. It does
> **not** run it, does **not** touch `src/`, `configs/`, `data/*.csv` (production), the four
> existing staging CSVs, or the 15 % optical score axis. The 15 % optical axis **stays
> DIAGNOSTIC** until the calibration described below is actually executed, reviewed, and signed
> off. Every anchor is staging-derived and still carries `needs_review=true`.

Addresses `STATUS.md` open debt **#3** ("the corrected three-dimer optical fit … remains too small
and ill-conditioned for scoring and needs the six experimental anchors/per-class expansion") and
**#5** ("Optical calibration needs the six experimental neutral-polymer anchors, longer-chain/
geometry sensitivity, and per-class validation. The three-dimer pilot must not change the 15 %
score axis").

Anchor source file: [`data/lit_curation/optical_anchors_selected.csv`](../../data/lit_curation/optical_anchors_selected.csv)
(selected from [`data/lit_curation/optical_doping_staging.csv`](../../data/lit_curation/optical_doping_staging.csv)).

---

## 1. What exists today (the pilot to be replaced)

The current optical pilot is a **method-to-method** check, not a calibration to experiment. From
`STATUS.md`, the corrected ORCA dimer pairs `(sTDA, TDA)` in eV are:

| monomer | sTDA (eV) | TDA (eV) |
|---|---|---|
| thiophene | 4.870360 | 4.396 |
| EDOT | 4.869517 | 4.687 |
| pyrrole | 5.488049 | 5.004 |

The three-point fit is **slope 0.747765, intercept 0.900028 eV, R² 0.7701, MAE 0.0973 eV**. It is
explicitly flagged *too small and ill-conditioned for scoring*. Two structural problems:

1. **n = 3, all dimers, three monomers** (thiophene, EDOT, pyrrole) — three points cannot resolve
   slope, intercept, and scatter; R² 0.77 on three points is not a fit.
2. It compares **cheap sTDA against reference TDA** (a self-consistency check between two computed
   methods). It contains **no experimental information at all**, so it cannot tell whether either
   computed method tracks real neutral-polymer optical gaps.

The selected anchors supply the missing experimental axis.

## 2. Selected anchors and their class mapping

Nine rows selected; **six HIGH-confidence primary π–π\* absorption-onset anchors** form the
calibration set, plus **three MEDIUM supporting points** (kept for span/sensitivity diagnostics
only, never as primary calibration points). All map by SMILES to a `monomer_class` present in
`data/monomers.csv` (8 of 9 are exact library-SMILES hits; PProDOP's ProDOP monomer is not in the
36-row library but its class, alkylenedioxypyrrole, is present via EDOP).

| polymer | monomer_class | broad type | Eg (eV) | method | confidence |
|---|---|---|---|---|---|
| PEDOP | alkylenedioxypyrrole | pyrrole-type | 2.00 | π–π\* onset | **high** |
| PProDOP | alkylenedioxypyrrole | pyrrole-type | 2.20 | π–π\* onset | **high** |
| P3HT (L43) | alkylthiophene | thiophene-type | 2.31 | abs. onset (λ_onset 537 nm, soln) | **high** |
| PEDOS | alkylenedioxyselenophene | selenophene-type | 1.38 | abs. onset (λ_onset 893 nm, film) | **high** |
| PFO | fluorene | fluorene-type | 2.95 | abs. onset (425 nm, film) | **high** |
| p-AlkyneDTP | fused donor | fused-donor type | 1.76 | abs. onset (703 nm, film) | **high** |
| Polyterthiophene PT3 | oligothiophene | thiophene-type | 2.02 | Tauc (not onset) | medium |
| Polyfuran (PFu3) | heteroaromatic (furan) | furan-type | 2.31 | Tauc (not onset) | medium |
| P[T1] TP-terthienyl | donor-acceptor | D–A type | 1.46 | abs. onset, CT-dominated | medium |

The six HIGH anchors span **1.38 – 2.95 eV** across five distinct classes and six broad monomer
types — i.e. low-gap (dioxyselenophene), mid-gap (dioxypyrrole, fused-donor, alkylthiophene) and
high-gap (fluorene) end-members, which is what an experimental regression needs to constrain both
slope and intercept. PEDOP/PProDOP additionally give a within-class pair (ethylene- vs
propylene-bridged dioxypyrrole, 2.0 vs 2.2 eV) that probes substituent sensitivity inside one
class.

**Why the three MEDIUM points are not primary anchors:** PT3 and polyfuran report **Tauc-extrapolated**
optical gaps `((αhν)² → 0)`, not absorption onsets, so they are not directly comparable to an
onset-defined computed gap; P[T1] is a clean onset but a **low-gap donor–acceptor** whose
low-energy band is intramolecular-charge-transfer-dominated rather than pure π–π\*. They are
retained only to (a) extend the type span (oligothiophene, furan, D–A) for a coverage check and
(b) serve as out-of-set sensitivity probes once the HIGH-anchor fit exists.

## 3. How the anchors would calibrate the pilot (NOT executed)

The calibration replaces the n=3 method-vs-method pilot with a **computed → experiment** regression.
Proposed procedure (to be run, reviewed, then — only if it passes — wired into scoring):

1. **Put the computed side on a polymer footing.** The anchors are *polymer* gaps (film or
   isolated-chain solution); the pilot computes *dimer* gaps. For each anchor monomer, compute the
   optical gap for an oligomer series (n = 1, 2, 3, 4, …) with the same paired sTDA/TDA protocol,
   then extrapolate the transition energy to the infinite-chain limit (linear in 1/n, with the
   1/n→0 intercept as Eg,∞). Reuse the **existing infinite-chain machinery**
   (`src/eps/properties/oligomer_series.py`) as the structural template — the same way it already
   extrapolates IP to the infinite chain and flags out-of-domain infinities. Do **not** fit on raw
   dimer values against polymer experiment.
2. **Regress experiment on the extrapolated computed gap.** Fit `Eg_exp = a · Eg_comp,∞ + b`
   using the **six HIGH anchors** (n = 6). Report slope, intercept, R², MAE, and a
   leave-one-out cross-validated MAE (LOO is essential at n = 6). Do this **per computed method**
   (sTDA and TDA separately) so the cheap-method penalty is explicit.
3. **Per-class check, not just a global fit.** With anchors in ≥5 classes, test whether one global
   `(a, b)` is adequate or whether class-family offsets are needed (e.g. dioxy-bridged rings vs
   bare heteroaromatics vs D–A). Report per-class residuals; flag any class whose single anchor
   forces an unconstrained offset.
4. **Keep the pilot as an internal cross-check.** The existing sTDA↔TDA agreement (slope 0.748,
   R² 0.77) stays as a *method-consistency* diagnostic, separate from the new computed→experiment
   fit. It must not be conflated with, or substituted for, an experimental calibration.

**Acceptance gate before any scoring change:** the computed→experiment fit must (i) use ≥6
experimental anchors, (ii) report LOO-CV error, (iii) show per-class residuals within a
reviewer-set tolerance, and (iv) pass the length/geometry sensitivity tests in §4. Until all four
hold, the 15 % optical axis remains diagnostic (see §6).

## 4. Oligomer length & geometry sensitivity that must be tested

Before any anchor↔computed comparison is trusted, these sensitivities must be quantified and
reported (none are executed here):

- **Chain-length extrapolation.** Verify the 1/n linearity of the transition energy and report the
  Eg,∞ extrapolation uncertainty for each anchor monomer. A dimer-only gap red-shifts substantially
  to the polymer limit; the size of that shift is monomer-class-dependent and is the dominant
  systematic error in step 3.1.
- **Backbone geometry / torsion.** Test planar vs relaxed inter-ring dihedral (and s-cis/s-trans
  where relevant). Twisting shortens effective conjugation and widens the computed gap; quantify the
  spread so the fit's intercept is not absorbing an uncontrolled conformer choice.
- **Solid-state vs isolated-chain.** Five HIGH anchors are films; P3HT (L43) is a dilute-solution
  (isolated-chain) onset. Film gaps carry aggregation/planarization red-shifts absent in an
  implicit-solvent single-chain computation. Record whether each anchor is film or solution and do
  not mix the two systematics silently.
- **Onset vs Tauc vs λ_max consistency.** The HIGH anchors are absorption *onsets*; the computed
  "gap" must be defined to match (lowest singlet transition onset, not λ_max). The two MEDIUM Tauc
  anchors and any λ_max-derived literature value must be excluded from, or separately modelled in,
  the primary fit.
- **Reference-frame note (potentials).** No potential conversions were performed for these optical
  anchors — they are eV gaps. Where a `doping_onset` column is present it is copied **verbatim**
  from the staging file, which already applied the **pinned** conversion
  (`src/eps/properties/redox.py`: `ABS_SHE_V = 4.28`, `AGAGCL_SHIFT_V = -0.197`,
  `ip_eV_to_potential_vs_AgAgCl`); no shift was hand-rolled here. Doping-onset values referenced to
  Fc/Fc⁺ (solvent not MeCN), Ag/Ag⁺, or Ag/AgCl pseudo-wire remain unconverted and flagged, exactly
  as in staging.

## 5. Coverage table (classes with anchors / classes still gapped)

Grouped by broad monomer type over all `data/monomers.csv` classes:

| Broad type | Library classes | Anchor status | Anchor(s) | Note |
|---|---|---|---|---|
| Pyrrole-type | heteroaromatic(pyrrole), N-substituted pyrrole, alkylpyrrole, **alkylenedioxypyrrole** | **COVERED (high)** | PEDOP, PProDOP | parent polypyrrole staging row is p-doped, not a neutral onset |
| Thiophene-type | heteroaromatic(thiophene), **alkylthiophene**, oligothiophene, alkoxythiophene, halothiophene, alkylenedioxythiophene | **COVERED (high)** | P3HT (+ PT3 supp.) | EDOT/ProDOT sub-class has **no clean primary onset** anchor — see gaps |
| Selenophene-type | heteroaromatic(selenophene), alkylselenophene, **alkylenedioxyselenophene** | **COVERED (high)** | PEDOS | parent polyselenophene staging row is an edge **estimate** ("zero-order approx.") |
| Fluorene-type | **fluorene** | **COVERED (high)** | PFO | high-gap end-member |
| Fused-donor type | **fused donor** (DTP, CPDT) | **COVERED (high)** | p-AlkyneDTP | CPDT itself appears only in CT copolymers (not clean π–π\*) |
| Furan-type | heteroaromatic(furan), alkylfuran, oligofuran | **PARTIAL (medium)** | Polyfuran (Tauc) | needs a **primary absorption-onset** furan gap to upgrade |
| Donor–acceptor type | **donor-acceptor** (BT–thiophene, thieno[3,4-b]pyrazine) | **PARTIAL (medium)** | P[T1] | onset is CT-dominated, not pure π–π\* |
| Aniline/amine-type | aniline, arylamine | **GAP** | — | see gaps |
| Carbazole-type | carbazole, N-vinylcarbazole | **GAP** | — | see gaps |

Summary: **5 / 9 types covered by HIGH anchors**, **2 / 9 partial (MEDIUM only)**, **2 / 9 gapped**.

### Gaps — flagged, NOT filled with estimates

- **Aniline/amine-type — GAP.** Polyaniline's optical response is oxidation- and protonation-state
  dependent; the emeraldine-base π–π\* (~3.7 eV) is distinct from a ~2.0 eV exciton band and from a
  quoted ~1.3 eV "semiconductor gap." There is **no single clean neutral-polymer π–π\* onset** that
  is unambiguous, so no anchor is recorded. A clean aniline-type anchor requires a primary source
  reporting a well-defined neutral-state onset with a locatable DOI.
- **Carbazole-type — GAP.** The optical-doping staging carbazole/PVK rows are **redox-only** (no
  optical gap). Literature reports ~2.4–2.5 eV for carbazole-*based* electrochromic polymers, but a
  clean primary **parent-polycarbazole (3,6- or 2,7-coupled) absorption-onset** value pinned to a
  locatable DOI was not sourced in this pass — recorded as a gap rather than filled.
- **Alkylenedioxythiophene (EDOT/ProDOT) clean-primary — GAP-within-covered-type.** The only
  staging values (PEDOT 1.6 eV; PProDOT 1.6 eV) come from a **review** and a **patent**, each as the
  **lower bound of a 1.6–1.7 eV range** — they fail the strict primary-source + single-onset bar, so
  they are **not** promoted to a HIGH anchor. The thiophene *type* is still covered (P3HT), but the
  flagship dioxythiophene sub-class lacks a clean primary onset anchor and should be sourced before
  per-class dioxythiophene scoring.
- **Substituent sub-classes** (alkoxythiophene, halothiophene, N-substituted/alkyl pyrrole,
  alkylfuran, alkylselenophene, oligofuran) have **no dedicated anchor**; they currently inherit
  their parent-type fit as a proxy. Per-class validation (§3.3) cannot confirm them until at least
  one anchor per sub-class exists.

## 6. Standing caveat (honesty language preserved)

The three-dimer sTDA/TDA pilot **must not change the 15 % optical score axis** (debt #5). This plan
does not change it either. The 15 % optical axis remains **DIAGNOSTIC** until: the §3 computed→
experiment calibration is executed on ≥6 experimental anchors, the §4 length/geometry sensitivities
are quantified, per-class residuals are reviewed, and a human signs off. All anchors here are
STAGING values (`needs_review=true`) requiring spot-check against their cited DOIs before they enter
any calibration or scoring.

---

### Planned calibration anchor count

- **Primary calibration set: n = 6** HIGH-confidence anchors (vs the current n = 3 pilot).
- Expandable to **n = 9** including the 3 MEDIUM supporting points for span/sensitivity diagnostics
  only (never as primary calibration points).

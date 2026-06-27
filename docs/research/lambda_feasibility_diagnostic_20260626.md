# T16 — Does computed reorganization energy λ_ox separate electropolymerization feasibility? (2026-06-26)

Status: **DIAGNOSTIC ONLY. No production weight / filter / score change.** Decide-and-report.
This is the λ-vs-feasibility diagnostic promised by THINK T16 (directive §3.2 wants λ "used";
the prior lean was "recommend a soft term"). **The diagnostic REVISES that lean: do not wire λ as a
feasibility term.**

## Question
λ_ox (reorganization energy on oxidation) is computed per monomer as a reported-only secondary
descriptor: `λ_ox = vertical_IP − adiabatic_IP` (GFN2-xTB, gas phase; `src/eps/properties/secondary_descriptors.py`).
The naive Marcus intuition behind directive §3.2 is "larger λ ⇒ larger electron-transfer / radical-coupling
barrier ⇒ less likely to electropolymerize." **Test it:** does λ_ox separate feasibility-YES monomers from
intrinsically-infeasible (chemical-NO) monomers?

## Inputs & method
- λ_ox from `outputs/secondary_descriptors.csv` (the 36-row library) **plus**
  `data/lit_curation/lambda_feasibility_extra_results.csv` — 13 feasibility-set monomers off the library,
  computed with the **same** real GFN2-xTB path on Lop (SGE 417946; `scripts/compute_lambda_extra.py`).
- Feasibility from `data/polymerizability_labels.csv`, collapsed per monomer: **YES** = any YES outcome;
  **NO-chem** = no YES and at least one `negative_type=chemical` (intrinsic); **NO-medium** = NO only in a
  specific medium.
- Analysis: `scripts/analyze_lambda_feasibility.py` (pure-stdlib rank-based Mann-Whitney U + AUC) →
  `outputs/lambda_feasibility/{lambda_feasibility_points.csv, lambda_feasibility_summary.json}`.
- Matched set: **n=29** (16 YES, 11 NO-chem, 2 NO-medium).

> Note on the extra rows' `status=failed`: that flag fired ONLY because the orthogonal cation
> **spin-density** sub-descriptor hit a cache `NOT NULL` IntegrityError; `vertical_IP`/`adiabatic_IP`
> (hence λ_ox) computed cleanly. The analyzer gates on a finite λ_ox, not on the conflated status flag.
> The spin-density write bug is logged separately (it is, ironically, the descriptor that *would* capture
> the real mechanism — see below).

## Result — λ_ox does NOT carry usable feasibility signal (and the weak signal is INVERTED)

| group | n | λ_ox mean (eV) | median | std | range |
|---|---:|---:|---:|---:|---|
| **YES** (feasible) | 16 | **0.195** | 0.230 | 0.110 | 0.012 – 0.329 |
| **NO-chem** (intrinsic) | 11 | **0.081** | 0.084 | 0.038 | 0.043 – 0.178 |
| NO-medium | 2 | 0.192 | — | 0.058 | 0.135 – 0.250 |

- **AUC(λ higher in NO-chem than YES) = 0.239** — i.e. P(YES has higher λ than NO-chem) = **0.76**.
  Mann-Whitney U=42, p≈0.023 (normal approx, no tie correction; small-n → indicative not definitive).
- The intrinsic-NO monomers have **lower** λ_ox, not higher. This is the **opposite** of the
  "large λ ⇒ infeasible" hypothesis. Any classifier built on it would run backwards, and even inverted it
  is unusable because the distributions overlap almost completely (YES spans 0.012–0.329, swallowing the
  entire NO-chem range 0.043–0.178).

### The decisive evidence is within-family, where electronics are held fixed
| YES | λ_ox | NO-chem (same family) | λ_ox | what differs |
|---|---:|---|---:|---|
| 3-ethylcarbazole | 0.040 | 3,6-diethylcarbazole | 0.045 | 2nd ethyl blocks the 3,6 coupling sites |
| 3-ethylcarbazole | 0.040 | 3-tert-butylcarbazole | 0.046 | bulky 3-substituent | 
| carbazole | 0.068 | 3,6-diphenylcarbazole | 0.105 | 3,6 coupling sites blocked (NO has *higher* λ) |
| 3-methylthiophene | 0.271 | 2,5-dimethylthiophene | 0.095 | α,α′ coupling sites blocked (YES has *higher* λ) |
| (triphenylamine couples para) | 0.084 | tris(4-bromophenyl)amine | 0.054 | para positions blocked by Br |

In every family the feasibility flip is set by **whether the radical-coupling positions are open**, while
λ_ox barely moves (or moves the wrong way). λ_ox measures how much the *radical cation relaxes its
geometry*; it is **physically blind to which ring positions are available for C–C coupling.**

## Interpretation — why this is the expected, not surprising, answer
The dominant infeasibility mechanism in our NO set is **coupling-site blocking** — a structural / steric /
topological property of where the radical cation can dimerize (THINK T15: position-blocked ⇒ intrinsic-NO).
λ_ox is an *electronic* reorganization energy; it cannot encode site availability. Worse, blocking
substituents often **rigidify** the ring (3,6-di-tert-butylcarbazole, fused benzofuran) and *lower* λ, which
is why the weak signal points the wrong way. So λ_ox is not merely weak for feasibility — it is the **wrong
observable** for the question.

This is quantitative confirmation of THINK T15: the optical/Eox/feasibility "NO" monomers fail for a
steric-topological reason an electronic single-molecule descriptor cannot see.

## Decisions (within directive authority; decide-and-report)
1. **Do NOT wire λ_ox as a feasibility filter or feasibility soft term.** This **supersedes** the earlier
   T16 lean ("recommend a soft term"). Justification: no separation (AUC 0.24, fully overlapping), and the
   only signal present is mechanistically spurious (it tracks ring rigidity, not coupling-site availability).
2. **Keep λ_ox as a reported-only descriptor for its legitimate meaning — charge-transport / polaron
   self-trapping**, not feasibility. This satisfies directive §3.2's "compute and report λ" without
   misusing it. No change to scoring (`configs/scoring.yaml` unchanged).
3. **The feasibility-relevant electronic descriptor is the cation spin at coupling sites**
   (`monomer_cation_max_spin_is_alpha` / `monomer_cation_alpha_spin_sum`) — it directly asks "does the
   radical localize on an *open* α/coupling position?" That is the descriptor to develop for a feasibility
   axis, and it is currently broken by the spin-density cache `NOT NULL` write bug surfaced here. Fixing it
   is the actionable follow-up (logged separately), not λ.

## Honesty / limits
- n=29, with NO-chem dominated by carbazoles/triarylamines; not a balanced multi-family sample. The verdict
  ("λ does not separate feasibility, and the mechanism is steric") is robust to this because it rests on the
  *within-family* contrasts, which hold electronics fixed — but the exact AUC/p are indicative, not a
  powered hypothesis test.
- λ_ox here is gas-phase GFN2 vertical−adiabatic IP; solvent reorganization (the outer-sphere Marcus term)
  is not included. Adding it would not rescue the feasibility use — outer-sphere λ is even less
  site-specific — but it is the honest caveat on the absolute λ values.

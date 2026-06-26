# B1–B3: coupling-feasibility criterion — results

_2026-06-25 director run. Directive §5; THINK T15. Evidence: real GFN2-xTB (SGE 417846/417848,
`conf-mmff94-n100`), structural RDKit analysis, canonical 36-row feasibility set._

## Question

Current feasibility prediction = `predicted-YES := Tier-1 survivor` (passes the 3 hard constraints).
It ignores coupling, so it passes a class of NO whose radical cation forms in-window but cannot build
a film (coupling site blocked / radical too stable). Directive §3.1 asks for spin density +
dimerization energy as coupling signals. **Can screening-grade descriptors separate the 7 intrinsic-NO
anchors from YES?**

## The three candidate signals — what actually exists

| signal | availability | finding |
|---|---|---|
| #1 α-/coupling-site count | RDKit (no calc) | **class-dependent**; only a *position-block* detector (below) |
| #2 dimerization ΔG | real GFN2-xTB | computed, but **size-confounded (r=0.67)** and uninformative even size-matched (below) |
| #3 radical-cation α-spin | — | **UNAVAILABLE**: GFN2-xTB 6.4.1 emits only Mulliken charges, no atomic spin (code `xtb.py:638-643` + live probe). All 36 harvest monomers have `secondary_monomer_calc_status=failed` for spin. → Tier-2 / Fukui only |

Sample reality: the 7 intrinsic-NO anchors are **absent from the production harvest** (its 36 monomers
overlap the canonical-36 feasibility set in only 10, none intrinsic-NO), so B1 required a dedicated
size-matched batch — not the "zero new calculation" the compact assumed.

## Signal #2 — size-matched dimerization ΔG (SGE 417846/417848)

Raw `dimerization_dG` tracks molecular size (Pearson r=0.67 with heavy-atom count over 36 monomers),
so the only valid test is each intrinsic NO vs its closest YES analog:

| intrinsic NO | heavy | dG (kcal/mol) | size-matched YES | heavy | dG | separated? |
|---|---|---|---|---|---|---|
| 3-thiophenecarboxaldehyde (electronic) | 7 | **−21.2** | 3-methylthiophene / thiophene | 6 / 5 | +9.5 / −20.1 | **NO** — looks *favorable* (≈ thiophene) |
| 3,4-dibutylthiophene (β-steric) | 13 | **+36.6** | 3-hexylthiophene | 11 | +32.9 | **NO** — Δ+3.7 ≈ the 2-heavy-atom size offset alone |
| 2,5-dimethylpyrrole (α,α′-blocked) | 7 | dimer **BUILD-FAILS** (0 free α) | pyrrole | 5 | −3.9 | caught by signal #1, not #2 |

The planar α-dimer formation energy is **thermodynamically normal** for the electronic and β-steric
NOs because their failure is kinetic/electronic (aldehyde EC′) or out-of-plane steric — invisible to a
thermodynamic α-dimer ΔG. **Signal #2 does not separate them.**

## B1 verdict

Only the **per-class coupling-SITE-availability signal** separates intrinsic NO from YES, and only for
**position-blocked** monomers. The intrinsic-NO failure modes partition:

- *Position-blocked* (α,α′-diblocked pyrroles; 3,6-blocked carbazoles) → **separable** (signal #1, per class).
- *Electronic* (3-thiophenecarboxaldehyde), *β-steric* (3,4-dibutylthiophene), *radical-overstabilized*
  (1-aminopyrene), *3,3′-only-dimerizing* (N-phenylcarbazole) → **screening-grade blind spots → Tier-2 / explicit kinetics.**

This is itself the directive-anticipated finding: "不可分 → 需 Tier-2/显式动力学（这本身是重要发现）."

## B2 — implemented soft flag

`src/eps/properties/coupling_risk.py` → `coupling_risk_flag(smiles, coupling_mode, min_free_alpha=…)`.
Reported-only; **never** changes survivors or the composite (hard reject = PI, `DECISIONS_PENDING` B4).
Thresholds from `configs/tier1.yaml: coupling_risk` (not hardcoded). Per-class rules:
- α-coupling 5-rings: flag if free-α count < `min_free_alpha` (default 1 → flags only α,α′-diblock; one
  free α still couples, so 2-methylfuran/YES is **not** flagged).
- carbazole scaffold: flag if **both** 3- and 6-positions substituted (alkyl or aryl); ≥1 free site → ok.
- other explicit couplers (fluorene/aniline/…): `not_assessed` (disclosed, not faked).

## B3 — validation on the canonical-36 (structural; no harvest needed)

On **simple** monomers (condition-specific NOs excluded — those are window/medium failures, not the
flag's job):

| | n | result |
|---|---|---|
| intrinsic NO caught | 3 / 7 | 2,5-dimethylpyrrole, 3,6-di-tert-butyl-/3,6-diphenyl-carbazole |
| intrinsic NO missed (Tier-2) | 4 / 7 | 1-aminopyrene, 3,4-dibutylthiophene, 3-thiophenecarboxaldehyde, N-phenylcarbazole |
| YES false-flags | **0 / 11** | — |

recall(intrinsic-NO) = 0.43, recall(YES) = 1.00 → **balanced accuracy 0.71** vs **0.50** baseline
(survivor-only, which ignores coupling and catches 0 intrinsic NOs).

**Known limitation (keeps it soft):** the flag can FALSE-POSITIVE on fused/constructed SMILES where
`detect_alpha_carbons` under-counts — e.g. the EDOT–CHO–EDOT trimer (a YES) is mis-flagged
`risk_alpha_blocked`. Constructed/oligomeric monomers must be reviewed, not auto-rejected.

## Recommendation (B4 → PI)

Keep `coupling_risk_flag` a **soft, reported** second-tier screen (catches position-blocked NOs at zero
false-positive cost on simple YES; improves balanced accuracy 0.50→0.71). Do **not** promote to a hard
reject: 4/7 intrinsic NOs are screening blind spots and the flag mis-fires on fused SMILES. The
electronic/β-steric/radical-stability NOs are a documented Tier-2 / explicit-kinetics need. Wiring the
flag into the harvest/feasibility report is a follow-up gated on the feasibility-anchor monomers being
in the library (the library-expansion / promote decision).

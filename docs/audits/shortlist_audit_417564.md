# Per-row artifact audit — 417564 30-row diagnostic shortlist

_Audit date: 2026-06-22 · Branch: `track/shortlist-audit` · Author task: formulation/data-artifact audit_

> **Scope and honesty boundary.** This is a **recommendation document**, not an edit to the
> shortlist and **not an experimental order list**. The audited artifact is the standards-compliant
> **diagnostic, screening-grade** 30-row shortlist emitted by read-only analysis job **417564**
> (`outputs/tier1_real_7488_capped_esw/analysis_standard_csv/shortlist.csv`, gitignored cluster
> output fetched read-only from Lop). Every conclusion below is screening-grade triage; none of it
> promotes any triad to an experiment. No `src/`, config, scoring-weight, or `data/*.csv` file was
> touched; no cluster job was submitted.

## 0. Inputs and provenance

| Input | Source | Role |
| --- | --- | --- |
| `shortlist.csv` (30 rows, 151 cols) | Lop `…/tier1_real_7488_capped_esw/analysis_standard_csv/` (read-only scp) | audited artifact |
| `summary.csv` | same dir | retention context |
| `tier1_all.csv` (7,488 rows) | Lop `…/tier1_real_7488_capped_esw/` | per-row descriptor cross-ref |
| `configs/scoring.yaml` | repo (read-only) | composite weights |
| `data/solvent_windows.csv`, `electrolytes.csv`, `polymerizability_labels.csv`, `needs_review.md`, `STATUS.md` | repo (read-only) | formulation / evidence cross-ref |

**Composite weights** (`configs/scoring.yaml`): window_margin **0.30**, anion_stability **0.20**,
solubility **0.20**, dimerization **0.15**, band_gap_deviation **0.15**.
The three axes STATUS flags as **uncalibrated** — solubility (dGsolv proxy), dimerization
(unknown proton-reference offset), band_gap/optical_gap (sTDA-xTB, uncalibrated vs TD-DFT) — sum to
**0.50 of the score**. The two better-grounded axes (window_margin, anion_stability) sum to the
other 0.50.

**Composition of the 30 rows.** Solvent: **24 propylene carbonate (PC) / 6 acetonitrile (MeCN)**.
Salt: TBABF4 ×9, LiBF4 ×4, AgClO4 ×3, HClO4 ×3, NaClO4 ×3, LiClO4 ×3, TBAClO4 ×3, LiTFSI ×1,
TBATFSI ×1. Monomers: terfuran ×10, terthiophene ×8, fluorene 9,9-dioctyl ×8, bifuran ×2,
o-methoxyaniline ×1, diphenylamine ×1. All 30 are on `pareto_front=True`.

## 1. Two structural artifacts that dominate the whole list

### A. Salt-permutation **score degeneracy** (the top recurring artifact)
The composite score for a fixed **(monomer, solvent, anion)** is **independent of the cation**:
- `window_margin` — on **PC** the solvent window is *solvent-only* (salt-agnostic), so it does not
  change with the salt at all;
- `anion_stability` — depends only on the **anion**;
- `solubility`, `dimerization`, `band_gap` — depend only on the **monomer**.
The cation enters the pipeline only through the `cation_reduction_below_solvent_cathodic` **pass/fail
filter** (True for all 30 rows) and the **report-only** ion-pair term. Result: the five ClO₄⁻ salts
(**AgClO4, HClO4, NaClO4, LiClO4, TBAClO4**) on the same monomer/PC produce **five rows with byte-
identical composite scores**. Three such 5-way clusters exist (terfuran/PC/ClO4 = 0.642396,
fluorene/PC/ClO4 = 0.590052, terthiophene/PC/ClO4 = 0.584086), plus BF4 and TFSI 2-way clusters.

The 30 rows collapse to **14 distinct (monomer, solvent, anion) chemistries** (6 MeCN + 8 PC). The
"24/30 PC" headline is therefore **inflated by cation permutations**, and this degeneracy is exactly
what smuggles **AgClO4** (reference-electrode salt) and **HClO4** (acid) into the top-30 — they ride
in as zero-information duplicates of the legitimate TBAClO4/LiClO4 rows.

### B. PC window is **solvent-only, computed-capped** (weaker evidence than MeCN)
PC anodic gate = **2.947 V**, `source = measured_conditioned_capped_by_fallback`,
`condition_match = solvent_only_conservative`, measurement salt = *(none; Et4NBF4 solvent-only,
B-crossref, native 3.6 V)*, **`cap_applied = True`** (3.6 V capped down to the 2.947 V computed
prior). So PC is **not riding an over-wide ESW** — the minimum-of-all-evidence cap did its job
(contrast the parked GBL 5.2 V artifact). But PC's gate is a **computed prior on solvent-only
B-tier evidence with no exact-salt match**. MeCN's gate = **3.245 V**, `measured_conditioned`,
`condition_match = exact_salt_conservative` (**exact TBABF4 match**, A-crossref, `cap_applied =
False`). **MeCN window evidence is materially stronger than PC's.** PC ranks high on a legitimately
wide-but-computed, salt-agnostic window — a caveat, not a removal trigger, but it is the mechanism
behind PC's apparent dominance.

### Universal (all-30) data caveats
- `oligomer_Eox_calibration_out_of_domain = **True** for all 30 rows` — every shortlisted Eox sits
  outside the calibration domain (Eox is an inclusion filter, not a scored axis, but it gates entry).
- `secondary_monomer_calc_status = failed` for **all 30** (spin-density secondary axis; **report-only**,
  does not affect score — matches `summary.csv` failure_count = 7,488 = every triad).
- `ionpair_calc_status = failed` for **22/30** rows; the 8 that computed return gas-phase-scale
  dissociation ΔG (44–156 kcal/mol), **not** a solution solubility/conductivity proof. Ion-pair is
  **report-only** for all rows. → **No row has validated salt-dissolution / conduction evidence.**
- Uncalibrated axes contribute **22–44 %** of each composite (lowest for the window-dominated
  aniline rows, highest for furan/fluorene rows).

## 2. Per-row verdict table

Driving axes = top weighted contributors (weight×norm). Flags use the shorthand under the table.

| # | monomer | solvent | salt (class) | composite | driving axes (weighted) | unc % | flags | verdict | rationale |
|---|---|---|---|---|---|---|---|---|---|
| 1 | terfuran | MeCN | TBABF4 (TAA) | 0.6840 | window .269 / anion .183 / bgap .148 | 34% | PC-free; exact-salt window; FuranFam; UNCAL; EoxOOD; SecMonRO; IonpairFail | **KEEP** | Lead row: exact-salt A-crossref MeCN window, strongest-evidence solvent gate; oligofuran (not bare furan). Carries only the universal screening caveat. |
| 2 | terfuran | PC | LiBF4 (Li) | 0.6486 | window .225 / anion .181 / bgap .148 | 38% | DEGEN(of R3); PC-SOLV; UNCAL; EoxOOD; IonpairFail | **PARK** | Score-degenerate BF4 duplicate of R3 (TBABF4 rep); Li⁺ compatibility/plating in PC unproven; no new chemistry. |
| 3 | terfuran | PC | TBABF4 (TAA) | 0.6486 | window .225 / anion .181 / bgap .148 | 38% | PC-SOLV(computed window); FuranFam; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | BF4 cluster representative for terfuran/PC; standard nonaqueous salt, but PC window is solvent-only computed (weaker tier than MeCN). |
| 4 | o-methoxyaniline | MeCN | TBABF4 (TAA) | 0.6477 | **window .300** / anion .199 / bgap .096 | 23% | MedMismatch; ApproxCoupling(opt+dimer); UNCAL; EoxOOD; IonpairFail | **CAVEAT** | Aniline family's documented electropolymerization is in **protic acid** (cf. o-toluidine/aniline labels), not aprotic MeCN/TBABF4 → medium mismatch; optical & dimer use approximate coupling site. Window-dominated so robust to uncalibrated axes, but medium must be re-checked. |
| 5 | terfuran | PC | **AgClO4 (silver)** | 0.6424 | window .225 / anion .174 / bgap .148 | 38% | **AgRef**; DEGEN; PC-SOLV; UNCAL; IonpairFail | **REMOVE** | AgClO4 is a **reference-electrode salt**, not a bulk supporting electrolyte; Ag⁺ deposits as metal (the cation_reduction filter, on an uncalibrated computed axis = 4.99 V, does not model plating). Pure score-degenerate duplicate of TBAClO4 (R9). |
| 6 | terfuran | PC | **HClO4 (acid)** | 0.6424 | window .225 / anion .174 / bgap .148 | 38% | **AcidNonaq**; DEGEN; PC-SOLV; UNCAL; SecMonRO | **REMOVE** | Perchloric **acid in aprotic nonaqueous PC** with a non-aniline monomer — not a genuine supporting electrolyte; strong-oxidizer/protic artifact. Degenerate duplicate of TBAClO4 (R9). |
| 7 | terfuran | PC | NaClO4 (Na) | 0.6424 | window .225 / anion .174 / bgap .148 | 38% | NaUnproven; DEGEN; PC-SOLV; UNCAL | **PARK** | Na⁺ supporting-electrolyte compatibility/plating in PC unproven; score-degenerate duplicate of TBAClO4 (R9). |
| 8 | terfuran | PC | LiClO4 (Li) | 0.6424 | window .225 / anion .174 / bgap .148 | 38% | DEGEN(of R9); PC-SOLV; UNCAL; IonpairFail | **PARK** | Legitimate salt but score-degenerate duplicate of TBAClO4 rep (R9); Li⁺ compatibility in PC unproven. |
| 9 | terfuran | PC | TBAClO4 (TAA) | 0.6424 | window .225 / anion .174 / bgap .148 | 38% | PC-SOLV; FuranFam; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | ClO4 cluster representative for terfuran/PC; canonical nonaqueous salt; PC window solvent-only computed. |
| 10 | terthiophene | MeCN | TBABF4 (TAA) | 0.6311 | window .277 / anion .187 / solub .084 | 26% | exact-salt window; lit-supported; UNCAL; EoxOOD; IonpairFail | **KEEP** | Cleanest row: terthiophene electropolymerization is **documented in MeCN/tetraalkylammonium** (labels: YES MeCN/TBAPF6); exact-salt A-crossref window; dimer axis ~0 (not inflating). |
| 11 | fluorene 9,9-dioctyl | MeCN | TBABF4 (TAA) | 0.6242 | window .232 / anion .163 / solub .140 | 37% | OptTrunc; exact-salt window; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | Polyfluorene via 2,7-coupling is real, but optical gap is computed on a **sidechain-truncated** model (octyl removed) → band_gap axis approximate; exact-salt MeCN window is a plus. |
| 12 | diphenylamine | MeCN | TBABF4 (TAA) | 0.6109 | **window .284** / anion .191 / bgap .074 | 22% | MedMismatch; ApproxCoupling(opt+dimer); dimer-prone; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | Arylamine; documented route is **aqueous H₂SO₄** (labels); radical-cation chemistry is dimerization-prone; optical/dimer approximate coupling. Window-dominated, but medium and coupling must be re-checked. |
| 13 | bifuran | MeCN | TBABF4 (TAA) | 0.6091 | window .214 / bgap .150 / anion .153 | 40% | FuranFam; bgap-driven; exact-salt window; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | Oligofuran (furan family flagged difficult; bifuran shorter than terfuran). Rank is **band_gap-driven** (norm 1.0, uncalibrated) — the high rank leans on the uncalibrated optical axis. |
| 14 | fluorene 9,9-dioctyl | PC | TBABF4 (TAA) | 0.5963 | window .186 / solub .160 / anion .160 | 42% | OptTrunc; PC-SOLV; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | BF4 cluster rep for fluorene/PC; PC solvent-only computed window + sidechain-truncated optical; **solubility (uncalibrated) is the #2 driver**. |
| 15 | fluorene 9,9-dioctyl | PC | LiBF4 (Li) | 0.5963 | window .186 / solub .160 / anion .160 | 42% | DEGEN(of R14); OptTrunc; PC-SOLV; UNCAL | **PARK** | Score-degenerate BF4 duplicate of R14; Li⁺/PC unproven. |
| 16 | terthiophene | PC | LiBF4 (Li) | 0.5903 | window .231 / anion .184 / solub .093 | 30% | DEGEN(of R17); PC-SOLV; UNCAL; IonpairFail | **PARK** | Score-degenerate BF4 duplicate of R17; Li⁺/PC unproven. |
| 17 | terthiophene | PC | TBABF4 (TAA) | 0.5903 | window .231 / anion .184 / solub .093 | 30% | PC-SOLV; PC-untested-for-monomer; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | BF4 cluster rep for terthiophene/PC; terthiophene is lit-supported in **MeCN** but **PC is untested** (labels show a wrong-solvent NO in DMF); PC window solvent-only computed. |
| 18 | fluorene 9,9-dioctyl | PC | LiClO4 (Li) | 0.5901 | window .186 / solub .160 / anion .154 | 42% | DEGEN(of R22); OptTrunc; PC-SOLV; UNCAL; IonpairFail | **PARK** | Score-degenerate ClO4 duplicate of R22; legitimate salt but redundant; Li⁺/PC unproven. |
| 19 | fluorene 9,9-dioctyl | PC | NaClO4 (Na) | 0.5901 | window .186 / solub .160 / anion .154 | 42% | NaUnproven; DEGEN; OptTrunc; PC-SOLV; UNCAL | **PARK** | Na⁺/PC compatibility unproven; score-degenerate duplicate of R22. |
| 20 | fluorene 9,9-dioctyl | PC | **HClO4 (acid)** | 0.5901 | window .186 / solub .160 / anion .154 | 42% | **AcidNonaq**; DEGEN; OptTrunc; PC-SOLV; UNCAL; SecMonRO | **REMOVE** | Perchloric acid in aprotic PC with a non-aniline monomer; degenerate duplicate of R22. |
| 21 | fluorene 9,9-dioctyl | PC | **AgClO4 (silver)** | 0.5901 | window .186 / solub .160 / anion .154 | 42% | **AgRef**; DEGEN; OptTrunc; PC-SOLV; UNCAL; IonpairFail | **REMOVE** | Reference-electrode salt mis-used as supporting electrolyte; Ag plating; degenerate duplicate of R22. |
| 22 | fluorene 9,9-dioctyl | PC | TBAClO4 (TAA) | 0.5901 | window .186 / solub .160 / anion .154 | 42% | OptTrunc; PC-SOLV; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | ClO4 cluster rep for fluorene/PC; canonical salt; PC solvent-only computed window + truncated optical; solubility (uncalibrated) is #2 driver. |
| 23 | terthiophene | PC | NaClO4 (Na) | 0.5841 | window .231 / anion .177 / solub .093 | 30% | NaUnproven; DEGEN; PC-SOLV; UNCAL | **PARK** | Na⁺/PC unproven; score-degenerate duplicate of R25. |
| 24 | terthiophene | PC | LiClO4 (Li) | 0.5841 | window .231 / anion .177 / solub .093 | 30% | DEGEN(of R25); PC-SOLV; UNCAL; IonpairFail | **PARK** | Legitimate salt, score-degenerate duplicate of R25; Li⁺/PC unproven. |
| 25 | terthiophene | PC | TBAClO4 (TAA) | 0.5841 | window .231 / anion .177 / solub .093 | 30% | PC-SOLV; PC-untested-for-monomer; UNCAL; EoxOOD; IonpairFail | **CAVEAT** | ClO4 cluster rep for terthiophene/PC; PC untested for this monomer; PC window solvent-only computed. |
| 26 | terthiophene | PC | **AgClO4 (silver)** | 0.5841 | window .231 / anion .177 / solub .093 | 30% | **AgRef**; DEGEN; PC-SOLV; UNCAL; IonpairFail | **REMOVE** | Reference-electrode salt mis-use; Ag plating; degenerate duplicate of R25. |
| 27 | terthiophene | PC | **HClO4 (acid)** | 0.5841 | window .231 / anion .177 / solub .093 | 30% | **AcidNonaq**; DEGEN; PC-SOLV; UNCAL; SecMonRO | **REMOVE** | Acid in aprotic PC with a non-aniline monomer; degenerate duplicate of R25. |
| 28 | terfuran | PC | LiTFSI (Li) | 0.5761 | window .225 / bgap .148 / anion .108 | 42% | DEGEN(of R29); TFSIlowAnion; PC-SOLV; UNCAL | **PARK** | Score-degenerate TFSI duplicate of R29; TFSI anion-stability margin is markedly lower (norm 0.54 vs 0.87 for ClO4); Li⁺/PC unproven. |
| 29 | terfuran | PC | TBATFSI (TAA) | 0.5761 | window .225 / bgap .148 / anion .108 | 42% | TFSIlowAnion; PC-SOLV; FuranFam; UNCAL; EoxOOD | **CAVEAT** | TFSI cluster rep for terfuran/PC; canonical salt but lower anion-stability margin; band_gap (uncalibrated) is the #2 driver. |
| 30 | bifuran | PC | LiBF4 (Li) | 0.5705 | window .169 / bgap .150 / anion .151 | 44% | sole-rep; FuranFam; bgap-driven; PC-SOLV; UNCAL; IonpairFail | **CAVEAT** | Sole representative of bifuran/PC/BF4 (no degenerate twin), so kept as CAVEAT not PARK; **highest uncalibrated share (44 %)**, rank leans on the uncalibrated band_gap axis; Li⁺/PC unproven. |

**Flag shorthand.** DEGEN = salt-permutation score-degenerate duplicate (cation ignored by score) ·
PC-SOLV = PC anodic window is solvent-only, computed-capped (weaker tier than exact-salt) ·
UNCAL = uncalibrated axes (solubility+dimerization+band_gap) carry a large score share ·
AgRef = AgClO4 reference-electrode salt mis-used as supporting electrolyte ·
AcidNonaq = acid (HClO4) in nonaqueous aprotic system ·
MedMismatch = monomer's documented electropolymerization medium ≠ the paired medium ·
OptTrunc = optical gap computed on sidechain-truncated model · ApproxCoupling = optical/dimer use
an approximate coupling site · NaUnproven = Na⁺ supporting-electrolyte compatibility/plating unproven ·
TFSIlowAnion = TFSI anion-stability margin notably lower · FuranFam = oligofuran (furan-family
electropolymerization caveat) · EoxOOD = oligomer Eox calibration out-of-domain (all 30 rows) ·
SecMonRO/IonpairFail = report-only secondary_monomer failure (all rows) / ion-pair term failed or
report-only (no dissolution evidence).

## 3. Summary

**Verdict counts:** **KEEP 2 · CAVEAT 12 · PARK 10 · REMOVE 6** (total 30).

- **KEEP (2):** R1 terfuran/MeCN/TBABF4, R10 terthiophene/MeCN/TBABF4 — both PC-free, on the
  **exact-salt A-crossref MeCN window** (strongest evidence tier), R10 additionally **literature-
  supported** for MeCN/TAA electropolymerization. "Clean" is relative: even these carry the
  **universal screening caveat** (uncalibrated axes 26–34 %, Eox out-of-domain, ion-pair/secondary
  report-only failures).
- **CAVEAT (12):** the distinct-chemistry representatives — one salt per (monomer, solvent, anion)
  cluster — plus the two aniline-family MeCN rows and the bifuran sole-rep. Defensible as screening
  candidates but each carries a specific named caveat (PC solvent-only computed window; sidechain-
  truncated optical; furan-family; aniline medium mismatch; TFSI low anion margin; PC-untested-for-
  monomer; uncalibrated-axis dependence).
- **PARK (10):** legitimate-but-redundant salts (Li/Na variants) that are **score-degenerate
  duplicates** of a CAVEAT representative and add no new chemistry; Li⁺/Na⁺ compatibility in PC is
  unproven. Park pending salt-solubility/conductivity validation and de-duplication of the score.
- **REMOVE (6):** all **AgClO4 (R5, R21, R26)** and **HClO4 (R6, R20, R27)** rows — a reference-
  electrode silver salt and a strong protic acid, neither a genuine nonaqueous supporting
  electrolyte, each present only as a score-degenerate duplicate.

**Top recurring artifact:** **salt-permutation score degeneracy** — the composite ignores the
cation, so every (monomer, solvent, anion) chemistry appears up to 5× (one per cation) at an
identical score. This single artifact (a) inflates the apparent PC dominance and (b) admits the
AgClO4/HClO4 rows. Secondary recurring artifacts: PC's solvent-only computed-capped window (all 24
PC rows), uncalibrated-axis dependence carrying 22–44 % of every score, and the all-row ion-pair /
secondary_monomer report-only failures + Eox-out-of-domain flag (no row has validated salt-
dissolution evidence).

**Is the shortlist still PC-dominated after artifact removal?**
- Raw: **24 PC / 6 MeCN (80 % PC)**.
- After REMOVE (6, all PC): 18 PC / 6 MeCN (**75 % PC**).
- After REMOVE + PARK (collapsing salt degeneracy): **8 PC / 6 MeCN (≈57 % PC)** — i.e. at the level
  of **distinct (monomer, solvent, anion) chemistries** the list is **6 MeCN + 8 PC**.
- **Conclusion:** PC still leads, but the overwhelming 80 % dominance is **largely a salt-permutation
  degeneracy artifact**, not a chemistry signal — and it is **not** driven by an over-wide ESW (the
  min-of-all-evidence cap reduced PC's 3.6 V solvent-only measurement to the 2.947 V computed prior).
  PC's residual lead rests on a legitimately wide but **solvent-only, computed** window that admits
  every salt equally; MeCN's 6 rows rest on **stronger, exact-salt measured** window evidence.

## 4. Rows that MUST be re-checked before any experimental hand-off

1. **All 6 REMOVE rows (R5, R6, R20, R21, R26, R27)** — salt identity/role: AgClO4 is reference-
   electrode-only (Ag plating); HClO4 is a protic acid mis-cast as a nonaqueous supporting
   electrolyte. The `cation_reduction` filter passed them on an **uncalibrated computed axis** and
   does **not** model metal deposition — do not treat the pass as protective.
2. **Aniline-family medium mismatch — R4 (o-methoxyaniline) and R12 (diphenylamine)** — documented
   electropolymerization is in **protic/acidic** media, not aprotic MeCN/TBABF4; both also use an
   **approximate coupling site** for optical and dimerization. Re-check medium and coupling before use.
3. **Na⁺ rows — R7, R19, R23 (NaClO4)** and **all Li⁺ rows (R2, R8, R15, R16, R18, R24, R28, R30)** —
   alkali-cation supporting-electrolyte compatibility, solubility, and plating in PC/MeCN are unproven.
4. **TFSI rows — R28, R29** — markedly lower anion-stability margin (norm 0.54 vs 0.87 for ClO4/BF4).
5. **Fluorene rows — R11, R14, R15, R18–R22** — optical gap computed on a **sidechain-truncated**
   (octyl-removed) model; the band_gap axis is approximate.
6. **terthiophene/PC rows — R16, R17, R23–R27** — terthiophene is lit-supported in **MeCN** but **PC
   is untested** for this monomer (a wrong-solvent NO is on record for terthiophene/DMF).
7. **Every row (all 30)** — (a) **salt dissolution/conductivity/ion-pairing is unvalidated** (ion-pair
   term failed for 22/30 and is report-only for all; the computed values are gas-phase-scale, not a
   solubility proof); (b) **oligomer Eox calibration is out-of-domain**; (c) uncalibrated axes
   (solubility, dimerization, optical/band_gap = 0.50 weight) remain unvalidated per STATUS debt
   items 3–6. This shortlist is a **diagnostic, screening-grade** route-validation artifact, **not an
   experimental order list**.

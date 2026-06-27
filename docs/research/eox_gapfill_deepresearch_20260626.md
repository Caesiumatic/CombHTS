# Eox gap-fill deep research (2026-06-26) — small-monomer primary CV anchors

Status: **decide-and-report; NOTHING staged into production.** Autonomous deep-research pass (workflow
`wf_eb8942d7-050`, 101 agents, 19 sources, 72 claims → 25 verified → 19 confirmed). Goal: find clean
primary-CV monomer oxidation potentials for the canonical electropolymerization monomers that currently
lack an anchor in `data/benchmark.csv` (EDOT, pyrrole, N-methylpyrrole, EDOP, furan, selenophene, EDOS,
carbazole, ProDOT, 3-hexylthiophene, 3,4-dimethylpyrrole, 3-methylfuran), on the aqueous Ag/AgCl scale.

## Headline finding (itself valuable)
**No directly-usable, convertible primary value was obtainable in this pass.** Every candidate failed on at
least one strict rule, and the failures cluster into two systematic walls:
1. **Paywall.** The cleanest primary CV tables (Tabba & Smith 1984 pyrroles; Diaz 1981 pyrroles; Aqad/Cava
   2001 EDOS; carbazole JES) return HTTP 403 — values not machine-extractable from the open web.
2. **Non-aqueous Ag/Ag⁺ or BFEE reference.** The classic electropolymerization CV literature
   overwhelmingly reports vs a non-aqueous Ag/Ag⁺ (AgNO₃/MeCN) pseudo-reference or in BFEE, **not** vs
   Ag/AgCl, SCE, or Fc/Fc⁺-in-MeCN — so even open-access values are *unconvertible* under our rules
   (this is the same structural reason NMP/sulfolane ESW failed; see `esw_nmp_thf_sulfolane_gapfill_20260626.md`).

This explains *why* these canonical anchors were missing from `benchmark.csv`: they exist, but mostly off
our master scale. Net: the gap is real and only closable via primary PDFs (where an internal Fc calibrant
or a true Ag/AgCl/SCE reference may exist in the full text).

> Caveat: the run was truncated by a session usage limit (synthesis phase + 4 verifications skipped/abstained).
> A resume (`resumeFromRunId: wf_eb8942d7-050`, after the limit resets) would complete synthesis and the
> abstained checks; the needs-PDF list below already captures the actionable output.

## NEEDS-PDF list (give me these PDFs → I extract + stage)
Priority order. For each: what to pull = the monomer first-anodic **peak (Epa)** and/or **onset**, plus
solvent / supporting electrolyte (+conc.) / working electrode / **reference electrode** / scan rate.

| # | source | DOI / URL | what to extract | why |
|---|---|---|---|---|
| 1 | **Tabba & Smith 1984**, *J. Org. Chem.* 49(11), 1870–1875 | `10.1021/jo00185a005` — https://pubs.acs.org/doi/abs/10.1021/jo00185a005 | pyrrole, N-methylpyrrole, 3,4-dimethylpyrrole Epa + the exact reference electrode | 117-pyrrole CV table; THE pyrrole-family anchor source. Confirm the reference (if SCE → convertible) |
| 2 | **EDOT / 3-methylselenophene precursor paper** (Dyes \& Pigments 2020) | PII `S025405842030081X` — https://www.sciencedirect.com/science/article/abs/pii/S025405842030081X | EDOT **onset 1.23 V** + 3-MeSe **onset 1.17 V**, confirm "vs Ag/AgCl" | abstract says vs Ag/AgCl → if confirmed, a CONVERTIBLE EDOT onset (our top missing anchor) |
| 3 | **Carbazole**, *J. Electrochem. Soc.* | `10.1149/1.2410929` — https://iopscience.iop.org/article/10.1149/1.2410929 | carbazole monomer Epa + conditions + reference | parent carbazole anchor; fully paywalled, nothing extractable open |
| 4 | **Aqad, Lakshmikantham \& Cava 2001**, *Org. Lett.* 3(26), 4283–4285 | `10.1021/ol0169473` — https://pubs.acs.org/doi/10.1021/ol0169473 | EDOS **absolute** Epa/onset + reference (paper only gave "0.26 V below EDOT") | would anchor EDOS *if* an absolute value + convertible reference is in the text |
| 5 | **Diaz, Martinez, Kanazawa \& Salmon 1981**, *J. Electroanal. Chem.* 130, 181–187 | PII `S0022072881803853` — https://www.sciencedirect.com/science/article/abs/pii/S0022072881803853 | parent pyrrole Epa + reference (note: paper is α,α′-disubstituted pyrroles) | classic Diaz pyrrole CV; may carry parent-pyrrole conditions/reference. Lower priority |
| 6 (optional) | **González-Tejera et al. 1998/99**, *Synth. Met.* (furan/2-methylfuran) | PII `S0379677998015094` — https://www.sciencedirect.com/science/article/abs/pii/S0379677998015094 | check for an internal Fc calibration alongside the Ag⁰/Ag⁺ values | furan 1.75 V / 2-MeF 1.50 V are vs Ag⁰/Ag⁺ (unconvertible) unless an Fc tie is in the full text |

## Documented as unconvertible (do NOT chase for our scale)
- **EDOS** RSC Adv. 2020 `10.1039/D0RA01436B` (open access): EDOS monomer onset 1.09/1.10/1.13 V (TBAClO₄/PF₆/BF₄, MeCN) — but **vs Ag/Ag⁺** → unconvertible. (Already cited for the PEDOS *optical* anchor.)
- **Furan family** González-Tejera (above): vs Ag⁰/Ag⁺ → unconvertible.
- **Selenophene** Synth. Met. `S0167577X04009486`: electropolymerized in **BFEE** (not MeCN/TBA) → out of scope.
- **Polyfuran/terthiophene** Sheberla/Bendikov 2015 `10.1039/c4sc02664k`: Ag/AgCl-**wire pseudo-ref** + onset, no Fc → unconvertible. (Already our polyfuran/terthiophene *optical* anchor.)
- **Bard group oligothiophene/fluorene** Chem. Sci. 2012 `10.1039/c2sc20263h`: oligomers (n≥2), **1:1 benzene:MeCN** mixed solvent → off-target + Fc-MeCN constant inapplicable.
- **CPDT/DTP** ferrocene-functionalized derivatives (PMC9079884): not parent monomers (Fc-ester decorated) → off-target.

## UPDATE 2026-06-26 (PDFs provided — needs-PDF list RESOLVED)
The user supplied 5 PDFs; values extracted and staged in `data/lit_curation/eox_gapfill_candidates_20260626.csv`
(candidates only — NOT promoted to production `data/benchmark.csv`). All converted to Ag/AgCl by allowed/same-paper ties.

**Clean convertible anchors found (library monomers, PEAK = calibration-track quality):**

| monomer | native | ref | → V vs Ag/AgCl | conditions | source | conf |
|---|---|---|---|---|---|---|
| **EDOT** | 1.44 V (peak) | SCE | **1.485** | MeCN/0.1 M TBAPF6/Pt/100 mV/s | Aqad & Cava, *Org. Lett.* 2001, 3, 4283 (10.1021/ol0169473) | high |
| **EDOS** | 1.18 V (peak) | SCE | **1.225** | same paper/conditions | 10.1021/ol0169473 | high |
| **pyrrole** | 1.20 V (Epa) | NaCE≈SCE | **1.245** | MeCN/0.1 M Et4NBF4/Pt/50 mV/s | Diaz, Martinez, Kanazawa, Salmon, *J. Electroanal. Chem.* 1981, 130, 181 | high |
| **pyrrole** (2nd) | 0.920 V (Epa) | Ag/AgNO3 (=+0.337 vs SCE, paper) | **1.302** | MeCN/0.1 M Bu4NClO4/Pt/100 mV/s | Tabba & Smith, *J. Org. Chem.* 1984, 49, 1870 (10.1021/jo00185a005) | medium |
| **N-methylpyrrole** | 1.14 V (Epa) | NaCE≈SCE | **1.185** | MeCN/0.1 M Et4NBF4/Pt/50 mV/s | Diaz 1981 | high |
| **carbazole** | 1.16 V (Ep/2) | SCE | **1.205** | MeCN/0.1 M TEAP/Pt/80 mV/s | Ambrose & Nelson, *J. Electrochem. Soc.* 1968, 115, 1159 | medium (Ep/2, not full Epa) |

Notes / cross-checks:
- **EDOT** now has a clean PEAK (1.485, calibration track) plus a low-confidence ONSET (~1.23 V, Ag/AgCl-wire quasi-ref in DCM; Hu et al., *Mater. Chem. Phys.* 2020, 244, 122699, 10.1016/j.matchemphys.2020.122699). Peak−onset ≈ 0.25 V, internally consistent.
- **pyrrole**: two independent PEAK values (1.245 vs 1.302) differ by ~60 mV — within the ~0.05–0.15 V reference floor; report both, mean ≈ 1.27 V.
- EDOS/EDOT paper notes "Fc/Fc⁺ shows 0.33 V under conditions" (vs the standard ~0.40 V vs SCE) → ~0.05–0.07 V reference uncertainty; SCE→Ag/AgCl +0.045 used (project standard).
- **B1/feasibility corroboration (bonus):** Diaz 1981 reports 2,5-dimethylpyrrole Epa 0.84 V and that α,α′-blocked pyrroles give *soluble* products / **no film** (vs N-substituted/parent pyrroles which form conducting films); Ambrose 1968 reports carbazoles with N and 3,6 positions blocked become electrochemically *reversible* (no coupling). Both independently confirm the THINK T15 "position-blocked → intrinsic-NO" mechanism.

**Promotion recommendation:** EDOT/EDOS/pyrrole/N-methylpyrrole are native-SCE-convertible irreversible PEAKs in MeCN — i.e. they meet the strict-set (tier-A) criteria and would strengthen the n=9 strict calibration set with canonical, chemically-diverse heteroaromatic monomers (it currently lacks EDOT/pyrrole/carbazole). carbazole is Ep/2 (half-peak) → tier-B. Promotion changes the calibration fit (a method change) → requires sign-off + re-validation under the freeze discipline; staged pending that.

## Recommendation
- Pursue PDFs #1, #2, #3 first (pyrrole family; a possible convertible EDOT onset; carbazole). #2 is the
  highest-value single item — a convertible EDOT anchor would fill the most glaring gap.
- Keep treating the EDOS/furan Ag/Ag⁺ values as *known-but-unconvertible* (record, never convert).
- Optionally resume `wf_eb8942d7-050` after the session limit resets to complete synthesis + the
  EDOT-specific Fc-in-MeCN search angle that abstained.

---

## ROUND-2 deep research 2026-06-26 (wf_33fd5a6c-4fe) — remaining canonical monomers: 0 convertible, paywall-bound

A second dedicated pass targeted the still-missing monomers (EDOP, furan, selenophene, ProDOT,
3-hexyl/3-methylthiophene, 3,4-dimethylpyrrole, 3-methylfuran, bithiophene, terthiophene). It was
**truncated by a session usage limit** (synthesis + most verifications failed; 9 verified claims returned).
**Net new convertible anchors: zero.** The verified claims are all walls, and they cluster the same two ways
as round 1 (paywall / non-convertible reference). Honest, useful negative result: the canonical-monomer Eox
gap is **paywall-bound**, not absent.

### NEEDS-PDF list (round 2) — give me these PDFs → I extract + stage
| # | source | DOI | what to extract | why |
|---|---|---|---|---|
| 1 | **Gaupp, Zong, Schottland, Thompson, Thomas & Reynolds 2000**, *Macromolecules* 33, 1132–1133 | `10.1021/ma9916180` | parent **EDOP** monomer Epa/onset + reference electrode + electrolyte | THE primary PEDOP-from-EDOP electrochemistry paper; verified-real, fully paywalled (403). Top EDOP anchor. |
| 2 | **Welsh, Kumar, Meijer & Reynolds 1999**, *Adv. Mater.* 11(16), 1379–1382 | `10.1002/(SICI)1521-4095(199911)11:16<1379::AID-ADMA1379>3.0.CO;2-Q` | **ProDOT** (and ProDOT-Me2) monomer Epa/onset + reference | verified-real, paywalled (402). The ProDOT anchor. |
| 3 | **Tourillon & Garnier 1982**, *J. Electroanal. Chem.* 135, 173–178 | `10.1016/0022-0728(82)90015-8` | parent **thiophene** and **furan** monomer oxidation potentials + reference electrode | seminal CV electropolymerization paper; verified-real, 403. Could anchor parent thiophene AND furan Eox. |

### Documented unconvertible / not-the-target (round 2; do NOT chase for our scale)
- **Parent furan / terfuran** (PMC5586207, Bendikov-type): smallest species is terfuran (not parent furan), and
  all potentials vs an **Ag/AgCl-wire pseudo-reference with no ferrocene calibrant** → unconvertible.
- **Substituted EDOP/ProDOP** (ACS Omega `10.1021/acsomega.8b00871`, `.8b02026`): only N-aryl/alkyl-substituted
  derivatives studied, and only an **aggregate range 0.96–1.12 V** is given — no individual monomer value and
  not the parent target.
- **"bithiophene/terthiophene"** hit (PMC9078966): actually benzofulvene polymers with oligothiophene side
  chains, not the parent oligomers → off-target.
- **Selenophene (parent):** no clean primary convertible value surfaced (consistent with round 1: parent
  selenophene electropolymerization is reported in BFEE or vs Ag/Ag⁺).

**Verdict:** the remaining canonical Eox anchors are real but locked behind 3 paywalled primary papers
(EDOP, ProDOT, parent thiophene+furan). Supplying those 3 PDFs is the unblock — the same route that turned
the round-1 needs-PDF list into 6 promoted anchors. A resume after the limit resets would only re-confirm the
walls; it cannot defeat a paywall.

### UPDATE 2026-06-26 — all 3 round-2 PDFs supplied; extracted + promoted

The user supplied the 3 paywalled PDFs. Extraction result (benchmark grew 45 → **48** rows; strict tier-A
peak set UNCHANGED at n=9 → production `tier1.yaml` untouched):

| monomer | paper | native | conversion → Ag/AgCl | result | track | status |
|---|---|---|---|---|---|---|
| **EDOP** | Gaupp et al. *Macromolecules* 2000, 33, 1132 (`10.1021/ma9916180`) | Ep,m **+0.7 V vs Ag/Ag⁺**, 0.1 M LiClO₄/**PC**, Pt, 20 mV/s | same-paper Ag/Ag⁺→SCE tie (E1/2 −0.5 Ag/Ag⁺ = ca. −0.3 SCE ⇒ **+0.20**) then SCE→Ag/AgCl **+0.045** = +0.245 | **0.945 V** | peak (tier B) | **PROMOTED** |
| **furan** (parent) | Tourillon & Garnier *J. Electroanal. Chem.* 1982, 135, 173 (`10.1016/0022-0728(82)90015-8`) | +1.85 V vs SCE, MeCN/0.1 M Bu₄NClO₄, Pt, 20 mV/s | SCE→Ag/AgCl +0.045 | **1.895 V** | onset (tier B) | **PROMOTED** (first parent-furan anchor) |
| **pyrrole** (onset) | Tourillon & Garnier 1982 (same) | +0.80 V vs SCE | SCE→Ag/AgCl +0.045 | **0.845 V** | onset (tier B) | **PROMOTED** (pyrrole had peaks only) |
| thiophene (onset) | Tourillon & Garnier 1982 (same) | +1.6 V vs SCE → 1.645 | — | 1.645 V | onset | **NOT promoted** — thiophene onset already in benchmark (Camarada 2011, 1.5 V); Tourillon corroborates (~0.15 V spread) |
| **ProDOT** | Welsh et al. *Adv. Mater.* 1999, 11, 1379 (`10.1002/...ADMA1379`) | film grown potentiostatically at **+1.2 V vs Ag/Ag⁺** | — | — | — | **WALL CONFIRMED** — no CV monomer peak/onset; only a deposition setpoint vs an uncalibrated Ag/Ag⁺ pseudo-ref (no Fc). Unconvertible. |

Notes:
- **EDOP** is the key new canonical monomer (it was entirely absent). Tier B (PC solvent + same-paper "ca."
  Ag/Ag⁺→SCE tie → ~0.1–0.2 V reference floor). Internal cross-check holds: the paper states EDOP oxidizes
  0.25 V easier than EDOT and 0.5 V easier than pyrrole, consistent with our EDOT (1.485) / pyrrole (~1.27) peaks.
- The Tourillon values are read off an anodic linear-sweep (current "rises sharply") with no CV peak reported,
  so they are labeled **onset (Eonset)**, not peak — keeping them out of the strict/relaxed peak calibration set.
- **Welsh (ProDOT)**: the only convertible-looking number is a *deposition* potential vs Ag/Ag⁺ — not a monomer
  oxidation observable and not on a convertible reference. ProDOT Eox remains open (needs a CV paper with SCE/
  Ag-AgCl/Fc-in-MeCN). Welsh *does* contain a PProDOT optical spectrum (neutral onset ~2 eV) but only as a
  figure, no numeric gap → not extractable as an optical anchor either.
- Snapshot tests updated (raw/eligible/selected 45→48, all-groups 44→47, relaxed peak 28→29, onset 16→18;
  eox_rescue existing onset 16→18 / peak 29→30, union onset 19→21 / peak 29→30, inventory 48→51). Full Lop
  validation re-fit submitted (SGE 417948).

### UPDATE 2026-06-26 (round 3, deep research wrfy9jvx5) — ProDOT onset found (the round-2 wall is cleared)

A dedicated ProDOT pass (after the Welsh deposition-setpoint dead end) found a usable value:
**ProDOT onset E_onset = 1.45 V vs Ag/AgCl** — native Ag/AgCl (identity conversion), 0.1 M Et₄NBF₄ in
ACN:DCM (3:1), 50 mV/s, estimated from the first electropolymerization cycle (i.e. the monomer onset before
any film exists). *J. Electrochem. Soc.* 2020, `10.1149/1945-7111/ab7f85`; verbatim: "the onset oxidation
potentials (E_onset) of ProDOT … initiated at 1.45 … V vs. Ag/AgCl." **PROMOTED** to benchmark (onset track,
tier B; benchmark 48 → 49). Confidence **low–med** (deep-research vote 2-1; first-cycle onset estimate; mixed
ACN:DCM solvent — `solvent_name` set to acetonitrile for the solvation model, true medium kept in the medium
column). The substituted perfluoro-ProDOT derivatives (≈1.60 V vs SCE) and ProDOT oligomers/D-A-D trimers
seen in the same pass are off-target and were not used.

Net Eox curation tally across rounds 1–3: **EDOT, EDOS, pyrrole (×2 peak + onset), N-methylpyrrole,
carbazole, EDOP, furan onset, ProDOT onset** all anchored. Still genuinely open: parent **selenophene** Eox
(Ag/Ag⁺/BFEE walls) and a true ProDOT **peak** (only an onset exists so far). Snapshot tests + validation
re-fit (SGE 417955) updated for the 49-row benchmark.

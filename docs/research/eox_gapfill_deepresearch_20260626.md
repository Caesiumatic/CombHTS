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

## Recommendation
- Pursue PDFs #1, #2, #3 first (pyrrole family; a possible convertible EDOT onset; carbazole). #2 is the
  highest-value single item — a convertible EDOT anchor would fill the most glaring gap.
- Keep treating the EDOS/furan Ag/Ag⁺ values as *known-but-unconvertible* (record, never convert).
- Optionally resume `wf_eb8942d7-050` after the session limit resets to complete synthesis + the
  EDOT-specific Fc-in-MeCN search angle that abstained.

# CombHTS Primary-Sourced Monomer Eox Calibration Table — Refinement of Part D

## TL;DR
- The cleanest, highest-confidence anchors are two single-lab/single-scale series on the Ag/AgCl master scale: the Camarada et al. 2011 thiophene-oligomer **onset** series (thiophene 1.50 V, bithiophene 1.15 V, terthiophene 0.880 V) and the Contal/Lakard 2019 carbazole work, which yields both a reversible 9-alkylcarbazole **formal-potential** series (E° 1.11–1.21 V vs Ag/AgCl) and a carbazole/N-vinylcarbazole **peak/onset** pair vs SCE.
- The literature for these film-forming monomers overwhelmingly reports **onset** potentials; clean **anodic-peak (Epa)** values for the small single-ring monomers are genuinely scarce, so the PEAK calibration track is thin and is best supplemented by the reversible carbazole formal potentials kept in a separate sub-model — never pooled with onset rows.
- Several priority small monomers (pyrrole, 3-methylthiophene, 3-hexylthiophene, ProDOT, N-methylpyrrole, EDOP, 3,4-dimethylpyrrole, CPDT, dithienopyrrole) could NOT be upgraded to clean, convertible, single-scale primary CV rows and remain explicit gaps; most published values for them are either deposition/steady-state potentials, BFEE/Lewis-acid media, or bare Ag-wire pseudo-reference numbers that fail the inclusion rules.

## Key Findings

### PRIMARY TABLE (master scale = Ag/AgCl sat'd KCl)

| monomer | SMILES | value_reported | observable | reference_electrode | solvent | electrolyte | electrode | scan_rate | value_vs_AgAgCl | conversion_note | primary_source (DOI) | confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Thiophene | c1ccsc1 | 1.50 V | onset | Ag/AgCl sat KCl | MeCN | (LiClO₄/MeCN) | Pt | — | 1.50 | exact (already Ag/AgCl) | 10.1002/polb.22360 | high |
| Bithiophene | c1ccc(-c2cccs2)s1 | 1.15 V | onset | Ag/AgCl sat KCl | MeCN | (LiClO₄/MeCN) | Pt | — | 1.15 | exact | 10.1002/polb.22360 | high |
| Terthiophene | c1ccc(-c2ccc(-c3cccs3)s2)s1 | 0.880 V | onset | Ag/AgCl sat KCl | MeCN | (LiClO₄/MeCN) | Pt | — | 0.880 | exact | 10.1002/polb.22360 | high |
| Carbazole | c1ccc2c(c1)[nH]c1ccccc12 | 1.05 V | onset | SCE | MeCN | 0.1 M LiClO₄ | Pt wire (0.785 mm²) | 50 mV/s | 1.095 | exact (SCE +0.045) | 10.3389/fmats.2019.00131 | high |
| 9-ethylcarbazole | CCn1c2ccccc2c2ccccc21 | E° 1.21 V (Epa +1.25 V) | formal E° (reversible couple) | Ag/AgCl | MeCN | 0.1 M TBAB | Pt microelectrode (246 µm) | 100 V/s | 1.21 | exact (already Ag/AgCl) | 10.3389/fmats.2019.00131 | high |
| 9-butylcarbazole | CCCCn1c2ccccc2c2ccccc21 | E° 1.19 V | formal E° (reversible) | Ag/AgCl | MeCN | 0.1 M TBAB | Pt microelectrode | 100 V/s | 1.19 | exact | 10.3389/fmats.2019.00131 | high |
| 9-hexylcarbazole | CCCCCCn1c2ccccc2c2ccccc21 | E° 1.16 V | formal E° (reversible) | Ag/AgCl | MeCN | 0.1 M TBAB | Pt microelectrode | 100 V/s | 1.16 | exact | 10.3389/fmats.2019.00131 | high |
| 9-octylcarbazole | CCCCCCCCn1c2ccccc2c2ccccc21 | E° 1.11 ± 0.02 V | formal E° (reversible) | Ag/AgCl | MeCN | 0.1 M TBAB | Pt microelectrode | 100 V/s | 1.11 | exact | 10.3389/fmats.2019.00131 | high |
| N-vinylcarbazole | C=Cn1c2ccccc2c2ccccc21 | +1.3 V (1st-scan anodic peak) | peak | SCE | MeCN | 0.1 M LiClO₄ | Pt | 50 mV/s | 1.345 | exact (SCE +0.045) | 10.3389/fmats.2019.00131 | med-high |
| Selenophene | c1cc[se]c1 | 1.60 V | onset | SCE | MeCN | 0.1 M TBABF₄ | Pt disk | 100 mV/s | 1.645 | exact (SCE +0.045) | 10.2478/s13536-014-0257-2 | med |
| EDOS | C1COc2cc[se]c2O1 | 1.09 V | onset | Ag/Ag⁺ (Fc/Fc⁺ = 0.40 V) | MeCN | 0.1 M TBAClO₄ | Pt disk | 100 mV/s | 1.135 | via internal Fc cal (exact) | 10.1039/D0RA01436B | med |
| Furan | c1ccoc1 | 1.75 V | peak (irreversible) | Ag⁰/Ag⁺ (no Fc cal) | MeCN | TBABF₄ | Pt | — | n/a | EXCLUDED — bare Ag/Ag⁺, not convertible | 10.1016/S0379-6779(98)01509-4 | excl |
| 2-methylfuran | Cc1ccco1 | 1.50 V | peak (irreversible) | Ag⁰/Ag⁺ (no Fc cal) | MeCN | TBABF₄ | Pt | — | n/a | EXCLUDED — bare Ag/Ag⁺ | 10.1016/S0379-6779(98)01509-4 | excl |

Notes on borderline rows that were considered but NOT placed in a clean track:
- **3-methoxythiophene** — reported at 1.1 V/SCE in a 3-substituted-thiophene copolymer paper (Calado/Donnici), but the source is a comparative tabulation without the explicit peak-vs-onset designation or full cell conditions for this specific monomer → marked **ambiguous**, kept out of both tracks.
- **EDOT** — multiple primary papers bracket the monomer at onset ~1.0–1.25 V and peak ~1.2–1.4 V; the PEDOT-co-EPh study (PMC4582677) gives "+1.25 V versus SCE" but does not cleanly disambiguate peak vs onset for bare EDOT in that sentence, and the EDOT-F patent gives a peak "Ep,m = +1.2 V vs Ag/Ag⁺" on a bare pseudo-reference → marked **ambiguous**; a clean EDOT Epa should be lifted from the Sotzing *Langmuir* paper (DOI 10.1021/la0344128) before use.
- **Pyrrole** — the cleanest non-aqueous primary number is an *estimated* E°′ ≈ +1.1 V vs SSCE in 0.1 M NaClO₄/MeCN from a rotating ring-disk study of the transient radical cation; this is a kinetically-extrapolated estimate, not a directly-read Epa or onset → **low confidence / ambiguous**.

### Existing anchor re-verified (retained)
The **Camarada et al. 2011** thiophene-oligomer onset series — thiophene 1.50 V, bithiophene 1.15 V, terthiophene 0.880 V vs Ag/AgCl sat'd KCl in MeCN, single lab/single scale — is confirmed and retained as the cleanest ONSET anchor. Full citation: **M. B. Camarada (Univ. Freiburg), P. Jaque (Univ. of Chile), F. R. Díaz & M. A. del Valle (Pontifical Catholic Univ. of Chile), "Oxidation potential of thiophene oligomers: theoretical and experimental approach," *J. Polym. Sci. B Polym. Phys.* 2011, 49(24):1723–1733, DOI 10.1002/polb.22360.** It is already on the master scale and needs no conversion.

### New high-value finding: carbazole reversible formal-potential series (Ag/AgCl, single lab)
**Contal, Sougueh, S. Lakard, Et Taouil, Magnenet & B. Lakard (Institute UTINAM, UMR CNRS 6213, Univ. of Bourgogne Franche-Comté, Besançon), *Front. Mater.* 6:131 (6 June 2019), DOI 10.3389/fmats.2019.00131** report, from 100 V/s fast voltammetry on a 246 µm Pt microelectrode (1.5 mM monomer + 0.1 M TBAB/MeCN) coupled to DigiElch simulation, reversible monomer/radical-cation formal potentials on the Ag/AgCl scale (their Table 1): **Cz1Me (9-ethyl) E° = 1.21, Cz3Me (9-butyl) 1.19, Cz5Me (9-hexyl) 1.16, Cz7Me (9-octyl) 1.11 ± 0.02 V**, with heterogeneous rate constants ks ≈ 0.055–0.09 cm/s and dimerization rate kdim ≈ (4.25 ± 0.75)×10⁵ M⁻¹ s⁻¹. The corresponding directly-observed anodic peak for 9-ethylcarbazole sits at **+1.25 V vs Ag/AgCl** ("The oxidation peak present at +1.25 V/Ag/AgCl is due to well-known monomer oxidation into radical cation"). Because these E° values are reversible thermodynamic couples (neither peak nor onset), they are the best IP proxies in the set but must be modeled as a **separate calibration sub-track** — not pooled with either the onset or the irreversible-peak rows.

The same paper anchors the carbazole/N-vinylcarbazole rows: carbazole onset "appears at 1.05 … V/SCE" and N-vinylcarbazole shows a first-scan anodic peak "at +1.3 V/SCE … which corresponds to the oxidation of the monomer into cation radicals leading to dimers."

### Selenophene & EDOS (subagent upgrade)
- **Selenophene** non-aqueous onset = **1.60 V vs SCE** (→ 1.645 V vs Ag/AgCl), MeCN + 0.1 M TBABF₄, Pt disk, 100 mV/s, from F. Alakhras, *Mater. Sci.-Poland* 2014, DOI 10.2478/s13536-014-0257-2. The widely-quoted alternative (1.83 V vs SCE in MeCN/Bu₄NBF₄) appears only as a literature citation inside BFEE-based papers and is therefore secondary; the 1.60 V row is the cleaner directly-measured value. Both are **onsets**, not peaks.
- **EDOS** onset = **1.09 V vs Ag/Ag⁺** (Fc/Fc⁺ internally calibrated at 0.40 V; → ~1.135 V vs Ag/AgCl), MeCN + 0.1 M TBAClO₄, Pt disk, 100 mV/s, from **P. Yadav, S. Naqvi & A. Patra (CSIR-National Physical Laboratory, New Delhi), *RSC Adv.* 2020, 10(21):12395–12406, DOI 10.1039/D0RA01436B** ("MeCN and TBAClO₄ were found to be the most suitable medium for electropolymerization of EDOS"). Onset, not peak.

## Details

**Track separation.** The clean tracks are:
- **ONSET track (screening-filter anchor):** thiophene 1.50, bithiophene 1.15, terthiophene 0.880, carbazole 1.095, selenophene 1.645, EDOS 1.135 (all vs Ag/AgCl). Six rows, two labs (Camarada single-lab triad is internally homogeneous; carbazole/Se/EDOS are independent single-lab points).
- **PEAK track (calibration anchor):** N-vinylcarbazole 1.345 V vs Ag/AgCl is the only clean irreversible monomer-peak row recovered. The 9-alkylcarbazole reversible E° series (1.11–1.21 V) is the strongest IP proxy but is a **formal-potential sub-track**, modeled separately.

The instructed ~0.15–0.35 V Epa−Eonset gap is consistent with the carbazole data themselves (carbazole onset 1.095 vs 9-ethylcarbazole peak 1.25 / E° 1.21), reinforcing that pooling peak and onset rows would inject ~0.2 V of structured error.

**Conversions applied:** SCE→Ag/AgCl +0.045 V (carbazole, N-vinylcarbazole, selenophene); EDOS via its internal Fc/Fc⁺ calibrant. No non-acetonitrile Fc conversions were needed for any included row, so no row carries the "approx" Fc-shift flag. All included rows are MeCN.

## Recommendations
- **Stage 1 (use now):** Build the ONSET screening-filter regression on the six clean onset rows. Build a small PEAK/IP calibration on the reversible 9-alkylcarbazole E° series (4 points) plus N-vinylcarbazole, treated as one reversible-couple sub-model; do not merge it with the onset regression.
- **Stage 2 (close the highest-value gaps):** Obtain the full text of the Sotzing *Langmuir* EDOT paper (DOI 10.1021/la0344128) to extract a clean EDOT Epa in TBAP/MeCN, and a primary Díaz- or Roncali-lineage pyrrole CV with an explicit reference electrode, to convert pyrrole and EDOT from "ambiguous" to clean rows. Target a primary 3-methylthiophene/3-hexylthiophene **monomer** CV (most existing values are polymer-film or deposition potentials).
- **Decision thresholds:** Promote an ambiguous row to a clean track only when the primary text states (a) the observable (peak vs onset) explicitly, (b) a non-pseudo reference electrode or a ferrocene calibrant, and (c) MeCN or an MeCN-convertible solvent. If post-calibration MAE on the onset track exceeds ~0.35 V, drop selenophene/EDOS (the two lowest-confidence onset rows) and re-fit on the homogeneous Camarada triad + carbazole before adding new monomers.

## Caveats
Residual scatter in this irreducible ~0.15–0.35 V regime stems from: (1) the kinetic nature of peak and onset potentials for irreversible film-forming oxidations, which are not the thermodynamic IP the ΔSCF/AIP computes; (2) liquid-junction and reference-conversion error when aqueous Ag/AgCl or SCE references meet nonaqueous solvent, compounded by use of the acetonitrile Fc constant; (3) pseudo-reference drift in any Ag-wire/Ag⁺ setup (the reason furan, 2-methylfuran, EDOT-F and ProDOT rows were excluded); and (4) genuinely monomer-dependent Epa−Eonset gaps, which make any peak↔onset interconversion unreliable. The carbazole formal potentials, being reversible, carry the least kinetic contamination and should be weighted accordingly.

### Separately-listed excluded / ambiguous rows (with reason)
- **Furan (1.75 V) and 2-methylfuran (1.50 V) vs Ag⁰/Ag⁺** (10.1016/S0379-6779(98)01509-4): EXCLUDED — bare Ag/Ag⁺ pseudo-reference, no ferrocene calibrant, not convertible.
- **Selenophene 1.23 V vs SCE in pure BFEE**: EXCLUDED — Lewis-acid (BFEE) medium.
- **Selenophene 1.83 V vs SCE**: not used as a primary row — appears only as a secondary citation inside BFEE-based papers.
- **EDOT-F Ep,m 1.2 V and ProDOT/POSS-ProDOT 1.20 V vs Ag/Ag⁺ (or Ag/AgNO₃)** (US 7,022,811; PMC5695877): EXCLUDED — Ag/Ag⁺ pseudo-reference without ferrocene calibration.
- **o-aminophenol (onset ~0.6 V, range to 1.8 V vs Ag/AgCl in 0.1 M HCl/KCl) and aniline (~1.0 V vs SCE in H₂SO₄/aqueous)**: EXCLUDED — aqueous-acid media for monomers that the screen runs nonaqueous; mechanism and proton coupling differ.
- **3-methoxythiophene 1.1 V, EDOT ~1.25 V, pyrrole E°′ ~1.1 V**: AMBIGUOUS — excluded from both clean tracks pending primary verification of observable type and reference electrode.

### Rows judged steady-state / deposition (must NOT enter calibration)
- **Poly(3-methylthiophene)/poly(3-octylthiophene) galvanostatic growth potentials (~1.3–1.4 V for PMT, ~1.3 V for POT)** from the EIS study (10.1016/j.electacta.2004.xx): these are recorded electrode potentials *during constant-current film deposition*, not clean CV monomer peaks/onsets.
- **PEDOT "optimum deposition potential" / onset-for-deposition values (0.9–1.5 V, water vs MeCN)** from the RSC Adv. comparative deposition study (10.1039/D4RA03543G): deposition-threshold values, not clean monomer CV.
- **Thieno-furan / SOS-type "monomer oxidises at more positive potentials than 0.7 V" constant-current film weights**: deposition/chronopotentiometric, not CV peak or onset.

### Upgrade audit: which prior draft rows moved from secondary → primary
- **Thiophene / bithiophene / terthiophene:** retained and re-verified directly against the Camarada primary (already clean; confirmed authorship and DOI).
- **Carbazole, 9-alkylcarbazoles, N-vinylcarbazole:** UPGRADED to primary — full-text verification of the Contal/Lakard 2019 CV (onset 1.05 V/SCE; reversible E° table; N-vinylcarbazole 1.3 V/SCE peak), replacing any prior secondary/review or patent sourcing.
- **Selenophene:** UPGRADED from secondary/review to a directly-measured primary onset (Alakhras 2014, MeCN/TBABF₄, SCE).
- **EDOS:** UPGRADED to primary (Yadav/Naqvi/Patra 2020, MeCN/TBAClO₄, Fc-calibrated).
- **Remaining unverifiable / not upgraded:** pyrrole (only a kinetically-estimated E°′ found), EDOT (clean Epa still behind paywalled primary — Sotzing Langmuir recommended), 3-methylthiophene, 3-hexylthiophene, ProDOT, N-methylpyrrole, EDOP, 3,4-dimethylpyrrole, furan/oligofurans (only bare-pseudo-reference or BFEE values), CPDT, dithienopyrrole, indacenodithiophene, fluorenes, anilines/o-anisidine/o-toluidine/o-aminophenol/diphenylamine (only aqueous-acid, mixed-solvent, or pseudo-reference primaries located within budget). These remain the explicit gap list for the next pass.

### Explicit gap list — priority small monomers with NO clean primary row
pyrrole · N-methylpyrrole · 3,4-dimethylpyrrole · EDOP · 3-methylthiophene · 3-hexylthiophene · EDOT (clean Epa) · ProDOT · fluorothiophenes · methoxythiophene (clean, disambiguated) · furan/bifuran/terfuran (clean reference) · alkylselenophenes · aniline/o-anisidine/o-toluidine/o-aminophenol/diphenylamine (nonaqueous, calibrated) · CPDT · dithienopyrrole · indacenodithiophene · 9,9-dialkylfluorenes.
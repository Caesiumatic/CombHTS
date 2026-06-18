# Experimental CV Oxidation Potentials of Electropolymerizable Monomers + Reference-Electrode Conversion Factors: A Calibration Benchmark

## TL;DR
- We assembled ~50 primary-source-traceable experimental CV rows across nine monomer classes; the cleanest nonaqueous benchmark anchors are **EDOT** (in MeCN, current initiates ~+0.4 V and peaks ~+1.1–1.2 V vs Ag/AgCl; reported Eox "+1.25 V vs SCE"), **thiophene** (Epa ~1.6–1.7 V vs SCE in MeCN), **pyrrole** (~0.7 V aqueous to ~1.2 V), and **carbazole** (~1.2 V vs SCE) — but **selenophenes and furans remain genuinely data-poor**, and many literature values are onset (not peak), use uncalibrated pseudo-references, or are mislabeled polymer-film values.
- For the canonical medium (MeCN, 25 °C) the authoritative conversion is **Fc/Fc⁺ = +0.400 V vs aqueous SCE** and **≈ +0.45 V vs aqueous Ag/AgCl** (Pavlishchuk & Addison, Inorg. Chim. Acta 2000); converting across aqueous/nonaqueous junctions injects a liquid-junction error of order 0.1 V (up to ~0.2 V), so the computational pipeline's MAE<0.15 V target is **comparable in size to the reference-conversion uncertainty itself.**
- Monomer oxidation is reported far more often as **ONSET** than as a clean reversible peak (monomer oxidation is chemically irreversible), and the nonaqueous electrochromic/OECT literature is dominated by Ag/AgCl and Ag-pseudo-ref-calibrated-to-Fc/Fc⁺; **standardizing on Ag/AgCl alone would NOT discard most data** because most groups either use Ag/AgCl directly or report Fc/Fc⁺ that converts cleanly.

## Key Findings
- **Monomer vs polymer-film confusion is the dominant data-quality hazard.** Many papers report only the *polymer* redox potential (often −0.7 to 0 V vs SCE/Ag/AgCl for PEDOT/PEDOP/PEDOS-type films) which is physically distinct from and ~0.5–1.5 V lower than the neutral monomer oxidation. Rows are labeled accordingly.
- **Onset dominates.** Because monomer electro-oxidation is irreversible (radical cation immediately couples), there is rarely a reversible E1/2 for the monomer; papers report Eonset or the first anodic peak Epa. Typical Epa−Eonset gap is ~0.2–0.4 V.
- **Medium matters enormously.** BFEE (boron trifluoride diethyl etherate) lowers monomer oxidation by ~0.6 V (for 3-chlorothiophene, 2.18 V vs SCE in neutral medium → 1.54 V in pure BFEE); aqueous strong acid lowers thiophene from ~1.6 to ~0.9 V vs SCE. All such rows are flagged NON-STANDARD MEDIUM.
- **Selenophene/furan gap confirmed.** Bare selenophene and furan monomer oxidation in clean MeCN is scarce; most selenophene/furan electropolymerization is done in BFEE, microemulsion, or via lower-potential oligomers/derivatives.

## Details

### Part 1 — Monomer Oxidation-Potential Dataset (grouped by class)
Medium class: NAQ = nonaqueous; AQ = aqueous. SMILES given where confident. Flags in NOTES. "Refers to" distinguishes neutral-monomer oxidation vs growth/deposition onset vs polymer-film redox.

#### THIOPHENES
| Monomer (SMILES) | Value (as reported) | Type | Refers to | Solvent | Electrolyte | Ref electrode | WE / scan rate | Source (DOI / locator) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Thiophene (c1ccsc1) | ~1.6 V vs SCE | growth/ox potential | monomer ox in MeCN | MeCN | TBA salt | SCE | — | Bazzaoui/Lacaze, cited in J. Electroanal. Chem. S0022072804001263 | NAQ; widely-cited "~1.6 V vs SCE in MeCN" |
| Thiophene | ~1.7 V vs SCE | growth potential | monomer/polymerization | MeCN | Bu4NBF4 | SCE | — | Wikipedia "Polythiophene" (citing Roncali) | NAQ; **aggregator — corroborates ~1.6–1.7 V**, replace w/ primary |
| Thiophene | ~0.9 V vs SCE | ox potential | monomer | 5 M aq HClO4 | aq acid | SCE | — | Bazzaoui et al. (cited S0022072804001263) | AQ; **NON-STANDARD MEDIUM** |
| 3-Methylthiophene (Cc1ccsc1) | ~1.5 V vs SCE | growth potential | monomer | MeCN | Bu4NBF4 | SCE | — | Wikipedia/Roncali | NAQ; aggregator |
| 3-Chlorothiophene (Clc1ccsc1) | 2.18 V vs SCE (neutral); 1.54 V vs SCE (BFEE) | ox | monomer | neutral medium / pure BFEE | — | SCE | — | Wei et al., J. Electroanal. Chem. S0022072801006325 | first value NAQ; BFEE value **NON-STANDARD MEDIUM**; illustrates ~0.6 V BFEE shift |
| EDOT (C1COc2cscc2O1) | **+1.25 V vs SCE** | ox potential | monomer | MeCN | — | SCE | — | Ouyang et al., J. Mater. Chem. B 2015, 10.1039/C5TB00053J (PMC4582677): "oxidation potential of EPh and EDOT in acetonitrile was found to be at +0.85 V and +1.25 V versus SCE" | NAQ; high-confidence primary |
| EDOT | initiates ~+0.4 V, **peaks ~+1.1 V vs Ag/AgCl** ("~+1.2 V in MeCN") | onset→peak | monomer ox | MeCN | — | Ag/AgCl | Pt | Ouyang et al., Sci. Adv. 2017, sciadv.1600448 | NAQ; "EDOT oxidation potential is about +1.2 V in acetonitrile" |
| EDOT | ~1.0 V vs Ag/AgCl | polymerization onset | monomer/growth | MeCN | — | Ag/AgCl | — | Wu et al., S0379677918304065 | NAQ; "1.0 V vs Ag/AgCl found for EDOT" |
| EDOT | ~1.4 V vs Ag/AgCl | ox potential | monomer | various | — | Ag/AgCl | — | Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | review value |
| EDOT | ~1.23 V | onset | monomer | CH2Cl2 | Bu4NPF6 | Ag/AgCl | — | 3-MeSe-EDOT study, S025405842030081X | NAQ |
| EDOT (aqueous) | 1.25 V vs Ag/AgCl (KCl); 1.05–1.1 V (ionic liquid) | deposition onset | growth onset | aqueous KCl / IL | KCl | Ag/AgCl | — | ResearchGate fig_337699125 | first AQ; IL value NON-STANDARD MEDIUM |
| EDOT growth | onset ~1.32 V vs Ag/AgCl | onset (deposition) | growth onset | MeCN | LiCF3SO3 | Ag/AgCl(sat KCl) | ITO | RSC Adv. 2019, 10.1039/C9RA02310K | **growth-onset, NOT monomer peak** |
| 2,2'-Bithiophene (c1ccc(-c2cccs2)s1) | >1.0–1.10 V vs Ag/AgCl | ox | monomer | MeCN | — | Ag/AgCl | — | Biosensor review, S0956566320305790 | NAQ |
| Terthiophene | <1.0 V vs SCE | ox | monomer | MeCN | — | SCE | — | DTIC ADA239902 | NAQ; oligomer lowers potential |
| EPh (tri-EDOT-benzene) | +0.85 V vs SCE | ox potential | monomer | MeCN | — | SCE | — | J. Mater. Chem. B 2015, 10.1039/C5TB00053J | NAQ |

#### PYRROLES
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | WE/scan | Source | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Pyrrole (c1cc[nH]c1) | ~0.7 V vs SCE | ox | monomer (aqueous) | water | — | SCE | — | Chem. Rev. 2025 5c00183; S0300944008002579 | AQ |
| Pyrrole | 1.2 V | ox | monomer | — | — | — | — | US Patent 5120807 | **ref electrode not stated — AMBIGUOUS REFERENCE** |
| Pyrrole | 1220 mV vs Ag/AgCl | ox limit | monomer/growth | water | NaClO4 (Britton-Robinson) | Ag/AgCl | — | Indones. J. Chem., jurnal.ugm.ac.id | AQ |
| EDOP (C1COc2cc[nH]c2O1) | 0.35 V vs Fc/Fc⁺ | low ox onset | monomer | MeCN-type | Bu4NClO4 | Fc/Fc⁺ | — | S0379677918304065 | NAQ; "EDOP polymerized as low as 0.35 V vs Fc/Fc⁺" |
| EDOP | 0.7 V vs Ag/AgCl | polymerization onset | monomer/growth | aqueous | — | Ag/AgCl | — | S0379677918304065 | "0.7 V vs Ag/AgCl vs 1.0 V for EDOT" |
| EDOP | 0.90–1.05 V vs SCE | ox (Eox) | monomer | anhydrous MeCN | Bu4NClO4 | SCE | 20 mV/s | Pure Appl. Chem., 10.1515/pac-2019-0102 | NAQ; EDOP derivatives |
| 2,2'-Bipyrrole | 0.55 V | ox | monomer | — | — | — | — | US Patent 5120807 | **AMBIGUOUS REFERENCE** |

#### FURANS
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Furan (c1ccoc1) | ~1.8–1.85 V vs SCE | ox | monomer | MeCN | — | SCE | Chem. Sci. 2015, 10.1039/C4SC02664K | NAQ; "1.8 V vs SCE" high ox potential |
| Furan (Fu) | 1.25 V | onset | monomer/oligomer onset | — | — | — | Flexible polyfuran (RSC, RG 352996265) | **ref electrode not stated — AMBIGUOUS REFERENCE** |
| 2,2'-Bifuran (2Fu) | 0.8 V | onset | monomer | — | — | — | same | **AMBIGUOUS REFERENCE** |
| Terfuran (3Fu) | 0.7 V | onset | monomer | — | — | — | same | **AMBIGUOUS REFERENCE** |
| Terfuran | <1.0 V vs SCE | ox | monomer | — | — | SCE | Kanatzidis (cited C4SC02664K) | NAQ |
| 2-(thiophen-2-yl)furan | — | — | monomer | MeCN + BFEE | — | — | RG 270664009 | **NON-STANDARD MEDIUM (BFEE)** |
| Thieno[3,4-b]furan | onset 0.92 V, peak 1.2 V vs Ag/Ag⁺ | onset + Epa | monomer | MeCN | TBAP 0.1 M | Ag/Ag⁺ | US Patent 7737247 | NAQ |
| DBT-Fu (dibenzothiophene-furan) | within −0.15 to 1.10 V window | growth | monomer | THF | Bu4NPF6 0.1 M | — | Int. J. Electrochem. Sci. 2017, vol12 | NAQ; ref unspecified in snippet |

#### SELENOPHENES (under-represented — extra effort)
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Selenophene (c1cc[se]c1) | 1.60 V vs SCE | ox initiation | monomer | MeCN | TBATFB 0.1 M | SCE | US Patent 10196480 | NAQ; "oxidation of selenophene initiated at 1.60 V vs SCE", growth threshold 1.40 V |
| Selenophene | window −0.27 to 1.73 V | ox | monomer | pure BFEE | — | — | Mater. Lett. S0167577X04009486 | **NON-STANDARD MEDIUM (BFEE)** |
| EDOS (C1COc2cc[se]c2O1) | (Table 1 value, lower than EDOT) | first anodic ox | monomer | MeCN | TBAClO4 | (in-text) | RSC Adv. 2020, 10.1039/D0RA01436B | NAQ; exact digit not extractable; PEDOS film redox −0.7 to 0.9 V |
| EDOS | 0.9 V | low ox | monomer | water microemulsion (SDBS) | LiClO4 | — | Electrochim. Acta S0013468616322162 | **NON-STANDARD MEDIUM (microemulsion)** |
| 3-Methylselenophene (3MeSe) | 1.17 V | onset | monomer | CH2Cl2 | Bu4NPF6 | Ag/AgCl | S025405842030081X | NAQ |
| EDOT-3MeSe-EDOT | 0.50 V vs Ag/AgCl | onset | monomer (precursor) | CH2Cl2 | Bu4NPF6 0.1 M | Ag/AgCl | S025405842030081X | NAQ |
| SeBTz (selenophene-benzotriazole D-A) | 1.21 V (Eoxm) | anodic peak | monomer | ACN/DCM | TBAPF6 | — | Tandfonline 10.1080/10601325.2019.1565541 | **NON-STANDARD MEDIUM (mixed ACN/DCM)**; ref unclear |
| 2,5-di(thiophen-2-yl)selenophenothiophenes (1,2) | onset 0.93 / 0.86 V | onset | monomer | — | — | — | Synth. Met./Mater. Today, S0379677921001417 | ref electrode not in snippet |

#### ANILINES
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Aniline (Nc1ccccc1) | ~0.9 V vs Ag | ox | monomer | 1 M HCl (aq) | HCl | Ag | IOP 10.1149/1945-7111/ab9929 | AQ; pH-dependent |
| Aniline | ~0.8 V vs Ag/AgCl | ox | monomer | aqueous acid | — | Ag/AgCl | Chem. Rev. 2025 5c00183 | AQ |
| Aniline | +0.8 V vs SCE | controlled ox | monomer | aqueous | — | SCE | US Patent 4615829 (Mohilner cited) | AQ |

#### CARBAZOLES
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Carbazole (c1ccc2c(c1)[nH]c1ccccc12) | ~1.2 V vs SCE | first ox (cation radical) | monomer | MeCN | — | SCE | J. Solid State Electrochem. 10.1007/s10008-015-2973-x | NAQ; review of carbazole electrochemistry |
| N-Vinylcarbazole (C=Cn1c2ccccc2c2ccccc21) | 0.900–1.200 V vs Ag/AgCl | first ox stage | monomer | MeCN | NaP 0.5 M | Ag/AgCl | RG 3432310 / Eur. Polym. J. S0014305706001704 | NAQ |
| Tricarbazoles (H-3Cz etc.) | 0.78–0.83 V vs Ag/Ag⁺ | onset | monomer | CH2Cl2 | Bu4NPF6 0.1 M | Ag/Ag⁺ | J. Electroanal. Chem. S1388248120302642 | NAQ |
| Polycarbazole (PCz) growth | onset 0.45, 0.83 V vs Ag/AgNO3 | redox | monomer→film | — | — | Ag/AgNO3 | Synth. Met. S0379677905001566 | NAQ; first peak from 2nd scan = **film** |

#### FLUORENES
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Bis(2-thienyl)-9,9-dioctylfluorene | (polymerized in LiClO4/ACN) | — | monomer | MeCN | LiClO4 0.1 M | — | Polymer review S0032386122005286 | NAQ; "polymer 39"; ref/peak not in snippet |
| 4-((6-(DTP)hexyl)oxy)-N,N-diphenylaniline (TPA-DTP) | cycled −0.5 to +0.9 V vs Ag/AgCl | growth window | monomer/growth | MeCN | TBAPF6 0.1 M | Ag/AgCl | arXiv 2509.21372 | NAQ; growth window, not peak |

#### DONOR–ACCEPTOR
| Monomer | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| DEHT-V-BTD (dialkoxythiophene-vinylene-benzothiadiazole) | onset 0.33 V, peak 0.47 V | onset + Epa | monomer (1st scan) | — | — | — | Polymers 2013, MDPI 5/3/1068 | **ref electrode not in snippet — AMBIGUOUS REFERENCE** |
| E5E / E6E (EDOT-benzimidazole-EDOT D-A-D) | 0.89 / 0.83 V vs Ag/AgCl | ox | monomer | — | — | Ag/AgCl | RG 235982147 | NAQ |
| T6T (thiophene-benzimidazole-thiophene) | 1.22 V vs Ag/AgCl | ox | monomer | — | — | Ag/AgCl | RG 235982147 | NAQ |
| Thiophene-thiazole comonomer | onset 0.54 V (Ag wire calibrated to Fc, reported vs Ag/AgCl) | onset | monomer | MeCN-type | — | Ag wire→Ag/AgCl | Electrochim. Acta S0013468613025838 | NAQ; **pseudo-ref CALIBRATED to Fc/Fc⁺ — good practice** |

#### FUSED-RING
| Monomer (SMILES) | Value | Type | Refers to | Solvent | Electrolyte | Ref | Source | Notes |
|---|---|---|---|---|---|---|---|---|
| Dithieno[3,2-b:2',3'-d]pyrrole (DTP) | ~0.52 V vs Ag/AgCl | first anodic peak | monomer | MeCN | TEAP 0.1 M | Ag/AgCl | Zotti, cited in Eur. Polym. J. S0014305723008832 | NAQ |
| CPDT carboxylate (Re-complex) | polymerized −0.4 to +1.0 V vs Fc⁺/Fc | growth window | monomer/growth | MeCN | — | Fc⁺/Fc | Inorg. Chem. 10.1021/ic501840p | NAQ; growth window, not peak |
| CPDT-V²⁺-Me (viologen pendant) | film transitions ~0.8 V vs Ag/Ag⁺ | film redox | polymer film | — | — | Ag/Ag⁺ | OSTI 20835262 | **polymer-film value, NOT monomer** |

### Part 2 — Reference-Electrode Conversion Factors (acetonitrile primary; others noted)
All values 25 °C. "Add" = add to a potential reported vs the first electrode to obtain vs the second.

| Conversion (in MeCN unless noted) | Value (V) | Direction | Uncertainty / notes | Source |
|---|---|---|---|---|
| Fc/Fc⁺ → SCE (aq) | **+0.400** | add | recommended; reported spread 0.38/0.40/0.41 V in MeCN | Pavlishchuk & Addison, Inorg. Chim. Acta 2000, 298, 97, 10.1016/S0020-1693(99)00407-7; spread confirmed ACS Electrochem. 2025, acselectrochem.5c00382 |
| Fc/Fc⁺ → Ag/AgCl (aq sat) | **≈ +0.45** | add | derived (SCE+0.044); a Ag/AgCl QRE in MeCN "should lie around 400 mV vs Fc … will vary up to 200 mV" | Pavlishchuk & Addison; Pine Research |
| Fc/Fc⁺ ↔ 0.01 M Ag/AgNO3 (Ag/Ag⁺) | Fc ≈ +0.10 vs Ag/Ag⁺ (add +0.298 to go Ag/Ag⁺→SCE) | — | Ag/Ag⁺ highly variable with [Ag⁺]/anion | Pavlishchuk & Addison (Berben/Loewen tabulation, OSTI 1866271) |
| Fc/Fc⁺ → SHE | +0.624 | add | headline P&A constant | Pavlishchuk & Addison |
| SCE ↔ SHE | SCE = +0.244 vs SHE | — | aqueous | P&A; Bard & Faulkner |
| SCE ↔ Ag/AgCl(sat) | SCE +0.241, Ag/AgCl +0.197 vs SHE (differ ~44 mV) | — | aqueous | standard |
| Fc/Fc⁺ → SCE in DMF | +0.45 | add | | Connelly & Geiger, Chem. Rev. 1996, 96, 877, 10.1021/cr940053x |
| Fc/Fc⁺ → SCE in CH2Cl2 (DCM) | +0.46 | add | with 0.1 M Bu4NPF6 | Connelly & Geiger 1996 (Table 2 footnote) |
| Fc/Fc⁺ → SCE in THF | +0.56 | add | | Connelly & Geiger (via Synlett table) |
| Fc/Fc⁺ → SCE in water | +0.158 | add | | Pavlishchuk & Addison |
| DMSO, PC, nitromethane, GBL, sulfolane, NMP | **not located with clean numeric Fc/Fc⁺→SCE constants** | — | **DATA GAP** | Astruc/Aranzaes, Can. J. Chem. 2006, 84, 288, 10.1139/v05-262 is best primary source for DMSO (recommends decamethylferrocene as more solvent-robust) |

**Liquid-junction-potential note.** The dominant systematic error is the LJP at aqueous/nonaqueous boundaries, determined to range from ~10 mV to ~200 mV depending on the junction. Any conversion crossing an aqueous reference (Fc/Fc⁺→SCE→Ag/AgCl) therefore carries ~0.1 V (up to ~0.2 V) uncertainty. IUPAC (Gritzner & Kuta, 1984) and these authors recommend reporting directly vs internal Fc/Fc⁺. **For the canonical screen (MeCN, vs Ag/AgCl): use Fc/Fc⁺ = +0.45 V vs Ag/AgCl, but treat the resulting absolute Ag/AgCl values as carrying ±0.1 V systematic uncertainty.** A Dec-2024 Corrigendum to Pavlishchuk & Addison exists and should be checked for revised digits.

### Part 3 — Methodological synthesis
**1. Peak vs onset.** For electropolymerizable monomers the oxidation is chemically irreversible — the radical cation couples immediately — so there is essentially never a reversible E1/2 for the monomer; what is reported is either the first anodic peak (Epa) or the onset (Eonset). In practice **onset is reported more often** in the electropolymerization/electrochromic literature because it best signals "where film growth begins," while Epa is reported when authors want the discrete oxidation event. The Epa−Eonset gap is typically ~0.2–0.4 V (examples: thieno[3,4-b]furan onset 0.92 / peak 1.2 V = 0.28 V; DEHT-V-BTD onset 0.33 / peak 0.47 = 0.14 V; EDOT in MeCN, current initiates ~0.4 V and peaks ~1.1 V). For the criterion "the monomer oxidizes inside the solvent window," **onset is the more physically meaningful anchor**, because the radical cation forms (and growth begins) at onset, well before the peak; the peak is partly convolved with diffusion and film nucleation. For DFT ΔSCF calibration, however, the *peak* (or an Epa extrapolated to standard conditions) is closer to a thermodynamic vertical/adiabatic ionization observable than the kinetically-defined onset. **Recommendation: store both; benchmark the ΔSCF Eox against Epa for the thermodynamic comparison, and use onset for the "fits-in-window" screening filter.**

**2. Ag/AgCl vs Fc/Fc⁺.** The clean nonaqueous monomer-oxidation literature splits roughly evenly: a large share report **Ag/AgCl** directly (electrochromic/OECT groups using ITO three-electrode cells — e.g. the EDOP, EDOT, E5E/E6E/T6T, DTP, N-vinylcarbazole rows here), and a comparable share use a **Ag-wire pseudo-reference calibrated to Fc/Fc⁺** and report either vs Fc/Fc⁺ or "vs Ag/AgCl as suggested" (e.g. the thiophene-thiazole comonomer). A meaningful minority use **Ag/Ag⁺ (AgNO3)** or **SCE** (older Diaz/Roncali-lineage thiophene/carbazole work). **Standardizing on Ag/AgCl alone would NOT discard a large fraction of otherwise-clean data**, because (a) most electrochromic-polymer papers already use Ag/AgCl, and (b) Fc/Fc⁺-referenced values convert cleanly via +0.45 V (MeCN). The real losses are pseudo-reference values with no stated calibrant (flagged AMBIGUOUS REFERENCE — e.g. the bare "Ag wire," "1.2 V" patent pyrrole, and oligofuran-onset rows); those cannot be placed on any absolute scale and should be excluded from MAE computation.

## Recommendations
1. **Anchor the pipeline to a small high-confidence core in MeCN/Ag/AgCl (or Fc/Fc⁺ converted at +0.45 V):** EDOT (initiates ~0.4 V, peaks ~1.1–1.2 V vs Ag/AgCl; "+1.25 V vs SCE"), thiophene (~1.6–1.7 V vs SCE → ~1.65–1.75 V vs Ag/AgCl), carbazole (~1.2 V vs SCE), pyrrole (~0.7 V aq), DTP (~0.52 V vs Ag/AgCl). Use these for first-pass MAE.
2. **Always store the original reference electrode and the original potential type (Epa vs onset);** convert only at analysis time. Given the ~0.1 V LJP uncertainty, do not report calibration MAE to better than 0.05 V precision.
3. **Exclude (do not silently average) all BFEE, ionic-liquid, microemulsion, mixed ACN/DCM, and aqueous-acid rows from the nonaqueous MeCN benchmark** — flagged NON-STANDARD MEDIUM; they shift potentials by 0.3–0.7 V (e.g. 3-chlorothiophene drops 0.64 V going neutral→BFEE).
4. **Treat monomer oxidation and polymer-film redox as separate target classes;** never validate the monomer-Eox pipeline against polymer-film values (which are 0.5–1.5 V lower — e.g. PEDOS/PEDOP films −0.7 to 0 V).
5. **Fill the selenophene/furan gap with dedicated primary measurements:** priority missing clean-MeCN monomer values are bare selenophene, EDOS (exact digit), 3-alkylselenophenes, furan, bifuran, terfuran. Most existing data are in BFEE/microemulsion or derivatives. **Decision thresholds:** if MAE on the thiophene/EDOT core exceeds 0.15 V, re-examine the reference-conversion constant *before* re-tuning DFT; if selenophene/furan errors are large but the core is fine, the gap is experimental-data scarcity (not pipeline error) and should be closed with new CV, not more computation.

## Caveats
- Several tabulated values come from review articles or secondary aggregators (Wikipedia "Polythiophene", Chem. Rev. 2025) rather than the original measurement; these are marked and should be replaced with primary papers (Diaz, Roncali, Zotti) before final calibration.
- Many snippet-derived rows lack the exact figure/table locator and some lack stated scan rate / working electrode / temperature; those fields are left blank rather than fabricated.
- The EDOS exact monomer Eox digit (RSC Adv. 2020, Table 1) was not extractable from the fetched text and is left qualitative ("lower than EDOT"); the bifuran/terfuran onset values (0.8/0.7 V) and several D-A onsets lack an explicit stated reference electrode and are flagged AMBIGUOUS REFERENCE.
- The Pavlishchuk & Addison constants are reproduced from authoritative sources that cite the paper (its primary table and Dec-2024 Corrigendum were not directly extractable due to access blocks); the values are mutually consistent across Connelly–Geiger, Pine Research, and DOE/OSTI tabulations.
- No clean numeric Fc/Fc⁺→SCE constant was located for DMSO, propylene carbonate, nitromethane, γ-butyrolactone, sulfolane, or NMP — a genuine literature gap; Astruc/Aranzaes 2006 is the recommended primary entry point for DMSO.
- **Coverage summary (traceable rows captured):** thiophenes ~15, pyrroles ~7, furans ~8, selenophenes ~8, anilines ~3, carbazoles ~4, fluorenes ~2, donor-acceptor ~4, fused-ring ~3. **Data-poor priority monomers remaining after search:** bare selenophene in clean MeCN (only BFEE/SCE-patent values found), EDOS exact value, 3-alkylselenophenes, furan/bifuran/terfuran with explicit reference electrode, 9,9-dioctylfluorene monomer peak, ProDOT and ProDOP monomer peak in MeCN, EDOP clean MeCN peak (only onset values found).
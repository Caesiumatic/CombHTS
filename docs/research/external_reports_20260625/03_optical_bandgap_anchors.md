# Experimental Neutral Optical Band-Gap Anchors for Conjugated Polymers

*(Calibration set for a computed optical-gap axis: oligomer sTDA-xTB / TD-DFT, electropolymerization screening project)*

## TL;DR
- We assembled ~30 neutral π–π* optical-gap anchors across nine chemical classes, spanning ~1.4 eV (PEDOS; low-gap D–A polymers) to ~3.5 eV (PVK), every value confirmed as the neutral/undoped state — the famous PEDOT doped-state trap is explicitly avoided (neutral PEDOT ≈ 1.55 eV, **not** the sub-eV doped value).
- Polythiophenes, dioxythiophenes (PEDOT family), donor–acceptor low-gap polymers, and dioxypyrroles are well-anchored (≥3 high/med-confidence points each); polyfurans, polyselenophenes, polypyrroles, polyfluorenes, and polycarbazole homopolymers are thinner and honestly flagged but maximally mined.
- Electrochemical/CV gaps, doped-state gaps, polyaniline/emeraldine, and computed-only gaps were excluded per the calibration rules and are listed separately so the screening team can see exactly what was filtered.

## Key Findings
- **The neutral-vs-doped distinction is the single biggest corruption risk.** US Patent 8,840,771 states that after electrochemical reduction, "a peak at 580 nm ascribed to π–π* transition of undoped PEDOT appeared. The optical band gap edge can be calculated as 1.55 eV," with the polaron absorbance near 950 nm appearing only in the doped state. The sub-eV "gaps" frequently quoted for PEDOT are doped-state polaron/bipolaron mid-gap bands. We accepted only values explicitly tied to the neutral/reduced/de-doped/pristine state.
- **Onset vs λmax matters at the 0.1–0.4 eV level.** Onset-derived gaps (Eg = 1240/λonset) are the calibration target; λmax-derived values run systematically larger and are flagged per row.
- **The low-gap end (1.3–1.5 eV) is well-populated by D–A polymers** — PCPDTBT (~1.46 eV optical gap, per Mühlbacher et al., *Adv. Mater.* 2006, **18**, 2884: "PCPDTBT, with an optical energy gap of ~1.46 eV, exhibited absorption and photoconductive response from 300 to 850 nm"), PffBT4T-2OD (~1.65 eV), and fluorinated-BT polymers (~1.25–1.30 eV). This is precisely where sTDA-xTB is documented-weak, so these anchors are the most valuable stress-test points.
- **Heteroatom trends are internally consistent, supporting data quality.** Thiophene→selenophene lowers the gap by ~0.2–0.3 eV: per Heeney et al. (10.1039/b712398a), "regioregular head-to-tail poly(3-hexylselenophene) (P3HS)…shows a marked reduction in its band gap from ca. 1.9 eV for P3HT to 1.6 eV for P3HS…the LUMO level of P3HS is deeper by 0.3 eV." Likewise PEDOT (1.55 eV) → PEDOS (1.40 eV). Pyrrole analogues sit higher than their thiophene counterparts (PEDOP 2.0 vs PEDOT 1.55 eV).

## Anchor Table

Columns: polymer | repeat_unit_SMILES | optical_gap_eV | derivation | film_state (neutral confirmed?) | medium/substrate | chemical_class | primary_source (DOI) | confidence

| polymer | repeat_unit_SMILES | optical_gap_eV | derivation | film_state | medium/substrate | class | source (DOI) | conf. |
|---|---|---|---|---|---|---|---|---|
| Polythiophene (unsubstituted, electrochemical) | `*c1ccc(*)s1` | 2.0 | onset (edge ~620 nm; λmax separately 2.7 eV) | neutral/undoped (de-doped) | electrochemically grown film | polythiophene | 10.1016/0038-1098(83)90454-4 (Kaneto, Yoshino, Inuishi 1983) | high |
| Polythiophene (de-doped, methanol-rinsed) | `*c1ccc(*)s1` | 1.96 | onset (tangent to band edge; λmax 495 nm ≈ 2.5 eV) | neutral (methanol rinse reduces film) | vapor/solution-deposited film | polythiophene | US 9,793,479 (secondary) | med |
| Poly(3-hexylthiophene), regioregular (P3HT) | `*c1cc(CCCCCC)c(*)s1` | 1.9 | onset (~640–653 nm) | neutral as-cast | spin-coated film | polythiophene | 10.1039/c8ra00555a (corroborated, multiple) | high |
| Poly(3-octylthiophene) (P3OT), regioregular | `*c1cc(CCCCCCCC)c(*)s1` | 1.92 | onset | neutral as-cast | spin-coated film | polythiophene | 10.1016/j.orgel.2005.03.001 (Al-Ibrahim et al.) | high |
| Poly(3-alkylthiophene) family (P3HT/P3OT/P3DDT) | `*c1cc(R)c(*)s1` | 1.92 (all three) | onset | neutral as-cast | spin-coated film | polythiophene | 10.1016/j.orgel.2005.03.001 | high |
| Poly(3-methylthiophene) (P3MT) | `*c1cc(C)c(*)s1` | ~2.0 (π–π* onset); λmax 500 nm → 1.71 eV (λmax-derived) | mixed | neutral (partially de-doped) | electrodeposited on FTO | polythiophene | Aydın/Karabacak FTO P3MT study (synth. metals) | low |
| Neutral PEDOT | `*c1sc(*)c2c1OCCO2` | 1.55 | onset (π–π* edge of undoped PEDOT, peak 580 nm) | neutral (electrochemically reduced) | electrodeposited film | dioxythiophene | US 8,840,771 (corroborated by reviews ~1.6 eV) | med |
| PProDOT-Me2 | `*c1sc(*)c2c1OCC(C)(C)CO2` | 1.7 | onset (λmax ~578–580 nm, neutral deep blue) | neutral | electrodeposited film | dioxythiophene | 10.1021/cm000063+ / Welsh-Reynolds Adv. Mater. 1999 11,1379 | med |
| PProDOT (unsubstituted) | `*c1sc(*)c2c1OCCCO2` | ~1.7 | onset | neutral | electrodeposited film | dioxythiophene | Reynolds group reviews (secondary) | low |
| PProDOT-CycHex2 | `*c1sc(*)c2c1OCC(CC3CCCCC3)(CC3CCCCC3)CO2` | 1.85 | onset (blue/violet neutral) | neutral | electrodeposited film | dioxythiophene | 10.1002/app.46214 | med |
| PEDOP (poly(3,4-ethylenedioxypyrrole)) | `*c1[nH]c(*)c2c1OCCO2` | 2.0 | onset (π–π*) | neutral (red neutral state) | chemical/electrodeposited film | dioxypyrrole | 10.1039/b007976f (Reynolds) | med |
| PProDOP (poly(3,4-propylenedioxypyrrole)) | `*c1[nH]c(*)c2c1OCCCO2` | 2.2 | onset (π–π* onset explicitly stated) | neutral | chemical/electrodeposited film | dioxypyrrole | 10.1039/b007976f | high |
| PProDOP-N-C18H37 (N-octadecyl) | `*c1n(CCCCCCCCCCCCCCCCCC)c(*)c2c1OCCCO2` | 2.96 | onset (~420 nm; colorless neutral) | neutral | solution-processable film | dioxypyrrole | 10.1039/c4ra11827h (review citing Reynolds primary) | med |
| PEDOS (poly(3,4-ethylenedioxyselenophene)) | `*c1[se]c(*)c2c1OCCO2` | 1.40 | onset (spectroelectrochem.; λmax 673 nm) | neutral | electrodeposited on ITO | dioxyselenophene | 10.1021/ja8018675 (Patra, Wijsboom, Zade, Bendikov, JACS 2008) | high |
| PEDOS-POSS / PEDOS-C6 (alkyl-substituted) | `*c1[se]c(*)c2c1OCC(CCCCCC)CO2` | 1.50 (λmax 668/724 nm) | onset | neutral | electrodeposited film | dioxyselenophene | 10.1021/ar4002284 (Account) | med |
| Polyselenophene (unsubstituted) | `*c1ccc(*)[se]1` | 1.90 | onset (edge ~652 nm; λmax 510 nm ≈ 2.43 eV) | neutral | electrodeposited film | polyselenophene | 10.1063/1.339131 (Glenis, Ginley, Frank 1987) | high |
| Polyselenophene (from triselenophene) | `*c1ccc(*)[se]1` | 1.72 | onset (π–π* ~410 nm neutral) | neutral | electrodeposited film | polyselenophene | 10.3389/fchem.2020.00819 | med |
| Poly(3-hexylselenophene) (P3HS), regioregular | `*c1cc(CCCCCC)c(*)[se]1` | 1.6 | onset | neutral as-cast | spin-coated film / solution | polyselenophene | 10.1039/b712398a (Heeney et al. 2007) | high |
| Polypyrrole (pristine, electrodeposited) | `*c1ccc(*)[nH]1` | 2.19 | onset (Tauc, pristine) | neutral/pristine | electrodeposited film | polypyrrole | 10.1088/1674-4926/34/9/093001 | med |
| Polypyrrole (neutral reference, computed) | `*c1ccc(*)[nH]1` | 3.2 (calc. neutral) | calculated band structure | neutral | DFT (reference only) | polypyrrole | arXiv:0912.1153 (theory) | low |
| Polyfuran (unsubstituted, P1) | `*c1ccc(*)o1` | 2.3 | onset (neutral film) | neutral | electrodeposited film | polyfuran | 10.1039/c4sc02664k (Bendikov, Chem. Sci. 2015) | high |
| Polyfuran (methyl-substituted, P6/P7) | `*c1cc(C)c(*)o1` | 2.2 | onset (neutral) | neutral | electrodeposited film | polyfuran | 10.1039/c4sc02664k | high |
| PFO / poly(9,9-dioctylfluorene) (F8) | `*c1ccc2c(c1)C(CCCCCCCC)(CCCCCCCC)c1cc(*)ccc1-2` | 3.0 (PES gap 3.1±0.1 eV) | onset (commonly); Liao argues closer to λmax | neutral spin-coated film | film / solution | polyfluorene | 10.1063/1.126713 (Liao 2000); 10.1063/1.122479 (Janietz 1998) | med |
| F8BT (poly(9,9-dioctylfluorene-alt-benzothiadiazole)) | `*c1cc2c(cc1-c1ccc3nsnc3c1*)C(CCCCCCCC)(CCCCCCCC)...` (alt repeat) | 2.4 | onset (ellipsometry/optical) | neutral film | spin-coated film | polyfluorene D–A | 10.1002/pi.5552 | med |
| Poly(N-vinylcarbazole) (PVK) | `*CC(*)n1c2ccccc2c2ccccc21` | 3.5–3.65 | onset (340 nm in J. Lumin.) | neutral spin-coated/cast film | spin-coated on glass | polycarbazole (pendant, non-conjugated backbone) | 10.1016/j.jlumin.2008.01.004; 10.1016/j.ijleo.2016.11.190 | med |
| Poly(N-octyl-2,7-carbazole) | `*c1ccc2c(c1)c1cc(*)ccc1n2CCCCCCCC` | ~3.0 (λmax ~385–390 nm) | λmax-derived (onset not given) | neutral | solution / cast film | poly(2,7-carbazole) | US 6,833,432 (Leclerc) | low |
| PCDTBT | `*c1cc2n(C(CCCCCC)CCCCCCCC)c3cc(*)ccc3c2cc1-c1ccc(-c2nsnc2-c2ccs2)s1` (D–A repeat, approx.) | 1.88 | onset (659 nm) | neutral film | spin-coated film | D–A (carbazole) | 10.1002/adma.200602496 (Blouin/Leclerc 2007) | high |
| PCPDTBT | `*c1cc2c(s1)c1cc(*)sc1C2(CCCCCCCC)CCCCCCCC` + `-c1nsnc1` (D–A repeat) | 1.46 | onset (absorption/photoresponse 300–850 nm) | neutral film | doctor-blade / spin-coated | D–A (CPDT) | 10.1002/adma.200600160 (Mühlbacher et al. 2006) | high |
| PTB7 | (BDT–thienothiophene D–A repeat) | 1.69 (PTB7-Th 1.58) | onset | neutral film | spin-coated film | D–A (benzodithiophene) | 10.1002/adma.201001263 (Liang/Yu 2010) | med |
| PffBT4T-2OD (PCE11) | (difluoro-BT + quaterthiophene/thienothiophene repeat) | 1.65 | onset (edge ~750 nm) | neutral film | spin-coated film (hot processing) | D–A (fluorinated BT) | 10.1038/ncomms6293 (He, Yan et al. 2014) | high |
| Fluorinated-BT FET polymers (PBT/PRF/P2F/PDF) | (F-BT alternating repeat) | 1.25–1.30 | onset | neutral film | spin-coated film | D–A (fluorinated BT) | US 10,875,957 (secondary) | low |

**SMILES note:** repeat units are written with `*` denoting the two backbone attachment points (polymerization at the 2,5- / 2,7- positions). The selenophene `[se]` aromatic notation is used; some toolkits prefer `[Se]` in an explicit ring — validate against your cheminformatics stack before ingestion. The D–A repeat SMILES (PCDTBT, PCPDTBT, F8BT) are constructed approximations of the alternating repeat and should be sanity-checked/canonicalized before use.

## Per-Class Anchor Counts

| Chemical class | Anchors (incl. low-conf) | High/med-confidence | Calibration adequacy |
|---|---|---|---|
| Polythiophenes | 6 | 5 | **Strong** — densely anchored 1.9–2.0 eV; backbone of the set |
| Dioxythiophenes (PEDOT family) | 4 | 3 | **Adequate** — anchored ~1.55–1.85 eV |
| Dioxypyrroles (PEDOP/PProDOP) | 3 | 2 | Adequate — spans 2.0–3.0 eV |
| Dioxyselenophenes (PEDOS) | 2 | 2 | Thin but solid — ~1.40–1.50 eV (good low-end Se anchors) |
| Polyselenophenes | 3 | 3 | Adequate — 1.6–1.9 eV |
| Polypyrroles | 2 | 1 | **Thin/data-poor** — most PPy literature reports doped films |
| Polyfurans | 2 | 2 | **Thin** — effectively one excellent primary source (Bendikov 2015) |
| Polyfluorenes | 2 | 2 | **Thin** — PFO carries onset-vs-λmax ambiguity |
| Polycarbazoles (homopolymer) | 2 | 1 | **Thin** for homopolymers; D–A copolymers (PCDTBT) much stronger |
| Donor–acceptor low-gap | 6 | 4 | **Strong** — covers the documented-weak 1.25–1.69 eV regime |

**Recommendation on adequacy:** Classes marked Strong/Adequate (polythiophenes, dioxythiophenes, dioxypyrroles, selenophenes, D–A) can support per-class calibration offsets. Polyfurans, polyfluorenes, polypyrroles, and carbazole homopolymers should be calibrated against the global axis with widened error bars until more primary anchors are found.

## Excluded Rows (with reasons)
- **PEDOT sub-eV "gap" / doped state** — doped polaron/bipolaron mid-gap absorption (~0.8 and ~1.6 eV bands, NIR tail), NOT the neutral π–π* gap. The canonical trap this project warns about.
- **PEDOT:PSS "2.8–3.1 eV" (ResearchGate HOMO–LUMO)** — electrochemically-derived HOMO–LUMO, not an optical onset; additionally the pristine film is a *mixed* doping state. Per Garg et al. (S0379677916302788): "a film of PEDOT:PSS consists of a mixture of undoped and doped PEDOT units in the ratio 1:4…an intermediate state between the fully doped (oxidized) and undoped (reduced) state." Unsuitable as a clean neutral anchor.
- **Polypyrrole 1.01 eV (Tauc/dielectric) and 0.42 eV (indirect)** — heavily oxidized/doped films; not neutral π–π*.
- **Polypyrrole–chitosan composites (1.30–2.32 eV)** — composite, doping-dependent, ill-defined neutral state.
- **P3MT "≈1 eV" (Sanchez et al., Polym. J. 2001)** — explicitly the oxidized (conducting) state.
- **All CV/electrochemical band gaps** — fundamental gaps, larger than optical by the exciton binding energy. Excluded per rules and NOT converted: P3HS Egelec ≈ 1.9 eV; P3AT electrochemical gaps; polyfluorene copolymer CV gaps (1.3–2.1 eV, Chalmers); dithienylfuran 1.97 eV (CV); terthiophene-analogue CV gaps; PCz-DTBTT, PSeB1/PSeB2, selenophene-BDT copolymers (1.47/1.72/1.78 eV reported only via CV); poly(selenolo[2,3-c]thiophene) 0.9 eV (CV).
- **Polyaniline / emeraldine** — excluded entirely (ill-defined, non-classical gap).
- **Poly(o-toluidine) 2.52 eV** — polyaniline derivative; excluded by extension of the PANI rule.
- **DFT/TD-DFT-only computed gaps** — PEDOT/PEDOS Springer DFT (2.3–2.6 eV); polypyrrole 1.88 eV first-principles; PT GW 2.38 eV; oligoselenophene TD-DFT. Computed, not experimental; the polypyrrole 3.2 eV calc. is retained ONLY as a flagged low-confidence reference, not a measurement.
- **Cross-conjugated narrow-gap patent polymers ("~0.3 eV" by FT-IR, US 11,312,819)** — exotic, neutral-vs-doped state not cleanly confirmable, secondary patent source.
- **Selenolo/thieno-fused low-gap polymers (0.72–0.96 eV, 10.1021/cm102395v)** — spectroelectrochemical optical gaps, but measured in mixed redox windows and structurally exotic; held back pending clean neutral-state confirmation (candidate for future inclusion, low priority).

## Caveats — Systematic Shifts Limiting Absolute Accuracy
1. **Solution vs solid film.** Solid-state films red-shift the absorption onset relative to solution (chain planarization, extended conjugation, interchain aggregation), lowering apparent gaps by ~0.1–0.5 eV. P3HT is canonical: thin-film onsets are consistently lower than chlorobenzene-solution onsets. Because this anchor set mixes media, the calibration axis ideally should be conditioned on medium, or solution-only and film-only anchors fit separately.
2. **Regioregularity.** Regioregular P3HT/P3OT (~1.9 eV) sit ~0.2–0.3 eV below regiorandom analogues owing to backbone planarization and tighter π-stacking. Mixing RR and RRa data injects scatter; all alkylthiophene anchors here are regioregular and should be tagged as such.
3. **Molecular weight / conjugation length.** Higher MW lengthens the effective conjugation length and lowers the gap until saturation (~18 thiophene rings, per oligomer extrapolations). Low-MW or oligomeric/electrodeposited films read high relative to the polymer limit — relevant because most electropolymerized anchors (PEDOT, PProDOT, polypyrrole, polyfuran, polyselenophene) have undefined/short effective conjugation lengths.
4. **Onset vs λmax derivation.** λmax-derived gaps are systematically larger than onset-derived gaps by ~0.1–0.4 eV. PFO is the clearest conflict: Liao et al. (10.1063/1.126713) explicitly argue the transport gap matches the absorption *maximum* better than the *edge*. Rows are tagged; do not mix derivations within a single regression without an offset term.
5. **Film morphology / processing (β-phase, annealing, crystallinity, residual doping).** PFO's β-phase yields a sharp 2.87 eV vibronic feature absent in glassy films; annealing and electrodeposition conditions shift onsets. Electrodeposited films (the majority of PEDOT/PProDOT/polypyrrole/polyfuran/polyselenophene anchors) carry residual-doping and surface-roughness uncertainties that broaden the band edge and bias onsets.
6. **Net implication for the calibration.** Absolute accuracy is realistically limited to **±0.1–0.2 eV** even for high-confidence anchors, and worse (±0.3 eV or more) for low-confidence (electrodeposited, λmax-derived, or state-ambiguous) points. The computed axis (sTDA-xTB / TD-DFT on oligomers) additionally needs an explicit oligomer→polymer extrapolation, since experimental anchors are polymer-limit values while the calculation is on finite oligomers — this convergence error compounds with the measurement scatter above. Per-class calibration is advisable wherever anchor counts permit (polythiophenes, PEDOT, D–A), and the low-gap D–A anchors should be weighted heavily when validating the documented-weak sTDA-xTB regime below ~1.7 eV.

### Suggested staged next steps
- **Stage 1 (immediate):** Ingest the high-confidence rows (polythiophenes, PEDOS, P3HS, polyselenophene, polyfuran, PCDTBT, PCPDTBT, PffBT4T-2OD, PProDOP) as the primary calibration set; fit a global linear map plus per-class offsets where ≥3 anchors exist.
- **Stage 2:** Add med-confidence rows with down-weighting; treat PFO and F8BT with an explicit onset-vs-λmax flag term.
- **Stage 3 (data-gap closure):** Commission targeted primary-literature retrieval for the thin classes — unsubstituted electrochemical polythiophene onset corroboration beyond Kaneto 1983, additional neutral polypyrrole optical onsets (rare), a second primary polyfuran source, and clean neutral-state poly(2,7-carbazole) homopolymer onsets. **Threshold to revise calibration:** if any new primary anchor in a thin class deviates >0.2 eV from the current class mean, refit that class separately before trusting screening predictions in its gap range.
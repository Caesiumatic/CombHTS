# CombHTS Calibration & Benchmark Report: Resolving the Eox Anchor, Reference Scale, Accuracy Ceiling, and Clean Experimental Data

## TL;DR
- **Calibrate the computed adiabatic IP against the anodic PEAK (Epa), not onset.** The peak is the closer experimental proxy to a one-electron thermodynamic ionization observable; onset is a kinetic/threshold quantity. Use ONSET only as the in-window screening filter. The project's proposed peak-for-calibration / onset-for-screening split is defensible and literature-consistent — provided peak and onset are kept as *separate* label columns and never regressed together.
- **Standardize on Ag/AgCl as the master scale** and convert native Fc/Fc⁺ rows in acetonitrile at Fc/Fc⁺ = +0.400 V vs SCE = +0.445 V vs Ag/AgCl(sat'd KCl), but carry a stated systematic floor of ~0.05–0.15 V (liquid-junction + solvent effects). Never pool two reference scales into one linear fit — the intercept absorbs the reference offset, so two scales require two intercepts.
- **Honest near-term MAE is 0.20–0.35 V** for onset/Epa-heavy nonaqueous data after linear calibration; **never claim < 0.15 V** — that is the irreducible floor set by potential-type mismatch plus liquid-junction error.

## Key Findings
1. Monomer electro-oxidation in electropolymerization is an irreversible EC′ process: no reversible E1/2 exists; only the kinetic observables Epa and Eonset are available.
2. The Epa − Eonset gap for conjugated monomers is typically 0.15–0.35 V (e.g., EDOT onset 0.88 V / peak 1.2 V vs Ag/Ag⁺, ΔE ≈ 0.3 V), and it is monomer-dependent.
3. IPEA-xTB vertical ΔSCF IP/EA errors are 0.2–0.4 eV vs DFT; GFN2-xTB redox MAD ≈ 0.30 V vs experiment (ROP313/OROP). Calibration to (TD)DFT recovers near-DFT ranking quality but does not erase the medium/label floor.
4. DFT ΔSCF oxidation potentials reach 0.07–0.17 V MAE only with per-class calibration; uncalibrated B3LYP systematically underestimates IP by 0.14–0.21 eV (oxidation potentials by ~0.33 V).
5. Pavlishchuk & Addison (2000) is the authoritative MeCN conversion source: Fc/Fc⁺ = +0.400 V vs SCE; SCE − Ag/AgCl(sat'd) ≈ +0.045 V; so Fc/Fc⁺ ≈ +0.445 V vs Ag/AgCl in MeCN.
6. The Camarada 2011 thiophene-oligomer onsets (T 1.50, T2 1.15, T3 0.880 V vs Ag/AgCl in MeCN) are the cleanest single-scale calibration anchors found.

---

## PART A — Calibration Anchor: Peak vs Onset

### A.1 What each quantity physically represents
Monomer electro-oxidation during electropolymerization is a textbook **EC′ (electrochemical–chemical) irreversible process**: one-electron removal generates a radical cation that couples immediately (radical–radical coupling, the mechanism reviewed by Heinze and reaffirmed in *Chem. Rev.* 2025, DOI 10.1021/acs.chemrev.5c00183, which describes the cascade as "oxidation, coupling, and propagation … initiated by monomer oxidation, whereupon a cationic monomer radical is generated through the Faradaic transfer of one electron to the anode"). Because the monomer radical cation is consumed chemically, the reverse reduction wave is absent and **no reversible half-wave potential E1/2 exists** for the monomer. The standard CV literature (Ossila CV reference) notes that "if the reverse peak is missing, an electron transfer is classified as irreversible," and that the half-wave average "remains the best measure [only] if cathodic and anodic peaks are present" — which they are not for the monomer wave.

- **Anodic peak potential (Epa):** potential of maximum anodic current on the forward scan. For an irreversible electron transfer it is a *kinetic* quantity dependent on the heterogeneous rate constant k₀, transfer coefficient α, and scan rate (Nicholson & Shain, *Anal. Chem.* 1964, 36, 706, DOI 10.1021/ac60210a007). It nonetheless tracks where the bulk one-electron removal occurs and correlates strongly and monotonically with HOMO/IP across a monomer series.
- **Onset potential (Eonset):** potential where faradaic current first rises measurably above baseline; physically marks where radical-cation generation and film nucleation begin. It is *more* kinetically and threshold-defined than the peak — sensitive to current-detection threshold, monomer concentration, and electrode condition.
- **E1/2 (half-wave):** thermodynamic formal-potential proxy, meaningful only for (quasi)reversible couples; unmeasurable for monomers.

### A.2 Magnitude and spread of the Epa − Eonset gap
Representative primary-literature values:
- **EDOT:** onset 0.88 V, peak 1.2 V vs Ag/Ag⁺ (ΔE ≈ 0.3 V) (US 8,227,567).
- **EDOT-F:** onset 1.0 V, peak 1.2 V vs Ag/Ag⁺ (ΔE ≈ 0.2 V) (US 7,022,811).
- **Thiophene oligomers (Camarada 2011):** onsets T 1.50, T2 1.15, T3 0.880 V vs Ag/AgCl.

Across thiophene/EDOT/pyrrole/carbazole families the gap is typically **0.15–0.35 V**, wider for sluggish high-overpotential monomers (unsubstituted thiophene) and narrower for electron-rich, fast-coupling monomers.

### A.3 What shifts Epa vs Eonset
- **Scan rate:** for a totally irreversible wave Epa shifts anodically by ~30/(αn) mV per decade of scan rate (≈ 30–60 mV/decade) (Nicholson & Shain 1964); onset is comparably scan-rate sensitive. Faster follow-up coupling (larger chemical rate constant) pulls the apparent wave cathodically.
- **Electrode material / nucleation / adsorption:** Pt vs Au vs glassy carbon vs ITO change overpotential and nucleation behavior; adsorption pre-peaks and gold-oxide peaks can confound assignment (cf. PANI electropolymerization, IOP *J. Electrochem. Soc.* 10.1149/1945-7111/ab9929, where a gold-oxide peak appears alongside the irreversible monomer-oxidation peak).
- **Follow-up radical chemistry:** stronger coupling/deprotonation shifts the wave to less positive potentials; trace water and monomer basicity alter proton scavenging and electron count.

### A.4 Which observable matches a computed adiabatic IP
A quantum-chemical adiabatic IP via ΔSCF is a **thermodynamic, one-electron, vertical-to-relaxed ionization free energy** (with implicit solvent, an approximate ΔG_ox). It contains no electrode kinetics, nucleation, or coupling chemistry. The **onset** is dominated by exactly those extra-thermodynamic factors plus a current-detection threshold, making it the *poorest* match to a thermodynamic IP. The **peak**, while kinetic, tracks the bulk one-electron removal and correlates far more tightly with HOMO/IP across a series (this is why HOMO-vs-Eox linear fits in the DFT literature reach R² ≈ 0.99). **Recommendation: calibrate the computed Eox against Epa (peak).**

### A.5 Critical evaluation of the peak-for-calibration / onset-for-screening split
The split is **supported, with caveats.**
- *Peak-for-calibration is correct* because (a) onset is more weakly defined and more method-dependent, increasing label noise, and (b) the peak is the more reproducible, more thermodynamically-correlated observable.
- *Onset-for-screening is correct* because electropolymerization feasibility ("does the monomer oxidize before the solvent/electrolyte anodic limit, so that radical cation forms and film growth begins?") is physically a threshold question answered at onset.

Caveats: (1) the two anchors differ by a roughly constant but monomer-dependent 0.15–0.35 V, so the screening filter should apply an onset margin — e.g., require the calibrated Epa to sit ≥0.2–0.3 V below the solvent anodic limit, or predict onset = Epa − Δ with a family-specific Δ. (2) Mixing peak-derived and onset-derived experimental values in the *same* calibration regression injects ~0.2 V of artificial scatter; keep peak and onset as distinct label columns.

---

## PART B — Master Reference Scale and Conversion Constants

### B.1 Authoritative MeCN constants (Pavlishchuk & Addison 2000)
**Pavlishchuk, V. V.; Addison, A. W., *Inorg. Chim. Acta* 2000, 298(1), 97–102, DOI 10.1016/S0020-1693(99)00407-7** is the standard citable source. Constants at 25 °C in acetonitrile:
- **Fc/Fc⁺ = +0.400 V vs aqueous SCE** (the universally attributed P&A constant; RSC and other groups apply "E°₁/₂(Fc/Fc⁺) = +0.400 V vs. SCE").
- **Fc/Fc⁺ ≈ +0.624 V vs SHE/NHE** (commonly cited as the P&A conversion constant).
- **0.01 M Ag/AgNO₃ → SCE = +0.298 V**, hence **Fc/Fc⁺ ≈ +0.10 V vs 0.01 M Ag/Ag⁺**.
- **SCE = +0.244 V vs SHE** (P&A value; standard tables give +0.241 V).

The breadth of the Fc-vs-SCE literature itself is a warning: the ACS Electrochemistry 2025 calibration paper (DOI 10.1021/acselectrochem.5c00382) records ferrocene reported as **0.38, 0.40, and 0.41 V vs SCE** in acetonitrile, and notes that across the literature "multiple reference electrode scales are used … leading to discrepancies of up to 0.3 eV."

### B.2 SCE vs Ag/AgCl and SHE offsets
- **Ag/AgCl (sat'd KCl) = +0.197 V vs SHE** (standard; some sources +0.199 V).
- **SCE − Ag/AgCl(sat'd) ≈ +0.045 V** (SCE is ~45 mV positive of saturated Ag/AgCl).
- In MeCN therefore: **Fc/Fc⁺ ≈ +0.400 + 0.045 = +0.445 V vs Ag/AgCl(sat'd)**; SHE = Ag/AgCl + 0.197 V.

**Practical conversions to the Ag/AgCl master scale:**
- E(vs Ag/AgCl) = E(vs SCE) + 0.045 V
- E(vs Ag/AgCl) ≈ E(vs Fc/Fc⁺) + 0.445 V (in MeCN)
- E(vs Ag/AgCl) = E(vs SHE) − 0.197 V

### B.3 Liquid-junction-potential error and the systematic floor
Force-converting nonaqueous Fc/Fc⁺ values to an aqueous Ag/AgCl scale requires a junction between aqueous reference electrolyte and nonaqueous sample. The literature is explicit that this LJP is "undefined, variable, and unmeasurable" (Wikipedia, citing Gritzner & Kuta), and that the assumption of solvent-invariant Fc is "actually false." Magnitudes:
- Generic aqueous–aqueous LJPs: 1–40 mV.
- Aqueous|nonaqueous junctions and Ag/Ag⁺ pseudo-references: vary by "hundreds of mV."
- A Ag/AgCl **quasi-reference** in MeCN: per Wikipedia, "The ferrocene (0/1+) couple should lie around 400 mV versus this Ag/AgCl QRE in an acetonitrile solution. This potential will vary up to 200 mV with specific undefined conditions, thus adding an internal standard such as ferrocene … is always necessary."
- The Fc couple itself shifts substantially with solvent: per Mozhzhukhina & Calvo, *J. Electrochem. Soc.* 2017, 164, A2295 (DOI 10.1149/2.0341712jes), "the reversible ferrocene/ferrocenium couple is observed with a potentials shift varying in different solvents and reaching 0.5 V difference between ACN and DMSO."

**Practical systematic floor for force-converted rows: ~0.05–0.15 V within one solvent (MeCN), larger across solvents.** This number bounds how tightly the calibration can honestly be tuned.

### B.4 Recommendation and why pooling two scales is algebraically wrong
**Standardize on Ag/AgCl as the master scale; convert native Fc/Fc⁺ MeCN rows at +0.445 V (SCE rows at +0.045 V) and tag each converted row with a +0.05–0.15 V systematic-uncertainty flag.** A separate Fc/Fc⁺ track is unnecessary only if the offset is treated explicitly as a per-reference constant rather than silently absorbed.

Why one shared fit fails: the calibration model is E_ox,exp = a·(IP_xTB) + b. The intercept **b absorbs all constant offsets, including the reference-electrode zero.** Two reference scales (Ag/AgCl vs Fc/Fc⁺) differ by a fixed ~0.445 V; a single b cannot satisfy both subsets simultaneously, so least-squares splits the difference and injects ~0.2–0.4 V of bias into both. Correct approaches: (i) convert everything to one scale *before* fitting (preferred), or (ii) fit a shared slope with **reference-specific intercepts** (a fixed effect per reference electrode).

**Unplaceable rows (must be EXCLUDED from clean calibration):** values vs a bare "Ag wire"/Ag/Ag⁺ pseudo-reference with no ferrocene calibrant reported; values in BFEE / BF₃·Et₂O Lewis-acid media; mixed-solvent media; and aqueous-acid media for monomers normally run in MeCN (different mechanism and junction). These cannot be honestly converted.

---

## PART C — Accuracy Ceiling for xTB-after-Calibration

### C.1 xTB IP and redox errors
- **IPEA-xTB** performs vertical ΔSCF; per Wilbraham, Berardo, Turcani, Jelfs & Zwijnenburg, *J. Chem. Inf. Model.* 2018, 58, 2450 (DOI 10.1021/acs.jcim.8b00256): "IPEA-xTB performs vertical ΔSCF calculations, and has previously been shown to result in typical errors for computed vertical IP/EA values of **0.2−0.4 eV** compared to DFT in vacuum." After linear calibration to (TD)DFT they report strong linear correlation (R² = 0.99 for both dielectric environments), i.e., calibration mainly fixes slope/offset and preserves ranking.
- **GFN2-xTB redox potentials:** per Neugebauer, Bohle, Bursch, Hansen & Grimme, *J. Phys. Chem. A* 2020, 124, 7166 (DOI 10.1021/acs.jpca.0c05052), on the OROP organic subset of ROP313: "mean absolute deviation from the experiment, **MAD_GFN2-xTB = 0.30 V**, MAD_GFN1-xTB = 0.31 V, PM6-D3H4 = 0.61 V, PM7 = 0.60 V), almost reaching low-cost DFT quality (MAD_B97-3c = 0.25 V)."
- Calibrated screening recovers near-DFT-quality ranking at orders-of-magnitude lower cost (Wilbraham 2018; Heath-Apostolopoulos, Wilbraham & Zwijnenburg, *Faraday Discuss.* 2019, 215, 98, DOI 10.1039/C8FD00171E).

### C.2 DFT ΔSCF oxidation-potential errors vs experiment
- Per Fu, Liu, Yu, Wang & Guo, *JACS* 2005, 127, 7227 (DOI 10.1021/ja0421856): a calibrated B3LYP scheme predicts gas-phase adiabatic IPs of 160 molecules "with a precision of 0.14 eV," and the full MeCN protocol predicts "the standard redox potentials of 270 structurally unrelated organic molecules in acetonitrile. The standard deviation of the predictions was **0.17 V**."
- Per-class calibrated B3LYP/COSMO reaches MAE ~0.07–0.074 V; an OLED-molecule study reports Eox MAE ~0.05 V (PBE0/def2-TZVP, post-fit).
- Uncalibrated B3LYP **systematically underestimates IP by 0.14–0.21 eV** and oxidation potentials by ~0.33 V (Schlegel group, "Theoretical Determination of One-Electron Oxidation Potentials").
- Range-separated functionals (ωB97X-D, CAM-B3LYP) reach MAE ~0.05–0.09 V on curated PCET sets.

### C.3 Irreducible label/medium noise floor
Two effects cap honesty regardless of method quality:
1. **Potential-type mismatch** — calibrating a thermodynamic adiabatic IP against a kinetic irreversible Epa (or onset) embeds the 0.15–0.35 V peak-onset overpotential and its monomer dependence (≥0.10–0.15 V residual scatter even after a global slope/offset).
2. **Liquid-junction/reference error** of ~0.05–0.15 V (Part B).

Combined in quadrature these give a floor of roughly **0.15–0.20 V** that no method improvement removes for force-converted, irreversible-Epa data.

### C.4 Synthesized accuracy statement
**Honest near-term MAE target is 0.20–0.35 V for onset/Epa-heavy nonaqueous monomer data after linear calibration; never claim < 0.15 V.** The 0.15 V floor (Z) is justified by the quadrature sum of the irreducible potential-type mismatch (≥0.10–0.15 V) and liquid-junction/reference noise (0.05–0.15 V), and is independent of the ~0.30 V intrinsic GFN2-xTB redox error that calibration only partially removes. Report MAE *separately* for peak-anchored and onset-anchored subsets so the two noise regimes are never conflated.

---

## PART D — Clean Experimental Monomer Oxidation Potentials

Conventions: "Value (as reported)" preserves original units/reference; "→Ag/AgCl" applies Part B constants (SCE → Ag/AgCl +0.045 V; Fc/Fc⁺ → Ag/AgCl +0.445 V in MeCN; converted values for non-MeCN solvents marked *approx* because the conversion constant is solvent-specific). Confidence reflects clarity of conditions and convertibility.

| # | Monomer | SMILES | Value (as reported) | Type | Ref electrode | Solvent | Electrolyte | Working electrode | Scan rate | →Ag/AgCl | Citation (DOI / source) | Conf. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Thiophene | c1ccsc1 | 2.05 V | peak | Ag/AgCl | MeCN | TBA salt | — | — | 2.05 | Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 (review citing primary) | med |
| 2 | Thiophene | c1ccsc1 | ~1.6 V | dep/onset | SCE | MeCN | TBABF4 | Pt | — | ~1.65 | via 10.1016/j.jelechem.2004.02.020 (PbO2 study) | med |
| 3 | Thiophene | c1ccsc1 | 1.50 V | onset | Ag/AgCl | MeCN | — | Pt | — | 1.50 | Camarada 2011, 10.1002/polb.22360 | high |
| 4 | 3-Methylthiophene | Cc1ccsc1 | ~1.5 V | dep | SCE | MeCN | TBABF4 | Pt | — | ~1.55 | Polythiophene review (Roncali) / 10.1016/j.jelechem.2004.02.020 | med |
| 5 | Poly(3-methylthiophene) film | Cc1ccsc1 | ~0.55 V | peak (film) | SCE | MeCN | LiClO4 | Pt | 100 mV/s | ~0.60 | DTIC ADA239902 (primary CV) | med |
| 6 | 3-Hexylthiophene | CCCCCCc1ccsc1 | 1.35 V | (deposition) | Ag/AgNO3 | MeCN | — | — | — | ~1.5 (approx) | via Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | low |
| 7 | EDOT | C1COc2cscc2O1 | onset 0.88 / peak 1.2 V | onset+peak | Ag/Ag⁺ | MeCN | TBAP | Pt | 50 mV/s | ~1.0 / ~1.3 (approx) | US 8,227,567 (patent) | med |
| 8 | EDOT | C1COc2cscc2O1 | 1.4 V | peak | Ag/AgCl | MeCN | — | — | — | 1.4 | Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | med |
| 9 | EDOT-F | — | onset 1.0 / peak 1.2 V | onset+peak | Ag/Ag⁺ | MeCN | TBAP | Pt disk | 20 mV/s | ~1.1 / ~1.3 (approx) | US 7,022,811 | med |
| 10 | Bithiophene (2,2′) | c1ccc(-c2cccs2)s1 | 1.15 V | onset | Ag/AgCl | MeCN | — | Pt | — | 1.15 | Camarada 2011, 10.1002/polb.22360 | high |
| 11 | Terthiophene | c1ccc(-c2ccc(-c3cccs3)s2)s1 | 0.880 V | onset | Ag/AgCl(sat'd KCl) | MeCN | — | Pt | — | 0.880 | Camarada 2011, 10.1002/polb.22360 | high |
| 12 | Pyrrole | c1cc[nH]c1 | ~0.7 V | (deposition) | SCE | aqueous | — | — | — | ~0.75 | Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | med |
| 13 | N-Methylpyrrole | Cn1cccc1 | — (electroactive) | — | Ag/Ag⁺ | MeCN | LiClO4 | Pt | — | — | 10.1016/0022-0728(91)85386-4 | low |
| 14 | Aniline | Nc1ccccc1 | +0.86 V (half-wave) | E1/2 (RDE) | SCE | MeCN | — | rotating Pt | — | ~0.91 | aromatic-amine oxidation, 10.1016/0026-265X(67)90012-4 | med |
| 15 | Aniline | Nc1ccccc1 | 0.96 V | peak | Ag/AgCl | MeCN | LiBF4 | Pt | — | 0.96 | aniline–thiophene copolymer, 10.1016/S0014-3057(04)00309-X | high |
| 16 | Aniline | Nc1ccccc1 | ~0.8 V | — | Ag/AgCl | aqueous | — | — | — | ~0.8 | Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | med |
| 17 | o-Anisidine | COc1ccccc1N | 0.76 V | peak | SCE | MeCN | — | — | — | 0.81 | tabulated from primary (IJIRSET compilation) | low |
| 18 | o-Toluidine | Cc1ccccc1N | 0.85 V | peak | SCE | MeCN | — | — | — | 0.90 | tabulated from primary (IJIRSET compilation) | low |
| 19 | Diphenylamine | c1ccc(Nc2ccccc2)cc1 | 0.83 V | peak | SCE | MeCN | — | rotating Pt | — | 0.88 | aromatic-amine oxidation, 10.1016/0026-265X(67)90012-4 | med |
| 20 | Carbazole | c1ccc2c(c1)[nH]c1ccccc12 | ~1.0 V (onset of ox. peak) | onset/peak | SCE | MeCN | LiClO4 | Pt | — | ~1.05 | Front. Mater. 2019, 10.3389/fmats.2019.00131 | med |
| 21 | 3-Ethylcarbazole | CCc1ccc2c(c1)[nH]c1ccccc12 | 1.04 V | peak (1st scan) | SCE | MeCN | — | Pt | 100 mV/s | 1.09 | 3,6-substituted carbazoles, 10.1016/j.jelechem.2021.115520 | high |
| 22 | N-Vinylcarbazole | C=Cn1c2ccccc2c2ccccc21 | 0.8 V (onset) | onset | SCE | MeCN | LiClO4 | Pt/ITO | 10 mV/s | 0.85 | PVK electropolymerization, 10.1515/epoly-2017-0105 | med |
| 23 | Selenophene | c1cc[se]c1 | 1.60 V | onset/threshold | SCE | MeCN | TBATFB | Pt | 100 mV/s | 1.65 | US 10,196,480 | med |
| 24 | Furan (oligofuran 5F) | — | 0.71 V | peak (irrev) | Ag/AgCl(NaCl) | propylene carbonate | TBABF4 | Pt disk | — | 0.71 | US 8,921,582 (Fc/Fc⁺ cal = 0.34 V) | med |
| 25 | 3-Methylselenophene | Cc1cc[se]c1 | 1.17 V | onset | Ag/AgCl | DCM | TBAPF6 | — | — | 1.17 | 3-MeSe-EDOT hybrid, 10.1016/j.matlet.2020.127456 | med |
| 26 | EDOT–3MeSe–EDOT (D–A trimer) | — | onset 0.50 V | onset | Ag/AgCl | DCM | TBAPF6 | — | — | 0.50 | 10.1016/j.matlet.2020.127456 | med |
| 27 | CPDT (cyclopentadithiophene) | C1CCc2c1cc1ccsc1c2 (core) | ox. cycling −0.4→+1.0 V | onset/peak | Fc/Fc⁺ | MeCN | TBA salt | various | — | ~1.4 (approx) | poly-CPDT metallopolymer, 10.1021/ic501840p | low |
| 28 | ETE-S (EDOT–thiophene–EDOT, S-side chain) | — | 0.63 V | onset | Ag/AgCl | aqueous/MeCN | — | — | — | 0.63 | via Chem. Rev. 2025, 10.1021/acs.chemrev.5c00183 | med |

### Lewis-acid / mixed / pseudo-reference flagged rows — EXCLUDE from clean calibration
- **Thiophene in 5 M aqueous HClO₄:** ~0.9 V vs SCE (vs 1.6 V in MeCN) — aqueous-acid medium changes mechanism. Bazzaoui et al. (cited in 10.1016/j.jelechem.2004.02.020). EXCLUDE.
- **Pyrene in BFEE/TFA/PEG:** 0.65 V vs SCE (vs 1.15 V in neutral MeCN) — BFEE Lewis-acid medium. EXCLUDE.
- **3-Methoxythiophene** kinetics often reported in BFEE-type / specialty media — verify medium before use.
- **Any "Ag wire" pseudo-reference without ferrocene calibration** — unplaceable. EXCLUDE.

### Recommended high-confidence seed set
The Camarada 2011 thiophene oligomers (T 1.50, T2 1.15, T3 0.880 V vs Ag/AgCl, MeCN, single lab, single scale, onset) are the cleanest anchors for an onset-track fit. For a peak-track fit, 3-ethylcarbazole (1.04 V vs SCE → 1.09 vs Ag/AgCl), aniline (0.96 V vs Ag/AgCl), and diphenylamine (0.83 V vs SCE → 0.88 vs Ag/AgCl) are well-documented and convertible. These small single-ring/simple species directly rebalance a benchmark currently dominated by large exotic molecules.

---

## Recommendations
1. **Adopt Epa (peak) as the calibration target and Eonset as the screening filter**; store them as separate label columns and never regress mixed peak/onset labels together.
2. **Make Ag/AgCl(sat'd KCl) the master scale.** Convert MeCN Fc/Fc⁺ rows with +0.445 V and SCE rows with +0.045 V; tag each converted row with a +0.05–0.15 V systematic-uncertainty flag. Exclude BFEE/mixed/aqueous-acid/uncalibrated-pseudo-reference rows.
3. **If non-MeCN or non-Ag/AgCl rows must be retained, fit a shared slope with reference-/solvent-specific intercepts**, rather than pooling into one regression.
4. **Set the MAE language to 0.20–0.35 V with a hard floor of Z = 0.15 V.** Report MAE separately for peak-anchored and onset-anchored subsets.
5. **Rebalance the benchmark toward the Part-D small monomers and the Camarada anchors**; deprioritize large exotic molecules that currently dominate.
6. **For the screening filter, encode an onset margin:** require calibrated Epa to sit ≥0.2–0.3 V below the solvent/electrolyte anodic limit (or model onset = Epa − Δ_family).

**Thresholds that would change these recommendations:**
- If a clean, single-lab, single-scale dataset of ≥30 small monomers with Epa vs Ag/AgCl in one solvent emerges, tighten the MAE target to **0.15–0.25 V** and consider dropping the explicit reference-offset flag for that subset.
- If cross-solvent rows come to dominate the benchmark, widen the target to **0.35–0.45 V** and report per-solvent MAEs, because the solvent-dependent Fc shift (up to ~0.5 V MeCN↔DMSO) then dominates the error budget.
- If the project moves to an internal Fc/Fc⁺ master scale (recommended long-term for nonaqueous purity), the floor Z can drop toward ~0.10 V because the liquid-junction term largely disappears — but only if every row carries a measured ferrocene calibrant.

## Caveats
- Many literature "monomer oxidation potentials" are reported loosely as onset/deposition thresholds; peak-vs-onset assignment is often ambiguous. The confidence flags in Part D reflect this; verify the exact observable in the primary text before assigning a row to the peak or onset track.
- The +0.624 V Fc/SHE P&A value carries a ~20 mV internal inconsistency (0.400 + 0.244 = 0.644 V vs SHE), possibly addressed by the 2024 corrigendum (Pavlishchuk & Addison, *Inorg. Chim. Acta* 2024, 578, 122468, DOI 10.1016/j.ica.2024.122468); the corrigendum text could not be retrieved, so treat the SHE-referenced numbers with this caveat. The SCE-referenced constant (+0.400 V) and the SCE−Ag/AgCl offset (+0.045 V) are unaffected and reliable.
- Several Part-D values are from patents or review citations of primary work. Where marked low/medium confidence, retrieve and verify against the cited primary article (especially exact electrolyte, working electrode, scan rate, and whether the value is peak or onset) before inclusion in the calibration set.
- The peak−onset gap is monomer-dependent, so any single global onset margin is approximate; family-specific Δ values will improve the screening filter.
- Reference-electrode conversions for non-MeCN solvents (DCM, propylene carbonate) using the MeCN P&A constants are approximate — the Fc/Fc⁺ potential is solvent-dependent (up to ~0.5 V across solvents), so converted values for rows #24–26 are flagged *approx* and should ideally be re-anchored with an in-solvent ferrocene calibrant.
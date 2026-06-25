# Practical Electrochemical Stability Windows for Nonaqueous Solvent + Tetraalkylammonium Systems — Reference Table for Electropolymerization Screening

## TL;DR
- The single most authoritative, condition-explicit primary dataset for these solvents is Ue, Ida & Mori (J. Electrochem. Soc. 1994, 141, 2989; DOI 10.1149/1.2059270), measured on glassy carbon with a 0.65 M quaternary-onium salt, a stated 1 mA cm⁻² current-density cutoff, 5 mV s⁻¹, 25 °C; it anchors the PC, MeCN, GBL and nitromethane rows after conversion to Ag/AgCl(sat'd KCl). (Note: one secondary citation reports Ue's cutoff as 0.1 mA cm⁻² — verify against the 1994 primary paper before locking this in; see Caveats.)
- Clean, convertible primary windows were obtained for PC (all four anions, via Ue's anion/cation-decoupled limits), MeCN/TBAPF6, nitromethane, GBL and benzonitrile. The priority pairs **NMP**, **nitrobenzene**, and the broader **DMSO, THF and sulfolane** systems could NOT be sourced to a clean, condition-explicit primary window with a tetraalkylammonium salt AND a convertible reference electrode — they are flagged as gaps.
- Every converted row carries the project's stated 0.05–0.15 V systematic floor; all non-acetonitrile conversions are flagged "approx" because the SCE/SHE/Fc reference scales themselves shift between solvents.

## Key Findings
- **Nitromethane is anodically robust but cathodically weak** (+2.9 V vs SHE anodic, only −1.0 V vs SHE cathodic on glassy carbon/Et4NBF4) — the least-negative cathodic limit among common aprotic solvents. It is a hard exclusion for any reductive electropolymerization and a strong choice only where high oxidative headroom is needed.
- **Windows are criterion- and electrode-dependent, not solvent constants.** The MeCN window with 0.1 M TBAPF6 on Pt is reported as 5.7 V (−2.7 to +3.0 V vs SCE) by Elgrishi et al. (J. Chem. Educ. 2018, 95, 197–206; DOI 10.1021/acs.jchemed.7b00361), but that source gives the window only qualitatively ("the current response should be relatively flat"), with no stated current-density criterion — so it is not directly comparable to Ue's 1 mA cm⁻² values.
- **Anion sets the anodic limit; cation sets the cathodic limit** (Ue). For the four PC salts, oxidative stability ranks PF6⁻ ≈ BF4⁻ > TFSI⁻ > ClO4⁻, while the cathodic limit (~−2.8 V vs SHE) is governed by the Bu4N⁺/Et4N⁺ cation and is essentially salt-anion-independent.

## Details

### Master-scale conversions applied
- SCE → Ag/AgCl(sat'd KCl): **+0.045 V**; SHE → Ag/AgCl: **−0.197 V**; Fc/Fc⁺ → Ag/AgCl: **+0.445 V (MeCN only)**.
- Non-MeCN conversions are flagged "approx" (the Fc/SCE/SHE couples shift by up to several tenths of a volt across solvents). Project sourcing authority for MeCN conversions: Pavlishchuk & Addison, Inorg. Chim. Acta 2000 (S0020169399004077).

### Clean reference table (one row per solvent–electrolyte–electrode–source)

| solvent | supporting_electrolyte | electrolyte_conc | working_electrode | anodic_limit_reported | cathodic_limit_reported | window_V | current_cutoff_criterion | reference_electrode | anodic_vs_AgAgCl | cathodic_vs_AgAgCl | conversion_note | water/purity_note | primary_source(DOI) | confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Propylene carbonate (PC) | TBABF4 (BF4⁻) | 0.65 M | glassy carbon | +3.6 V vs SHE (anion-limited) | −2.8 V vs SHE (Bu4N⁺/Et4N⁺-limited) | ~6.4 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE (converted from SCE by compiler) | +3.40 | −3.00 | approx | not stated | Ue, Ida & Mori 1994 (10.1149/1.2059270) via Gong et al. 2015 (10.1039/C5EE02341F) | med |
| Propylene carbonate (PC) | TBAPF6 (PF6⁻) | 0.65 M | glassy carbon | +3.8 V vs SHE | −2.8 V vs SHE | ~6.6 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +3.60 | −3.00 | approx | not stated | Ue 1994 / Gong 2015 (10.1039/C5EE02341F) | med |
| Propylene carbonate (PC) | TBAClO4 (ClO4⁻) | 0.65 M | glassy carbon | +3.1 V vs SHE | −2.8 V vs SHE | ~5.9 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +2.90 | −3.00 | approx | not stated | Ue 1994 / Gong 2015 | med |
| Propylene carbonate (PC) | TBATFSI (TFSI⁻) | 0.65 M | glassy carbon | +3.3 V vs SHE | −2.8 V vs SHE | ~6.1 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +3.10 | −3.00 | approx | not stated | Ue 1994 / Gong 2015 | med |
| Acetonitrile (MeCN) | TBAPF6 | 0.1 M | Pt | +3.0 V vs SCE | −2.7 V vs SCE | 5.7 | qualitative ("flat current"); no current cutoff stated | SCE | +3.05 | −2.66 | exact (SCE) | dried, anhydrous | Elgrishi et al. 2018 (10.1021/acs.jchemed.7b00361) | med |
| Acetonitrile (MeCN) | Et4NBF4 | 0.65 M | glassy carbon | +3.5 V vs SHE | −2.6 V vs SHE | 6.1 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +3.30 | −2.80 | exact (SHE) | not stated | Ue 1994 / Gong 2015 | med |
| Nitromethane | Et4NBF4 | 0.65 M | glassy carbon | +2.9 V vs SHE | −1.0 V vs SHE | 3.9 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +2.70 | −1.20 | approx | not stated | Ue 1994 / Gong 2015 | med-high |
| Nitromethane | Mg(ClO4)2 (TBA salts give narrower window) | 0.1 M | Pt | +2.4 V vs NHE | −2.4 V vs NHE | 4.8 | 0.3 mA cm⁻² | NHE/SHE | +2.20 | −2.60 | approx | dry NM | Voorhies & Schurdak 1962 (10.1021/ac60188a019) | med |
| γ-Butyrolactone (GBL) | Et4NBF4 | 0.65 M | glassy carbon | +5.4 V vs SHE | −2.8 V vs SHE | 8.2 | 1 mA cm⁻², 5 mV s⁻¹, 25 °C | SHE | +5.20 | −3.00 | approx | not stated | Ue 1994 / Gong 2015 | low-med |
| Benzonitrile | TBAP (TBAClO4) | not stated | Pt | +1.8 V vs SCE | −1.95 V vs SCE | 3.75 | not stated | SCE | +1.85 | −1.91 | approx | purified | IUPAC Pure Appl. Chem. 1987, 59, 703 | med |
| DMF | TBAClO4 | 0.1 M | glassy carbon | not measured (anodic) | −2.85 V (cathodic breakdown) | n/a | steep breakdown | reference unclear | n/a | n/a | approx | water <0.02 wt% | J. Electroanal. Chem. (S0022072899004374) | low |
| DMF | TBAClO4 | 0.1 M | Pt | not measured (anodic) | −1.8 V (cathodic) | n/a | onset | reference unclear | n/a | n/a | approx | water <0.02 wt% | J. Electroanal. Chem. (S0022072899004374) | low |

### Notes on individual systems
- **PC priority pairs (all four salts):** Ue's data are anion/cation-decoupled — the anodic limit is set by the anion and the cathodic limit by the tetraalkylammonium cation (Bu4N⁺ ≈ −2.8 V vs SHE). This is the cleanest available primary source covering all four requested salts. The numerical anion-resolved oxidation values were extracted via Gong et al.'s faithful reproduction of Ue's table (Table 2: BF4⁻ 3.6, PF6⁻ 3.8, ClO4⁻ 3.1, TFSI⁻ 3.3 V vs SHE, Et4N⁺ cathodic −2.8 V); confidence is medium pending a direct read of the 1994 paper.
- **MeCN/TBAPF6:** Elgrishi's "Practical Beginner's Guide to Cyclic Voltammetry" gives −2.7 to +3.0 V vs SCE on Pt (5.7 V); authoritative as a teaching/handbook reference but with no explicit current cutoff, so it should be treated as an onset-style window, not a 1 mA cm⁻² window.
- **Nitromethane:** Two primary sources agree on a strong anodic limit but disagree on the cathodic limit (−1.0 V SHE on GC/Et4NBF4 [Ue] vs −2.4 V NHE on Pt/Mg(ClO4)2 [Voorhies & Schurdak]). The discrepancy reflects electrode, cation and criterion differences; Voorhies & Schurdak explicitly note the widest range was obtained with Mg(ClO4)2, with tetraalkylammonium salts giving a narrower window. The conservative gate for screening is the Ue cathodic value, −1.0 V vs SHE (≈ −1.2 V vs Ag/AgCl). The widely quoted "−1.95/+1.8 V vs SCE, Pt, TBAP" figure is for **benzonitrile, not nitromethane** — do not misapply it.
- **GBL:** Ue's +5.4 V vs SHE anodic figure is unusually high; treat cautiously (possible compilation artifact) — hence low-med confidence.

## Recommendations
1. **Apply a conservative gate** by using the converted Ag/AgCl values and subtracting an extra ~0.15 V from each anodic limit to absorb the liquid-junction/solvent floor; monomers whose Eox lands within ~0.2 V of a converted anodic gate should be flagged "edge" rather than "pass."
2. **For PC triads**, prefer PF6⁻ or BF4⁻ for maximum oxidative headroom (~+3.4 to +3.6 V vs Ag/AgCl); treat the cathodic gate (~−3.0 V vs Ag/AgCl) as cation-limited and salt-independent.
3. **For reductive monomers, exclude nitromethane** (cathodic gate only ≈ −1.2 V vs Ag/AgCl) and treat benzonitrile and DMF with caution on the cathodic side.
4. **Fill the gaps** (NMP, nitrobenzene, DMSO, THF, sulfolane) with dedicated blank-CV measurements on your actual working electrode before relying on them in the screen; do not substitute secondary tabulations.
5. **Harmonize criteria:** re-measure all thresholds at a fixed 1 mA cm⁻² cutoff on your working electrode to match the Ue dataset. **Benchmark that would change these recommendations:** if a direct read of Ue 1994 confirms a 0.1 mA cm⁻² (rather than 1 mA cm⁻²) cutoff, every Ue-derived limit narrows modestly and the gates should be tightened by ~0.1–0.2 V accordingly.

## Caveats
A solvent's "window" is not a property of the solvent alone: it is jointly set by the solvent, the supporting-electrolyte anion (anodic limit) and cation (cathodic limit), the working-electrode material, the current-density cutoff criterion, the scan rate and the water content. Reported limits scatter by several hundred millivolts for these reasons, and cross-source comparison is valid only when these conditions match — which is why MeCN appears here with two non-identical windows from two sources using different criteria. Two specific data-integrity flags remain: (1) the Ue cutoff criterion is reported as 1 mA cm⁻² in Gong et al. (the source actually read here) but as 0.1 mA cm⁻² in at least one other secondary citation of the same 1994 paper, so the primary should be checked directly; and (2) the PC/GBL/nitromethane vs-SHE limits are quoted via Gong et al.'s reproduction of Ue's table rather than from the paywalled 1994 original, hence medium confidence. Finally, all conversions to Ag/AgCl carry the project's 0.05–0.15 V systematic floor, and every non-acetonitrile conversion is additionally approximate because the SCE/SHE/Fc reference scales shift between solvents; record the original reference value alongside the converted value in the master dataset and never pool the two scales as identical.

### Excluded / ambiguous rows (listed separately, with reason)
- **Ionic-liquid and IL/organic-solvent mixed media** (e.g., Buzzeo et al., ChemPhysChem 2006, 10.1002/cphc.200500361; biredox IL in BMImTFSI): mixed/IL media — excluded per scope.
- **Ag-wire / Ag/Ag⁺ pseudo-reference rows without a ferrocene calibrant** (numerous patent-derived CV setups using "RE5 Ag/Ag⁺, BAS" with no Fc): not honestly convertible to Ag/AgCl — excluded.
- **Li/Li⁺-referenced battery-electrolyte windows in PC/LiPF6, LiClO4** (e.g., GC anodic instability 3.5–4.5 V vs Li/Li⁺): wrong reference framework and Li-salt (not tetraalkylammonium) — excluded.
- **Aqueous-acid and water-in-salt media** (KCl(aq), LiNO3/water, acetic-acid mixtures): aqueous — excluded.
- **BenchChem "Application Notes" MeCN/TBAPF6 table** (GC +2.5/−2.9; Pt +2.3/−2.7 vs Ag/Ag⁺): secondary vendor tabulation vs an uncalibrated Ag/Ag⁺ scale with no Fc calibrant — excluded from the clean table (listed here for awareness only).

### Priority pairs with NO clean primary data found
- **NMP + tetraalkylammonium:** only Li-air-battery CVs in TBAClO4/NMP referenced to Li/Li⁺ were found (reversible O2 couple ~2.4 V vs Li/Li⁺); no clean blank-solvent window vs a convertible reference. **Gap.**
- **Nitrobenzene + tetraalkylammonium:** found only analyte-reduction studies and an IL-medium study; no clean blank-window primary measurement with a tetraalkylammonium salt and convertible reference. **Gap.**
- **PC/TBATFSI, TBAClO4, TBABF4 specific blank-CV windows:** only the Ue anion/cation-decoupled compilation values are available (no single primary CV paper reporting all four PC salts directly); treat as medium confidence.
- **Sulfolane, DMSO, THF blank windows with tetraalkylammonium + convertible reference:** not cleanly sourced within budget (sulfolane data found only vs Li/Li⁺ for battery sulfones; DMSO/THF found only as analyte studies). **Gaps** for the broader-coverage tier.
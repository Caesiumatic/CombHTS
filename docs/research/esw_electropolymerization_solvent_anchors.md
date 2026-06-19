# Benchmark of Experimentally Measured Electrochemical Stability Windows (ESW) for 11 Electrochemistry Solvents

**DRAFT FOR HUMAN VETTING before entering a benchmark CSV.** This compilation prioritizes anodic-limit reliability on platinum (Pt) and glassy-carbon (GC) electrodes, because the validation target — "monomer oxidation potential must fall within the solvent's anodic limit" — depends almost entirely on getting the anodic edge right under realistic electropolymerization conditions (Pt/GC/ITO, tetraalkylammonium electrolytes), not on BDD or battery (Li/Li⁺) systems.

## TL;DR
- **For an electropolymerization screen run on Pt/GC/ITO, the single most defensible self-consistent anchor set is Ue's glassy-carbon dataset** (0.65 M Et₄NBF₄, GC, 25 °C, 5 mV/s, 1 mA cm⁻² cutoff), tabulated by Gong et al. 2015: anodic (limiting oxidation, V vs SHE) MeCN +3.5, PC +3.8, γ-butyrolactone +5.4, nitromethane +2.9; cathodic limits ≈ −2.6 to −2.8 V vs SHE. Convert to the Ag/AgCl scale by subtracting ≈0.197 V (or to SCE by subtracting 0.24 V, the exact constant Gong uses).
- **In nearly all aprotic non-aqueous media the *practical* anodic limit is set by the supporting-electrolyte anion (ClO₄⁻/BF₄⁻/PF₆⁻) or by trace water — not by the intact solvent.** MeCN in particular is so oxidation-resistant that the salt almost always breaks down first. Always report the electrolyte; an ESW with no stated electrolyte is near-meaningless.
- **Boron-doped diamond (BDD) gives anomalously wide windows** (water ≈ 3.5–4.3 V; non-aqueous 5–7.5 V) and **must not be used as the generic anchor.** Water must additionally be split by pH and electrode (GC/BDD wide, Pt narrow due to low H₂/O₂ overpotentials).

## Key Findings
1. **One internally consistent cross-solvent dataset exists and should be the backbone of the CSV.** Ue's glassy-carbon limiting oxidation/reduction potentials (measured with 0.65 M Et₄NBF₄, GC, 25 °C, 5 mV/s, 1 mA cm⁻² threshold) cover MeCN, PC, GBL, nitromethane, DMF, THF, DCM and NMP under *identical* conditions. They are reproduced (with the explicit conversion "SCE = 0.24 V vs SHE") in the open-access review Gong, Fang, Gu, Li, Yan, *Energy Environ. Sci.* 2015, 8, 3515 (DOI 10.1039/C5EE02341F), which cites Ue's original work as ref. 59.
2. **MeCN/TBAPF₆ on Pt** — the most common electropolymerization medium — is canonically quoted as **−2.7 to +3.0 V vs SCE** (Elgrishi et al., "A Practical Beginner's Guide to Cyclic Voltammetry," *J. Chem. Educ.* 2018, 95, 197, DOI 10.1021/acs.jchemed.7b00361). GC is marginally wider on the anodic side because of its higher solvent-oxidation overpotential.
3. **Water requires pH- and electrode-resolved values.** From Benck, Pinaud, Gorlin & Jaramillo, *PLoS ONE* 2014, 9(10):e107942 (DOI 10.1371/journal.pone.0107942), using a **50 µA cm⁻² (above baseline capacitance) cutoff** and a Ag/AgCl (4 M KCl) reference calibrated to RHE: GC inert window is **−0.42 to +1.76 V vs RHE in 0.1 M H₂SO₄ (pH 1.0)** and **−0.76 to +1.96 V vs RHE in 0.1 M NaAc (pH ~7)**; Au is much narrower (−0.10 to +1.33 V vs RHE at pH 1). (This paper does NOT report Pt or BDD.)
4. **Reference-electrode anchoring for conversions:** Fc/Fc⁺ ≈ +0.40 V vs SCE and ≈ +0.45–0.46 V vs Ag/AgCl *in MeCN*; this conversion carries ~0.1 V uncertainty and is strictly valid only in MeCN. SCE = +0.24 V vs SHE; Ag/AgCl(sat) ≈ +0.197 V vs SHE.

## Consolidated Table

Flags: **[CONV]** = cross-solvent / cross-reference conversion applied (carries ~0.1 V uncertainty); **[BDD]** = boron-doped diamond, anomalously wide, not representative; **[NoElec]** = supporting electrolyte not stated/uncertain; **[NoRef]** = reference electrode not stated/secondary; **[Li]** = value on Li/Li⁺ battery scale, not directly comparable.

| Solvent | Anodic limit (V, scale) | Cathodic limit (V, scale) | Reference electrode | Supporting electrolyte | Working electrode | Cutoff criterion | Window width (V) | εr (~25 °C) | Source |
|---|---|---|---|---|---|---|---|---|---|
| **Acetonitrile (MeCN)** — primary anchor | **+3.5 vs SHE** (≈ +3.30 vs Ag/AgCl; ≈ +3.26 vs SCE) **[CONV]** | **−2.6 vs SHE** (≈ −2.80 vs Ag/AgCl) **[CONV]** | reported vs SCE (SCE=0.24 vs SHE) | 0.65 M Et₄NBF₄ | GC | 1 mA cm⁻² | 6.1 | 37.5 | Gong 2015, DOI 10.1039/C5EE02341F (citing Ue, ref. 59) |
| **MeCN/TBAPF₆ (electropoly medium)** | **+3.0 vs SCE** | **−2.7 vs SCE** | SCE | 0.1 M TBAPF₆ | Pt | not stated **[NoElec-cutoff]** | 5.7 | 37.5 | Elgrishi 2018, DOI 10.1021/acs.jchemed.7b00361 |
| **Dichloromethane (DCM)** | ~+1.8 vs Ag/Ag⁺ (electrolyte/anion-limited) **[NoElec-cutoff]** | ~−1.7 vs Ag/Ag⁺ | Ag/Ag⁺ (0.01 M) | 0.1 M TBAPF₆ | GC | not stated | ~3.5 | 8.93 | Standard CV practice; Fc=0.40 V calib. (e.g. US Pat. 9,324,505) **[NoRef-secondary]** |
| **Propylene carbonate (PC)** | **+3.8 vs SHE** (≈ +3.60 vs Ag/AgCl) **[CONV]** | **−2.8 vs SHE** | reported vs SCE→SHE | 0.65 M Et₄NBF₄ | GC | 1 mA cm⁻² | 6.6 | 64.9 | Gong 2015, DOI 10.1039/C5EE02341F (citing Ue) |
| **PC (Pt oxidation onset)** | +2.1 vs Li/Li⁺ (onset; accelerates >+3.5) **[Li]** | — | Li/Li⁺ | (in-situ FTIR) | Pt (and GC) | CO₂/FTIR onset | — | 64.9 | Rasch et al., *J. Electroanal. Chem.* 1989, DOI 10.1016/0022-0728(89)80122-6 |
| **N,N-Dimethylformamide (DMF)** | ~+1.5 vs SCE | ~−2.0 vs SCE (DMF radical reducible to ≈ −2.8 vs SCE) | SCE | 0.1 M TBAPF₆ | GC | not stated **[NoElec-cutoff]** | ~3.5 | 36.7 | Community/literature consensus **[NoRef-secondary]**; Ue Ered/Eoxi not tabulated for DMF |
| **Dimethyl sulfoxide (DMSO)** | ~+1.5 vs SCE | ~−2.9 vs SCE | SCE | electrolyte not stated **[NoElec]** | (GC/Pt) | not stated | ~4.4 | 46.7 | Aurbach (ed.), *Nonaqueous Electrochemistry*, Marcel Dekker 1999, ISBN 0-8247-7334-7 |
| **Tetrahydrofuran (THF)** | >+4 vs Li/Li⁺ (anodic; electrolyte/anion-limited) **[Li]** | not reduced even at −2 vs Li/Li⁺ **[Li]** | Li/Li⁺ | none (ultramicroelectrode) | UME | onset | small (electrolyte-limited) | 7.58 | Mann/Fleischmann-type study, *J. Electroanal. Chem.* 1990, DOI 10.1016/0022-0728(90)87072-R |
| **THF/TBAPF₆ (practical CV)** | ~+1.7 vs Fc (narrow; Fc couple sits near edge) **[NoElec-cutoff]** | ~−3.0 vs Fc | Fc/Fc⁺ or Ag/AgNO₃ | 0.1 M TBAPF₆ (or TBABPh₄) | GC | not stated | ~3–4 | 7.58 | f-element CV guide, DOI 10.1021/acs.inorgchem.5c05041 |
| **Water, pH 1 (GC)** | **+1.76 vs RHE** | **−0.42 vs RHE** | Ag/AgCl(4 M KCl)→RHE | 0.1 M H₂SO₄ | GC | 50 µA cm⁻² above baseline | 2.18 | 80.1 | Benck/Jaramillo 2014, DOI 10.1371/journal.pone.0107942 |
| **Water, pH 7 (GC)** | **+1.96 vs RHE** | **−0.76 vs RHE** | Ag/AgCl→RHE | 0.1 M NaAc | GC | 50 µA cm⁻² | 2.72 | 80.1 | Benck/Jaramillo 2014 |
| **Water, pH 1 (Au)** | +1.33 vs RHE | −0.10 vs RHE | Ag/AgCl→RHE | 0.1 M H₂SO₄ | Au | 50 µA cm⁻² | 1.43 | 80.1 | Benck/Jaramillo 2014 |
| **Water (thermodynamic)** | +1.23 vs SHE (pH 0) / +0.82 (pH 7) | 0.00 vs SHE (pH 0) / −0.41 (pH 7) | SHE | — | — | reversible (Nernst) | 1.23 | 80.1 | Standard; Gong 2015 restates |
| **Water (BDD) [BDD] — not generic** | +2.3 vs SHE | −1.25 vs SHE | SHE | 0.5 M H₂SO₄ | BDD | not stated | 3.55 | 80.1 | Martin et al., *J. Electrochem. Soc.* 1996, DOI 10.1149/1.1836901 |
| **Nitromethane (MeNO₂)** | **+2.9 vs SHE** (≈ +2.70 vs Ag/AgCl) **[CONV]** | **−1.0 vs SHE** (≈ −1.2 vs Ag/AgCl) **[CONV]** | reported vs SCE→SHE | 0.65 M Et₄NBF₄ | GC | 1 mA cm⁻² | 3.9 | 35.9 | Gong 2015 (citing Ue) |
| **γ-Butyrolactone (GBL)** | **+5.4 vs SHE** (≈ +5.20 vs Ag/AgCl) **[CONV]** | **−2.8 vs SHE** | reported vs SCE→SHE | 0.65 M Et₄NBF₄ | GC | 1 mA cm⁻² | 8.2 | 39.1 | Gong 2015 (citing Ue) |
| **Sulfolane** | ~+5 vs Li/Li⁺ (battery; >4.7 cathode use) **[Li] [NoElec]** | — (anodic-favoured solvent) | Li/Li⁺ | 1 M LiFSI / LiPF₆ | (varies) | not stated | "wide" (~5–6) | 43.3 | Battery literature (e.g. DOI 10.1002/batt.202200565) — re-vet |
| **N-Methyl-2-pyrrolidone (NMP)** | Ue Eoxi not listed (FLAG incomplete) | Ered ~ −? | reported vs SCE→SHE | 0.65 M Et₄NBF₄ | GC | 1 mA cm⁻² | — | 32.2 | Gong 2015 Table 1 (NMP row partly blank) — re-vet **[NoElec-complete]** |

### Dielectric constant cross-check (εr, ~25 °C)
The directive's library values agree well with authoritative references (Gong 2015 Table 1 / CRC Handbook / Izutsu): MeCN 37.5 (Gong 35.9–36.6), DCM 8.9 (Gong 8.93), PC 64.9 (✓), DMF 36.7 (✓), DMSO 46.7 (✓), THF 7.6 (Gong 7.58), nitromethane 35.9 (Gong 36.7), water 80.1 (✓), GBL 39.0 (Gong 39.1), sulfolane 43.3 (✓), NMP 32.0 (Gong 32.2). The only notable spreads are MeCN (35.9–37.5 across sources) and nitromethane (35.9–36.7); both are within normal literature scatter and do not affect the screen.

## Details — per-solvent commentary (electrode/reference effects and the recommended anchor)

**Acetonitrile.** The keystone solvent for the screen. MeCN is one of the most oxidation-resistant common solvents, so on Pt or GC the *anodic* edge is almost always set by the electrolyte anion (PF₆⁻ > BF₄⁻ > ClO₄⁻ in oxidative robustness), not by MeCN. Pt tends to give a slightly *narrower* anodic range than GC because Pt catalyzes side reactions at extremes. **Recommended anchor:** for the generic library value use Ue's GC number (+3.5 V vs SHE → **+3.30 V vs Ag/AgCl**); for the literal electropolymerization medium (0.1 M TBAPF₆, Pt) use **+3.0 V vs SCE** (Elgrishi 2018). Both agree to ~0.2–0.3 V, comfortably inside the 0.3 V MAE target. Convert monomer oxidation potentials onto whichever scale the CSV adopts using Fc/Fc⁺ = +0.40 V vs SCE / +0.45 V vs Ag/AgCl (MeCN only, ~0.1 V uncertainty).

**Dichloromethane.** Low dielectric (8.93) means high iR drop and an *electrolyte-limited* window; rigorous drying is essential (a spurious reduction peak near −0.8 V appears with trace water). DCM is excellent for *oxidations* (resists anodic decomposition; common with 0.1 M TBAPF₆ on GC/Pt, Fc calibrated to ≈+0.40 V) but poor for reductions. Treat the listed limits as electrolyte-set, not intrinsic, and flag.

**Propylene carbonate.** Two regimes: (i) Ue's GC anodic limit +3.8 V vs SHE (electrolyte-limited, the value to put in the CSV); (ii) the intrinsic *solvent* oxidation onset, which the in-situ FTIR study pins precisely: "At a polished Pt electrode held at +2.0 V (vs. Li/Li⁺), PC is stable but above +2.1 V oxidation of PC begins; this oxidation accelerates significantly above about +3.5 V (vs. Li/Li⁺)... On a bare glassy-carbon electrode, the oxidation of PC proceeds at a rate comparable to that on PPy" (DOI 10.1016/0022-0728(89)80122-6). So the *intrinsic* PC limit is lower than the electrolyte-limited CV limit — important to note which one the screen means. **Recommended anchor:** Ue GC +3.8 V vs SHE (≈+3.60 V vs Ag/AgCl) for the electrolyte-limited practical window.

**DMF.** DMF oxidizes around +1.5 V vs SCE on GC; the cathodic side is complicated because DMF acts as an H-atom donor and the resulting radical is reducible to ≈ −2.8 V vs SCE while the practical clean limit is ~ −2.0 V vs SCE. Sourcing here is community/secondary — flag and re-vet against Izutsu or Aurbach for a primary electrolyte-specified value.

**DMSO.** Broad cathodic range but a relatively *low anodic limit* (~+1.5 V vs SCE) — DMSO itself oxidizes fairly readily, which is the binding constraint for electropolymerizing higher-oxidation-potential monomers. The widely cited −2.9 to +1.5 V vs SCE figure traces to Aurbach, *Nonaqueous Electrochemistry* (Marcel Dekker, 1999), but the *specific* supporting electrolyte/electrode in that table is not stated — flag. For the screen, DMSO's anodic ceiling (~+1.5 V vs SCE ≈ +1.7 V vs Ag/AgCl) is the number that will most often *exclude* monomers, so it should be re-vetted with a primary CV source (e.g., 0.1 M TBAP on GC/Pt) before entering the CSV.

**THF.** Very low dielectric (7.58); without deliberate electrolyte THF "breaks down anodically at >+4 V vs Li/Li⁺ but is not reduced even at −2 V vs Li/Li⁺" (DOI 10.1016/0022-0728(90)87072-R) — i.e., a wide *intrinsic* window but a narrow *practical* one because the electrolyte (often TBABPh₄ or TBAPF₆) and iR drop dominate. With TBABPh₄ the window is so tight the ferrocene couple sits on its edge. Requires careful drying. Use as an oxidation solvent only with caution.

**Water.** The only solvent that *must* be entered as multiple rows. Thermodynamic window is 1.23 V (pH 0). Real inert windows are much wider on high-overpotential electrodes: GC −0.42→+1.76 V vs RHE (pH 1) and −0.76→+1.96 V vs RHE (pH 7); Au is far narrower (low overpotentials). The Benck/Jaramillo study used a strict 50 µA cm⁻² cutoff — a tighter criterion than the 1 mA cm⁻² used for the non-aqueous data, so widths are not directly comparable across the two datasets. **BDD is anomalous** (−1.25→+2.3 V vs SHE in 0.5 M H₂SO₄, ≈3.55 V; some films reach ≈4.25 V) and is flagged out-of-scope. For an aqueous electropolymerization (e.g., pyrrole/EDOT, which polymerize in water on Pt/ITO), the GC/Pt acidic-pH anodic limit (~+1.5–1.8 V vs RHE) is the relevant ceiling.

**Nitromethane.** Ue GC: +2.9/−1.0 V vs SHE (ECW 3.9 V). Lower anodic ceiling than MeCN, so fewer monomers fit. Anchor on the GC value; convert to ≈+2.70 V vs Ag/AgCl.

**γ-Butyrolactone.** Exceptionally wide on GC (+5.4/−2.8 V vs SHE, ECW 8.2 V — among the widest of any common solvent), again electrolyte-limited in practice. Excellent anodic headroom for electropolymerization. Anchor on Ue GC value.

**Sulfolane.** Anodically very robust (the reason it is a high-voltage battery solvent, stable to >4.7 V vs Li/Li⁺ ≈ >+1.9 V vs SHE region depending on salt), but almost all quantitative data are on the Li/Li⁺ scale with Li salts — not directly transferable to a Pt/GC/TBAPF₆ electropolymerization context. **Re-vet**: find a GC/Pt + tetraalkylammonium value before entering the CSV.

**NMP.** Listed in Ue/Gong Table 1 but the oxidation-limit cell is effectively blank/incomplete in the reproduced table, so no reliable anodic anchor was recovered. **Re-vet** against Izutsu or a primary CV paper (NMP is moderately oxidizable, comparable to DMF/DMAc).

## Recommendations (staged, with thresholds that would change them)
1. **Adopt the Ue glassy-carbon dataset as the primary CSV anchor** for MeCN, PC, GBL, nitromethane (and, once re-vetted, DMF/THF/DCM/NMP), converting SHE→Ag/AgCl by −0.197 V (or →SCE by −0.24 V, the constant Gong states). This single source minimizes cross-dataset scatter and keeps you under the 0.3 V MAE target. *Change trigger:* if the screen's working electrode is fixed as Pt (not GC), shift anodic anchors ~0.2–0.3 V negative for solvents where Pt oxidizes the solvent earlier.
2. **For the literal MeCN/TBAPF₆ medium, use +3.0 V vs SCE (Pt, Elgrishi 2018)** as the anodic gate and explicitly model the electrolyte-anion limitation: if the candidate electrolyte is TBAClO₄ rather than TBAPF₆, lower the effective anodic gate by ~0.2–0.3 V.
3. **Enter water as ≥3 rows (pH 1 GC, pH 7 GC, pH 1 Au), all vs RHE, 50 µA cm⁻² cutoff.** Exclude BDD from the generic field (keep only as a flagged comparison row). *Change trigger:* if aqueous electropolymerization on Pt is intended, source a Pt-specific pH-resolved window (Pt has lower O₂/H₂ overpotentials → ~0.3–0.5 V narrower than GC).
4. **Re-vet DMSO, sulfolane, and NMP with primary CV sources** (Izutsu, *Electrochemistry in Nonaqueous Solutions*; Aurbach, *Nonaqueous Electrochemistry*) before finalizing — these three have the thinnest electrolyte-specified sourcing and DMSO's low anodic ceiling materially affects monomer inclusion.
5. **Standardize one reference scale for the whole CSV** (recommend Ag/AgCl, since most electropolymerization papers report against it or against Fc) and record both the original value+reference and the converted value, flagging every conversion.

## Caveats
- **Electrolyte-ion vs solvent limit:** For MeCN, PC, GBL, DCM, THF and sulfolane the reported anodic edge is in practice set by the anion (or trace water), not the intact solvent. The CSV should carry a boolean "limit set by electrolyte?" field; for electropolymerization the electrolyte-limited number is usually the operationally correct one, but it shifts with the chosen salt.
- **Cutoff-criterion mismatch:** Non-aqueous anchors use 1 mA cm⁻² (Ue); the aqueous anchors use 50 µA cm⁻² (Benck/Jaramillo). Tighter cutoffs give narrower windows; widths are therefore not directly comparable between the aqueous and non-aqueous blocks (can differ ~0.1–0.3 V at the edge).
- **Cross-solvent / cross-reference conversions** (all rows flagged [CONV]) carry ~0.1 V uncertainty; the Fc/Fc⁺→Ag/AgCl = +0.45 V relation is valid only in MeCN and should not be applied silently in other solvents.
- **Li/Li⁺-scale values** (PC-Pt, THF, sulfolane rows) are from battery studies and are NOT directly comparable to Pt/GC tetraalkylammonium CV; they are included only to bound intrinsic solvent stability and are flagged [Li].
- **Unverified/incomplete sources** are flagged: DMF and DCM rows rest on community/secondary consensus; NMP's Ue oxidation cell is blank; sulfolane lacks a tetraalkylammonium GC/Pt value. Do not enter these as final without primary-source confirmation.
- **Some widely circulated "tables" (e.g., AI-generated vendor PDFs quoting MeCN GC +2.5/−2.9 V vs Ag/Ag⁺) were deliberately excluded** as non-authoritative; they were not used as sources here.
- No DOIs were fabricated; where a precise locator could not be pinned (DMF/DCM consensus values, sulfolane window) this is stated explicitly rather than cited.
---

## Curation log — rows entered into `data/solvent_benchmark.csv` (2026-06-19)

This doc is the doc-of-record for the solvent-ESW benchmark seeding (directive §7). Six rows were
curated onto the Ag/AgCl scale; conversions applied consistently (SHE→Ag/AgCl = −0.197 V; SCE→Ag/AgCl
= +0.044 V), with the native value + reference recorded in each row's `source` field.

| solvent | anodic V (Ag/AgCl) | cathodic V (Ag/AgCl) | electrode / electrolyte | tier | limit_set_by_electrolyte | native (source) |
|---|---|---|---|---|---|---|
| acetonitrile | +3.30 | −2.80 | GC / 0.65 M Et₄NBF₄ | B-crossref | TRUE | +3.5/−2.6 vs SHE (Ue/Gong) |
| propylene carbonate | +3.60 | −3.00 | GC / 0.65 M Et₄NBF₄ | B-crossref | TRUE | +3.8/−2.8 vs SHE (Ue/Gong) |
| GBL | +5.20 | −3.00 | GC / 0.65 M Et₄NBF₄ | B-crossref | TRUE | +5.4/−2.8 vs SHE (Ue/Gong) |
| nitromethane | +2.70 | −1.20 | GC / 0.65 M Et₄NBF₄ | B-crossref | FALSE | +2.9/−1.0 vs SHE (Ue/Gong) |
| benzonitrile | +1.844 | −1.906 | Pt / 0.1 M TBAP | A | FALSE | +1.8/−1.95 vs SCE (IUPAC PAC 1987, 59, 703) |
| nitrobenzene | +1.844 | −1.006 | Pt / 0.1 M TEABF₄/TBAP-type | B-approx | FALSE | +1.8(mid)/−1.05 vs SCE (windows doc) |

**`limit_set_by_electrolyte` flag (appended boolean column; the validation reader tolerates extra
trailing columns).** TRUE where the research docs say the anodic edge is electrolyte/anion-set rather
than intrinsic to the solvent — MeCN, PC, GBL (the Ue/Gong GC limiting-oxidation values are anion-set
in practice). FALSE for benzonitrile, nitrobenzene, nitromethane, where the entered anodic edge is the
solvent's own oxidation onset/window.

**DEFERRED — deliberately NOT entered as rows** (thin or under-conditioned sourcing per the research
docs; entering them would inject systematic error):
- **DMSO** — anodic ceiling (~+1.5 V vs SCE) traces to Aurbach *Nonaqueous Electrochemistry* with the
  specific electrolyte/electrode unstated; re-vet with a primary CV source (e.g. 0.1 M TBAP on GC/Pt).
- **Sulfolane** — quantitative windows are on the Li/Li⁺ battery scale with Li salts; no GC/Pt
  tetraalkylammonium value located.
- **NMP** — the Ue/Gong oxidation-limit cell is effectively blank/incomplete; no reliable anodic anchor.
- **Water** — needs pH- and electrode-resolved RHE handling (≥3 rows: pH 1 GC, pH 7 GC, pH 1 Au), not a
  single Ag/AgCl value; out of scope for the single-value schema.

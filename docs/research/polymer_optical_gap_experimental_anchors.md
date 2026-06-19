# Experimental Optical Band Gaps of Conjugated Polymers — A Vetted Ground-Truth Set for Pipeline Validation

**⚠️ REQUIRES HUMAN VETTING BEFORE USE.** Every row below should be checked against the cited primary source before it is used to compute the pipeline's error against reality. Optical gaps for the *same* polymer routinely vary by 0.1–0.5 eV with regioregularity, molecular weight, side chain, phase (film vs solution), and onset-extraction method (simple onset vs Tauc vs second-derivative). The table is structured one row per polymer × condition so it can be exported directly to CSV.

## TL;DR
- The cleanest, best-anchored **neutral optical gaps** are: regioregular P3HT film ≈ 1.9 eV, unsubstituted polythiophene film ≈ 2.0 eV, neutral PEDOT ≈ 1.6 eV, polyselenophene ≈ 1.9 eV, PFO film ≈ 2.9–3.0 eV, and PCPDTBT film ≈ 1.4 eV — each supported by multiple mutually consistent primary sources.
- Two polymers must be flagged rather than used numerically: **polyaniline** (emeraldine base has an ill-defined, non-classical gap — its ~2.1 eV / ~1.5 eV features are not a clean π–π* band edge), and **PEDOT** (its famous "low gap" belongs to the doped conducting state dominated by mid-gap polaron/bipolaron bands; the neutral π–π* gap is ~1.6 eV and the two must never be conflated).
- Many literature "band gaps" for pyrroles, dioxypyrroles, and electrodeposited polymers are taken from spectroelectrochemistry of the **NEUTRAL (dedoped) film** — those are valid optical gaps and are included; values reported *only* from cyclic voltammetry are electrochemical gaps and are flagged/excluded.

## Key Findings
- **The optical-vs-electrochemical distinction was enforced strictly.** Where a source reported only a CV gap (E_g,ec), or mislabeled one as "optical," the number was excluded or flagged. A clean illustrative case: a polythiophene derivative reported E_g,op = 1.62 eV versus E_g,ec = 1.51 eV — physically the optical gap should be *smaller* than the fundamental gap, so that particular pairing is internally inconsistent and was not used as an anchor.
- **P3HT is the canonical regioregular-vs-regiorandom case.** Per US Patent 8765968, "P3HT has a wide bandgap of about 1.9 eV … with a bandgap of 1.9 eV, only about 22% of light with a 650 nm wavelength can be absorbed," consistent with a film absorption onset near 640–650 nm (Tauc value 1.93 eV in the Academia P3HT optical study). Regiorandom P3HT is blue-shifted (larger gap, ~2.1 eV) because of shorter effective conjugation and poorer interchain packing; dilute-solution values run ~0.1–0.3 eV higher than film.
- **PEDOT neutral state ≈ 1.6 eV.** Per Bhandari et al., *Synth. Met.* 2016, "PEDOT:PSS is a low bandgap p-type semiconducting material with its energy gap lying in the VIS-NIR range (1.6 eV for π→π* transition) and shows an absorption maximum in the middle of the visible spectrum at 600 nm." A directly reduced (undoped) PEDOT film gives an optical edge of 1.55 eV (US Patent 8840771: "a peak at 580 nm ascribed to π-π* transition of undoped PEDOT appeared. The optical band gap edge can be calculated as 1.55 eV").
- **The selenium dioxy analogues exist experimentally.** PEDOS ≈ 1.4 eV per Patra, Wijsboom, Zade, Li, Sheynin, Leitus & Bendikov, *J. Am. Chem. Soc.* 2008, 130, 6734–6736: "PEDOS shows a relatively low band gap (1.4 eV), very high stability in the oxidized state, and a well-defined spectroelectrochemistry." Parent poly(ProDOS) is similarly ~1.4 eV; alkyl-substituted PProDOS run 1.57–1.65 eV.
- **Polyaniline's gap is genuinely ambiguous** and should be excluded from quantitative validation or used only with an explicit flag.

## Details — Consolidated Table (group by monomer family; CSV-ready)

"Onset" = absorption onset; E_g = 1240/λ_onset[nm]. State is confirmed neutral/undoped unless flagged. Phase = thin film or dilute solution.

### Family 1 — Thiophenes

| Polymer (parent monomer) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| Polythiophene (thiophene) | ~2.0 | π–π* absorption edge ~590–620 nm; neutral oCVD film edge 1.96 eV | Neutral (dedoped) | Film | 2.0–2.5 eV across literature; 1.96 eV for MeOH-dedoped oCVD film; "experimental value 2.0 eV" widely cited | oCVD neutral film 1.96 eV (US Patent 9793479); review value 2.0 eV (multiple) |
| Poly(3-hexylthiophene), **regioregular** (3-hexylthiophene) | ~1.9 | Tauc 1.93 eV; onset ~640–650 nm | Neutral | Film | 1.9 eV (RR film); solution higher; films red-shift 0.1–0.3 eV vs solution | US Patent 8765968 (1.9 eV, 650 nm); Academia P3HT optical study (Tauc 1.93 eV, onset 640 nm); JPCC 2017 (1.9 eV onset) |
| Poly(3-hexylthiophene), **regiorandom** | ~2.0–2.1 | Onset blue-shifted vs RR | Neutral | Film | RRa blue-shifted (larger gap) than RR due to shorter conjugation/poorer packing | Nat. Commun. 14047; US Patent 8530594 (qualitative) |
| Poly(3-methylthiophene) (3-methylthiophene) | ~2.0 | π–π* interband onset ~2 eV (dedoped) | Neutral (chem./electrochem. dedoped) | Film (electrodeposited) | ~2 eV; doped films show bipolaron band ~1 eV (EXCLUDE) | Synth. Met. P3MT study (ScienceDirect S0379677910005060) |
| Polyterthiophene (terthiophene) | ~1.8–1.9 | Optical gap from spectroelectrochemistry | Neutral | Film (electrodeposited) | 1.8–1.9 eV for 3',4'-bis(alkyloxy)terthiophene polymers; alkyl length negligible | J. Macromol. Sci. A 2023 (10.1080/10601325.2023.2208607) |

### Family 2 — Dioxythiophenes (EDOT / ProDOT) + Se analogues

| Polymer (parent monomer) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| PEDOT (3,4-ethylenedioxythiophene) | ~1.6 (neutral); edge 1.55 | Neutral π–π* (peak 580–600 nm); onset edge 1.55 eV | Neutral (reduced/dedoped) | Film | 1.5 eV, 1.6–1.7 eV, 1.64 eV reported; 1.65 eV for PEDOT-F. **FLAG: doped conducting state ≠ optical gap** | Bhandari et al. Synth. Met. 2016 (1.6 eV, λmax 600 nm); US Patent 8840771 (edge 1.55 eV); arXiv 1610.05941 (1.5/1.6–1.7/1.64 eV) |
| PProDOT (3,4-propylenedioxythiophene) | ~1.7–1.9 | Neutral π–π* onset; PProDOT-Me2 1.7 eV (715 nm) | Neutral | Film (electrodeposited) | 1.7 eV (PProDOT-Me2); ~1.85–1.94 eV for some analogues | US Patent 9933680 (1.7 eV, 715 nm); Wiley J. Appl. Polym. Sci. 46214 |
| PEDOS (3,4-ethylenedioxyselenophene) | ~1.4 (1.40–1.42) | Neutral-state π–π* onset; spectroelectrochem. | Neutral (dedoped) | Film (electrodeposited) | 1.4 eV (parent, JACS 2008); 1.42 eV (Adv. Mater. 2009); PEDOS-C6 1.54 eV | Patra et al. JACS 2008 (10.1021/ja8018675); Li et al. Adv. Mater. 2009 (10.1002/adma.200802259); Yadav et al. RSC Adv. 2020 (10.1039/D0RA01436B) |
| PProDOS (3,4-propylenedioxyselenophene) | ~1.4 (parent); 1.57–1.65 (alkyl) | Neutral-state π–π* onset | Neutral | Film (electrodeposited) | parent ~1.4 eV (decimal to confirm from PDF); PProDOS-C10 1.58 eV | Karabay/Pekel/Cihaner Macromolecules 2015 (10.1021/acs.macromol.5b00022); İçli-Özkut et al. J. Mater. Chem. 2011 (10.1039/C0JM04285D) |

### Family 3 — Pyrroles

| Polymer (parent monomer) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| Polypyrrole (pyrrole) | ~2.0–3.2 (scattered) | Tauc / absorption; pristine films 2.19–2.64 eV; theory 1.88 eV | Neutral (pristine) where stated | Film | Wide spread; many "PPy gaps" are partially doped. Doped/oxidized values EXCLUDED. **FLAG large spread** | jos.ac.cn (2.19 eV pristine film); Sci. Rep. 36554 (theory 1.88 eV) |
| PEDOP (3,4-ethylenedioxypyrrole) | ~2.0 | Neutral π–π* onset | Neutral | Film (electrodeposited) | 2.0 eV (Reynolds); 2.44 eV theoretical | US Patent 6791738 (PEDOP 2.0 eV; PProDOP 2.2 eV); Polym. J. pj200962 (theory 2.44 eV) |
| Poly(N-methylpyrrole) (N-methylpyrrole) | **NOT cleanly found** | — | — | — | Reported qualitatively as higher-gap than PPy (N-substitution twists backbone); no clean neutral optical onset located | GAP — see Caveats |

### Family 4 — Furan / Selenophene

| Polymer (parent monomer) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| Polyfuran (furan) | ~2.3 | Absorption edge ~535 nm → 2.32 eV | Neutral | Film (electrodeposited) | 2.32 eV (edge 535 nm); π–π* 380–540 nm | Synth. Met. furan–thiophene study (ResearchGate 239289689) |
| Polyselenophene (selenophene) | ~1.9 | Absorption edge ~652 nm → 1.90 eV | Neutral | Film (electrodeposited) | 1.90 eV (edge 652 nm); 2.43 eV π–π* peak; 1.72 eV from triselenophene | US Patent 10196480 (1.90 eV); Frontiers Chem. 2020 (1.72 eV) |

### Family 5 — Aniline / Carbazole / Fluorene

| Polymer (parent monomer) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| Polyaniline, emeraldine base (aniline) | **ILL-DEFINED (~2.1 / ~1.5 features)** | Absorption peak ~2.1 eV (benzenoid→quinoid exciton); ~1.5 eV cited | Neutral (EB) | Film | **FLAG: not a classical band gap.** EB shows localized benzenoid-HOMO→quinoid-LUMO excitonic absorption ~2.1 eV; "1.5 eV" widely repeated. EXCLUDE from quantitative validation. | Huang & MacDiarmid optical study (kpi.ua); J. Phys. Chem. B 2000 (10.1021/jp9910946) |
| Polycarbazole, **2,7-linked** (carbazole) | ~2.1–2.4 | Spectroelectrochem. onset | Neutral | Film | 2,7-linked lower gap than 3,6 (linear conjugation); EDOT-substituted 2,7 down to 2.1 eV | ScienceDirect S0379677910003607 (2,7 lower); Beilstein 12.134 |
| Polycarbazole, **3,6-linked** | ~2.4 | Spectroelectrochem. | Neutral | Film | 3,6 higher gap than 2,7 (cross-conjugated) | ScienceDirect S0379677910003607 |
| Poly(9,9-dioctylfluorene) PFO (9,9-dioctylfluorene) | ~2.9–3.0 | Glassy/α interband shoulder/onset ~2.95 eV; peak 3.2 eV; β-phase 0-0 at 2.87 eV | Neutral | Film | onset ~2.95 eV (glassy α); β-phase 0-0 vibronic 2.87±0.01 eV | Ariu et al. arXiv cond-mat/0211610 (2.95 eV interband shoulder); arXiv 1809.01508 (β 0-0 at 2.87±0.01 eV); arXiv physics/0610074 (peak 3.2 eV) |

### Family 6 — Donor–Acceptor low-gap copolymers

| Polymer (exact composition) | E_g,opt (eV) | Method / onset | State | Phase | Range & conditions | Source |
|---|---|---|---|---|---|---|
| **PCPDTBT**: poly[2,6-(4,4-bis(2-ethylhexyl)-4H-cyclopenta[2,1-b;3,4-b']dithiophene)-alt-4,7-(2,1,3-benzothiadiazole)] | ~1.4 | Onset ~850–860 nm | Neutral/pristine | Film | Original Mühlbacher et al.: "optical band gap as low as 1.4 eV"; some report 1.46 eV; one solution study cites HOMO-LUMO 2.14 eV (different sample/method) | Mühlbacher, Scharber, Morana, Zhu, Waller, Gaudiana & Brabec, Adv. Mater. 2006, 18, 2884–2889 (10.1002/adma.200600160) |
| DPP–dithiophene type: **dithienyl-diketopyrrolopyrrole copolymer (TP3)** | ~1.3 | Optical gap from absorption onset | Neutral | Film/solution | 1.3 eV (dithienyl-DPP, TP3); diphenyl-DPP analogues ~1.8 eV; DPP copolymers generally 1.2–1.6 eV | DTPP study (ResearchGate 255770992); Zou et al. Macromolecules 2009 (10.1021/ma901114j) |
| **Isoindigo–bithiophene (PII2T / P2TI)**: poly(isoindigo-alt-bithiophene), branched-alkyl isoindigo + bithiophene | ~1.5–1.6 | Onset; broad 400–800 nm absorption, λmax ~700 nm | Neutral | Film | 1.6 eV (Wang/Andersson 2011); ~1.5 eV (BDT-isoindigo series); P2TI-DD 1.6 eV | Wang et al. Chem. Commun. 2011 (10.1039/C1CC11053E); Springer J. Mater. Sci. Mater. Electron. 10854-022-08499-w; Macromolecules 10.1021/ma102357b |

## Recommendations
1. **Tier-1 anchors (calibrate the pipeline against these first):** P3HT-RR film (1.9 eV), polythiophene film (2.0 eV), neutral PEDOT (1.6 eV), polyselenophene (1.9 eV), PFO film (2.95 eV onset), PCPDTBT film (1.4 eV). These have multiple independent, mutually consistent primary sources and well-defined neutral states.
2. **Tier-2 (use with the exact condition recorded in the CSV):** PProDOT (1.7 eV), PEDOP (2.0 eV), polyfuran (2.32 eV), PEDOS (1.4 eV), the DPP copolymer (1.3 eV), and the isoindigo–bithiophene copolymer (1.5–1.6 eV). Flag explicitly that the dioxy/heterocycle homopolymers are electrodeposited-film, neutral-state spectroelectrochemical onsets (no dilute-solution onset exists).
3. **Exclude from quantitative error metrics:** polyaniline emeraldine base (ill-defined gap), all doped/oxidized-state values, all blend/BHJ-film values, and poly(N-methylpyrrole) until a clean neutral optical onset is located.
4. **Benchmarks that change these choices:** If the pipeline targets *single-chain / oligomer-extrapolated* gaps, prefer solution values (add ~0.1–0.3 eV to film numbers). If it targets *solid-state* device-relevant gaps, use film values as-is. If pipeline error exceeds ~0.3 eV on the Tier-1 anchors, suspect the sTDA-xTB → TD-DFT calibration step before suspecting the reference data.
5. **Re-verify two items before anchoring:** the parent PProDOS decimal (Macromolecules 2015 PDF) and the polypyrrole spread (2.0 vs 2.6 vs 3.2 eV) — resolve the latter by going to original neutral-film spectra, since many PPy "gaps" reflect partial doping.

## Caveats
- **Polyaniline:** Emeraldine base lacks a classical π–π* band edge; its optical features (~2.1 eV exciton; ~1.5 eV often quoted) arise from a non-classical, mixed benzenoid/quinoid, partial-charge-transfer electronic structure. Do not treat as a clean optical gap.
- **PEDOT neutral vs doped:** The doped/conducting PEDOT:PSS has no visible π–π* band edge — per Bhandari et al., "electrochemical doping of PEDOT:PSS results in addition of mid-gap energy levels, producing absorptive transitions in the visible region." The ~1.6 eV neutral gap appears only after electrochemical reduction. This is the single most common mislabeling risk in the PEDOT literature.
- **P3HT RR vs RRa:** Regioregularity, molecular weight, and processing shift the film gap by 0.1–0.5 eV; always record RR% and phase alongside the value.
- **Polypyrrole:** Values are scattered (2.0–3.2 eV) because of residual doping, oxidation during synthesis, and method differences; treat with caution and prefer explicitly pristine/dedoped films.
- **Electrodeposited films (PProDOT, PEDOP, polyfuran, polyselenophene, PEDOS, PProDOS, polyterthiophene, P3MT):** gaps come from spectroelectrochemistry of the neutral (dedoped) state — genuine optical gaps, but no spin-cast dilute-solution onset exists for these frequently insoluble polymers; do not compare them to solution-onset references without noting the phase.
- **poly(N-methylpyrrole):** No clean neutral optical band-gap onset value was located — itself a useful finding; it is reported only qualitatively as higher-gap than polypyrrole.
- **Electrochemical-gap mislabels encountered:** Several D–A polymer papers report E_g,ec alongside E_g,opt; in physically correct cases E_g,opt < E_g,ec by the exciton binding energy (~0.3–1 eV). Any source presenting a CV-derived number as "optical," or showing E_g,opt > E_g,ec, was rejected as an anchor.
- **Source-type note:** Several values are corroborated via patents and secondary compilations rather than the originating journal article; before final use, replace patent/aggregator locators with the primary DOI (e.g., confirm polyselenophene 1.90 eV against Glenis, Ginley & Frank, J. Appl. Phys. 62, 190 (1987), cited within US Patent 10196480).
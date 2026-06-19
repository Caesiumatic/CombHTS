# Experimental Oxidation Potentials (Eox) of Electropolymerizable Monomers — Benchmark Extraction for xTB→DFT Calibration

## TL;DR
- **Only a handful of these 25 monomers have clean, unambiguous, primary-source neutral-monomer oxidation potentials**: the thiophene family (3-methylthiophene ≈1.55 V vs SCE in MeCN; terthiophene **+0.880 V vs Ag/AgCl** in MeCN, Camarada 2011) and DTP (**≈+0.52 V vs Ag/AgCl** / onset 770 mV, Zotti/Rasmussen) are the strongest anchors; everything else is either Tier B (needs reference conversion or uses an analog) or must be **Rejected** (film redox, pseudo-reference, or non-standard medium).
- **The dominant hazard is mislabeling**: oligofuran, IDT, DPP, isoindigo, thienopyrazine and thiadiazoloquinoxaline literature overwhelmingly reports *thin-film/polymer* redox or Fc/Fc⁺ HOMO-estimation values, not neutral-monomer-in-solution oxidation — these were excluded.
- **Genuinely data-poor (flag, do not pad)**: 3-fluorothiophene, 3,4-difluorothiophene, 3-methylfuran, 3-hexylfuran, N-octylpyrrole, 3,4-dimethylpyrrole, 3-hexylselenophene, isoindigo, IDT, and the parent thiadiazoloquinoxaline. The anilines (o-anisidine, o-aminophenol, o-toluidine) are *data-rich but only in aqueous strong acid* — flagged NON-STANDARD and kept out of the clean set.

## Key Findings
1. The **Camarada/del Valle thiophene-oligomer dataset** (J. Polym. Sci. B 2011, 49, 1723–1733, DOI 10.1002/polb.22360) is the single best multi-monomer anchor: clean Ag/AgCl(KCl sat) scale, 0.1 M TBAPF₆, Pt disk, explicitly **monomer (not film)** values obtained from slow (1 mV/s) steady-state anodic polarization curves — thiophene +1.50 V, bithiophene +1.15 V, terthiophene **+0.880 V** in CH₃CN.
2. **DTP** is the best clean low-Eox donor lead (Berlin/Pagani/Zotti/Schiavon 1992; reviewed Rasmussen & Evenson, Prog. Polym. Sci. 2013, 38, 1773): "first CV gave an oxidation peak at about 0.52 V vs Ag/AgCl" in 0.1 M TEAP/MeCN; an N-functionalized DTP variant shows an irreversible monomer-oxidation onset at 770 mV (Rasmussen, RSC Adv. 2022, DOI 10.1039/D2RA03265A).
3. **Two previously promising anchors did NOT survive verification** and are flagged: the diphenylamine "~0.86 V" trace traces to *aniline* (860 mV/SCE half-wave), not diphenylamine; and the "+1.25 V vs Ag/AgCl N-vinylcarbazole monomer" value coexists in the same paper with a +1.2 V/SCE *film* peak — a genuine ambiguity surfaced for human vetting rather than resolved.
4. **Reference-scale hygiene is decisive**: oligofuran (Bendikov, Glenis/Kanatzidis) values use a *bare Ag-wire pseudo-reference* (unconvertible) and the authors themselves disclaim CV reliability; furan/fluorothiophene work is done in BF₃·OEt₂ (BFEE). All Rejected from the clean set.

---

## TABLE 1 — TIER A / TIER B CANDIDATE ROWS (one row per measurement)

| # | Monomer (synonyms) / SMILES | Eox as reported (units) | Type | Refers to | Solvent | Electrolyte | Reference electrode | Working electrode / scan rate | Source (authors, year, journal, locator/DOI) | Tier |
|---|---|---|---|---|---|---|---|---|---|---|
| 1a | 3-methylthiophene (3-MeT) / `Cc1ccsc1` | **1.55 V vs SCE** | onset of monomer oxidation (current rise) | NEUTRAL MONOMER in solution | acetonitrile (neutral electrolyte) | (TBA salt; conc. not stated in secondary report) | SCE | not stated / not stated | Zhang & Xue lineage poly(chlorothiophene)/BFEE study; "much lower than … in a neutral electrolyte such as acetonitrile (1.55 V vs. SCE)"; primary family lineage = Waltman, Diaz & Bargon, *J. Phys. Chem.* **1984**, 88, 4343 | B (electrolyte/electrode/scan rate not all stated; SCE→Ag/AgCl +0.044 V) |
| 1b | 3-methylthiophene / `Cc1ccsc1` | ~1.5 V vs SCE ("polymerizes at about 1.5 V") | onset of monomer oxidation/electropolymerization | NEUTRAL MONOMER | MeCN | Bu₄NBF₄ | SCE | Pt / — | Polythiophene review consensus citing Roncali, *Chem. Rev.* **1992**, 92, 711 (tabulates ~1.6 V vs SCE) | B |
| 5a | 2,2′:5′,2″-terthiophene (T3, 3Th) / `c1ccc(-c2ccc(-c3cccs3)s2)s1` | **+0.880 V vs Ag\|AgCl\|KCl(sat)** (CH₃CN); +0.96 V (CH₂Cl₂) | steady-state anodic polarization potential of monomer (paper labels neither "onset" nor "Epa") | NEUTRAL MONOMER in solution (explicitly distinguished from film) | CH₃CN (and CH₂Cl₂) | 0.1 M TBAPF₆ | Ag/AgCl, KCl(sat) | polycrystalline Pt disk 0.07 cm² / **1 mV/s** | Camarada, Jaque, Díaz & del Valle, *J. Polym. Sci. B Polym. Phys.* **2011**, 49(24), 1723–1733, **DOI 10.1002/polb.22360**, Table 5 | **A** |
| 5b | 2,2′:5′,2″-terthiophene / same | 1.4 V vs Ag (pseudo-ref), oxidation peak, no reduction | monomer oxidation peak | NEUTRAL MONOMER | DMF | 10 mM TBAPF₆ | Ag wire (pseudo) | Au / 10–100 mV/s | Carbon-fiber poly(terthiophene) morphology study, *Surf. Coat. Technol.* (S0257897203008892) | B/borderline (pseudo-ref → see Rejected note) |
| 4 | 3-methoxythiophene (MOT) / `COc1ccsc1` | **1.1 V vs SCE** | monomer oxidation (peak/region) | NEUTRAL MONOMER | MeCN | (TBA salt) | SCE | — / scan-rate-dependent anodic potential reported | "Electrochemical polymerization … 3-substituted thiophenes" (S0379677909004962): "MOT … 1.1 V/SCE" | B (SCE convertible; electrode/scan rate incomplete) |
| 6 | N-methylpyrrole / `Cn1cccc1` (parent pyrrole proxy) | parent pyrrole irreversible peak **+1.0 V** | monomer oxidation peak (Epa) | NEUTRAL MONOMER | MeCN | 0.1 M Et₄NBF₄ | (SCE-class, per Diaz) | Pt / 0.1 V/s | del Valle reproduction of Díaz et al. (RG fig. 228772839); N-methylpyrrole sits slightly above pyrrole | B/uncertain (value is for parent pyrrole; N-Me proxy) |
| 13 | 3-hexylselenophene / `CCCCCCc1cc[se]c1` (via 3-methylselenophene analog) | **1.17 V vs Ag/AgCl** (onset) | onset of monomer oxidation | NEUTRAL MONOMER | CH₂Cl₂ | 0.10 M Bu₄NPF₆ | Ag/AgCl | — / — | "Tuning optoelectronic performances for 3-methylselenophene-EDOT" (*Dyes Pigm.*, S025405842030081X): "3-methylselenophene (1.17 V)" | B (analog: methyl not hexyl) |
| 18 | N-vinylcarbazole (NVK/VCz) / `C=Cn1c2ccccc2c2ccccc21` | **+1.25 V vs Ag/AgCl** (monomer Epa); CONFLICT: +1.2 V/SCE reported as film peak in same study | first anodic peak (monomer→radical cation) — DISPUTED vs film | NEUTRAL MONOMER (claimed) | MeCN | 0.1 M LiClO₄ | Ag/AgCl (also SCE used) | Pt / fast CV (≥50–100 V/s) | Frontiers Mater. **2019**, 6, 131 (N-alkylcarbazole series; monomer peak +1.25 V/Ag/AgCl). **Enricher caveat: the +1.2 V/SCE value is the poly(9-vinylcarbazole) FILM doping peak — verify which is the monomer** | B (conflict flagged for human vetting) |
| 19 | 3,6-dimethylcarbazole / `Cc1ccc2c(c1)[nH]c1cc(C)ccc12` (via 3-ethylcarbazole analog) | **≈1.04 V vs SCE** | first-scan monomer oxidation (Epa) | NEUTRAL MONOMER | MeCN | 0.1 M LiClO₄ | SCE | Pt / 100 mV/s | "Electrochemical oxidative coupling of 3 and 6 substituted carbazoles," *J. Electroanal. Chem.* **2021** (S1572665721003829): "3-ethylcarbazole monomer … about 1.04 V/SCE" | B (analog; 3,6-disubstituted carbazoles dimerize rather than polymerize) |
| 24a | dithieno[3,2-b:2′,3′-d]pyrrole (DTP), unfunctionalized / parent `c1cc2c(s1)c1ccsc1[nH]2` | **≈0.52 V vs Ag/AgCl** | first CV anodic peak of monomer | NEUTRAL MONOMER | acetonitrile | 0.1 M TEAP (tetraethylammonium perchlorate) | Ag/AgCl | ITO / repetitive CV | Berlin, Pagani, Zotti, Schiavon **1992**; via Eur. Polym. J. **2023** DTP review (S0014305723008832) & Rasmussen & Evenson, *Prog. Polym. Sci.* **2013**, 38, 1773 | B (ITO working electrode; value "about 0.52 V") |
| 24b | N-functionalized DTP (alkyne/aryl variant) / N-substituted DTP | **onset 770 mV** (irreversible monomer oxidation) | onset | NEUTRAL MONOMER | acetonitrile | 0.1 M TBAPF₆ | (Ag/AgCl-class) | Pt / — | Rasmussen group, *RSC Adv.* **2022**, **DOI 10.1039/D2RA03265A**: "the irreversible peak oxidation of the monomer has an onset at 770 mV" | B |
| 21 | dithienyl-DPP, N-alkyl (e.g., 2,5-dialkyl-3,6-di(thiophen-2-yl)pyrrolo[3,4-c]pyrrole-1,4-dione) | **E₁/₂(ox) = 0.86 V vs Fc/Fc⁺** (reversible) | half-wave E₁/₂ (rare reversible oxidation) | NEUTRAL MONOMER (small molecule) | CH₂Cl₂ | 0.1 M TBAHFP | Fc/Fc⁺ internal standard | — / — | US Patent 8,946,376 (BASF, "Semiconductors based on diketopyrrolopyrroles"), CV data | B (Fc/Fc⁺→Ag/AgCl: +0.45 V ⇒ ≈1.31 V vs Ag/AgCl, ±0.1–0.2 V LJ) |
| 23 | thiadiazolo[3,4-g]quinoxaline (selenophene-flanked diphenyl proxy) / parent `c1cnc2cc3nsnc3cc2n1` (parent core) | **≈1.1 V vs Ag/AgCl** | monomer oxidation (CV) | NEUTRAL MONOMER (substituted proxy) | DCM | 0.1 M TBAH | Ag/AgCl | — / 100 mV/s | Polym. Bull. **2024**, **DOI 10.1007/s00289-024-05393-9**: "oxidation potential of 1 … approximately 1.1 V" | B (heavily substituted proxy, not parent) |
| 20 | thieno[3,4-b]pyrazine-based terthienyls (proxy) / parent `c1cnc2cscc2n1` | monomer **Epa region** (numeric values in their Table 2) | first anodic peak (Epa) | NEUTRAL MONOMER (terthienyl proxy) | CH₃CN or CH₂Cl₂ | 0.10 M TBAPF₆ | (Ag/AgCl-class) | Pt disk / — | Rasmussen group, *Materials* **2016**, 9, 404 (PMC5456834) | B/uncertain (parent TP itself not isolated as clean monomer Eox) |

**Reference-conversion constants used (only where a converted value is offered):** Fc/Fc⁺→Ag/AgCl = +0.45 V (MeCN; Pavlishchuk & Addison, *Inorg. Chim. Acta* 2000), flag ±0.1 V (up to 0.2 V) liquid-junction uncertainty. SCE→Ag/AgCl ≈ +0.044 V (aqueous). Native scales are preserved above; conversions are noted parenthetically only.

---

## TABLE 2 — REJECTED ROWS (with specific reason)

| Monomer / context | Reported value | Reason for rejection |
|---|---|---|
| Terfuran (2,2′:5′,2″-terfuran) — Glenis & Kanatzidis | polymerization potential <1.0 V vs SCE | SCE figure is a *polymerization* potential, not a clean monomer Eox; companion oligofuran CVs (Bendikov, *Chem. Sci.* **2015**, 6, 360, DOI 10.1039/C4SC02664K) use **Ag/AgCl-wire pseudo-reference** and authors state "we cannot reliably measure the oxidation potentials from CV." UNCONVERTIBLE pseudo-ref / authors disclaim reliability |
| 2,2′-bifuran — same lineage | onset ~0.8 V (vs Fu 1.25 V, 3Fu 0.7 V) | Reported in **BFEE** and/or vs Ag-wire pseudo-ref (Chinese polyfuran work, RG 271379964). NON-STANDARD medium / pseudo-ref |
| Oligofurans 5F–8F — US Patents 8,759,550 / 8,921,582 | Epa 0.71→0.67 V vs SCE | Wrong oligomers (penta–octafuran, not bi/terfuran); propylene carbonate + **Ag/AgCl-wire pseudo-ref** calibrated by Fc. Off-target + pseudo-ref |
| Furan / 3-methylfuran / 3-hexylfuran | furan onset 1.25 V (BFEE) | Electropolymerized essentially only in **BF₃·OEt₂ (BFEE)**. NON-STANDARD medium; no clean MeCN/DCM monomer Eox located |
| 3-fluorothiophene | — | No experimental monomer Eox found; only DFT/ionization-potential computational studies. DATA ABSENT (excluded; not fabricated) |
| 3,4-difluorothiophene — US Patent 7,399,433 | could not polymerize in MeCN/PC | Monomer Eox exceeds solvent window; only via **BF₃·OEt₂**. No clean monomer value; NON-STANDARD medium |
| poly(N-vinylcarbazole) film | +1.2 V/SCE | **FILM redox** (perchlorate insertion), not monomer |
| o-anisidine / o-aminophenol / o-toluidine | rich CV data | Measured in **aqueous H₂SO₄/HClO₄** (strong acid). NON-STANDARD MEDIUM — flagged, kept out of clean set |
| Diphenylamine "~0.86 V vs SCE" | 860 mV/SCE half-wave | **Misattribution**: that half-wave is for *aniline*, not diphenylamine (Talanta/J. Electroanal. Chem. aromatic-amine MeCN paper). No confirmed clean diphenylamine monomer Eox extracted — DATA UNVERIFIED |
| IDTz-BARO/BARS, PBDTT-DPP, DPP copolymers, isoindigo polymers | HOMO from Eox,onset vs Fc/Fc⁺ | **Thin-film / polymer** drop-cast measurements used for HOMO estimation, not neutral-monomer-in-solution oxidation |
| Thieno[3,4-b]pyrazine in EDOT-TP copolymers (Zotti) | electrochemical gap values | **Polymer/film** redox, not monomer |
| Terthiophene 5b (Au/DMF, Ag-wire) | 1.4 V vs Ag | Bare Ag-wire **pseudo-reference, no internal calibrant** — lowest tier / not convertible (listed in Table 1 only as borderline) |

---

## Per-Monomer Data-Availability Notes (single best source named)

1. **3-methylthiophene** — **RICH**. Best: Waltman, Diaz & Bargon, *J. Phys. Chem.* **1984**, 88, 4343 (primary substituent-effect table); ~1.55 V vs SCE in MeCN.
2. **3-fluorothiophene** — **VERY THIN**. No experimental monomer Eox; only computational (flagged "most suitable for electropolymerization" by DFT). Best lead: fluorine-thiophene computational papers (no experimental value to ingest).
3. **3,4-difluorothiophene** — **VERY THIN**. Best: US Patent 7,399,433 (electropolymerizable only in BFEE; no clean Eox).
4. **3-methoxythiophene** — **MODERATE**. Best: 3-substituted-thiophene copolymer study (1.1 V/SCE). Note: forms only soluble oligomers (Zotti: "all attempts to polymerize 3-methoxythiophene failed").
5. **2,2′:5′,2″-terthiophene** — **RICH**. Best: Camarada et al. **2011**, DOI 10.1002/polb.22360 (+0.880 V vs Ag/AgCl, MeCN, monomer).
6. **N-methylpyrrole** — **MODERATE**. Best: Diaz lineage / del Valle pyrrole CV (parent pyrrole +1.0 V vs SCE-class; N-Me slightly higher).
7. **N-octylpyrrole** — **THIN**. Best lead: N-substituted pyrrole electropolymerization (*J. Solid State Electrochem.* **2010**, DOI 10.1007/s10008-009-0985-0) — qualitative, no clean isolated Eox.
8. **3,4-dimethylpyrrole** — **THIN**. Best analog: 3,4-dialkylthio/dialkyl-pyrroles oxidize at 0.58–0.71 V vs ~SCE (substituted pyrrole study); parent 3,4-dimethyl value not cleanly isolated.
9. **3-methylfuran** — **VERY THIN** (BFEE only).
10. **3-hexylfuran** — **VERY THIN** (no clean value).
11. **2,2′-bifuran** — **THIN** (Kanatzidis/Bendikov; pseudo-ref / BFEE — Reject).
12. **terfuran** — **THIN**. Best: Glenis, Benz, LeGoff, Schindler, Kannewurf & Kanatzidis, *J. Am. Chem. Soc.* **1993**, 115, 12519 (polymerization <1.0 V vs SCE; pseudo-ref caveats — Reject for clean set).
13. **3-hexylselenophene** — **THIN**. Best analog: 3-methylselenophene 1.17 V vs Ag/AgCl in DCM (*Dyes Pigm.* S025405842030081X).
14. **o-anisidine (o-methoxyaniline)** — **RICH but aqueous acid only** (Reject from clean set).
15. **o-aminophenol** — **RICH but aqueous acid only** (Reject from clean set).
16. **o-toluidine** — **RICH but aqueous acid only** (Reject from clean set).
17. **diphenylamine** — **MODERATE but UNVERIFIED here**. Clean nonaqueous CV exists (aromatic-amine MeCN literature; oxidizes ~0.8–0.9 V vs SCE region), but the specific number I located was a *misattributed aniline* value — needs direct primary reading before ingestion. Best lead: Adams-school aromatic-amine acetonitrile voltammetry (0026-265X/0040-4039 lineage).
18. **N-vinylcarbazole** — **MODERATE**, but monomer-vs-film conflict flagged. Best: Frontiers Mater. **2019**, 6, 131 (+1.25 V/Ag/AgCl assigned to monomer; verify against the +1.2 V/SCE film peak in the same paper).
19. **3,6-dimethylcarbazole** — **THIN**. Best analog: 3-ethylcarbazole +1.04 V/SCE (*J. Electroanal. Chem.* **2021**). 3,6-disubstituted carbazoles dimerize (blocked reactive positions) — report monomer first-oxidation only.
20. **thieno[3,4-b]pyrazine** — **THIN** (strong acceptor; usually inside copolymers). Best: Rasmussen group, *Materials* **2016**, 9, 404.
21. **dithienyl-DPP (N-alkyl)** — **MODERATE** (Fc/Fc⁺ in DCM). Best: BASF US Patent 8,946,376 (E₁/₂ox = 0.86 V vs Fc/Fc⁺).
22. **isoindigo (N,N′-dialkyl)** — **THIN** for monomer-in-solution *oxidation* (isoindigo is n-type/acceptor; oxidation is weak/high and usually reported as polymer HOMO). No clean monomer Eox extracted.
23. **[1,2,5]thiadiazolo[3,4-g]quinoxaline** — **THIN** (parent rarely measured alone). Best: Polym. Bull. **2024**, DOI 10.1007/s00289-024-05393-9 (substituted proxy ~1.1 V vs Ag/AgCl).
24. **dithieno[3,2-b:2′,3′-d]pyrrole (DTP)** — **MODERATE** and the cleanest low-Eox lead. Best: Zotti 1992 / Rasmussen review **2013** (+0.52 V vs Ag/AgCl) + Rasmussen *RSC Adv.* **2022** (onset 770 mV).
25. **indacenodithiophene (IDT)** — **THIN** for clean monomer oxidation (almost all data are Fc/Fc⁺ thin-film HOMO estimates; first oxidations often quasi-/irreversible, some compounds insoluble). No clean neutral-monomer-in-solution Eox extracted.

---

## Recommendations
**Stage 1 — ingest now (Tier A, high confidence):**
- 2,2′:5′,2″-terthiophene **+0.880 V vs Ag/AgCl** (Camarada 2011) — already on the target Ag/AgCl scale; ideal calibration point.
- 3-methylthiophene ≈1.55 V vs SCE (convert +0.044 V → ≈1.59 V vs Ag/AgCl) — pending a direct read of Waltman 1984 to confirm electrolyte/electrode/scan rate (then promote fully to Tier A).

**Stage 2 — ingest with conversion + caveat (Tier B):**
- DTP +0.52 V vs Ag/AgCl (native) and N-DTP onset 770 mV; 3-methoxythiophene 1.1 V/SCE; 3-methylselenophene 1.17 V vs Ag/AgCl (as a *proxy* for 3-hexylselenophene, label clearly); 3-ethylcarbazole 1.04 V/SCE (proxy for 3,6-dimethylcarbazole); dithienyl-DPP 0.86 V vs Fc/Fc⁺ (convert +0.45 V → ≈1.31 V vs Ag/AgCl, carry ±0.2 V uncertainty).

**Stage 3 — do NOT ingest without human vetting:**
- All furan-family, fluorothiophene, aniline (aqueous-acid), and any DPP/IDT/isoindigo/thienopyrazine/TQ *thin-film* values.
- N-vinylcarbazole and diphenylamine: resolve the monomer-vs-film / misattribution conflicts by reading the primary CVs before use.

**Benchmarks that would change these recommendations:** (a) obtaining the primary Waltman 1984 and Roncali 1992 tables would let several homocyclic monomers (3-MeT, N-MePy) move to Tier A on a single internally consistent SCE scale; (b) finding any nonaqueous (MeCN/DCM) CV for o-anisidine/o-toluidine would let an aniline-family point enter the clean set; (c) a primary report of parent thienopyrazine or IDT *monomer* oxidation (vs a stated standard reference) would upgrade those from "thin/absent" to Tier B.

## Caveats
- Several Table 1 values are quoted via reviews, secondary syntheses, or patents; the underlying primary CV tables (especially Waltman 1984, Zotti 1992, the DPP patent) should be read directly before final ingestion. Fields left blank (scan rate, exact electrolyte concentration, working-electrode material) are genuinely not stated in the sources consulted — they are not inferred.
- The Camarada terthiophene value is the most trustworthy: a subagent confirmed it is a *steady-state anodic polarization* monomer value (1 mV/s), explicitly distinguished from the polymer-film band-gap CV in the same paper. Note the paper labels it neither "onset" nor "Epa"; the secondary NREL report calling it a "CV onset" is a mild mischaracterization.
- Pseudo-reference (bare Ag-wire) values are not convertible to an absolute scale and are Rejected/lowest-tier.
- Fc/Fc⁺→Ag/AgCl conversion (+0.45 V, MeCN) carries ±0.1–0.2 V liquid-junction uncertainty; SCE→Ag/AgCl (+0.044 V) is for aqueous and is only approximate in nonaqueous media.
- For donor–acceptor monomers, "oxidation potential" in OPV/OFET papers almost always means a polymer/thin-film HOMO estimate — treat every such number as Reject unless the text explicitly states neutral-monomer-in-solution oxidation.
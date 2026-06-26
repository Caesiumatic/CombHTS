# T3 — NMP / THF / sulfolane ESW curation (2026-06-26)

Status: **decide-and-report; source-limited; NOTHING new promoted or staged.** This documents a fresh
primary-literature sweep for measured-first, Ag/AgCl-convertible electrochemical-stability-window (ESW)
rows for the three survivor/relevant solvents flagged in `data/lit_curation/esw_remaining_gap_matrix.csv`.

## Conclusion up front
After a fresh sweep (primary CV papers, the Izutsu *Electrochemistry in Nonaqueous Solutions* compilation,
the IUPAC/Mann purification tables, the ALS/Izutsu vendor table, and battery/EDLC literature), **no clean
primary Pt or glassy-carbon, tetraalkylammonium ESW row that is honestly convertible to the project's
Ag/AgCl master scale was found for NMP, THF, or sulfolane.** The existing staging already captures the only
rows that exist, and they are all on unconvertible reference frames. No new rows are added, because adding
one would require an unverified reference conversion — forbidden by the project's do-not-approximate rule.

## Per-solvent findings

### NMP (1-methyl-2-pyrrolidone) — still completely absent from `solvent_esw_staging.csv`
- All accessible ESW-type data is **Li/Li⁺ battery context** (NMP as a Li-air / Li-battery solvent, e.g.
  Walker et al. *J. Power Sources* 2012, 219, 263). Li/Li⁺ has **no pinned Li/Li⁺→Ag/AgCl shift** in this
  project → unconvertible.
- TBAClO₄ ORR/OER studies on Au/GC in NMP exist but report electrode reactions of dissolved O₂, **not a
  full solvent anodic/cathodic breakdown window** vs a convertible reference.
- **Outcome:** gap stands. NMP has no measured-first Ag/AgCl ESW row.

### THF (tetrahydrofuran) — 2 staged rows, both unconvertible
- Both staged primary rows (Niklas/Duffy/La Pierre, *Inorg. Chem.* 2026; TBAPF₆ and TBABPh₄) are referenced
  to **Fc/Fc⁺ measured against a bare-Ag pseudo-reference**. The project's Fc→Ag/AgCl +0.445 V pin is
  **MeCN-only**, so THF Fc rows cannot be converted.
- Other THF electrochemistry surfaced is cryogenic / low-temperature (non-standard conditions) or
  water-in-THF behaviour — not a standard-condition solvent ESW.
- **Outcome:** gap stands. No SCE/SHE/native-Ag/AgCl THF row located.

### Sulfolane (TMS) — 3 staged rows, all unconvertible
- All staged rows are **Li/Li⁺ battery / GPE full-cell windows** (Xing 2014; Wang 2019; Sheina 2018), plus
  newer high-voltage Li/Na-battery sulfolane electrolytes from this sweep — all battery-context, anodic-only
  or full-cell, on **Li/Li⁺** (unconvertible) or quoted as a >7 V *full-cell* number, not a three-electrode
  solvent window.
- EDLC/capacitor sulfolane electrolytes (TEABF₄-type, Ue lineage) exist but the accessible reports do not
  give a three-electrode anodic/cathodic pair vs SCE/Ag/AgCl with conditions.
- **Outcome:** gap stands. No tetraalkylammonium Pt/GC sulfolane window vs a convertible reference located.

## Decision (within directive authority)
- **Stage nothing.** No row clears the conversion bar; staging a fabricated/assumed conversion would violate
  the measured-first integrity rule. The `esw_remaining_gap_matrix.csv` entries for NMP (full ESW), THF
  (reference scale), and sulfolane (electropolymerization-scale ESW) are **confirmed accurate as of
  2026-06-26**.
- **Gate behaviour:** keep these three solvents **parked from the measured-first Ag/AgCl ESW gate** — i.e.
  scored on the conservative solvent-only / fallback window, never on a hard measured ESW gate, until a
  convertible primary row is obtained. This is already the de-facto state; this note makes it explicit and
  dated.
- **Future closure paths (manual, not blocking):** (1) obtain the Izutsu 2nd-ed. potential-window table page
  directly (paywalled/PDF-host unreachable from here) to read NMP/THF/sulfolane limits with their stated
  reference; (2) commission a primary CV for any of the three on Pt/GC with a tetraalkylammonium salt vs
  Ag/AgCl or SCE; (3) for THF specifically, find a source-internal Fc→Ag/AgCl calibration measured *in THF*
  so the existing Fc rows become convertible.

## UPDATE 2026-06-26 (deep-research pass) + RESOLUTION

A dedicated deep-research sweep (artifact `compass_…_text_markdown.md`) refined the picture. Net change:
**THF gains a conditional bridge; NMP and sulfolane gaps stand.** Verdict and plan below.

### THF — conditional bridge found (soft prior only, NOT a hard gate)
- **Connelly & Geiger, *Chem. Rev.* 1996, 96, 877 (DOI 10.1021/cr940053x), Table 1** ("Formal Potentials
  for the Ferrocene⁺¹/⁰ Couple vs SCE in Selected Electrolytes") gives **Fc/Fc⁺ in THF = 0.56 V vs SCE**
  (0.1 M NBu₄PF₆) and **0.53 V** (0.1 M NEt₄PF₆). Via the task-allowed SCE→Ag/AgCl +0.045 V (Pavlishchuk &
  Addison 2000) → **Fc/Fc⁺ ≈ +0.605 / +0.575 V vs Ag/AgCl(sat. KCl) in THF**.
- **Two reasons this stays a soft prior, not a measured-first gate:** (1) it is a **secondary-compilation**
  value (Connelly & Geiger), not a primary measurement; (2) the only staged primary THF rows (La Pierre
  2026) are referenced to a **bare-Ag pseudo-reference**, so applying the C&G Fc-vs-SCE offset to them is a
  **cross-paper bridge** — it violates the same-cell tie rule that a hard gate requires.
- **Correction to the research artifact:** it suggested the THF Fc value traces to "Shalev & Evans" as the
  primary. On checking the open-access IntechOpen chapter 81101, reference [22] is *Shalev H, Evans DH,
  J. Am. Chem. Soc. 1989, 111(7), 2667* — a paper on **anion-radical solvation**, used by that chapter only
  for **low-electrolyte referencing**, NOT as the primary source of the 0.56 V vs SCE value. So the 0.56 V
  origin remains Connelly & Geiger's compilation; there is **no cleaner primary** behind it yet.
- **Pavlishchuk & Addison caveat:** a 2024 corrigendum exists (Inorg. Chim. Acta 578, 122468) — verify the
  +0.045 V constant is unaffected before any finalization.

### NMP & sulfolane — gaps stand; primary candidates located but values NOT extractable
- **Sulfolane window:** Coetzee & Simon, *Anal. Chem.* 1972, 44(7), 1129 (DOI 10.1021/ac60315a012,
  "Voltammetry in methanol, ethanol, and sulfolane") — confirmed real, the best primary window candidate;
  numeric limits not extractable from open web. **NOT FOUND (= real but unread), not staged.**
- **Sulfolane Fc tie:** Armstrong, Quinn & Vanderborgh, *J. Electrochem. Soc.* 1976, 123, 646 ("Heterogeneous
  charge transfer rates of the ferrocene oxidation in sulfolane") — confirmed real; half-wave value not
  extractable. **NOT FOUND.**
- **NMP:** no qualifying primary three-electrode window and no in-solvent Fc-vs-SCE/Ag-AgCl tie exist.
  Tsierkezos *J. Solution Chem.* 2007 covers ACN/DMF/DMSO/etc. but **not NMP or sulfolane**. The Izutsu/Mann
  Pt window table lists NMP & sulfolane but **vs Fc/Fc⁺** — useless without those solvents' Fc offsets.

### RESOLUTION — how we close (or honestly bound) point 3
The data does not support a measured-first **hard ESW gate** for any of the three from literature today.
The integrity-preserving resolution has three layers:

1. **Policy (recommended, default-safe — PI to ratify):** keep NMP/THF/sulfolane on the **conservative
   solvent-only fallback window**; they never gate on a *measured* window. This is already the de-facto
   state and is the safe choice — the fallback is more restrictive, so survivors through it stay valid; we
   simply don't *reward* these solvents with a precise measured window. No fabricated conversion enters the
   benchmark.
2. **THF soft prior (do now, documented, non-gating):** record the C&G bridge (Fc/Fc⁺ +0.605 V vs Ag/AgCl in
   THF, 0.1 M NBu₄PF₆) as a **low-confidence diagnostic prior** in this doc and the gap matrix — usable for
   sanity-checking THF predictions, explicitly flagged "cross-paper / secondary / NOT a gate." It does NOT
   go into the `converted_*` columns of `solvent_esw_staging.csv` (those stay BLANK = honest).
3. **Real closure (bounded, needs UIUC library access — fastest path):** pull THREE confirmed-real primary
   PDFs and extract the numbers. This is the only thing that upgrades sulfolane/NMP to convertible and THF to
   a primary same-cell tie:
   - **Coetzee & Simon 1972**, DOI 10.1021/ac60315a012 → sulfolane usable-potential range (anodic/cathodic
     limit, reference electrode, electrolyte conc., electrode, cutoff criterion, scan rate).
   - **Armstrong, Quinn & Vanderborgh 1976**, J. Electrochem. Soc. 123, 646 → sulfolane Fc/Fc⁺ half-wave +
     its native reference (if SCE/Ag-AgCl → directly convertible).
   - **Izutsu, *Electrochemistry in Nonaqueous Solutions*** (window appendix) / **Mann 1969** (Electroanal.
     Chem. Vol. 3, p. 57) → NMP & sulfolane Pt positive/negative limits **with their stated reference**, then
     trace each to its primary.
   Any of these, once the user can supply the PDF, is read-and-stage in minutes (PDFs are directly readable
   here). Until then the rows stay NOT FOUND — confirmed-real, unread, never fabricated.

**Gate threshold (unchanged):** a row may be converted and used as a hard gate only if it is a three-electrode
**solvent** window (not full-cell voltage), on tetraalkylammonium / GC or Pt, with a native SCE/SHE/true-aqueous
Ag/AgCl reference **OR** a same-paper Fc/Li tie in that solvent. Cross-paper bridges and bare-Ag pseudo-refs
are soft priors at most.

## Sources consulted (this sweep)
- Connelly & Geiger, *Chem. Rev.* 1996, 96, 877 (DOI 10.1021/cr940053x) — THF Fc/Fc⁺ vs SCE 0.56/0.53 V (compilation; THF bridge).
- IntechOpen chapter 81101 "Effects of Electrolyte on Redox Potentials" — corroborates the C&G THF value; Shalev & Evans [22] = JACS 1989 111 2667 (anion-radical solvation, NOT the value's primary).
- Coetzee & Simon, *Anal. Chem.* 1972, 44(7), 1129 (DOI 10.1021/ac60315a012) — sulfolane window primary (value NOT extracted).
- Armstrong, Quinn & Vanderborgh, *J. Electrochem. Soc.* 1976, 123, 646 — sulfolane Fc primary (value NOT extracted).
- Walker et al., NMP for Li-air electrolyte, *J. Power Sources* 2012, 219, 263 — Li/Li⁺, unconvertible.
- Niklas, Duffy, La Pierre, *Inorg. Chem.* 2026, 65(7), 3758 — THF Fc/Fc⁺ rows (already staged).
- Xing et al., *Electrochim. Acta* 2014, 133, 117; Wang et al., *Polymers* 2019, 11, 1306; Sheina et al.,
  *Russ. J. Appl. Chem.* 2018, 91, 1427 — sulfolane Li/Li⁺ (already staged).
- Izutsu, *Electrochemistry in Nonaqueous Solutions*, 2nd ed., Wiley-VCH 2002 — compilation confirmed to
  contain NMP/THF/sulfolane window data; exact numbers + reference convention not verifiable from accessible
  copies, so not transcribed (do-not-approximate rule).
- ALS/Izutsu vendor "Solvent and Supporting Electrolyte" table — Fc/Fc⁺-referenced; non-MeCN unconvertible.

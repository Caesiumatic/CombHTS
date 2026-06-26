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

## Sources consulted (this sweep)
- Walker et al., NMP for Li-air electrolyte, *J. Power Sources* 2012, 219, 263 — Li/Li⁺, unconvertible.
- Niklas, Duffy, La Pierre, *Inorg. Chem.* 2026, 65(7), 3758 — THF Fc/Fc⁺ rows (already staged).
- Xing et al., *Electrochim. Acta* 2014, 133, 117; Wang et al., *Polymers* 2019, 11, 1306; Sheina et al.,
  *Russ. J. Appl. Chem.* 2018, 91, 1427 — sulfolane Li/Li⁺ (already staged).
- Izutsu, *Electrochemistry in Nonaqueous Solutions*, 2nd ed., Wiley-VCH 2002 — compilation confirmed to
  contain NMP/THF/sulfolane window data; exact numbers + reference convention not verifiable from accessible
  copies, so not transcribed (do-not-approximate rule).
- ALS/Izutsu vendor "Solvent and Supporting Electrolyte" table — Fc/Fc⁺-referenced; non-MeCN unconvertible.

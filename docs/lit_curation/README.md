# Literature curation — STAGING benchmark data

> **STAGING ONLY — needs human review before use.** Every value here is a literature
> value harvested by an automated source-verified web search. It carries `needs_review=true`
> and **must be human-spot-checked against the cited DOI/reference BEFORE it enters
> calibration or scoring.** Nothing in `data/lit_curation/` is wired into `configs/`,
> `data/benchmark.csv`, `src/`, or the scoring path. The priority deliverable (A, solvent ESW)
> is intended to feed the measured-first ESW selection in
> `src/eps/properties/solvent_windows.py` only after review, by adding reviewed rows to the
> production `data/solvent_windows.csv`.

Files (all in `data/lit_curation/`):

| File | Priority |
|---|---|
| `solvent_esw_staging.csv` | **A — solvent electrochemical stability window (priority)** |
| `polymerization_outcomes_staging.csv` | B — electropolymerization yes/no/conditional |
| `solubility_staging.csv` | C — monomer solubility in library solvents |
| `optical_doping_staging.csv` | D — polymer optical gap + doping onset |
| `_raw_curation.json` | raw research output (provenance) |
| `build_staging.py` | deterministic rebuild of the four CSVs from the JSON (applies pinned conversions) |

Rebuild: `python3 data/lit_curation/build_staging.py` (run from repo root).

## Coverage (N sourced / N target)

| Priority | Target | Sourced | Rows | Notes |
|---|---|---|---|---|
| **A — Solvent ESW** | 13 library solvents | **11 / 13** | 26 candidate rows | 11 high-confidence; 14 rows carry a pinned Ag/AgCl conversion (12 left empty — non-pinned reference or one-sided limit) |
| B — Polymerization | 36 library monomers | **31 / 36** | 91 (53 `yes`, 38 `conditional`, 0 `no`) | negatives surface as `conditional` with the failing/narrow condition recorded |
| C — Solubility | 36 monomers × 13 solvents | **10 / 36 monomers, ~1 / 13 solvents** | 33 (29 quantitative) | almost entirely **aqueous**; organic-solvent solubility largely untabulated |
| D — Optical / doping | polymers of 36 monomers | 27 polymer rows | 24 with optical gap, 21 with doping onset | only 6 doping onsets convertible (pinned reference); rest flagged |

## Reference→Ag/AgCl conversion (pinned only — never hand-rolled)

Conversion is the additive shift `E(vs Ag/AgCl) = E(vs ref) + SHIFT`, recorded per row in the
`conversion` column so each converted value is reproducible from (orig, reference, shift).
Pinned shifts (consistent with `src/eps/properties/redox.py` `AGAGCL_SHIFT_V = -0.197` and the
spec values already used in `data/solvent_windows.csv`):

| Reference | Shift (V) | Applied? |
|---|---|---|
| SCE | **+0.045** | yes |
| Fc/Fc⁺ | **+0.445** | **only in MeCN/acetonitrile** — pinned for MeCN only |
| SHE / NHE | **−0.197** | yes |
| Ag/AgCl | 0.000 | yes (already in target frame) |
| Ag/Ag⁺ (Ag/AgNO₃), Li/Li⁺, decamethylferrocene (DMFc), Ag/AgCl pseudo-wire, Fc outside MeCN | — | **no — converted cell left EMPTY, reason in `flags`** |

**Sanity check:** the SCE/SHE conversions reproduce the existing human-curated production
values in `data/solvent_windows.csv` exactly (e.g. acetonitrile +3.2/−3.1 V SCE → +3.245/−3.055;
DMF +1.7/−2.2 V SCE → +1.745/−2.155; water +1.1/−1.3 V SCE → +1.145/−1.255; GBL +5.4/−2.8 V SHE
→ +5.203/−2.997). This validates the constants but does **not** validate the underlying literature
values — those still need review.

## GAPS — what could NOT be sourced

### A — Solvent ESW
- **N-methyl-2-pyrrolidone (NMP): NO sourced ESW** with full conditions found.
- **Nitrobenzene: NO sourced ESW** with full conditions found independently. (Production
  `data/solvent_windows.csv` carries only an *approximate* review value for nitrobenzene; this run
  did not improve on it.)
- **THF, DMSO, nitromethane**: best determinations found use **ferrocene** reference outside MeCN,
  so they are **not convertible** with the pinned constants — orig values are recorded but the
  Ag/AgCl columns are empty and flagged. Need a SCE/SHE/Ag/AgCl-referenced source or a pinned
  Fc-shift for those solvents.
- **Propylene carbonate**: best-conditioned modern source (Bu₄NBF₄, GC, 0.1 mA cm⁻²) is referenced
  to **Ag/Ag⁺** → not convertible; the convertible PC row is the older SHE Ue value.
- **DCM**: highest-confidence determination (Black & Bartlett 2022, fully conditioned) uses
  **decamethylferrocene** → not convertible; the convertible DCM row is the lower-confidence SCE
  compilation.
- **Sulfolane**: all three sourced rows are battery-context **Li/Li⁺** anodic-only limits → not
  convertible and no cathodic limit.

### B — Polymerization
- **0 hard `no`** outcomes. The literature rarely reports clean non-polymerization; the
  negatives for the §7 yes/no metric appear as `conditional` rows whose `conditions` field records
  *why* it fails or *what narrow condition* is required (e.g. furan: poor films / overoxidation;
  selenophene: high oxidation onset; 3-fluorothiophene: insoluble electron-poor product). A human
  must decide how `conditional` maps onto a binary yes/no label.
- **5 / 36 monomers not covered**: ProDOT, 3-methylfuran, 3-hexylfuran, 3,4-dimethylfuran,
  3-hexylselenophene. (ProDOT is well known to electropolymerize; this run simply did not return a
  citable row for it — likely findable on review.)
- 3 rows cite a reference without a DOI.

### C — Solubility
- **Organic-solvent solubility essentially missing.** 32 of 33 rows are **aqueous** (plus one DMSO
  catalog value). Quantitative solubility of these monomers in the *organic* library solvents
  (MeCN, DCM, THF, DMF, DMSO, PC, GBL, sulfolane, NMP, nitrobenzene, benzonitrile) is largely not
  tabulated in the open literature — most are reported only as "miscible"/"soluble". This is the
  weakest priority.
- **26 / 36 monomers uncovered** (only EDOT, thiophene, terthiophene, furan, pyrrole, aniline,
  o-toluidine, o-methoxyaniline, carbazole, diphenylamine have any sourced value).
- 21 rows cite a handbook/database/catalog (Merck Index, Yalkowsky, Riddick, ICSC, NIOSH, NTP,
  HMDB) rather than a DOI — acceptable as a full citation, but verify the edition/record.

### D — Optical / doping
- **Only 6 / 21 doping onsets are convertible** to Ag/AgCl. The dominant reference is **Ag/Ag⁺**
  (11 rows), plus ferrocene (solvent not captured) and one Ag/AgCl pseudo-wire — none have a pinned
  shift, so their `doping_onset_vs_AgAgCl_V` is empty and flagged.
- The optical schema **did not capture the CV solvent**, so even the ferrocene-referenced rows
  cannot be confirmed as MeCN; convert only after recovering the solvent from the source.
- 3 rows have no optical gap; 6 have no doping onset.

## Specific per-row caveats to check first
- **nitromethane, SHE row (+1.0 / −2.9 V):** flagged `CROSS-CHECK ... likely SWAPPED`. The known
  Ue/production nitromethane window is **+2.9 / −1.0 V vs SHE** (the nitro group reduces easily →
  narrow cathodic). This row's anodic/cathodic look transposed — verify against primary
  `10.1149/1.2059270` before use.
- **GBL, SHE row (+5.4 / −2.8 V):** flagged outlier — 8.2 V total window is implausibly wide and
  formulation-limited; matches the production caveat. Treat the anodic limit as a high formulation
  bound, not an intrinsic solvent edge.
- **sulfolane, +5.9 / +5.5 V row:** both limits positive (narrow 0.4 V window) — likely an
  extraction error; low confidence.

---
*These are STAGING values requiring human spot-check against the cited DOIs/references before they
enter calibration or scoring.*

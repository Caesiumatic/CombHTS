# Section 7 staging-data audit and targeted gap curation

Date: 2026-06-23
Branch: `research/section7-staging-audit`
Pre-work local HEAD: `e7e8c3967d9bf5fefb0e191722197ed0af136b41`
Pre-work `origin/main`: `e7e8c3967d9bf5fefb0e191722197ed0af136b41`

## Scope and boundary

This work audited existing literature-curation staging data and added compact review tables for
Section 7 validation readiness. It did not edit production data, configs, scoring code, calibration
policy, or engine outputs. No Lop / cluster output was accessed, and no quantum-chemistry run was
performed.

Optical job 417587 is acknowledged only as the already-documented diagnostic result: 6/6 sTDA and
6/6 TDA anchor dimers completed, but dimer-vs-polymer fits were weak, so the 15% optical axis remains
diagnostic and unchanged. Nothing here reinterprets 417587 or uses it for production calibration.

## Files created

- `scripts/audit_lit_curation_staging.py`
- `data/lit_curation/staging_audit_summary.csv`
- `data/lit_curation/staging_audit_issues.csv`
- `data/lit_curation/eox_gapfill_candidates.csv`
- `data/lit_curation/esw_promotion_candidates.csv`
- `data/lit_curation/esw_remaining_gap_matrix.csv`
- `data/lit_curation/polymerizability_promotion_candidates.csv`
- `data/lit_curation/library_waveA_readiness_candidates.csv`

## Existing staging inventory and audit counts

The audit covered five staging CSVs under `data/lit_curation/`. All expected schemas passed. All
SMILES-bearing rows parsed in RDKit: 127 valid parsed SMILES cells and 0 invalid SMILES cells.

| staging file | rows | internal duplicate rows | exact production duplicate rows | promote candidates | needs source | needs reference conversion | needs condition match | park | reject |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `solvent_esw_staging.csv` | 26 | 0 | 3 | 8 | 1 | 13 | 0 | 3 | 1 |
| `polymerization_outcomes_staging.csv` | 91 | 30 | 3 | 29 | 35 | 0 | 27 | 0 | 0 |
| `optical_anchors_selected.csv` | 9 | 0 | 0 | 0 | 0 | 6 | 0 | 3 | 0 |
| `solubility_staging.csv` | 33 | 2 | 0 | 0 | 2 | 0 | 31 | 0 | 0 |
| `optical_doping_staging.csv` | 27 | 0 | 0 | 0 | 0 | 15 | 0 | 12 | 0 |

Totals: 186 staging rows; 37 machine-classified `PROMOTE_NOW_CANDIDATE`, 38
`NEEDS_SOURCE_CHECK`, 34 `NEEDS_REFERENCE_CONVERSION_CHECK`, 58
`NEEDS_CONDITION_MATCH_CHECK`, 18 `PARK`, and 1 `REJECT`.

The single reject is the staged nitromethane ESW row flagged as likely anodic/cathodic-swapped
relative to Ue / production provenance. It stays visible in the issues file so it is not silently
rediscovered.

## Targeted candidate outputs

| output | rows | headline |
|---|---:|---|
| `eox_gapfill_candidates.csv` | 8 | 5 source-check rows and 3 reference-conversion blockers; strongest new leads are EDOT condition rows with a source-calibrated pseudo-reference, plus blocked furan/EDOS provenance rows. |
| `esw_promotion_candidates.csv` | 12 | 8 exact-salt, 3 solvent-only, 1 same-anion/one-sided row; several are already production-represented and are retained as review/provenance rather than new production edits. |
| `esw_remaining_gap_matrix.csv` | 10 | Highest blockers are PC exact-salt rows, MeCN/TBAPF6, nitromethane primary-source reconciliation, NMP, and nitrobenzene. |
| `polymerizability_promotion_candidates.csv` | 20 | 8 YES and 12 NO candidates; 16 are review-ready after source spot-check, with explicit chemical / medium / electrode / soluble-product classes. |
| `library_waveA_readiness_candidates.csv` | 22 | 12 monomers, 4 solvents, 6 electrolytes; all RDKit-valid and non-duplicate at the species or salt-pair level. |

## Top remaining Section 7 gaps

1. PC exact-salt ESW: current convertible evidence is generic Et4NBF4 / GC, but corrected survivors
   are PC-heavy. BF4/PF6/ClO4/TFSI rows under electropolymerization-like Pt/GC conditions are the
   highest-value ESW curation target.
2. MeCN/TBAPF6 ESW: polymerization validation rows often use TBAPF6, while staging has TBABF4 and
   LiClO4 exact rows plus generic Et4NBF4.
3. Nitromethane ESW provenance: production uses the corrected Ue-derived window, but staging still
   contains a likely swapped row and an unconverted primary placeholder. Read Ue 1994 directly.
4. NMP ESW: no full-condition staged row exists, so NMP remains uncovered in solvent_benchmark MAE.
5. Nitrobenzene ESW: production has approximate review evidence but no full-condition staging row.
6. GBL wide-window control: Ue/Gong row is convertible but formulation-limited and must remain capped.
7. Sulfolane and THF: staged values are Li/Li+ or Fc/Fc+ outside MeCN, so no pinned Ag/AgCl conversion.

## Rows needing human / mentor source check first

- EDOT 2025 solvent/dopant rows (`10.1007/s10853-025-11477-2`): recover exact figure/table/page and
  confirm each value is a monomer oxidation onset rather than a film-growth feature.
- Furan and 2-methylfuran Synthetic Metals 1999 rows: do not convert Ag0/Ag+ without an in-medium
  calibration.
- EDOS JACS 2008 (`10.1021/ja8018675`): recover the reference electrode from the supporting source
  before any conversion.
- 3'-carboxyl-terthiophene (`10.1021/ac015572w`): source metadata and higher-precision value need
  primary-article confirmation.
- ESW low-confidence exact rows from Schotten / Green Chem. 2020 (`10.1039/D0GC01247E`): confirm
  cutoff, concentration, and whether the row is a primary measurement or compilation.
- GBL and nitromethane Ue rows: verify primary values and formulation-limited caveats directly.
- Polymerizability: recover ProDOP-br-C3 exact SMILES; resolver-check the thiophene-water DOI; pin
  primary source for the 2,5-dimethylthiophene alpha-blocked negative.

## Decision and escalation

No item meets `ESCALATE_PI` criteria. The work stays within Directive_CombHTS, uses no unusual
shared-cluster resources, and opens no new scientifically consequential ambiguity beyond existing
Section 7 curation gaps. Recommended next step is human source-check of the rows above, then a
separate production-ingest task for any approved rows.

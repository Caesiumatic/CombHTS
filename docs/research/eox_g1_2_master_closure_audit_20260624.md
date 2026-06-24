# G1.2 Eox master closure audit

This is a review-only, no-engine curation audit. It does not modify production benchmark,
library, config, redox, scoring, Tier-1, Tier-2, validation, cache, or output-schema files.

## Provenance

- Repo SHA: `87f62157e16a1e33baa73ff4504efed1e2863784`
- Engine: none (no-engine curation)
- Input hashes:
  - benchmark: `572ecd8e4339fcd1e7bb31834f90ee5b4f7bf3690550e3f53ad2044d9b2fa6fe`
  - external_manifest: `3698c8fae7dd7ffc0e85ad50dd73aaa352964ce4952551374decf4056e004075`
  - r11_r21_review: `ed72def28074d34bee8db5fe16923fb3a2e1894654e8206d54ca20b06883ca2a`

The external source manifest records canonical filenames, SHA-256 hashes, DOI/status,
and extraction status only. PDFs, zips, and raw extracted text remain outside the repo.

## Closure Counts

- Source-manifest rows: 31
- External evidence rows: 29
- Master evidence rows: 86
- Production benchmark rows reviewed: 39
- R11-R21 staging rows reviewed: 11
- External measurement/provenance rows reviewed: 36
- RDKit parse-ok rows: 64
- Directive-eligible combinations: 31 (PASS vs >=30)
- Onset-profile eligible combinations: 11
- Peak-profile eligible combinations: 23
- Native-Fc eligible combinations: 0
- Production corrections proposed: 10
- Camarada non-CV steady-state rows found in production: 10
- Paywalled DOI rows with no lawful PDF downloaded: 2

## Master Class Counts

- CLEAN_CV_ONSET_AGAGCL: 11
- CLEAN_CV_ONSET_NATIVE_FC: 4
- CLEAN_CV_PEAK_AGAGCL: 23
- MIXED_SOLVENT_PARKED: 8
- NON_CV_POLARIZATION_ONSET: 5
- NON_CV_STEADY_STATE: 10
- PROVENANCE_BLOCKED: 6
- REJECT: 1
- SOURCE_CONFLICT: 8
- STRUCTURE_BLOCKED: 1
- UNRESOLVED_REFERENCE: 9

## Disposition Counts

- ADD_NEW_BENCHMARK_ROW: 5
- KEEP: 29
- PARK: 41
- REJECT: 1
- RELABEL_ONTOLOGY: 10

## Production Proposal Counts

- ADD_NEW_BENCHMARK_ROW: 5
- MARK_CALIBRATION_INELIGIBLE: 10
- PARK: 41
- REJECT: 1

## Scientific Findings

- The 10 Camarada thiophene-oligomer rows in current production are not ordinary CV
  onset rows. The source uses slow steady-state polarization curves, so this audit
  marks them non-CV and proposes a future production correction rather than treating
  them as calibration/onset-profile evidence.
- R11-R13 remain staging-only because they are mixed ACN/DCM pseudo-reference rows.
  R14-R21 remain parked because source-internal reference and condition conflicts
  are unresolved.
- Direct Ag/AgCl clean-CV external rows from the prepared official evidence packet
  are proposal-only additions. Native-Fc, mixed-solvent, unresolved-reference,
  polarization, structure-blocked, and paywalled rows remain separate or parked.

## Count Semantics

Directive combinations collapse onset and peak reports for the same canonical
monomer/solvent/electrolyte formulation and ignore concentration-only variants.
Current model groups keep onset and peak separate. All counts above are recomputed
from the generated CSV rows, not copied from prior reports.

## Review Tables

- `data/lit_curation/eox_g1_2_source_manifest.csv`
- `data/lit_curation/eox_g1_2_master_evidence.csv`
- `data/lit_curation/eox_g1_2_combination_summary.csv`
- `data/lit_curation/eox_g1_2_production_change_proposal.csv`

## Combination Snapshot

| status | count |
| --- | ---: |
| CURRENT_PRODUCTION_CORRECTION_REQUIRED | 10 |
| CURRENT_PRODUCTION_ELIGIBLE | 26 |
| MIXED_SOLVENT_PARKED | 8 |
| NEW_ELIGIBLE_PROPOSAL | 5 |
| NON_CV_METHOD_PARKED | 5 |
| PARKED | 4 |
| PROVENANCE_BLOCKED | 6 |
| REFERENCE_BLOCKED | 9 |
| REJECTED | 1 |
| SOURCE_CONFLICT_BLOCKED | 8 |
| STRUCTURE_BLOCKED | 1 |

## Guardrails

- No production ingest was performed.
- No branch was created or switched for this work unit.
- No Lop, xTB, Gaussian, ORCA, or other quantum engine was run.
- Production CSVs and configs are only read for hashing/counting.

# R11-R21 Eox staging-rescue review

This is a review-only curation package. No candidate was promoted into `data/benchmark.csv`.

## Provenance

- Repo SHA used: `a5ae41b972bbc05a5ff41a9f59150a41b520b154`
- Normalized source and optional external evidence inputs:
  - `eox_r11_r21_source_candidates.csv`: `03a09c06c2c3c0643994833a9a5107e323267879b844efc920b591cc3cfa9bfc` (`/Users/shichen/GitHub/CombHTS/data/lit_curation/eox_r11_r21_source_candidates.csv`)

Optional external reports are evidence/context inputs only; the normalized source-candidate CSV is the only machine-loaded candidate source.

## Counts

- Source rows: 11
- RDKit parsed rows: 11
- Internal duplicates: 0
- Production benchmark duplicates: 0
- Reference-source conflicts: 8
- Condition-source conflicts: 4
- Conversion checks passed: 11
- Canonical duplicate collapse: 11 raw rows -> 11 unique canonical structures (0 duplicate rows).
- Existing production groups: 16 onset; 23 peak.
- Promotable rescue groups: 3 onset; 0 peak.
- Projected union groups: 19 onset; 23 peak; 42 combined experimental combinations.
- Production benchmark structures: 29 unique; 7 current-library; 22 benchmark-only.
- Rescue structures: 11 unique; 0 current-library; 11 benchmark-only.

The combined experimental-combination inventory exceeds 30 only when peak and onset benchmarks are counted together. The onset-only projected union remains below 30, and the peak track is unchanged by this rescue package. Therefore this package does not close the Directive >=30 benchmark question by raw row count.
Numerically reproducible conversions are retained as audit transcriptions only; a source-internal reference or condition conflict keeps the affected row out of PROMOTE_NOW_CANDIDATE.

## Disposition

| record | class | RDKit | canonical SMILES | formula | conversion | reference conflict | condition conflict | production duplicate | blocker |
| --- | --- | :---: | --- | --- | :---: | :---: | :---: | :---: | --- |
| R11 | PROMOTE_NOW_CANDIDATE | True | `c1sc(-c2cnc(-c3scc4c3OCCO4)c3nsnc23)c2c1OCCO2` | NOT_PROVIDED | True | False | False | False | - |
| R12 | PROMOTE_NOW_CANDIDATE | True | `Cc1csc(-c2cnc(-c3cc(C)cs3)c3nsnc23)c1` | NOT_PROVIDED | True | False | False | False | - |
| R13 | PROMOTE_NOW_CANDIDATE | True | `CCCCc1csc(-c2cnc(-c3cc(CCCC)cs3)c3nsnc23)c1` | NOT_PROVIDED | True | False | False | False | - |
| R14 | NEEDS_REFERENCE_CHECK | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cccs4)cnc(-c4cccs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | True | False | False | source reference conflict unresolved: Section 2.3 reports Ag wire = 0.03 V vs SCE, whereas Table 2 footnote (b) uses a +0.02 V reference correction. |
| R15 | NEEDS_REFERENCE_CHECK | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(CCCC)cs4)cnc(-c4cc(CCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | True | False | False | source reference conflict unresolved: Section 2.3 reports Ag wire = 0.03 V vs SCE, whereas Table 2 footnote (b) uses a +0.02 V reference correction. |
| R16 | NEEDS_REFERENCE_CHECK | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(OCCCCCC)cs4)cnc(-c4cc(OCCCCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | True | False | False | source reference conflict unresolved: Section 2.3 reports Ag wire = 0.03 V vs SCE, whereas Table 2 footnote (b) uses a +0.02 V reference correction. |
| R17 | NEEDS_REFERENCE_CHECK | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4scc5c4OCCO5)cnc(-c4scc5c4OCCO5)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | True | False | False | source reference conflict unresolved: Section 2.3 reports Ag wire = 0.03 V vs SCE, whereas Table 2 footnote (b) uses a +0.02 V reference correction. |
| R18 | NEEDS_REFERENCE_CHECK | True | `COc1ccc(-c2nc3c(-c4scc5c4OCCO5)ccc(-c4scc5c4OCCO5)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | True | True | False | source reference conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M.; source condition conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M. |
| R19 | NEEDS_REFERENCE_CHECK | True | `COc1ccc(-c2nc3c(-c4sccc4OC)ccc(-c4sccc4OC)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | True | True | False | source reference conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M.; source condition conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M. |
| R20 | NEEDS_REFERENCE_CHECK | True | `COc1ccc(-c2nc3c(-c4sccc4C)ccc(-c4sccc4C)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | True | True | False | source reference conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M.; source condition conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M. |
| R21 | NEEDS_REFERENCE_CHECK | True | `COc1ccc(-c2nc3c(-c4cccs4)ccc(-c4cccs4)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | True | True | False | source reference conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M.; source condition conflict unresolved: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas Table 1 footnote (b) uses +0.02 V; Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1 caption reports 0.2 M. |

## Classification Counts

- PROMOTE_NOW_CANDIDATE: 3
- NEEDS_STRUCTURE_CHECK: 0
- NEEDS_PROVENANCE_CHECK: 0
- NEEDS_REFERENCE_CHECK: 8
- NEEDS_CONDITION_CHECK: 0
- DUPLICATE_PRODUCTION: 0
- REJECT: 0

## Human Review Recommendation

Review only the PROMOTE_NOW_CANDIDATE rows against the primary figures/schemes before any production ingest. Keep source-conflicted rows in staging until a later scientific decision resolves or excludes their internal reference/condition contradictions. If approved, ingest through a separate benchmark-promotion task that preserves onset labels and keeps peak/onset counts separate.

# R11-R21 Eox staging-rescue review

This is a review-only curation package. No candidate was promoted into `data/benchmark.csv`.

## Provenance

- Repo SHA used: `b9a2d26fb2231d37402c6a178b77d3076f4f9a49`
- External and normalized inputs:
  - `deep-research-report (4).md`: `60ac32f7d895ec282b5c5aed187aece85ff6e96d369a91d16ec0bc7dd7ebf202` (`/Users/shichen/Downloads/deep-research-report (4).md`)
  - `deep-research-report (8).md`: `5615c17dbe40bd974b5a896bdfa15b4acd295ce0c055330936c53e3a1f456aa3` (`/Users/shichen/Downloads/deep-research-report (8).md`)
  - `eox_r11_r21_source_candidates.csv`: `576611a6744df00ffc49aa35909df2c64b4e31dbf94903a74eb1b46f794cdba5` (`/Users/shichen/GitHub/CombHTS/data/lit_curation/eox_r11_r21_source_candidates.csv`)

External reports are evidence/context inputs; the normalized source-candidate CSV is the only machine-loaded candidate source.

## Counts

- Source rows: 11
- RDKit parsed rows: 11
- Conversion checks passed: 11
- Canonical duplicate collapse: 11 raw rows -> 11 unique canonical structures (0 duplicate rows).
- Existing production groups: 16 onset; 23 peak.
- Promotable rescue groups: 11 onset; 0 peak.
- Projected union groups: 27 onset; 23 peak; 50 combined experimental combinations.
- Production benchmark structures: 29 unique; 7 current-library; 22 benchmark-only.
- Rescue structures: 11 unique; 0 current-library; 11 benchmark-only.

The combined experimental-combination inventory exceeds 30 only when peak and onset benchmarks are counted together. The onset-only projected union remains below 30, and the peak track is unchanged by this rescue package. Therefore this package does not close the Directive >=30 benchmark question by raw row count.

## Disposition

| record | class | RDKit | canonical SMILES | formula | conversion | production duplicate | blocker |
| --- | --- | :---: | --- | --- | :---: | :---: | --- |
| R11 | PROMOTE_NOW_CANDIDATE | True | `c1sc(-c2cnc(-c3scc4c3OCCO4)c3nsnc23)c2c1OCCO2` | NOT_PROVIDED | True | False | - |
| R12 | PROMOTE_NOW_CANDIDATE | True | `Cc1cc(-c2cnc(-c3csc(C)c3)c3nsnc23)cs1` | NOT_PROVIDED | True | False | - |
| R13 | PROMOTE_NOW_CANDIDATE | True | `CCCCc1cc(-c2cnc(-c3csc(CCCC)c3)c3nsnc23)cs1` | NOT_PROVIDED | True | False | - |
| R14 | PROMOTE_NOW_CANDIDATE | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4ccsc4)cnc(-c4ccsc4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | False | - |
| R15 | PROMOTE_NOW_CANDIDATE | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(CCCC)c4)cnc(-c4csc(CCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | False | - |
| R16 | PROMOTE_NOW_CANDIDATE | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(OCCCCCC)c4)cnc(-c4csc(OCCCCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | False | - |
| R17 | PROMOTE_NOW_CANDIDATE | True | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4scc5c4OCCO5)cnc(-c4scc5c4OCCO5)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | TRUE | True | False | - |
| R18 | PROMOTE_NOW_CANDIDATE | True | `COc1ccc(-c2nc3c(-c4scc5c4OCCO5)ccc(-c4scc5c4OCCO5)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | False | - |
| R19 | PROMOTE_NOW_CANDIDATE | True | `COc1ccc(-c2nc3c(-c4sccc4OC)ccc(-c4sccc4OC)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | False | - |
| R20 | PROMOTE_NOW_CANDIDATE | True | `COc1ccc(-c2nc3c(-c4sccc4C)ccc(-c4sccc4C)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | False | - |
| R21 | PROMOTE_NOW_CANDIDATE | True | `COc1ccc(-c2nc3c(-c4ccsc4)ccc(-c4ccsc4)c3nc2-c2ccc(OC)cc2)cc1` | NOT_PROVIDED | True | False | - |

## Classification Counts

- PROMOTE_NOW_CANDIDATE: 11
- NEEDS_STRUCTURE_CHECK: 0
- NEEDS_PROVENANCE_CHECK: 0
- NEEDS_REFERENCE_CHECK: 0
- NEEDS_CONDITION_CHECK: 0
- DUPLICATE_PRODUCTION: 0
- REJECT: 0

## Human Review Recommendation

Review the PROMOTE_NOW_CANDIDATE rows against the primary figures/schemes before any production ingest. Give special attention to rows without source formula/HRMS evidence, because those are supported by the recorded structure/source locators and NMR-only text rather than a machine-checkable formula line. If approved, ingest through a separate benchmark-promotion task that preserves onset labels and keeps peak/onset counts separate.

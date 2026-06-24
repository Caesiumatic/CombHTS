# R11-R21 primary-PDF correction memo

Date: 2026-06-24

## Scope

This memo records manual inspection of the three primary articles and two Supporting Information
files behind the review-only R11-R21 Eox staging package. It corrects source transcriptions used for
review staging only. No production benchmark row, library row, config value, scoring rule, or engine
workflow was changed.

## Corrected Structures

The manual audit found six thiophene donor attachment errors. The old structures attached the
acceptor core through a beta thiophene carbon. The systematic names and reaction schemes require
thiophen-2-yl donors, meaning the acceptor core is attached through the alpha carbon directly
adjacent to sulfur.

| record | old input SMILES | corrected input SMILES |
| --- | --- | --- |
| R12 | `Cc1cc(-c2cnc(-c3csc(C)c3)c3nsnc23)cs1` | `Cc1csc(-c2cnc(-c3cc(C)cs3)c3nsnc23)c1` |
| R13 | `CCCCc1cc(-c2cnc(-c3csc(CCCC)c3)c3nsnc23)cs1` | `CCCCc1csc(-c2cnc(-c3cc(CCCC)cs3)c3nsnc23)c1` |
| R14 | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4ccsc4)cnc(-c4ccsc4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cccs4)cnc(-c4cccs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` |
| R15 | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(CCCC)c4)cnc(-c4csc(CCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(CCCC)cs4)cnc(-c4cc(CCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` |
| R16 | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4csc(OCCCCCC)c4)cnc(-c4csc(OCCCCCC)c4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` | `CCCCCCCCCCOc1ccc(-c2nc3c(-c4cc(OCCCCCC)cs4)cnc(-c4cc(OCCCCCC)cs4)c3nc2-c2ccc(OCCCCCCCCCC)cc2)cc1` |
| R21 | `COc1ccc(-c2nc3c(-c4ccsc4)ccc(-c4ccsc4)c3nc2-c2ccc(OC)cc2)cc1` | `COc1ccc(-c2nc3c(-c4cccs4)ccc(-c4cccs4)c3nc2-c2ccc(OC)cc2)cc1` |

## Structure Disposition

| record | disposition |
| --- | --- |
| R11 | Structure retained; no source-internal conflict recorded. |
| R12 | Corrected to 4-methylthiophen-2-yl connectivity; no source-internal conflict recorded. |
| R13 | Corrected to 4-butylthiophen-2-yl connectivity; no source-internal conflict recorded. |
| R14 | Corrected to thiophen-2-yl connectivity; reference-source conflict recorded. |
| R15 | Corrected to 4-butylthiophen-2-yl connectivity; reference-source conflict recorded. |
| R16 | Corrected to 4-hexyloxythiophen-2-yl connectivity; reference-source conflict recorded. |
| R17 | Structure retained; reference-source conflict recorded. |
| R18 | Structure retained; reference-source and condition-source conflicts recorded. |
| R19 | Structure retained; reference-source and condition-source conflicts recorded. |
| R20 | Structure retained; reference-source and condition-source conflicts recorded. |
| R21 | Corrected to thiophen-2-yl connectivity; reference-source and condition-source conflicts recorded. |

## Source Conflicts

R14-R17 have a reference-source conflict: Section 2.3 reports Ag wire = 0.03 V vs SCE, whereas
Table 2 footnote (b) uses a +0.02 V reference correction.

R18-R21 have a reference-source conflict: Figure 1 caption reports Ag wire = 0.03 V vs SCE, whereas
Table 1 footnote (b) uses +0.02 V.

R18-R21 also have a condition-source conflict: Section 3.1 reports 0.1 M TBAPF6, whereas Figure 1
caption reports 0.2 M.

No source conflict was silently resolved. The current raw Eonset values, working converted
potentials, and working electrolyte concentrations were retained as unresolved audit
transcriptions only. No row was promoted into `data/benchmark.csv`, and the PDFs themselves were not
committed.

## Updated Counts

- 3 promotable onset candidates.
- 8 source-conflicted candidates.
- Projected onset union: 19 groups.
- Existing/union peak groups: 23.
- Combined experimental-combination inventory: 42.

## Next Action

A later scientific decision must resolve or exclude the conflicted R14-R21 records before any
production benchmark ingest. Until then, the conflicted rows remain review-only staging records and
are ineligible for `PROMOTE_NOW_CANDIDATE`.

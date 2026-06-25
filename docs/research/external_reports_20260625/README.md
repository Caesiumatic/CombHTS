# External research reports — director ingest 2026-06-25

Verbatim archive of the deep-research reports + mentor material handed to the director run on
2026-06-25, committed so the chat / codex / Lop parties all see one copy via git. Each file is
the **as-received** report; the repo's own curated/refined docs and CSVs are the actionable
derivatives and live elsewhere (cross-referenced below).

| # | archived file | content | repo counterpart / status |
|---|---|---|---|
| 01 | `01_eox_calibration_table_primary_sourced_partD.md` | Primary-sourced monomer Eox calibration table (onset + peak/reversible tracks; Camarada thiophene onsets, carbazole reversible E° series) | refines [`eox_anchor_refscale_accuracy_partD.md`](../eox_anchor_refscale_accuracy_partD.md); calibration anchors feed `configs/calibration_profiles.yaml` |
| 02 | `02_feasibility_labels_binary_validation_set.md` | YES/NO electropolymerization feasibility validation set + 9 matched pairs + 3 NO-mechanism families | **canonical table = 36 rows / 19 YES / 17 NO** → [`data/lit_curation/feasibility_labels_canonical_36row.csv`](../../../data/lit_curation/feasibility_labels_canonical_36row.csv); report prose "34-row" is stale (see [`feasibility_reconcile_20260625.md`](../feasibility_reconcile_20260625.md)) |
| 03 | `03_optical_bandgap_anchors.md` | ~30 neutral π–π* optical-gap anchors across 9 classes (neutral-state, onset-derived) | optical calibration plan [`docs/lit_curation/optical_calibration_plan.md`](../../lit_curation/optical_calibration_plan.md); gate ③ (sTDA-xTB) |
| 04 | `04_esw_solvent_windows_reference.md` | Practical ESW windows for nonaqueous solvent+TBA systems (Ue 1994 anchor); NMP/nitrobenzene/DMSO/THF/sulfolane gaps | `data/solvent_windows.csv`; gate ① (measured window as conservative cap) |
| 05 | `05_eox_anchor_refscale_accuracy_resolution.md` | Resolves Eox anchor (peak-for-calibration / onset-for-screening), Ag/AgCl master scale, **honest MAE 0.20–0.35 V floor** | gate ② accuracy floor; the authoritative argument that <0.15 V is physically unreachable |
| 06 | `06_al_benchmark_feasibility_inventory.md` | Retrospective active-learning benchmark + data inventory (PANDA, cortisol e-MIP, OMG, Polybot) for downstream ML/AL | downstream (per-species descriptor table is the durable product fed to AL/ML); no current code dependency |
| 07 | *(pointer — NOT committed)* `DirectiveLit_OMIEC_Electropolymerization_Review.pdf` (24 MB) | OMIEC electropolymerization review (Gerasimov et al., *Chem. Rev.* 2025, DOI 10.1021/acs.chemrev.5c00183), 52 pp | **binary kept out of git history** (size + published-article redistribution); local copy at `~/Downloads/CombHTS files/`. Add via git-LFS only if the PI wants it tracked — see `DECISIONS_PENDING.md` |
| 08 | `08_mentors_info_sharing.md` | Mentor (Jingdan / Seonghwan) resource pointers: reactivity-ratio ML, BO+DFT, generative polymer ML, AI4Chem tutorials | reference for the downstream ML/generative direction |

**Decision gate cross-reference:** ① ESW physics wall ← 04; ② Eox accuracy floor ← 05; ③ band-gap
route ← 03. See `THINK.md` for the dialectics and `DECISIONS_PENDING.md` for the PI checklist.

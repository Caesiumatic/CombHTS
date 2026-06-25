# Research Ingest Audit — 2026-06-25

**Scope:** Review-only curation (Directive Section 7). Four primary-literature deliverables were
parsed into NEW staging + quarantine + review tables under `data/lit_curation/`. **Nothing is
promoted.** No production CSV, config, or scoring file was edited. This document is a review
artifact; every staged row still requires human sign-off before any promotion.

**Master-scale convention:** all numeric potentials are on the repo's Ag/AgCl (sat'd KCl) master
scale. Original reported values (with their native reference scale) are preserved verbatim in the
`*_orig_V` / `value_reported` columns; the `*_vs_AgAgCl_V` columns carry the source's already-
converted master-scale numbers (sign/`+` normalized to ASCII only — magnitudes untouched).
Confidence flags, conversion notes, and track/observable labels are carried through unchanged.
Missing fields are left blank (no invention, no re-derivation).

**Reproducer:** `data/lit_curation/build_research_ingest_20260625.py` (parses the four source
markdown tables directly, canonicalizes with RDKit, routes quarantine, and emits the dedup review).

---

## 1. Per-file row counts (clean vs quarantine) and RDKit pass/fail

| Source | Staging file (clean) | Clean rows | Quarantine file | Quar rows | RDKit (clean) |
|---|---|---|---|---|---|
| research1 — ESW windows | `esw_windows_staging_20260625.csv` | 12 | — (no SMILES in source) | 0 | n/a (no SMILES) |
| research2 — Eox calibration | `eox_calibration_staging_20260625.csv` | 11 | `eox_calibration_quarantine_20260625.csv` | 2 | 11/11 parse, 0 fail |
| research3 — feasibility | `feasibility_labels_staging_20260625.csv` | 32 | `feasibility_quarantine_20260625.csv` | 4 | 32/32 parse, 0 fail |
| research4 — optical anchors | `optical_anchors_staging_20260625.csv` | **0** | `optical_anchors_quarantine_20260625.csv` | 31 | 0 clean (see §4) |

Quarantine reason breakdown:

- **research2 (2):** `selenophene_se_token_toolkit_check` ×2 — Selenophene (`c1cc[se]c1`), EDOS
  (`C1COc2cc[se]c2O1`). Both parse in this RDKit build but carry the aromatic `[se]` token the
  source flagged as toolkit-sensitive, so they are held for cheminformatics-stack confirmation.
- **research3 (4):** `hand_constructed_smiles` ×2 (EDOT-flanked trimer; An-EDOT-An) +
  `selenophene_se_token_toolkit_check` ×2 (selenophene NO/YES pair).
- **research4 (31):** `star_attachment_repeat_unit` ×20, `rdkit_parse_failed` ×6
  (descriptive non-SMILES like "(BDT–thienothiophene D–A repeat)", and the F8BT alternating-repeat
  approximation which fails to kekulize), `selenophene_se_token_toolkit_check` ×5.

All SMILES that reach a **clean** staging file parse and canonicalize; failures/flags are isolated
in the quarantine files with an explicit `quarantine_reason`.

---

## 2. Feasibility NEW / DUPLICATE / CONFLICT reconciliation (vs production)

Compared `feasibility_labels_staging` (all 36 source-table rows, incl. the 4 quarantined) against
the **unmodified** production `data/polymerizability_labels.csv` by canonical SMILES + normalized
solvent medium, then outcome. Review table: `feasibility_dedup_review_20260625.csv` (read-only).

| Status | Count |
|---|---|
| NEW | 27 |
| DUPLICATE | 7 |
| CONFLICT | 2 |

- **DUPLICATE (7):** Furan/NO·MeCN, 3,4-dimethoxythiophene/YES·MeCN, terthiophene/YES·MeCN,
  3-methylthiophene/YES·MeCN, EDOT/YES·MeCN, carbazole/YES·MeCN, aniline/NO·MeCN. (Same
  monomer + medium + outcome already in production; electrolyte/electrode may still differ — not
  merged.)
- **CONFLICT (2):** **Aniline YES** in `MeCN + acid` and in `aqueous H₂SO₄` vs production
  **aniline NO** at the same coarse medium token (MeCN-neutral / H₂O-neutral). This is a genuine
  *condition-distinguished* conflict (acidic vs neutral medium), not a contradiction — exactly the
  kind of row that must not be auto-merged. Human review must decide whether the production neutral-
  medium NO and the staged acidic-medium YES are kept as distinct conditioned rows.
- **Structure-check flags (subset of NEW):** `3-ethylcarbazole`, `3,6-di-tert-butylcarbazole`, and
  `3,6-diphenylcarbazole` carry the same trivial names as existing production rows but their source
  SMILES **canonicalize differently** from production's (positional isomer drawn differently). They
  are reported NEW with a `note` flagging a structure check; once the structures are reconciled they
  are likely DUPLICATE (carbazoles) — do **not** promote until the SMILES discrepancy is resolved.
- **Normalization caveat:** pyrrole's source cell "MeCN or aqueous" collapses to one medium token in
  the review; production has pyrrole/YES in MeCN. The row is reported NEW (medium = aqueous) with a
  detail line naming the production MeCN coverage. A human should treat the MeCN portion as duplicate.

---

## 3. Eox calibration track breakdown (clean staging)

Tracks are kept strictly separate per the source (onset / peak / reversible formal E° must never be
pooled). Clean staging = 11 rows:

| Track | Count | Rows |
|---|---|---|
| `onset` | 4 | thiophene 1.50, bithiophene 1.15, terthiophene 0.880, carbazole 1.095 |
| `reversible_formal_E` | 4 | 9-ethyl 1.21, 9-butyl 1.19, 9-hexyl 1.16, 9-octyl 1.11 carbazole |
| `peak` | 3 | N-vinylcarbazole 1.345 (usable); **furan & 2-methylfuran are EXCLUDED placeholders** |

- The two furan rows are retained on the `peak` track only to preserve the source's exclusion record:
  `confidence = excl`, `value_vs_AgAgCl_V` blank, conversion note "EXCLUDED — bare Ag/Ag⁺, not
  convertible". They are **not** usable calibration anchors. Net usable peak-track rows: **1**
  (N-vinylcarbazole).
- Quarantined onset anchors (held for `[se]` toolkit check, value preserved): selenophene 1.645,
  EDOS 1.135.

---

## 4. Optical anchors — per-class counts (all quarantined)

The research4 source provides **repeat-unit** SMILES with `*` attachment points (or descriptive
text, or `[se]`) for every row. Per the ingest quarantine policy, every such row is routed to
quarantine, so the **clean optical staging file has 0 rows** and all 31 anchors sit in
`optical_anchors_quarantine_20260625.csv` with provenance (`optical_gap_eV`, `derivation`,
`film_state_neutral_confirmed`, `chemical_class`, `confidence`) intact. No monomer SMILES was
invented to "rescue" these rows.

Per-class anchor counts (quarantined):

| Class | n | Class | n |
|---|---|---|---|
| polythiophene | 6 | polypyrrole | 2 |
| dioxythiophene (PEDOT family) | 4 | polyfuran | 2 |
| dioxypyrrole | 3 | D–A (fluorinated BT) | 2 |
| polyselenophene | 3 | polyfluorene | 1 |
| dioxyselenophene (PEDOS) | 2 | polyfluorene D–A | 1 |
| poly(2,7-carbazole) | 1 | polycarbazole (pendant, PVK) | 1 |
| D–A (carbazole, PCDTBT) | 1 | D–A (CPDT, PCPDTBT) | 1 |
| D–A (benzodithiophene, PTB7) | 1 | | |

These remain useful as a calibration *target list*, but cannot enter staging-clean until a human
supplies canonical monomer (or sanitized repeat-unit) SMILES and confirms neutral film-state.

---

## 5. ESW coverage additions vs remaining gaps

Newly staged solvent + supporting-electrolyte windows (12 rows, all on baseline nonaqueous /
tetraalkylammonium chemistry where the source provided it):

- **Propylene carbonate** × {TBABF4, TBAPF6, TBAClO4, TBATFSI} (Ue 1994 via Gong 2015; med)
- **Acetonitrile** × {TBAPF6 (Elgrishi, onset-style), Et4NBF4 (Ue)}
- **Nitromethane** × {Et4NBF4 (Ue; med-high), Mg(ClO4)₂ (Voorhies & Schurdak)}
- **γ-Butyrolactone** × Et4NBF4 (low-med; flagged as an implausibly wide 8.2 V outlier in source)
- **Benzonitrile** × TBAP
- **DMF** × TBAClO4 (cathodic-only; anodic blank, reference unclear — low)

**STILL GAP (no clean primary window staged):** **NMP, nitrobenzene, DMSO, THF, sulfolane** — all
five priority pairs remain unstaged, consistent with research1's own conclusion (only Li/Li⁺-
referenced battery CVs, IL media, or analyte studies were available; none with a tetraalkylammonium
salt **and** a convertible reference).

---

## 6. Staging audit results (machinery)

Ran `eps.curation.staging_audit.audit_staging(..., specs=RESEARCH_INGEST_20260625_SPECS)` over the
four new clean staging files (review artifacts: `research_ingest_audit_summary_20260625.csv`,
`research_ingest_audit_issues_20260625.csv`).

| File | rows | columns_ok | rdkit_valid | rdkit_invalid | internal_dup | production_dup |
|---|---|---|---|---|---|---|
| esw_windows | 12 | ✅ | 0 (no SMILES) | 0 | 0 | 0 |
| eox_calibration | 11 | ✅ | 11 | 0 | 0 | 0 |
| feasibility_labels | 32 | ✅ | 32 | 0 | 0 | 0 |
| optical_anchors | 0 | ✅ | 0 | 0 | 0 | 0 |

- Schema registration is **additive**: a new `RESEARCH_INGEST_20260625_SPECS` tuple plus an optional
  `specs=` argument on `audit_staging`. The established `STAGING_SPECS` surface (and its
  production-touching classification/duplicate logic) is **unchanged**; existing curation tests still
  pass (5-file surface intact).
- New dated files fall through to the generic `PARK` classification in the audit (they are not wired
  into the production-duplicate dispatch by design). Production reconciliation for feasibility is
  handled rigorously and separately in §2.
- `eps doctor` passes (21 checks, 0 FAIL, 4 cluster-only WARN) but **does not cover staging** — it is
  an environment/config health check, not a curation validator.
- Tests: `tests/test_research_ingest_audit_20260625.py` added; full suite green; `ruff check src
  tests` clean.

---

## 7. STILL GAP / NEEDS HUMAN SIGN-OFF BEFORE PROMOTION

Nothing here is promoted. Before any production promotion, a human curator must sign off on:

1. **Selenophene / EDOS / selenophene-polymer rows** (quarantined `[se]`): confirm the aromatic
   `[se]` SMILES against the production cheminformatics stack (`[se]` vs explicit-ring `[Se]`) before
   any Eox/feasibility/optical use.
2. **Hand-constructed feasibility SMILES** (EDOT-flanked trimer; An-EDOT-An): valence/structure
   verification required; the An-EDOT-An baseline electrolyte/electrode for the *failed* attempt is
   not in the source abstract.
3. **Carbazole-derivative SMILES discrepancies** (3-ethyl-, 3,6-di-tert-butyl-, 3,6-diphenyl-
   carbazole): reconcile staged SMILES vs production SMILES (positional isomers) before treating as
   DUPLICATE.
4. **Aniline acid-vs-neutral CONFLICTs (×2):** decide the conditioned-row policy; do not overwrite
   production neutral-medium NO.
5. **Feasibility row-count discrepancy:** the source table contains **36** rows (YES 19 / NO 17), but
   the source prose states 34 (YES 16 / NO 18). The 36 table rows were staged faithfully; the
   discrepancy needs a human read of the primary deliverable before counting.
6. **`baseline_medium` flags:** auto-derived (clean: 25 TRUE / 7 FALSE; all 36: 27 TRUE / 9 FALSE);
   borderline cases (e.g. thiophene on SnO₂; pyrrole "MeCN or aqueous") need human confirmation.
7. **Eox peak track:** only N-vinylcarbazole is a usable peak anchor; furan/2-methylfuran are
   exclusion placeholders, not data. Several priority small monomers (pyrrole, 3-methylthiophene,
   3-hexylthiophene, ProDOT, EDOT clean Epa, etc.) remain explicit Eox gaps per research2.
8. **ESW gaps:** NMP, nitrobenzene, DMSO, THF, sulfolane still need dedicated blank-CV primary
   windows; GBL/Et4NBF4 (+5.2 V outlier) and the DMF cathodic-only rows are low-confidence.
9. **Optical anchors (all 31 quarantined):** require human-supplied canonical monomer SMILES and
   neutral film-state confirmation before any could enter staging-clean.

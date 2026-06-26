# Feasibility-label reconciliation: canonical 36-row vs production vs staged

_2026-06-25 · director autonomous run · decidable curation/QA, no production scoring change_

## Decision (per PI/user, 2026-06-25)

The **canonical 36-row feasibility table is the single source of truth** for the qualitative
electropolymerization feasibility validation set and for the B1 coupling-feasibility diagnostic.
It is ingested verbatim at
[`data/lit_curation/feasibility_labels_canonical_36row.csv`](../../data/lit_curation/feasibility_labels_canonical_36row.csv).

- **Canonical = 36 rows = 19 YES / 17 NO** (verified by row count + tally, not by the report prose).
- The feasibility deep-research report's own TL;DR / Counts text ("34 rows / 16 YES / 18 NO") is a
  **stale self-summary of an earlier draft and is void**; the markdown *table* is authoritative.
- The production [`data/polymerizability_labels.csv`](../../data/polymerizability_labels.csv)
  (34 rows / 18 YES / 16 NO) is an **earlier, superseded ingest**, kept only as a diff target.
- The staged branch `curate/research-ingest-20260625` 32/33-row expansion is **work-in-progress**,
  recorded but not authoritative.

## Canonical vs production — set-level diff

| | canonical-36 | production-34 |
|---|---|---|
| rows | 36 | 34 |
| YES / NO | 19 / 17 | 18 / 16 |
| unique monomers (by canonical SMILES) | 27 | 30 |

These are **genuinely different curations**, not a count bump: only a partial monomer overlap.

**In production but NOT in canonical (21 monomers)** — an older/broader ingest, several useful
(triphenylamine, tris(4-methoxyphenyl)amine, tris(4-bromophenyl)amine, 2,5-dimethylthiophene,
N-phenylpyrrole, 3-phenylcarbazole, 3-tert-butylcarbazole, 2,3-benzofuran, o-toluidine,
N-methylpyrrole, N-vinylcarbazole, EDOP, EDOS, 3-hexylthiophene, 3-methoxythiophene), a few
low-quality (`9-fluorenylidene-dianiline (FDA)` and `ProDOP-br-C3` have **empty SMILES**). These
are **candidate future additions** to the canonical set, each needing a primary source — not
silently merged.

**In canonical but NOT in production (17 monomers)** — the report's net-new feasibility evidence,
including all 7 intrinsic-NO anchors (3-thiophenecarboxaldehyde, 3,4-dibutylthiophene,
3,6-di-tert-butylcarbazole, 3,6-diphenylcarbazole, N-phenylcarbazole, 1-aminopyrene,
2,5-dimethylpyrrole) plus YES comparators (bithiophene, 2,7-diaminofluorene, 2-methylfuran, DMOT,
3-ethylcarbazole, fluorene, pyrene, the EDOT–CHO–EDOT trimer) and the An-EDOT-An / diphenylbenzidine
condition-specific NOs.

**Outcome conflicts on shared (monomer, solvent):** none genuine. The lone apparent aniline flip
(prod NO vs canonical YES in "MeCN") is a solvent-prefix matching artifact — canonical correctly
separates **aniline/MeCN-neutral = NO** from **aniline/MeCN+acid = YES**.

## Structural QA finding — production carbazole SMILES are WRONG (canonical are correct)

Three carbon-substituted carbazoles appear in both sets with **different InChIKeys** (different
molecules). Topological position assignment (distance of the substituent-bearing aromatic carbon to
the ring N; carbazole position 3 = the para position in the benzo ring = **distance 4** from N)
resolves it unambiguously:

| compound | production SMILES → position | canonical SMILES → position | correct (3,6)? |
|---|---|---|---|
| 3-ethylcarbazole | dist 3 → **pos 2** | dist 4 → **pos 3** | **canonical** |
| 3,6-di-tert-butylcarbazole | dist 3 → **pos 2/7** | dist 4 → **pos 3/6** | **canonical** |
| 3,6-diphenylcarbazole | dist 3 → **pos 2/7** | dist 4 → **pos 3/6** | **canonical** |

So the **canonical report's carbazole SMILES are the structurally correct 3,6-isomers**, and the
production CSV's are mis-placed (position 2/4). This is an independent, third reason production is
superseded, and it confirms the directive §4 note that the canonical-report carbazoles are
"verified correct at 3/6" (the verification refers to the report, not the old production CSV).
Carbazole electropolymerization couples at 3,6; using the production (pos-2/4) structures would
have mis-modelled the coupling chemistry. **B1 used the canonical SMILES throughout**, so the B1
carbazole-class conclusion is unaffected.

## Actions taken / pending

- [x] Canonical 36-row CSV ingested as source of truth (this commit).
- [x] B1 diagnostic uses canonical SMILES + the 7 intrinsic-NO subset (NO_type = `intrinsic`).
- [x] **Done 2026-06-25:** corrected all **six** wrong production carbazole SMILES (3-ethyl,
  3-tert-butyl, 3-phenyl, 3,6-diethyl, 3,6-di-tert-butyl, 3,6-diphenyl) from position 2/4 → 3/6
  (verified at distance-4 from the ring N); `flags` column annotated. The error was systematic across
  every substituted carbazole in the generator.
- [ ] **Pending (PI):** whether to retire the production CSV in favor of canonical-36, and which
  production-only monomers (triphenylamine, tris-amines, …) to fold into a future expanded set with
  primary sources. See `DECISIONS_PENDING.md` B4.

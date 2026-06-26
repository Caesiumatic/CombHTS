# Decisions pending — human / PI checklist

_Created 2026-06-25 (director autonomous run). Read this first. One line per decision: what to
decide · the recommendation · why it needs a human. Full dialectics are in `THINK.md` (T-entries);
evidence is in `docs/research/`. Nothing here was executed unilaterally._

Governance: per `THINK.md` "How to read", the directive is the PI's delegated authority — sound,
directive-faithful calls are decide-and-report (PI veto via the group cadence). Items below are the
ones that are genuine **value / scope / resource / sign-off** calls, not correctness calls.

## A. The three directive decision gates (group-meeting material)

| Gate | Question | Status in repo | Recommendation | Why human |
|---|---|---|---|---|
| **① ESW physics wall** | Isolated-molecule ΔSCF cannot compute a real electrochemical window (audit: anodic MAE 5.4 V / cathodic 3.8 V vs measured). | **Decided & implemented** as measured-first-conservative cap (`THINK` T14); §6 audit reconfirmed the raw descriptor must stay an audited prior, not the window. | Keep measured window as conservative upper bound; treat the directive §3.2 *literal* ΔSCF-window as physically unachievable. | **Deviates from directive §3.2 literal** — PI should acknowledge the deviation (it serves the goal; veto via cadence). |
| **② Accuracy floor** | Directive §8 wants Tier-2 Eox MAE < 0.15 V. | **Decided** (`THINK` T3): physically unreachable; honest band **0.20–0.35 V**, hard floor 0.15 V. Active Tier-1 profile = 0.186 V LOO-CV (passes the <0.30 V gate). | Adopt 0.20–0.35 V language; never claim <0.15 V. | PI should accept that the §8 <0.15 V target is **retired as physically impossible** (literature-argued in report 05). |
| **③ Band-gap route** | sTDA-xTB vs ML/GNN for the optical gap. | sTDA-xTB chosen (directive §3.1/§4.1-faithful); `THINK` T6. **Caveat:** production currently uses the HOMO-LUMO hexamer *fallback* because `stda` is absent on Lop, and the 15% optical axis is diagnostic (weak fits). | Stay on sTDA-xTB now; keep ML/GNN as a future enhancement (sTDA-xTB is documented-weak on low-gap D–A). | Resource/scope: installing `stda` on Lop, and any future ML/GNN pivot, are PI calls. |

## B. New decisions from this run

1. **B4 — coupling-feasibility flag: soft vs hard.** *Recommend:* implement a config-driven **soft**
   `coupling_risk_flag` (does not drop survivors); keep any **hard** reject for PI. *Why human:* a hard
   reject removes Tier-1 survivors — a scope call. (`THINK` T15; B1 evidence pending SGE 417845.)
2. **Reorganization energy λ — wire it or not.** Directive §3.2 wants λ *used*; it is currently
   report-only (the audit's most directive-divergent finding). *Recommend:* publish a λ-vs-feasibility
   diagnostic, then add λ as a *reported / lightly-weighted soft term* — **not** a hard filter (GFN2
   λ is noisy). *Why human:* any weight change reshapes ranking → group/PI + a fresh harvest. (`THINK` T16.)
3. **Calibration strict vs relaxed + active-calibration manifest.** Production Tier-1 uses
   `agagcl_peak_strict`; `eps validate` defaults to `agagcl_peak_relaxed`. *Recommend:* publish an
   active-calibration manifest (decidable, doing it), then decide strict-vs-relaxed from the recorded
   DFT 417442 Fit-2 LOO-CV. *Why human:* the choice reshapes the window filter + 0.30-weight axis. (`THINK` T1.)
4. **Feasibility set reconciliation.** Canonical 36-row is now source of truth. Production
   `polymerizability_labels.csv` (34) had **six wrong carbazole SMILES** (substituent at position 2/4,
   not 3,6) — a systematic generator error; **all six CORRECTED 2026-06-25** (3-ethyl, 3-tert-butyl,
   3-phenyl, 3,6-diethyl, 3,6-di-tert-butyl, 3,6-diphenyl; verified at distance-4 = pos 3/6). *Remaining
   PI part:* whether to retire production in favor of canonical-36, and which production-only monomers
   (triphenylamine, tris-amines, …) to fold into a future expanded set with primary sources.

## C. Standing sign-offs / no-go's

5. **Promote staged research → production.** The Phase-1A staged branch
   `curate/research-ingest-20260625` (ESW / Eox / optical / feasibility curation) remains **staged, not
   merged**. The canonical-36 feasibility CSV was ingested as source-of-truth, but the broader ESW/Eox/
   optical promotions need **provenance + PI sign-off** before production ingest. Not auto-promoted.
6. **The two §0 full-scale actions are NOT to be launched without a "methods frozen" confirmation:**
   (i) the full ~50,000-triad Tier-1 harvest, (ii) the full-survivor Tier-2 DFT batch. A code
   **scale guardrail** now blocks both unless `--allow-large-scale` is passed (commit `6aca1be`).
7. **Method freeze itself** (the irreversible freeze-then-scale step) is a **PI action**. This run is
   *preparing* freeze readiness (assembling calibration/solvation/optical, running the validations it
   can), not executing it. See the freeze-readiness summary in `STATUS.md` / `THINK` (pending T17).
8. **Library expansion to directive scale** (~80–150 monomers × 25–35 solvents × 20–30 salts ≈ 50k)
   is a **resource/scope** call (`THINK` T8), gated on stable ESW/solubility/optical evidence.
9. **External dependencies (UPDATED 2026-06-25 per Lop admin):** (a) `stda`/`xtb4stda` — admin confirmed
   users may install into `$HOME` and submit from there; build tools (gfortran/gcc/cmake/make) are present,
   36 TB free home. → **now an in-progress engineering task** (install + real sTDA-xTB smoke), no longer an
   external blocker. (b) **COSMOtherm is NOT licensed on the cluster** → commercial COSMO-RS is out; the
   only true-solubility path is **openCOSMO-RS via ORCA 6.1 (open-source, already on Lop)**, with the
   ΔGsolv ALPB affinity proxy as the documented fallback. PI/resource call: how far to push the
   openCOSMO-RS solvent-profile expansion (PC/NMP σ-profiles were deferred in the pilot).
10. **OMIEC review PDF (24 MB)** kept out of git history (size + published-article redistribution);
    pointer in `docs/research/external_reports_20260625/README.md`. Add via git-LFS only if you want it tracked.

## D. Already decided autonomously this run (reported, not asking)

- Canonical-36 feasibility set ingested as source of truth; reconcile documented.
- 8 external reports archived + indexed; §1–§9 code audit run and saved.
- Scale guardrail implemented + tested (protects §0 actions).
- B1 diagnostic from existing data + size-matched batch launched (417845); B1/λ dialectics written.
- No production scoring weight / threshold / calibration coefficient / redox constant / cache key /
  filter / library / harvest was changed.

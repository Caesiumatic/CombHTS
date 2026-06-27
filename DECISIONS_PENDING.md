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
| **③ Band-gap route** | sTDA-xTB vs ML/GNN for the optical gap. | sTDA-xTB chosen (directive §3.1/§4.1-faithful); `THINK` T6. **UPDATED 2026-06-26:** `stda`+`xtb4stda` installed on Lop, engine fixed, all 36 monomers re-harvested with REAL sTDA-xTB (HOMO-LUMO fallback fully retired, SGE 417866). Hexamer-vs-experiment calibration (8 anchors) → **stays 15% diagnostic**: LOO-CV 0.30 eV > ±0.2 eV anchor floor; every class is a singleton so per-class offsets are not estimable. | Stay on sTDA-xTB diagnostic now; graduation requires ≥3 anchors/class (curation, not compute); keep ML/GNN as future (sTDA-xTB documented-weak on low-gap D–A). | Resource/scope: anchor-density curation + any future ML/GNN pivot are PI calls. |

## B. New decisions from this run

1. **B4 — coupling-feasibility flag: soft vs hard.** *Recommend:* implement a config-driven **soft**
   `coupling_risk_flag` (does not drop survivors); keep any **hard** reject for PI. *Why human:* a hard
   reject removes Tier-1 survivors — a scope call. (`THINK` T15; B1 evidence pending SGE 417845.)
2. **Reorganization energy λ — wire it or not. RESOLVED 2026-06-26 (decide-and-report): NO.** The
   λ-vs-feasibility diagnostic is now closed on a full **n=29** set (the intrinsic-NO monomers, previously
   absent from the library, were computed on Lop — SGE 417946): YES mean λ_ox **0.195 eV** vs intrinsic-NO
   **0.081 eV** — *no separation* (AUC 0.24, fully overlapping; weak signal in the WRONG direction for a
   barrier filter). Mechanism is steric coupling-site blocking (THINK T15), which an electronic
   vertical−adiabatic IP is physically blind to. **λ_ox stays report-only** (legitimate as a
   charge-transport descriptor, not feasibility); no `scoring.yaml` change, no fresh harvest. This
   SUPERSEDES the earlier "lightly-weighted soft term" recommendation. The genuinely feasibility-relevant
   electronic descriptor is the cation spin at coupling sites — currently broken by a spin-density cache
   NOT-NULL bug (separate fix). Evidence `docs/research/lambda_feasibility_diagnostic_20260626.md`. (`THINK` T16.)
3. **Calibration strict vs relaxed — RESOLVED 2026-06-26: STRICT.** Re-validated on the current
   benchmark with real GFN2-xTB (SGE 417876): strict (tier A, n=9) LOO-CV **0.197 V** / R² 0.889 / ρ
   0.833 beats relaxed (A+B, n=23) LOO 0.232 V / R² 0.508 / ρ 0.663 on every metric; DFT 417442
   composed line corroborates (max |Δ| 0.087 V). Production `tier1.yaml` **already pins the strict
   coefficients** (0.725837 / −3.145372) — no production change. *Remaining PI part (one calibration-
   freeze action):* flip `configs/calibration_profiles.yaml` `default_screening_profile`
   relaxed→strict to remove the validate-default label inconsistency (`configs/CALIBRATION_ACTIVE.md`).
   Not executed because changing the default profile is a calibration-freeze call.
   Evidence `docs/research/eox_strict_vs_relaxed_loocv_20260626.md`. (`THINK` T1.)
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

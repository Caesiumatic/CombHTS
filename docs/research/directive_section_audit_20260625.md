# CombHTS Electropolymerization Screening — Lead Auditor Synthesis Report

**Date:** 2026-06-25 · **Scope:** Directive sections 1–9, 9 audit units · **Auditor synthesis:** cross-section reconciliation of raw unit findings

---

## 1. Executive summary

- **The hard-constraint gates are real and wired.** Monomer Eox-in-window (`src/eps/workflow/tier1.py:716`, threshold 0.3 V), anion oxidation stability (`tier1.py:717-718`, 0.2 V margin), solvation, and supporting-electrolyte role are all in the `passes_all_tier1_filters` AND chain (`tier1.py:737-742`). This contradicts any assumption that the gates are aspirational — they are live.
- **The five composite-score terms are live, normalized, and non-degenerate.** Weights sum to 1.0 (`configs/scoring.yaml:1-6`), min-max normalization is correct (`src/eps/scoring/composite.py:53-65`), and ground-truth harvest reconstruction matches stored scores to machine precision (max diff 1.67e-16). No silent NaN/constant term in the composite.
- **CRITICAL CONTRADICTION TO "already wired" assumption — reorganization energy λ is computed but NOT used.** The directive "specifically wants it used," yet `monomer_lambda_ox_eV` / `solvent_lambda_ox_eV` (`secondary_descriptors.py:122,221`) enter neither a filter nor the score. This is the single most directive-divergent finding. (See Needs-judgment.)
- **Several §3.3 descriptors are computed-but-unwired by design:** cation reduction, ion-pair ΔG, anion vdW volume are all REPORTED-ONLY (`secondary_descriptors.py:1-10`). Only `anion_Eox` is actually wired into filter + score. This is consistent with the docstring intent but should be confirmed as deliberate, not accidental drift.
- **Calibration is internally inconsistent:** production Tier-1 uses `agagcl_peak_strict` (`tier1.yaml:55-62`) while `eps validate` defaults to `agagcl_peak_relaxed` (`calibration_profiles.yaml:17`). The pinned tier1 calibration is self-labeled "provisional, not production-grade," gated on pending DFT batch 417442. No published active-calibration manifest exists outside THINK.md.
- **No scale guardrails exist** — swapping `data/monomers.csv` for a 50k-row file would launch an unbounded Tier-1/Tier-2 run with no warning (`loaders.py:21-26`, `tier1.py:106-108`). This is the top freeze-time / scale risk.
- **sTDA-xTB is unavailable on the production cluster**; all real harvests use the HOMO-LUMO fallback (`xtb.py:372-390`, `optical_gap_method='homo_lumo_hexamer_fallback'`). The fallback is correctly wired and labeled, but the 15% band-gap term is therefore running on a weak proxy in production.
- **Doping-onset potential (secondary §3.3 goal) is not computed anywhere** — `doping_onset` appears only as a curation/label string, never as a calculator output.

---

## 2. Decidable fixes

| Priority | Section | Issue | File to change | Concrete change | Confidence |
|---|---|---|---|---|---|
| **H** | 4+7 (c) | No size guardrail — a swapped large CSV silently triggers an unbounded 50k Tier-1/Tier-2 run | `src/eps/workflow/tier1.py` (after `load_*()` at `:106-108`); `src/eps/workflow/tier2.py` (plan fn) | Add `SAFE_MAX` check after loads; raise `ValueError` if `len(monomers) > ~100` (Tier-1) / task count > threshold (Tier-2); add `--force-large-scale` flag requiring explicit sign-off; document intended scale in CLI help | high |
| **M** | 3.3 (d) | Partial wiring of electrolyte descriptors is undocumented — only `anion_Eox` is wired; cation_reduction/anion_volume/ionpair are computed but unused | `src/eps/properties/secondary_descriptors.py` docstring + a design note | Document explicitly that report-only is intentional; OR if wiring intended, add filter/score logic (PI threshold needed first — see Needs-judgment) | high |
| **M** | 3.1 (d) | Applicability-domain (out-of-domain) flag exists in validation only (`directive.py:418-493`), not in production `tier1.csv` | `src/eps/workflow/tier1.py:242-336` (`compute_monomer_table`) | Load calibration domain min/max, check each monomer's raw Eox, store boolean `monomer_Eox_calibration_out_of_domain` column in the harvest | high (impl) |
| **M** | 3.1 (e) | No published active-calibration manifest; tier1.yaml/calibration_profiles.yaml disagree on active profile | new `configs/CALIBRATION_ACTIVE.md`; `configs/tier1.yaml`; `configs/calibration_profiles.yaml` | After DFT 417442 lands: reconcile both files onto chosen profile; publish manifest (active profile, n_points, LOO-CV MAE, strict-vs-relaxed rationale, date, batch ref) | high |
| **L** | 1+3.3 (e) | Doping-onset potential (§3.3 secondary goal) not computed | `src/eps/properties/secondary_descriptors.py` | If required: add calculator alongside `cation_reduction_descriptors`; if optional: log as a noted gap in the research doc. Needs scope confirmation first | high |
| **L** | 3.1 (b) optical / 3.2 (a) | Implicit design choices not documented in-code: oligomer-Eox monotonicity report-only, no per-class optical-gap calibration, single global `target_gap_eV=1.8` | `src/eps/properties/oligomer_series.py`, `src/eps/scoring/composite.py` comments | Add a comment documenting that per-class (D-A vs homopolymer) optical calibration is intentionally NOT implemented and monotonicity is human-audit-only | high |
| **L** | 3.1 oligomer (bonus) | No machine check that per-n oligomer Eox trend is monotonic | `src/eps/properties/oligomer_series.py` | Add a diagnostic/warning flag when `Eox(n)` is non-monotonic, or document why non-monotonicity is acceptable at xTB screening grade | medium |

---

## 3. Needs-judgment items (for THINK.md / PI)

- **Reorganization energy λ — report vs. use (3.2b).** Directive states λ should be *used* as kinetic protection beyond the thermodynamic window, but `monomer_lambda_ox_eV`/`solvent_lambda_ox_eV` (`secondary_descriptors.py:122,221`) are report-only and absent from filters (`tier1.py:711-745`) and score (`composite.py:39-72`). **Tension:** directive intent ("specifically wants it used") vs. current report-only implementation. PI must decide: (1) hard-filter margin, (2) score component with a weight, or (3) accept report-only. If used, threshold/weight must be chosen.
- **Active calibration: strict vs. relaxed (3.1e).** `agagcl_peak_strict` (n=9, LOO-CV 0.197 V, pinned in tier1.yaml) vs. `agagcl_peak_relaxed` (n=23, LOO-CV 0.169 V, validate default). **Tension:** smaller strict/cleaner set vs. larger better-generalizing mixed-tier set; decision is data-gated on pending DFT batch 417442. PI sign-off required after Fit-2 LOO-CV comparison.
- **Electrolyte descriptor wiring scope (3.3d).** cation_reduction, anion_volume, ionpair ΔG are computed and joined but never decide anything. **Tension:** report-only design (per docstring) vs. directive's broader electrolyte-property intent. PI: are these intentionally diagnostic, or should one/more become filters/score terms (each needs a threshold)?
- **Anchor / library coverage gap (2c).** Library = 36 monomers; feasibility-label set references 28 monomers with only 9 in the library; 11 of 17 "NO"-outcome feasibility monomers are missing. **Tension:** is the curated 36-row subset deliberately decoupled from the literature feasibility set (for future expansion), or is the library underpopulated for a preliminary feasibility metric? PI to confirm intent and whether calibration-anchor monomers are all present.
- **Oligomer Eox per-n physical sanity (3.1 bonus).** Series is computed/reported but trend monotonicity is not machine-validated; requires human inspection of the (gitignored) real harvest CSV. **Tension:** xTB screening-grade noise vs. expectation of monotone decrease with chain length.
- **Compute budget for 50k scale (9d).** Estimates span widely depending on library-expansion assumptions; Tier-1 ≈ 12–18 core-hours xTB, Tier-2 DFT ≈ 167 core-hours for ~4k survivors. **Tension:** scope of expansion (more monomers vs. more conditions) and whether Tier-2 Gaussian refinement is roadmap or diagnostic. PI to confirm scope + cluster allocation.

---

## 4. Already-done confirmations (do not redo)

- **Eox-in-window hard gate** wired with configurable 0.3 V threshold (`tier1.py:652-659,716,737-742`).
- **ESW measured-first-conservative policy** never widens; caps with `min(measured, min(csv, computed))` (`solvent_windows.py:78-227`, esp. `:164-166`); water's pathological 3.77 V computed value is correctly blocked (`tier1.yaml:11-17`).
- **Anion Eox** directly computed and used as a hard constraint with 0.2 V margin (`calculators.py:130-147`, `tier1.py:657-659,717-718`).
- **Solubility correctly documented as a ΔGsolv solvation-affinity proxy** (GFN2 ALPB), not true solubility; openCOSMO-RS is a separate pilot, not production (`calculators.py:150-166`, `configs/solvation_cosmors_pilot.yaml`).
- **PEAK and ONSET calibration tracks kept strictly separate**, never co-fit (`calibration_profiles.yaml:5-16`, `benchmark.py:131-144`).
- **One pinned, tested reference-scale conversion** `ip_eV_to_potential_vs_AgAgCl` with pinned constants `ABS_SHE_V=4.28`, `AGAGCL_SHIFT_V=-0.197` (`redox.py:11,14,18`; `tests/test_redox.py:13-15`).
- **HOMO/LUMO are report-only**, never a pre-screen; adiabatic IP is the sole basis for filter/score (`secondary_descriptors.py:83-137`).
- **Five composite terms live, normalized, weights sum to 1.0, no degeneracy** (`scoring.yaml:1-6`, `composite.py:53-65`); failed `monomer_cation_alpha_spin_sum` is correctly excluded (report-only).
- **Per-species descriptor tables emitted as independent first-class outputs** (`tier1.py:211-224`): `oligomer_buildingblocks.csv`, `oligomer_eox_series.csv`, `secondary_descriptors.csv`.
- **Selenophene `[se]` handled correctly** via T10 Se-skip → ETKDG → xTB GFN2 (no MMFF/UFF), 0 geometry failures in real harvest (`geometry.py:99-108,168-173`).
- **Optical-anchor SMILES validated**; no `*` SMILES in the curated set; oligomer assembly produces clean, anchor-free canonical hexamers (`staging_audit.py:76-97`, `oligomer.py:114-131,169-179`).
- **dSCF solvent limits correctly NOT used as standalone window**; identified as known-to-fail and gated behind measured fallback (`calculators.py:69-115`, `solvent_windows.py:1-19`).
- **Tier-2 DFT correctly isolated as build-only**, flagged OUT_OF_SCOPE; existing DFT number is in-sample only (`directive.py:799-804`, `cli.py:94`).
- **Benchmark set assembled (40 rows ≥ 30 minimum)**, covering peak + onset label types (`data/benchmark.csv`).
- **Provenance + resumability sufficient for Tier-1 at scale:** SHA-256-hashed config provenance sidecars (`provenance.py:41-69`), idempotent SQLite per-species cache with INSERT OR REPLACE (`cache.py:27-158`), wall-kill = resumable via cache reuse (`scripts/run_tier1.sge:13-15`). `outputs/` gitignored; `docs/runs/` manifest discipline consistent (35 files).

---

## 5. External dependencies / blockers

- **sTDA-xTB binary absent on Lop cluster** (`module avail stda` empty per STATUS.md). All production optical gaps use the HOMO-LUMO hexamer fallback (`xtb.py:372-390`). **Blocker for production-grade optical gap:** install/load `stda` on the cluster; until then the 15% band-gap term runs on a weak proxy. Fallback path itself is complete and labeled — no code defect.
- **openCOSMO-RS / ORCA 6.1 — pilot only, not production** (`configs/solvation_cosmors_pilot.yaml`, `orca.py:70-154`). ORCA exists on Lop (`module orca/6.1.0-418`), but built-in COSMORS profiles cover only 3 of 13 solvents (MeCN, NM, water); propylene carbonate and NMP are explicitly gated out. **Scaling to the full 13-solvent library requires** in-scope built-in profiles or external/commercial sigma-profile parametrization. Feasibility: MEDIUM, and an external/research decision, not an engineering task.
- **Ion-pair dissociation uses an ALPB contact-pair proxy, not COSMO-RS** (`secondary_descriptors.py:309-351`, `IONPAIR_METHOD='alpb_contact_pair_approx'`). True COSMO-RS upgrade is a separate install + runtime + PI cost/value decision.
- **Pending DFT batch 417442** is the data gate for the strict-vs-relaxed calibration decision; until it lands, the production calibration remains self-labeled provisional.

---

## 6. Cross-cutting risks (50k scale / freeze validity)

- **Unbounded scale is the dominant risk.** No size guard anywhere (`loaders.py:21-26`, `tier1.py:106-108`, `tier2.py` plan). A misconfigured or swapped data file launches a 50k run with no warning. This must be fixed before any "freeze-then-scale" step is trusted. **(See Decidable fix H.)**
- **A "freeze" today would freeze a provisional calibration.** `tier1.yaml` is self-labeled "provisional, not production-grade" and disagrees with the validate default. Freezing without reconciling and publishing a manifest bakes in an undeclared inconsistency. **(3.1e.)**
- **A "freeze" would freeze a weak-proxy optical-gap term.** The 15% band-gap term currently rides on HOMO-LUMO fallback in production. Any downstream ranking treating it as TD-DFT-grade would be over-trusting it. Document the active `optical_gap_method` in run manifests so frozen rankings disclose the proxy.
- **Directive-vs-implementation drift on λ.** Freezing now ships a harvest where a descriptor the directive wants used contributes nothing to decisions — a scientific-completeness gap, not a code bug. **(3.2b.)**
- **Tier-1 is single-pass, not internally checkpointed.** A mid-run wall-kill is recoverable only via per-species cache reuse + full orchestration restart (`tier1.py:92-239`, `scripts/run_tier1.sge:13-15`). Acceptable at 7.5k triads (10h54m proven); at 50k with library expansion this approaches/exceeds a 72h queue on small core counts and will require array-job parallelization. Plan parallel orchestration before scaling.
- **Tier-2 DFT is NOT resumable like Tier-1** — task-local caches prevent concurrent writes; re-submission + separate harvest orchestration required (`scripts/run_tier2_pilot_array.sge:84-85`). Budget ~167 core-hours for ~4k survivors; confirm parallelization strategy before authorizing.
- **Applicability-domain blindness in production.** OOD status is computed only in validation (`directive.py:418-493`), not flagged in `tier1.csv`. At 50k scale with an expanded library, more monomers will fall outside the 9-point (or 23-point) calibration domain; frozen rankings could include extrapolated Eox values with no in-harvest warning. **(3.1d.)**
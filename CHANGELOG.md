# Changelog

## 2026-06-19 — directive §3 secondary descriptors (additive, reported-only)
New `src/eps/properties/secondary_descriptors.py`: per-species, cached, failure-tolerant,
screening-grade descriptors joined into the Tier-1 harvest. PURELY ADDITIVE — none enters a hard
filter or the composite score (verified: survivors 664→664, composite max-abs-diff = 0.0, total
7020→7020 with the new section enabled vs disabled). Pinned `configs/tier1.yaml` calibration,
`configs/scoring.yaml`, and `redox.py` untouched (blob-hash verified).

- **Engine (additive):** `base.py` SUPPORTED_QUANTITIES gains `homo`, `lumo`, `vertical_ip`,
  `vertical_ea`; `spin_density` now also returns a per-heavy-atom `raw["atomic_spin_density"]`
  array (sums to 1.0). MockEngine implements all (vertical = adiabatic + reorganization ≥ 0; LUMO >
  HOMO), and the existing `adiabatic_ip`/`adiabatic_ea`/etc. values are unchanged (same hash basis).
  XTBEngine adds best-effort real paths (frontier-orbital + Mulliken-spin parsers; single-point
  vertical) documented as screening approximations; the cache round-trips `raw`, so per-atom arrays
  persist.
- **§3.1 monomer (per monomer):** `monomer_HOMO_eV`, `monomer_LUMO_eV`, `monomer_HL_gap_eV`;
  radical-cation Mulliken spin → `monomer_cation_max_spin`, `_max_spin_atom_idx`, `_max_spin_is_alpha`
  (α coupling-atom membership via `detect_alpha_carbons`), `_alpha_spin_sum`; `monomer_vertical_IP_eV`,
  reused `monomer_adiabatic_IP_eV`, `monomer_lambda_ox_eV`.
- **§3.2 solvent (per solvent):** `solvent_lambda_ox_eV` = vertical IP − adiabatic IP, and
  `solvent_lambda_red_eV` = vertical EA − adiabatic EA (reusing the anodic/cathodic adiabatic points).
- **§3.3 electrolyte:** `anion_vdw_volume_A3` (RDKit 3D grid volume, with a flagged
  `anion_volume_method=bondi_additive_fallback` for anions distance geometry cannot embed, e.g.
  octahedral PF6⁻); `cation_reduction_raw_V_vs_AgAgCl` (RAW — a reduction potential, deliberately NOT
  on the oxidation calibration per T11) + the reported `cation_reduction_below_solvent_cathodic`
  flag; `ionpair_dissociation_dG_kcal` (ALPB contact-pair proxy, `ionpair_method=alpb_contact_pair_approx`,
  `status=skipped` when the pair can't be assembled — never guessed).
- Config knob `secondary_descriptors.enabled` (default true) in `tier1.yaml` (calibration block
  untouched). Verification artifact `outputs/secondary_descriptors.csv`. New tests
  `tests/test_secondary_descriptors.py` (engine ordering, per-species smokes, cache reuse, strict
  additivity). Suite green (154 passed, 4 skipped); ruff clean.

## 2026-06-18 (later 7) — calibrate-dft: emit the DFT-anchored composed xTB->V calibration
`eps calibrate-dft` now emits the screen-ready COMPOSED calibration that collapses the directive §7
two-stage design (Fit 1 xTB->DFT, Fit 2 DFT->exp peak) into one linear map from the xTB descriptor
straight to V vs Ag/AgCl — a drop-in for the pinned `configs/tier1.yaml` `monomer_eox` slope/intercept.
`configs/tier1.yaml` is NOT modified; this is an emitted artifact pending a real `--engine gaussian`
batch + review.

- New pure helper `compose_xtb_to_agagcl(fit1, fit2)`: `composed_slope = fit2.slope*fit1.slope`,
  `composed_intercept = fit2.slope*fit1.intercept + fit2.intercept`; `mae_V = fit2.mae` (the
  experimental MAE on the peak set). Returns `None` if either stage fit is missing (never fabricates).
- `xtb_to_dft_calibration.json` gains `"composed_xtb_to_AgAgCl_V": {slope, intercept, mae_V,
  n_points_xtb_to_dft, n_points_dft_to_exp_peak}`.
- `report.md` gains a "Screen-ready calibration (DFT-anchored, directive §7)" section: composed
  slope/intercept, a side-by-side with the pinned tier1.yaml values (0.725837 / -3.145372), and the
  switch note ("replace the tier1.yaml monomer_eox slope/intercept with these composed values ...
  Requires a real --engine gaussian batch + review first").
- Tests: pure-arithmetic composition test (known fit1, fit2 -> expected composed; None-on-missing)
  + an end-to-end emission test (JSON key/fields, report section, pinned side-by-side, tier1.yaml
  never written). Full suite green (146 passed, 4 skipped); `ruff` clean.

## 2026-06-18 (later 6) — scale chemical-space library toward directive §2
Purely additive growth of the chemical-space library toward the directive's §2 named lists. The
15/11/10 validated seed rows are byte-identical; scoring weights, the composite formula, the pinned
`configs/tier1.yaml` calibration, and `redox.py` are untouched. Mock-first; no live binaries.

- **Monomers `data/monomers.csv` 15 → 36 (+21).** Every new SMILES is RDKit-parsed + molecular-
  formula-verified and every new monomer carries a verified coupling site with a matching
  `data/polymerization.csv` row that assembles into n=2 and n=6 oligomers. Auto-derived α coupling
  (`detect_alpha_carbons`, exactly 2 sites) for the 5-membered heteroaromatics: 3-methyl/3-fluoro/
  3,4-difluoro/3-methoxythiophene, terthiophene, N-methyl/N-octyl/3,4-dimethylpyrrole, 3-methyl/
  3-hexyl/3,4-dimethylfuran, bifuran, terfuran, 3-hexylselenophene. Explicit building blocks for
  o-anisidine, o-toluidine, diphenylamine (4,4'), N-vinylcarbazole (3,6), 9,9-dimethylfluorene
  (2,7), thieno[3,4-b]pyrazine, and dithieno[3,2-b:2',3'-d]pyrrole (2,6). D-A and fused-ring (and
  the aniline-family / diphenylamine) couplings are flagged `approximate=True`.
- **Solvents `data/solvents.csv` 11 → 13 (+2):** nitrobenzene, benzonitrile (directive §2.2). Their
  ESW is a literature-PROVISIONAL fallback only — the computed adiabatic anodic limit is primary —
  and is flagged as such in the row notes pending cross-check vs directive table 2.2. Each uses a
  documented ALPB proxy keyword (nitromethane / acetonitrile).
- **Salts `data/electrolytes.csv` 10 → 15 (+5):** TEAPF6, LiBF4, KCl, CSA (camphorsulfonate), HClO4,
  each with verified cation + anion SMILES and a salt class.
- **`data/needs_review.md` (new):** species named in §2 whose SMILES or coupling site could not be
  assigned with confidence are parked here with a one-line reason rather than guessed into the live
  CSVs — DPP, isoindigo, thiadiazoloquinoxaline, indacenodithiophene, o-aminophenol,
  3,6-dimethylcarbazole, the acenaphtho-pyrrole hybrid (monomers); the ionic liquids, choline-Cl/urea
  DES, and BFEE (not simple molecular solvents); NaPSS and NaDBSA (polymeric/surfactant anions).
- **Tests:** `test_chemspace.py` counts updated to 36/13/15 with subset assertions that the validated
  seed rows stay present + byte-identical, plus new directive-§2.2 solvent and §2.3 salt presence
  tests; `test_smoke.py` derives the triad count from the loaders (now 7,020) with a `>= 15*11*10`
  floor guard. The existing building-block-artifact test now covers all 36 monomers' assembly
  (zero ASSEMBLY_ERROR). Full suite green (144 passed, 4 skipped); `ruff` clean.

## 2026-06-18 (later 5) — literature-grounded refinements (Eox benchmark; band-gap route)
Small refinement pass grounded in two literature reviews added under `docs/research/`
(`eox_benchmark_and_reference_conversion.md`, `bandgap_route_oligomer_stda_vs_ml.md`). All
additive; no live Gaussian; pinned tier1.yaml calibration / scoring weights / redox.py untouched.

- **R1 — peak-only DFT->experiment validation** (`eps calibrate-dft`): the DFT ΔSCF Eox is a
  thermodynamic PEAK observable, so Fit 2 (DFT->experiment) now fits ONLY `monomer_oxidation_peak`
  rows; Fit 1 (xTB->DFT) is unchanged (uses all eligible monomers). New `label_type` column in the
  points CSV; report + CLI state peak-fed vs onset-excluded counts (18 peak / 4 onset on v3).
- **R2 — reference-floor flags** in the Fit 2 report section: a fixed ~0.1 V (up to 0.2 V)
  reference-floor note (Fc/Fc+ = +0.45 V vs Ag/AgCl, Pavlishchuk & Addison 2000; "do not over-tune
  below ~0.1 V"), plus a computed core-monomer flag (thiophene/EDOT/carbazole/pyrrole/DTP): if the
  core DFT->exp MAE > 0.15 V, print "re-examine the reference-conversion constant BEFORE re-tuning
  the DFT method." New unit-testable helpers `dft_to_exp_residuals` + `core_monomer_reference_flag`.
- **R3 — honest extrapolation** (`oligomer_series.py`): added a 2nd-order polynomial 1/n fit
  (`oligomer_Eox_infinite_raw_poly2_eV`, `oligomer_Eox_poly2_r2`; <3 pts -> NaN) alongside the
  linear one, and a constant `oligomer_Eox_extrap_caveat` ("non-converged: naive 1/n from short
  oligomers; needs >=20-mer or PBC", Zade & Bendikov). Docstring + columns state neither extrapolated
  value is a converged polymer Eox; the durable signal is the per-n trend + the n=6 raw Eox. Still
  reported-only/additive (113 -> 113 survivors).
- **R4 — docs**: THINK.md records literature-backed PROPOSED resolutions (pending PI confirmation)
  for T1 (store both; calibrate DFT vs peak, screen window vs onset), T2 (Ag/AgCl master scale,
  Fc/Fc+ at +0.45 V, accept ~0.1 V floor), and T6 (Route A oligomer+sTDA-xTB now / Route B GNN
  later; range-separated functional + per-class validation for the TD-DFT calibration).
- Full suite green: 142 passed, 4 skipped; `ruff check` clean.

## 2026-06-18 (later 4) — Step-2 DFT-calibration engineering (mock-first) + oligomer-Eox descriptor
All additive; NO live Gaussian was run; the pinned xTB->experiment calibration
(`configs/tier1.yaml`), the composite weights (`configs/scoring.yaml`), and `redox.py` are
untouched; no pinned data file was edited.

- **Tier-2 engine is now config-driven (WS1).** New `configs/tier2.yaml` (v1 defaults: B3LYP/
  6-31G(d,p), `smd_solvent: null`, `use_freq: false`, `mem: 8GB`, `nprocshared: 8`,
  `calibration_set`). `build_gaussian_input` prepends Link0 `%mem`/`%nprocshared` (g16 no longer
  runs single-core) and adds `Freq` when `use_freq`. `GaussianEngine` reads `smd_solvent`/`use_freq`
  from the config instead of hardcoding gas-phase; v1 keeps the same gas-phase ΔSCF behavior.
  Setting `smd_solvent` + `use_freq: true` is the documented rigor toggle (solvated ΔG). The
  return-code-before-parse safety and "g16 absent -> RuntimeError, never fabricate" are unchanged.
- **`eps calibrate-dft` (WS2, directive §7), mock-first.** Calibrates the cheap xTB descriptor
  against DFT, then validates DFT against experiment. The xTB descriptor REUSES the identical
  existing path (`monomer_eox_vs_AgAgCl`), so the new xTB->DFT slope/intercept are directly
  comparable to the pinned xTB->experiment fit. Calibration set = `data/benchmark.csv` rows with
  `calibration_eligible == true`, deduped by canonical SMILES (32 rows -> 22 unique monomers).
  DFT Eox is cached per species (gas-phase v1); a cache hit reuses both the neutral and the cation
  jobs (never recomputed). Per-monomer failures -> `dft_calc_status`/`dft_calc_error`, skipped.
  Writes `outputs/dft_calibration/{dft_calibration_points.csv, report.md,
  xtb_to_dft_calibration.json}`; report.md carries both fits (xTB->DFT in eV; DFT->experiment as a
  units-aware V/eV correlation, not equality) and a clearly-labeled side-by-side of the pinned vs
  new slope/intercept (no files overwritten). `--engine mock|gaussian`, `--only`, `--limit`.
  NEW artifact only — `default_screening_profile` and `configs/tier1.yaml` are unchanged.
  `scripts/run_dft_calibration.sge`: the only g16 template (node-local `GAUSS_SCRDIR` + cleanup);
  states it is the SMALL calibration batch, distinct from the full Tier-2 production screen.
- **`eps doctor` Tier-2 readiness (WS3).** Adds `tier2:g16` (g16 on PATH via `shutil.which`;
  WARN, never FAIL, cluster-only) and `tier2:config` (configs/tier2.yaml loads, with the effective
  method string, e.g. "B3LYP/6-31G(d,p), gas phase, opt only (ΔE_SCF)"). Runs no g16.
- **Oligomer Eox-vs-chain-length descriptor (WS4), reported-only.** Reuses the existing oligomer
  assembly + side-chain truncation to compute the RAW xTB adiabatic IE (eV) of the n-mer for
  `oligomer.eox_oligomer_lengths` (default [2,3,4,6]), per-monomer, cached, failure-tolerant. New
  harvest columns `oligomer_Eox_raw_n{1,2,3,4,6}`, `oligomer_Eox_infinite_raw_eV` (classic 1/n
  extrapolation, incl. n=1 monomer anchor), `oligomer_Eox_extrap_r2`,
  `oligomer_Eox_infinite_calibrated_V_vs_AgAgCl` (flagged `oligomer_Eox_calibration_out_of_domain
  = True`), `oligomer_Eox_sidechain_truncated`, `oligomer_Eox_calc_status`/`_error`. Verification
  artifact `outputs/oligomer_eox_series.csv`. ADDITIVE: the mock screen gives 113 -> 113 survivors
  (identical sets) and composite_score max abs diff 0.0; no column feeds a filter or the score.
- Tests: +21 new (gaussian config/Link0/Freq, doctor Tier-2, calibrate-dft plumbing incl. cache
  reuse + failure-skip + descriptor identity + live-g16 skip, oligomer-Eox math/reuse/failure/
  additivity). Full suite green: 137 passed, 4 skipped; `ruff check` clean.

## 2026-06-18 (later 3) — fixes from the first real oligomer harvest
- Issue 1 (bug): the `fluorene 9,9-dioctyl` n=6 oligomer (416 atoms) failed RDKit 3D embedding,
  so its `optical_gap_eV` was NaN and all ~110 fluorene triads dropped out of survivors.
  - For the OPTICAL-GAP oligomer ONLY, long inert saturated alkyl side chains are now truncated
    to methyl before embedding (`truncate_inert_alkyl_to_methyl`): the gap is a backbone
    property and saturated chains are electronically innocent. Recorded as
    `optical_gap_sidechain_truncated` in the all-triads output and the building-blocks artifact.
    The monomer Eox / solvation / dimerization paths keep the full side chains (unchanged).
  - Embedding hardened generally (`geometry.py`): ETKDGv3 deterministic embed first, then
    random-coordinate retries across several seeds with a larger iteration budget; a clear
    ValueError on total failure (never a silent NaN). The full dioctylfluorene hexamer now
    embeds even without truncation.
- Issue 2 (science): `dimerization_dG` used the wrong dimer charge state. The directive's
  `2 M+. -> [M-M]2+ + 2 H+` is charge-imbalanced (+2 vs +4); the correct oxidative coupling is
  `2 M+. -> M-M(neutral) + 2 H+` (the rearomatized dimer is neutral). The dimer is now evaluated
  NEUTRAL (charge 0, singlet) on the same α,α′-coupled structure, removing a spurious second
  oxidation that made every monomer look ~+650 kcal/mol endothermic and distorted the ordering.
  The reaction is charge- and electron-balanced, so the bare proton's electronic energy is
  rigorously 0 (re-documented `PROTON_GIBBS_EV`): ΔG = E(M-M neutral) - 2·E(M+.) is the
  physically interpretable, self-contained screening-grade coupling energy (dG<0 favorable).
  Still a SCORE input only, not a hard filter; composite formula/weights unchanged.
- NOTE: the prior harvest's fluorene `optical_gap` (was NaN) and ALL `dimerization_dG` values
  are superseded and will be recomputed by the next cluster run. No cluster run performed here.

## 2026-06-18 (later 2) — corrected the alkylenedioxy monomer SMILES (2,3 -> 3,4)
- Fixed a logged pinned-data error: `data/monomers.csv` stored EDOT/ProDOT/EDOP/EDOS as the
  2,3-dioxy isomer (one α-carbon blocked); corrected to the directive §2.1 3,4-dioxy isomer
  (both α free for clean 2,5 coupling): EDOT `C1COc2cscc2O1`, ProDOT `C1CCOc2cscc2O1`,
  EDOP `C1COc2c[nH]cc2O1`, EDOS `C1COc2c[se]cc2O1`.
- `data/polymerization.csv`: those four switched from `explicit`/`approximate=True` to `alpha`
  (auto-derived 2,5-α coupling), building block cleared and the 2,3-dioxy caveat removed.
  Verified via `eps run-tier1 --engine mock`: each auto-detects exactly two free α-carbons and
  assembles a clean 2,5-α-linked oligomer (no blocked α, no assembly errors).
- Added a regression test asserting EDOT/ProDOT/EDOP/EDOS each have exactly two ring-heteroatom-
  adjacent α-carbons, both bearing an H, and that their spec is `alpha`/non-approximate.
- The pinned oxidation calibration is unaffected (none of the four appear in
  `data/benchmark.csv`); the only downstream effect is these four monomers' own screening
  descriptors (Eox/optical_gap/dimerization_dG), now stale pending the next cluster harvest.
  Marked the data-curation item RESOLVED in `docs/step1_real_bandgap_dimerization_report.md`;
  STATUS updated. No cluster run performed.

## 2026-06-18 (later) — made the two placeholder scoring axes real (band gap + dimerization)
- Both previously-placeholder Tier-1 axes are now real, screening-grade physics computed the
  directive's way; all five composite axes are real (the composite is no longer
  "placeholder-contaminated", but it is screening-grade and NOT validated).
- Deliverable A — reusable n-mer oligomer assembly (`src/eps/structures/oligomer.py`): RDKit
  α-coupling via ditopic [1*]/[2*] building blocks (documented substitution for `stk`, which is
  unavailable in the env). Coupling regiochemistry is data-driven in `data/polymerization.csv`
  (auto-α for the clean 5-membered heteroaromatics + CPDT; explicit for carbazole 3,6 /
  fluorene 2,7 / aniline / dioxy / D-A). `eps run-tier1` writes a human-reviewable
  `outputs/oligomer_buildingblocks.csv`. APPROXIMATE coupling flagged (aniline N-para, the D-A
  simplification) and a monomers.csv DATA-CURATION item recorded: stored EDOT/ProDOT/EDOP/EDOS
  canonical SMILES encode the 2,3-dioxy isomer (one α blocked), out of scope to fix here.
- Deliverable B — optical (band) gap: `optical_gap_eV` is now the optical gap of the assembled
  n=6 oligomer — the sTDA-xTB lowest singlet excitation when `stda` is on PATH, else the
  oligomer GFN2-xTB HOMO-LUMO gap as a flagged proxy (`optical_gap_method` column). Per-monomer,
  cached by oligomer SMILES. RAW/uncalibrated vs TD-DFT (Step-2 hook). `parse_stda_lowest_excitation`
  + fixture added; `configs/tier1.yaml` gains an `oligomer:` section (n=6; pinned calibration
  untouched).
- Deliverable C — dimerization: `dimerization_dG` is now the radical-radical coupling ΔG
  (2 M+. -> [M-M]2+ + 2 H+) = G([M-M]2+) + 2 G(H+) - 2 G(M+.) via the cached engine; the proton
  free energy is one documented constant that cancels across monomers (absolute is
  screening-grade, relative ordering sound). Not a hard filter; feeds the w4 term only.
- `eps analyze` honesty labels updated from "placeholder-contaminated" to "screening-grade"
  (real but uncalibrated/proton-referenced; not validated); invariant/analysis tests updated.
  Added `scripts/run_oligomer.sge` (hexamer-sized resources; loads `stda` if available).
  STATUS + THINK (T5 done, T6 exploring) updated. ruff + pytest green.

## 2026-06-18
- Added `eps doctor`: a no-compute environment readiness self-check (`src/eps/doctor.py`)
  reporting PASS/WARN/FAIL for Python version, `xtb`/`g16` on PATH (WARN if absent —
  cluster-only), importability of rdkit/pandas/numpy (FAIL if missing) and matplotlib/sklearn
  (WARN), and the existence + parseability of the pinned configs and expected `data/*.csv`.
  No network, no subprocess beyond `shutil.which`. Tests in `tests/test_doctor.py`.
- Added scientific-invariant regression tests (`tests/test_invariants.py`): the pinned
  redox→V conversion reproduces its constants, is monotonic, and round-trips; the single
  `tier1.yaml` oxidation calibration (slope 0.725837 / intercept -3.145372) is applied with the
  identical slope/intercept transform to monomer Eox, the solvent anodic limit, AND anion Eox
  (T11); `eps sanity` can FAIL (EDOT forced above thiophene → FAIL) and the clean directional
  ordering passes; the memo always marks both unmeasurable §7 metrics "not computable" and never
  fabricates a number; and `eps analyze` placeholder/diagnostic labels are present.
- Added native provenance sidecars: every primary CLI output (`run-tier1`, `validate`, `memo`,
  `analyze`) now also writes `<output>.provenance.json` (`src/eps/provenance.py`) capturing a UTC
  timestamp, git commit short+long + dirty flag, `eps` version, engine/method, SHA-256 of the
  pinned config files, and the library CSV row counts. Pure stdlib + pandas; best-effort
  (a provenance failure warns, never crashes the command) and degrades to `"unknown"`/`"missing"`
  outside a git repo or when files are absent. Replaces the by-hand MANIFEST. Tests in
  `tests/test_provenance.py`.
- Added continuous integration (`.github/workflows/ci.yml`): on push and pull_request, sets up
  Python 3.11 and 3.12, installs the package + `[dev]` extra, runs `ruff check` then `pytest -q`.
  xtb/g16 are absent in CI so their live smokes skip (not fail).
- Added a conservative `ruff` lint config (`[tool.ruff]`, select E/F/I, ignore E501,
  line-length 110) and a `dev` optional-dependency group (`ruff`). Fixed all findings
  (import sorting + two genuinely-unused imports); `ruff check` is clean.
- Tier-1 all-triads output now carries the scoring columns (`composite_score`, `pareto_front`,
  `band_gap_deviation_eV`, and the `norm_*` components) via a one-to-one left-join from the
  ranked survivors onto `all_triads` by triad identity (`monomer_name, solvent_name, salt`).
  Survivor rows carry IDENTICAL values to the ranked CSV; non-survivors are NaN (and
  `pareto_front` False). Nothing is recomputed — `add_composite_score`, the weights, and the
  Pareto front are unchanged. Net effect: `eps analyze --harvest <all.csv>` now produces every
  §8 output (Pareto plot + shortlist included) from the single all-triads file (closes batch-1
  TODO #1).
- Scaffolded the Tier-2 DFT engine (Gaussian 16), BUILD-ONLY — no g16 is ever run.
  `src/eps/engines/gaussian.py` adds `GaussianEngine(Engine)` (`gas_energy`, `adiabatic_ip`,
  `adiabatic_ea`) mirroring `XTBEngine`'s structure and the same charge/multiplicity convention
  (oxidation → charge+1, multiplicity+1; ΔG = G(cation) − G(neutral), preferring the thermally
  corrected Gibbs free energy when present). It checks the subprocess return code BEFORE parsing
  (Task-1a lesson) and raises a clear RuntimeError when `g16` is absent — it never fabricates a
  value. `build_gaussian_input(...)` emits a valid `.gjf` (route `#p B3LYP/6-31G(d,p) Opt
  SCF=Tight`, optional `SCRF=(SMD,Solvent=...)`, charge/multiplicity, Cartesian coords from
  `smiles_to_xyz`); `parse_gaussian_log(...)` extracts the final `SCF Done` energy and the
  optional `Sum of electronic and thermal Free Energies`, Hartree→eV via `HARTREE_TO_EV`.
- Registered `"gaussian"` in the CLI engine factory (method label `b3lyp-6-31g(d,p)-smd`); it is
  NOT wired into any production workflow run. Added `tests/fixtures/gaussian_scf.log` and
  `tests/test_gaussian.py` (input/route/SMD, log parsing, no-fake-when-absent, return-code-first
  ordering, live smoke skips without g16).
- Added experimental `eps tier2 --dry-run` (`src/eps/workflow/tier2.py`): writes neutral+cation
  `.gjf` inputs per UNIQUE survivor monomer for human inspection and prints a rough CPU-hour
  estimate; it never submits or runs g16 (a test asserts no subprocess is launched).
- Added `eps analyze` (directive §8): a read-only post-processing command (`src/eps/analysis/`)
  that NEVER recomputes or rescores, only reads an existing Tier-1 harvest CSV. Produces
  `summary.csv` (total vs surviving triads, overall retention, retention by monomer/solvent/
  salt_class, per-property failure counts from `*_calc_status`), real-axis distribution PNGs
  (`window_margin_V`, `solubility_score`, `anion_stability_margin_V`), a Pareto PNG
  (`window_margin_V` vs `solubility_score`, marked by the existing `pareto_front`, point size
  ~ `-band_gap_deviation_eV`), a chemical-space map (per-triad Morgan fp r2/1024 → PCA(~50)
  concatenated with min-max-normalized descriptors → t-SNE, or PCA(2) for n<10) colored by
  `monomer_class` and by `passes_all_tier1_filters`, and a `shortlist.csv` (top-30 Pareto by
  composite). Honesty: every output touching a placeholder axis is labeled
  "PLACEHOLDER-CONTAMINATED / DIAGNOSTIC ONLY"; the shortlist carries the diagnostic note.
- `eps analyze` degrades gracefully: missing matplotlib skips figures, missing scikit-learn
  skips only the chemical-space map, and a harvest without `composite_score`/`pareto_front`
  skips the Pareto/shortlist — each with a note, never a crash. Added `matplotlib` and
  `scikit-learn` to `pyproject.toml`. Tests in `tests/test_analysis.py`.
- Hardened `XTBEngine._run_xtb`: the subprocess return code is now checked and raises the
  xTB-exit `RuntimeError` BEFORE `xtbout.json` is parsed, so a present-but-garbage JSON can no
  longer mask a real xTB failure with a JSON `ValueError`. Success path is byte-identical;
  added a regression test that simulates a nonzero exit with corrupt `xtbout.json` (debt #9).
- Replaced the hand-written `tests/fixtures/xtbout.json` with a synthetic-but-schema-faithful
  fixture mirroring real `xtb --json` keys/nesting (`total energy`, `HOMO-LUMO gap/eV`, plus
  realistic siblings); existing parser tests unchanged (debt #7, fixture part).
- Version-controlled cluster job templates under `scripts/` (`run_tier1.sge`,
  `run_validate.sge`, `run_memo.sge`, `run_analyze.sge`) — each starts its SGE directives with
  `#$ -S /bin/bash` and uses the known-good modules/conda/OMP preamble; `run_analyze` omits the
  xtb module (read-only). Added `scripts/README.md` documenting `qsub` usage and the `-S`
  requirement (debt #10). Templates only — not submitted.

## 2026-06-17
- Extended the experimental-validation step (directive §7). `eps validate` now additionally
  reports, per calibration profile: Spearman rank correlation ρ (computed with pandas
  rank + numpy corrcoef, no scipy dependency), residual standard deviation after
  calibration, the 5 worst-predicted benchmark monomers (name, calibrated/experimental Eox,
  signed error), and MAE grouped by coarse chemical family assigned from SMILES via RDKit
  substructure (thiophene/pyrrole/furan/selenophene/aniline/carbazole/fluorene/other; a
  `chemical_family` column is added to the report CSV and ρ/residual-std columns to the
  profile-comparison CSV). All additive; existing outputs unchanged.
- Added `eps sanity`: directional monomer-Eox checks on `outputs/tier1_all_xtb.csv`
  (EDOT<thiophene, 3-hexylthiophene<thiophene, EDOP<pyrrole, EDOS<selenophene,
  bithiophene<thiophene), compared WITHIN a single solvent (acetonitrile) because the
  calibrated monomer Eox is solvent-dependent; PASS/FAIL/SKIP per check. Monomer-Eox only,
  no oligomer assembly.
- Added `eps memo`: writes `docs/validation_memo_<YYYYMMDD>.md` with the per-profile accuracy
  table (n, MAE-after, LOO-CV MAE, residual std, ρ, R², PASS/FAIL vs the 0.30 V provisional
  gate), the worst-5 and per-family MAE, the sanity-check results, a "What we CANNOT validate
  yet" section (solvent ESW MAE → no solvent benchmark; yes/no feasibility >85% → no binary
  labels), and the T3/T4 caveat. The two unmeasurable §7 metrics are marked not-computable,
  never fabricated. With the mock engine the memo carries a NON-PHYSICAL banner (T9) and the
  exact cluster command to regenerate with real numbers.
- Added tests for the new metrics, the sanity checks, and the memo; full suite green
  (63 passed, 2 xtb skips). Pinned `configs/tier1.yaml` calibration and the redox conversion
  are untouched.
- First fully-clean real-xTB Tier-1 harvest completed on the SCS Lop cluster (GFN2-xTB, with
  the EDOS/Se geometry fix, cache rebuilt from scratch): 1650 triads (15 monomers × 11
  solvents × 10 salts), ZERO calculation failures across all seven per-property stages
  (monomer_Eox, solvation, optical_gap, dimerization, solvent_anodic_limit,
  solvent_cathodic_limit, anion_Eox), and 1007 surviving triads. EDOS now computes (calibrated
  Eox ~1.47 V). This is the first complete, reproducible real-physics per-species descriptor
  harvest.
- Marked THINK T10 (xTB failure clusters) DECIDED: both clusters were input/settings issues,
  not a method problem — EDOS geometry corruption (fixed in geometry.py) and PF6/high-dielectric
  anion non-convergence (already cured by --iterations 500 --etemp 400). Confirmed by the clean
  harvest (0 EDOS failures, 0 anion failures); no move to ddCOSMO is needed.
- Caveats preserved: the clean harvest is a real-physics milestone, not a final ranking — the
  composite remains diagnostic because optical_gap and dimerization_dG are still placeholders
  (T6) and the anion Eox is a monomer-fit calibration extrapolation (T11). Updated STATUS open
  debt #8 (ddCOSMO no longer needed on convergence grounds; ALPB-proxy PI sign-off still open).
- Fixed EDOS (3,4-ethylenedioxyselenophene) geometry corruption that failed real xTB across
  all 110 of its triads. Root cause was RDKit force-field pre-optimization, not xTB/SCF:
  `src/eps/structures/geometry.py` ran UFF whenever MMFF lacked params, but Se is typed by
  neither MMFF nor UFF ("Unrecognized atom type: Se2+2"); UFF then collapsed the clean ETKDG
  embedding to a ~0.26 Å atom clash, so xTB aborted geometry optimization
  ("|grad| > 500, something is totally wrong!", exit 128) and the single-point `optical_gap`
  ran on the clashed geometry (cached value also garbage).
- Geometry now skips force-field pre-optimization when no classical FF can type every atom
  (added an `UFFHasAllMoleculeParams` branch with an explicit no-FF fallthrough), handing the
  clean ETKDG geometry (~1.0 Å min interatomic distance) to xTB, whose GFN2 optimizer handles
  Se. The ETKDG seed (61453), embed logic, and MMFF branch are unchanged.
- Added a pure-RDKit `tests/test_geometry.py` case asserting EDOS produces 15 atoms with a
  minimum pairwise interatomic distance > 0.7 Å (the buggy UFF path produced ~0.26 Å).
- Advanced THINK T10 (open → exploring): both real-xTB failure clusters are now explained as
  input/settings issues, not a method problem — EDOS geometry corruption (fixed here) and
  PF6/high-dielectric anion failures already cured by `--iterations 500 --etemp 400`
  (0 anion failures in the harvest); no move to ddCOSMO needed. STATUS updated; full "decided"
  pending a cluster re-run confirming 0 EDOS failures.
- Decided THINK T11: apply the SINGLE oxidation calibration in `configs/tier1.yaml`
  (slope=0.725837, intercept=-3.145372) to ALL computed oxidation potentials — monomer Eox,
  solvent ANODIC limit, and anion Eox — so every oxidation potential lives on one calibrated
  V-vs-Ag/AgCl scale (spec §4.1). The solvent CATHODIC/reduction limit is excluded and stays
  raw/informational. The intercept cancels in every margin, so filter decisions are governed
  by raw IP differences; absolute calibrated solvent/anion values are screening-grade
  extrapolations (monomer-fit) pending a future benchmark.
- `configs/tier1.yaml`: `calibration.monomer_eox.scope` changed `monomer_only` →
  `all_computed_oxidation` and notes expanded; slope/intercept/enabled and the `monomer_eox`
  key name unchanged.
- `tier1.py`: renamed `_monomer_eox_calibration` → `_oxidation_calibration`;
  `compute_solvent_table` now takes an optional `calibration_config` and emits a new
  `solvent_anodic_limit_calibrated_V` column, with `solvent_anodic_limit_V` using the
  calibrated anodic value (CSV fallback is never calibrated); `compute_anion_solvent_table`
  now takes `calibration_config` and emits
  `anion_Eox_{raw,calibrated,filter}_V_vs_AgAgCl` (keeping `anion_Eox_V` as the filter alias).
- `build_triad_table`: `anion_stability_margin_V` now uses `anion_Eox_filter_V_vs_AgAgCl`,
  making the previously inert (raw-vs-calibrated no-op) anion-stability filter LIVE;
  `window_margin_V` form unchanged but `solvent_anodic_limit_V` now carries the calibrated value.
- Added MockEngine tests for the calibrated solvent anodic column / used-value rule, the
  raw-when-disabled default, and the calibrated anion raw/filter columns; full suite green
  (mock smoke now yields 154 survivors).
- Made the solvent anodic/cathodic limits spec-faithful: `solvent_anodic_limit` and
  `solvent_cathodic_limit` now COMPUTE the limit from the solvent molecule itself via the
  cached Engine — adiabatic ΔSCF oxidation (`adiabatic_ip`) and reduction (`adiabatic_ea`)
  in implicit self-solvent, projected to V vs Ag/AgCl through the pinned `redox.py`
  function (spec §3.2/§4.2) — instead of returning the hardcoded `esw_*_V` CSV stopgap.
- Kept the CSV `esw_anodic_V`/`esw_cathodic_V` columns as an explicit per-solvent fallback
  via new `solvent_anodic_limit_csv`/`solvent_cathodic_limit_csv` helpers; if an engine calc
  fails for a solvent the row falls back to CSV instead of aborting the screen.
- `compute_solvent_table` now takes `(solvents, engine, cache, method)` and emits twelve audit
  columns — `solvent_{anodic,cathodic}_limit_{computed_V,csv_V,V,source,calc_status,calc_error}` —
  where `solvent_anodic_limit_V` remains the value used downstream and `build_triad_table`'s
  `window_margin_V = solvent_anodic_limit_V − monomer_Eox_filter_V_vs_AgAgCl` is unchanged.
- Cathodic limit (via EA) documented as informational only and not used in any Tier-1 filter;
  no calibration is applied to the solvent side in this pass.
- Added `tests/test_solvent_limits.py` (MockEngine-based: IP/EA projection for acetonitrile
  and water, cache reuse, CSV fallback on engine failure) plus a live-xtb smoke test guarded
  by `skipif(shutil.which("xtb") is None)`.
- Corrected THINK T5 (solvent anodic limits are a COMPUTED quantity, not a zero-compute
  literature curation) and opened THINK T11 on whether the computed solvent limit should share
  the monomer calibration / sit on the same scale as the calibrated monomer Eox it is
  compared against in the window filter.
- Clarified THINK T1 by separating the purity argument for `agagcl_peak_strict` from the
  conditioning/sample-size argument, which instead favors `agagcl_peak_relaxed`.
- Updated THINK T1 to flag the current config mismatch: `configs/tier1.yaml` implements
  `agagcl_peak_strict`, while `configs/calibration_profiles.yaml` defaults validation to
  `agagcl_peak_relaxed`.
- Advanced THINK T1 status from `open` to `exploring` and seeded the Decision log with the
  provisional 2026-06-17 `agagcl_peak_strict` pinning pending PI sign-off.
- Updated THINK T4 to cross-reference STATUS open debt #1, which marks the >=30 clean-group
  milestone as MET while T4 questions whether >=30 belongs on the calibration-purity layer.
- Added a STATUS open debt to reconcile the `tier1.yaml` vs `calibration_profiles.yaml`
  calibration-anchor mismatch.
- Created `THINK.md` as the living register for open scientific, research, and decision
  questions, distinct from `STATUS.md` snapshots and `CHANGELOG.md` history.
- Seeded THINK entries T1-T10 covering calibration anchoring, reference scale,
  potential-type mismatch, >=30-group framing, placeholder-axis priority, band-gap strategy,
  deliverable framing, chemical-space expansion, the mock-preview caveat, and xTB failure
  clusters.
- Appended the `AGENTS.md` documentation-maintenance clause requiring THINK updates when
  genuine research questions, tradeoffs, or sign-off needs open, advance, or resolve.
- Refit `configs/tier1.yaml` monomer Eox calibration from a real GFN2-xTB all-profile
  validation on strict benchmark v3, choosing `agagcl_peak_strict` as the screening anchor:
  slope=0.725837, intercept=-3.145372, R^2=0.889, LOO-CV MAE=0.197 V.
- Added xTB SCF-robustness flags (`--iterations 500 --etemp 400`) and per-species failure
  isolation in the validation runner so one non-converged species does not abort all
  profiles.
- Recorded that SeSeSe/DCM SCF non-converged and was excluded from the relaxed peak fit; it
  is tier B and does not affect the chosen tier-A strict anchor.
- Integrated strict benchmark v3: appended 12 verified native-Ag/AgCl monomer-oxidation
  rows to `data/benchmark.csv`, bringing the benchmark to 32 calibration-eligible rows
  and 32 collapsed groups.
- Recorded the v3 label/profile split: 19 `monomer_oxidation_peak`, 13
  `monomer_oxidation_onset`, `agagcl_peak_relaxed=19`, `agagcl_onset_relaxed=13`,
  `agagcl_peak_strict=9`, and empty/skipped Fc/Fc+ profiles.
- Added Cakal/Cihaner/Onal 2020 FTPF/TTPT/STPS DCM peak+onset rows, Oguzturk/Tirkes/Onal
  2015 journal carbazole M1-M4 MeCN peak rows with the M3 value resolved to 0.98 V, and
  Algi et al. 2017 pyridazinedione compounds 5/6 MeCN peak rows.
- Reconciled `data/benchmark_candidates.csv` from 21 to 19 rows by removing four promoted
  Oguzturk 2013 MSc-thesis carbazole candidates and adding two parked rows, including
  Asil/Cihaner/Onal 2009 TTT-Lum excluded for Lewis-acid-modified MeCN + 5% BF3-Et2O.
- Left `configs/tier1.yaml` unchanged and documented that its mock-derived calibration is
  stale relative to strict benchmark v3 pending a real xTB `eps validate --engine xtb
  --all-profiles` refit.
- Updated validation tests and benchmark curation/status docs for strict benchmark v3 and
  the now-met >=30 clean-group target.
- Integrated six verified native-Ag/AgCl monomer-oxidation peak rows into
  `data/benchmark.csv`, moving the strict benchmark from 14 to 20 calibration-eligible
  collapsed groups while keeping `data/benchmark_candidates.csv` at 21 provenance rows.
- Preserved the source-level corrections from the curation report: FSeF is 1.06 V and FSF
  is 1.16 V, and the OSeO/SSeS/SeSeSe source is `J. Electroanal. Chem.` rather than
  `Organic Electronics`.
- Refit `configs/tier1.yaml` from `agagcl_peak_relaxed` with n_points=10:
  slope=0.051941, intercept=1.345652, LOO-CV MAE=0.466255 V.
- Added a regression test showing OSeO and FSeF share canonical SMILES but remain distinct
  calibration groups because their solvents differ.
- Updated `STATUS.md` and the benchmark curation protocol for strict benchmark v2.
- Added profile-driven benchmark calibration with `configs/calibration_profiles.yaml`.
  Profiles now fit independently by `reference_frame`, `label_type`, tier, and medium,
  preventing Ag/AgCl vs Fc/Fc+ pooling and peak/onset co-fitting.
- Added `reference_frame` as the final `data/benchmark.csv` column and set all 14 strict-v1
  rows to `agagcl`; loaders default missing or blank values to `agagcl` for backward
  compatibility.
- Extended validation with optional `label_types` and `reference_frames` filters,
  `run_calibration_profile()`, and `run_all_calibration_profiles()`; empty Fc profiles are
  reported as `skipped_insufficient_points` instead of raising.
- Changed `eps validate` to run the default screening profile by default and added
  `--profile` / `--all-profiles` CLI modes with a profile comparison CSV.
- Added regression tests for reference-frame defaulting, disjoint peak/onset profile group
  sets, profile fit separation, and all-profile skip/report behavior.
- Documented calibration profiles in the benchmark curation protocol and updated
  `STATUS.md` for the profile-driven calibration phase.

## 2026-06-16
- Archived the final benchmark curation report at
  `docs/literature/deep_research_benchmark_finalization_20260616.md` and linked it from
  the status/protocol docs as the provenance basis for strict benchmark v1.
- Changed strict benchmark duplicate group IDs from raw `monomer_smiles + solvent_name +
  label_type` to canonical SMILES + `solvent_name + label_type`, with a regression test
  showing equivalent SMILES collapse into one calibration group.
- Tightened the benchmark protocol's SCE example to require source-internal,
  source-calibrated, or explicitly PI-approved nonaqueous SCE -> Ag/AgCl conversions.
- Implemented strict benchmark v1 from the final curation report: replaced
  `data/benchmark.csv` with 14 benchmark-ready calibration rows and added
  `data/benchmark_candidates.csv` with 21 demoted/excluded/unresolved provenance rows.
- Changed benchmark duplicate collapse to group by canonical SMILES + `solvent_name +
  label_type`, keeping thiophene/acetonitrile peak-like and onset-like labels separate.
- Relaxed source metadata validation so `source_doi` may be blank only when
  `source_doi_or_ref` and `source_locator` are populated; calibration still requires
  explicit reference-conversion metadata.
- Added validation reporting fields for raw rows, calibration-eligible rows, collapsed
  groups, label-type counts, medium-class counts, and a warning when strict groups are
  below the >=30 target.
- Added tests for the 14-row strict benchmark, identity Ag/AgCl conversions, source DOI
  fallback, label-aware grouping, thiophene peak/onset separation, and provenance-file
  exclusion from default calibration.
- Documented "Strict benchmark v1 status" in `docs/benchmark_curation_protocol.md`,
  including the 14-group current state, the unmet >=30 target, candidate-file policy,
  and the rule that onset and peak labels must not be averaged.
- Added explicit benchmark label ontology columns to `data/benchmark.csv` so monomer
  oxidation labels, electropolymerization setpoints, polymer-film labels, and unknown/mixed
  rows cannot be silently blended.
- Strengthened benchmark validation: calibration now requires `calibration_eligible=true`,
  a monomer oxidation `label_type`, converted potential values, and reference-conversion
  metadata; excluded rows remain in reports with `calibration_exclusion_reason`.
- Added `docs/benchmark_curation_protocol.md` with rules and examples for clean monomer
  oxidation benchmarks, reference-electrode conversion metadata, low-confidence rows, and
  unacceptable calibration labels.
- Added validation tests for growth-setpoint exclusion, required exclusion reasons,
  source DOI/locator confidence rules, and eligible-only calibration point counts.
- Recorded the successful Lop/Grid Engine xTB Tier-1 smoke milestone: 1650 audit rows,
  1273 ranked survivors, 152 calculation-failure audit rows, EDOS monomer_Eox/dimerization
  failures across 110 triads, and PF6 anion_Eox failures across 45 triads.
- Removed the brittle wall-clock assertion from the Tier-1 smoke/cache test; functional
  cache and output assertions remain.
- Added `.gitignore` coverage for common scheduler logs, cluster job scripts, and
  `.last_*_jobid` files while keeping generated outputs ignored.
- Made Tier-1 robust to per-property xTB failures: monomer Eox, solvation, optical gap,
  dimerization, and anion Eox exceptions now produce NaN values plus `*_calc_status` and
  `*_calc_error` audit columns instead of aborting the whole screen.
- Tier-1 hard-filter annotation now marks calculation failures as non-survivors with
  `calculation_failed` plus specific reasons such as `monomer_eox_failed`,
  `solvation_failed`, or `anion_eox_failed`; ranked output excludes failed required
  properties while all-triads audit output remains complete.
- Made Tier-1 smoke auditable and calibration-explicit: raw monomer xTB Eox is preserved,
  provisional calibrated monomer Eox is loaded from `configs/tier1.yaml`, the exact filter
  Eox is exposed, and the old `monomer_Eox_V` column is now a backward-compatible alias.
- Added all-triads audit output for Tier-1 runs, including hard-filter booleans,
  `failed_filter_reasons`, raw/calibrated/filter Eox columns, and a zero-survivor CLI
  warning pointing to the audit CSV.
- Refactored Tier-1 hard filters to use `monomer_Eox_filter_V_vs_AgAgCl` for solvent-window
  and anion-stability margins; anion oxidation remains explicitly uncalibrated pending a
  separate benchmark.
- Added Tier-1 audit tests for calibration math, margin source, failure reasons, zero-survivor
  audit behavior, and the backward-compatible `monomer_Eox_V` alias.
- Replaced the conservative seed re-curation with the provided deep-research benchmark
  nucleus verbatim, preserving the superseded CSV as
  `data/benchmark_superseded_codex_v1.csv`.
- Added medium/tier filtering, duplicate collapsing by (monomer, solvent), leave-one-out
  CV, within-group spread reporting, and integrity guards for SMILES parsing, library
  SMILES cross-checks, and native+conversion consistency.
- Changed the Tier-1 PASS/FAIL validation gate to use LOO-CV instead of in-sample MAE,
  while keeping the in-sample metrics for continuity.
- Dropped the EDOT/methanol row to avoid touching the solvent library and retained the
  VNUHCM 2023 3-hexylthiophene row only as Tier C because of source-condition concerns.
- Replaced the old approximate benchmark seed with a full provenance CSV schema for
  monomer oxidation potentials: native potential/reference, potential type, conversion
  constant/source, standardized V vs Ag/AgCl value, medium, conditions, DOI/citation,
  reliability tier, and row-level caveats. Current curated state is deliberately
  conservative: 13 traceable rows, 3 Tier B, 10 Tier C, and 0 Tier A.
- Added `docs/benchmark_methods_memo.md` documenting electrode conversion constants,
  the nonaqueous liquid-junction caveat, the recommendation to migrate nonaqueous
  calibration to Fc/Fc+, the xTB thermodynamic-vs-onset/Epa mismatch, realistic MAE
  expectations, and deliberately excluded monomer families.
- Updated project status to make primary CV recovery, not more mock/xTB plumbing, the
  next benchmark-critical action.
- Recorded the first real cluster xTB validation milestone: SCS Lop/Grid Engine environment confirmed, `xtb/6.4.1` with `--json` and `--alpb <name>` verified on a compute node, `eps run-tier1 --engine mock` completed on the cluster, and `eps validate --engine xtb` completed with MAE 5.398 V before calibration and 0.145 V after in-sample calibration.
- Updated the living project status to make benchmark curation and queue-safe real xTB Tier-1 execution the next priorities.

## 2026-06-15
Back-filled on 2026-06-15 from session history; exact per-milestone dates not recorded.

- M7 — xTB solvent fix + robust JSON parsing: --alpb takes solvent NAMES (removed the invalid numeric-dielectric path); filled xtb_gbsa_name for all solvents incl. nitromethane + 4 nearest-dielectric ALPB proxies; switched energy/gap parsing to xtbout.json with last-match regex fallback; added xtbout.json fixture.
- M6 — Real GFN2-xTB engine: XTBEngine via subprocess (RDKit ETKDG->xyz, adiabatic IP/EA with q/multiplicity rule, solvated redox, GBSA/ALPB solvation), fixture-tested + skipif live test; added structures/geometry.py and xtb_gbsa_name column; CLI --engine {mock,xtb}.
- M5 — Corrected solvent anodic limits: previous derivation reused a stale column and corrupted 6 solvents; replaced with cathodic + spec ESW width (CombHTS table 2.2), all flagged TODO for measured values.
- M4 — Calibration + validation harness: benchmark.csv (seed CV Eox), linear xTB->reference calibration, validation runner reporting MAE before/after vs targets in validation.yaml; `eps validate`.
- M3 — Data/reference fixes: solvent ESW semantics corrected (anodic limit vs width), added potential_reference column + loader warning, water eps_r 80.1, rdkit-pypi -> rdkit.
- M2 — Tier-1 driver + SQLite cache + composite scoring + Pareto + end-to-end mock smoke test (`eps run-tier1`).
- M1 — Engine interface + deterministic MockEngine + pinned redox conversion.
- M0 — Project brief (AGENTS.md), repo scaffold, chemical-space data layer (monomers/solvents/electrolytes CSVs, pydantic models, RDKit-validating loaders).

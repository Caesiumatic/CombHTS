# THINK

THINK.md is the register of OPEN SCIENTIFIC / RESEARCH / DECISION questions for this project — the "why and what-if" layer. It is distinct from STATUS.md (a mutable snapshot of current state) and CHANGELOG.md (append-only history). THINK.md holds only items that require genuine scientific judgment, a tradeoff, or a sign-off — NOT routine engineering debt (those stay in STATUS.md). Entries are opened, updated as thinking evolves, and marked `decided`/`parked` with a resolution; this file is neither a snapshot nor append-only.

_Last updated: 2026-06-17_

## How to read this

Each entry is a question we have not fully resolved. The `Forum` field says who decides: self = objective/rigor call we make and merely report at group meeting; group-meeting = a tradeoff to surface for discussion; PI sign-off = a resource/scope/policy call. The `Cost` field says how expensive resolution is.

| ID | Title | Status | Forum | Cost |
| --- | --- | --- | --- | --- |
| T1 | Screening calibration anchor: peak vs onset | exploring | group-meeting then PI sign-off | scope/policy |
| T2 | Master reference scale: Ag/AgCl vs Fc/Fc+ | open | PI sign-off | scope/policy |
| T3 | Potential-type mismatch sets the accuracy ceiling | open | self (rigor) | lit-curation (no compute) |
| T4 | What ">=30 clean groups" actually validates | open | group-meeting | scope/policy |
| T5 | Which placeholder axis to make real first | decided/done | self (rigor) | scope/policy |
| T6 | Band gap: oligomer + sTDA-xTB (directive route) vs an ML model | exploring | group-meeting | compute-heavy |
| T7 | What is the real deliverable? | open | group-meeting | scope/policy |
| T8 | Chemical-space coverage vs weight tuning | open | group-meeting / PI sign-off | compute-heavy |
| T9 | The mock-preview trap after real-xTB calibration is pinned | open | self (rigor) | lit-curation (no compute) |
| T10 | xTB failure clusters: data problem or engine problem? | decided | self (rigor) | one xTB round |
| T11 | Should the computed solvent anodic limit share the monomer calibration / live on the same scale? | decided | group-meeting | scope/policy |

## T1 — Screening calibration anchor: peak vs onset
- **Status**: exploring
- **Forum**: group-meeting then PI sign-off
- **Cost**: scope/policy
- **Question**: Which calibration profile should convert every xTB Eox in the screen — `agagcl_peak_strict` (Epa) or `agagcl_onset_relaxed` (Eonset)?
- **Why it matters**: This single line defines the Eox the whole 50k-triad screen believes; it feeds the constraint-① window filter and the highest composite weight (0.30). Peak vs onset shifts BOTH slope and intercept, so it reshapes the ranking, not just offsets it.
- **Thinking / options**: Onset is physically closer to where electropolymerization initiates (more faithful to "Eox inside solvent window"). The conditioning / sample-size argument says more points => better-conditioned linear fit; it favors `agagcl_peak_relaxed` (n=19, tiers A+B) over `agagcl_onset_relaxed` (n=13, tiers A+B), and explicitly does NOT support `agagcl_peak_strict` (n=9, tier A only). The purity argument favors `agagcl_peak_strict` because it uses tier-A native-Ag/AgCl rows only, at the cost of the smallest n. xTB adiabatic IP is conceptually an E1/2, sitting between onset and peak, so neither matches perfectly. The repo is also internally inconsistent on this exact question: `configs/tier1.yaml` implements the screen's monomer-Eox calibration from profile `agagcl_peak_strict` (slope=0.725837, intercept=-3.145372), but `configs/calibration_profiles.yaml` sets `default_screening_profile: agagcl_peak_relaxed`. Consequence: a default `eps validate` reports a peak_relaxed fit, while the actual 50k-triad screen's constraint-(1) window filter uses the peak_strict calibration baked into `tier1.yaml`.
- **Current lean**: `agagcl_peak_strict`, pending sign-off. This lean is chosen on PURITY grounds, not on sample size; the sample-size argument would instead point to `agagcl_peak_relaxed`.
- **Resolves when**: The group discusses peak vs onset, the PI signs off on the screening calibration anchor, and `configs/tier1.yaml` plus `configs/calibration_profiles.yaml` are reconciled onto one agreed anchor.
- **Links**: [STATUS open debts #3 and #13](STATUS.md#open-debts); [configs/calibration_profiles.yaml](configs/calibration_profiles.yaml); [configs/tier1.yaml](configs/tier1.yaml).

## T2 — Master reference scale: Ag/AgCl vs Fc/Fc+
- **Status**: open
- **Forum**: PI sign-off
- **Cost**: scope/policy
- **Question**: Keep aqueous Ag/AgCl as the benchmark master scale, or fund a separate Fc/Fc+ track for nonaqueous data?
- **Why it matters**: Most clean nonaqueous monomer CVs are reported vs Fc/Fc+; staying Ag/AgCl-only blocks data growth, while force-converting nonaqueous SCE/Ag/Ag+ rows injects liquid-junction error comparable to the model error we are trying to measure.
- **Thinking / options**: In y = a·x + b, the intercept b absorbs the scale's reference offset, so two scales need two fits — pooling Ag/AgCl and Fc/Fc+ into one line is algebraically wrong, not just untidy. The xTB prediction x is scale-agnostic, so a Fc/Fc+ track costs almost nothing: native-Fc rows enter as-is, the intercept eats the offset, and the pinned 4.28/-0.197 projection is used only once at screening output.
- **Current lean**: Dual-scale — keep Ag/AgCl output, track Fc/Fc+ for nonaqueous curation; `fc_*` profiles already stubbed and auto-skip until clean native-Fc rows exist.
- **Resolves when**: The PI signs off on either Ag/AgCl-only curation or a separate Fc/Fc+ benchmark/calibration track.
- **Links**: [STATUS open debt #4](STATUS.md#open-debts); [docs/benchmark_methods_memo.md](docs/benchmark_methods_memo.md#recommendation-on-master-scale).

## T3 — Potential-type mismatch sets the accuracy ceiling
- **Status**: open
- **Forum**: self (rigor)
- **Cost**: lit-curation (no compute)
- **Question**: How accurate can xTB-after-calibration honestly be, given what it computes vs what the benchmark measures?
- **Why it matters**: Prevents over-claiming. The 0.30 V Tier-1 MAE gate is an aspirational engineering target, not a demonstrated accuracy.
- **Thinking / options**: xTB adiabatic IP -> a thermodynamic one-electron E1/2; benchmark values are kinetic, irreversible Epa/onset shifted by follow-up radical chemistry, adsorption, nucleation, scan rate. A linear fit removes the ~constant part; the residual ~0.2 V spread is the irreducible label/medium noise. Defensible near-term target is 0.3–0.5 V MAE for onset/Epa-heavy nonaqueous data.
- **Current lean**: Report LOO-CV MAE and within-group spread together; never claim < 0.3 V.
- **Resolves when**: The limitation is consistently documented in validation/status language and reported alongside calibration metrics.
- **Links**: [docs/benchmark_methods_memo.md, "Potential Type Mismatch"](docs/benchmark_methods_memo.md#potential-type-mismatch); [docs/benchmark_methods_memo.md, "Accuracy Expectation"](docs/benchmark_methods_memo.md#accuracy-expectation).

## T4 — What ">=30 clean groups" actually validates
- **Status**: open
- **Forum**: group-meeting
- **Cost**: scope/policy
- **Question**: Is the >=30 target a CALIBRATION-purity requirement or a VALIDATION-coverage requirement, and are we calibrating the way the brief intends?
- **Why it matters**: If >=30 is a validation requirement, we should not be straining benchmark purity to feed the calibration fit; the pressure is on the wrong layer.
- **Thinking / options**: The brief's design is two-stage — calibrate xTB->DFT (self-generated y-values, no reference-electrode heterogeneity, unlimited points), then validate the whole pipeline against experimental CV (>=30 rows, MAE + qualitative rank-order). Because Tier-2 DFT is not built yet, we collapsed calibration to xTB->experimental, which wrongly pushed the >=30 reference-purity burden onto the calibration training set. Tension with STATUS: STATUS open debt #1 treats the ">=30 clean groups" target as MET / a milestone, whereas T4 questions whether ">=30" should sit on the calibration-purity layer at all.
- **Current lean**: Record this as the framing to raise; treat current xTB->experimental fit as an explicit interim stand-in until the DFT tier exists.
- **Resolves when**: The group agrees whether >=30 governs calibration purity, validation coverage, or both, and whether the interim xTB->experimental fit remains acceptable.
- **Links**: [STATUS open debts #1 and #12](STATUS.md#open-debts); [configs/tier1.yaml](configs/tier1.yaml).

## T5 — Which placeholder axis to make real first
- **Status**: decided/done (all five axes now real; remaining work is calibration, not realism)
- **Forum**: self (rigor)
- **Cost**: scope/policy
- **Question**: Four of the five ranking axes were placeholders — which to upgrade, in what order?
- **Why it matters**: STATUS warned ranked output is not a recommendation while these were fake; the composite was contaminated by them.
- **Thinking / options**: Solvent anodic limits (top weight 0.30) were the lowest-effort fix — a COMPUTED adiabatic ΔSCF over the solvent molecules, done first (CHANGELOG 2026-06-17). The remaining two structure-aware axes were then made real together via the directive's oligomer route (see T6): `optical_gap` = sTDA-xTB (or HOMO-LUMO proxy) gap of the assembled n=6 oligomer, and `dimerization_dG` = the xTB radical-radical coupling ΔG of the α,α' dimer. `anion_Eox` is on the shared oxidation calibration (T11).
- **Current lean**: All five composite axes are now real physics (screening-grade). The open work is no longer "make axes real" but "calibrate / validate them": optical gap vs TD-DFT (Step-2), dimerization's absolute proton constant, and the approximate coupling regiochemistries (aniline, D-A, the 2,3-dioxy monomers.csv data issue).
- **Resolves when**: Treated as the realism milestone being complete; calibration/validation tracked separately (T6 for band gap, T11 for oxidation scale, the monomers.csv dioxy data-curation item).
- **Links**: [STATUS open debts #6 and #11](STATUS.md#open-debts); [data/polymerization.csv](data/polymerization.csv); [src/eps/structures/oligomer.py](src/eps/structures/oligomer.py); [src/eps/properties/calculators.py](src/eps/properties/calculators.py).

## T6 — Band gap: oligomer + sTDA-xTB (directive route) vs an ML model
- **Status**: exploring (directive route implemented; ML alternative parked, not needed to proceed)
- **Forum**: group-meeting
- **Cost**: compute-heavy
- **Question**: Reach the polymer band gap via real oligomer assembly -> sTDA-xTB, or via a trained ML/GNN predictor?
- **Why it matters**: `optical_gap` drives the `band_gap_deviation` scoring term; it was a monomer MMFF HOMO-LUMO placeholder.
- **Thinking / options**: We took the DIRECTIVE's route for now: assemble the n=6 oligomer (RDKit α-coupling — `stk` substitution, documented) and take the sTDA-xTB lowest singlet excitation, with the oligomer GFN2-xTB HOMO-LUMO gap as a flagged proxy until `stda` is confirmed on the cluster. This is implemented and screening-grade (uncalibrated vs TD-DFT). The mentors' ML/GNN direction may be the more durable long-term route for the AI-foundation goal, but it is NOT needed to proceed and remains the open fork only if we later choose to deviate. The directive also wants the sTDA gap calibrated vs a TD-DFT reference — deferred to Step-2 (a calibration hook mirrors the solvent-limit "compute now, calibrate later" pattern).
- **Current lean**: Proceed on the directive's oligomer + sTDA-xTB route; revisit ML only if the screening-grade gap proves insufficient. Calibrate vs TD-DFT in Step-2.
- **Resolves when**: The group accepts the oligomer/sTDA route (with TD-DFT calibration as Step-2) or explicitly chooses to pivot to an ML/GNN predictor.
- **Links**: [STATUS open debt #11](STATUS.md#open-debts); [src/eps/structures/oligomer.py](src/eps/structures/oligomer.py); [src/eps/engines/xtb.py](src/eps/engines/xtb.py).

## T7 — What is the real deliverable?
- **Status**: open
- **Forum**: group-meeting
- **Cost**: scope/policy
- **Question**: Is the deliverable the composite ranking, or a clean, reproducible, real-physics per-species descriptor table plus a small set of trusted experimental anchors?
- **Why it matters**: If the screen is a foundation for downstream AI/ML, the composite is just a heuristic the model will re-weight; the durable asset is the descriptor table + coverage, so priority should be "make each axis real + expand coverage", not tune weights.
- **Thinking / options**: Composite-first keeps attention on ranking triads. Descriptor-table-first treats the ranking as a diagnostic and puts priority on real per-species axes plus trusted anchors.
- **Current lean**: Treat the descriptor table as the primary product; composite as a diagnostic.
- **Resolves when**: The group agrees which deliverable should drive prioritization, status language, and next actions.
- **Links**: [README objective](README.md#objective); [AGENTS.md architecture principles](AGENTS.md#architecture-principles-do-not-violate).

## T8 — Chemical-space coverage vs weight tuning
- **Status**: open
- **Forum**: group-meeting / PI sign-off
- **Cost**: compute-heavy
- **Question**: When and how to scale from 15×11×10 toward the spec's ~100×30×25?
- **Why it matters**: A downstream model can learn weights but cannot learn data that does not exist; coverage likely matters more than composite-weight tuning.
- **Thinking / options**: Coverage expansion + a real-xTB harvest outputs a reusable descriptor table. Composite refinement tunes the present heuristic before the target chemical space exists.
- **Current lean**: Prioritize coverage expansion + a real-xTB harvest that outputs a reusable descriptor table, over composite refinement.
- **Resolves when**: The group/PI chooses a scale-up target and resource plan for moving toward the specified chemical space.
- **Links**: [STATUS open debt #12](STATUS.md#open-debts); [AGENTS.md target space](AGENTS.md).

## T9 — The mock-preview trap after real-xTB calibration is pinned
- **Status**: open
- **Forum**: self (rigor)
- **Cost**: lit-curation (no compute)
- **Question**: Why does `eps run-tier1 --engine mock` no longer give a meaningful science preview?
- **Why it matters**: `tier1.yaml`'s calibration (slope 0.726, intercept -3.145) was fit on REAL xTB predictions, whose raw Eox is ~5 V too high; applied to mock raw values it yields meaningless/negative Eox. Tests don't catch this because they only assert survivors > 0.
- **Thinking / options**: Keep using mock for pipeline smoke tests only; use real xTB for any scientific preview once real-xTB calibration is pinned.
- **Current lean**: Mock is now pipeline-smoke only; any scientific preview must use real xTB.
- **Resolves when**: CLI/status language makes the mock-vs-science boundary explicit enough that a mock run is not misread as a ranking preview.
- **Links**: [configs/tier1.yaml](configs/tier1.yaml); [CHANGELOG 2026-06-17](CHANGELOG.md#2026-06-17).

## T10 — xTB failure clusters: data problem or engine problem?
- **Status**: decided — both clusters were input/settings issues, not a method problem; confirmed by a fully-clean real-xTB harvest (0 failures across all seven stages).
- **Forum**: self (rigor)
- **Cost**: one xTB round
- **Question**: Are the 152 Tier-1 smoke failures a chemistry/data issue or an engine/method issue?
- **Why it matters**: Determines whether we fix inputs or the engine path before any large run.
- **Thinking / options**: Two clusters — EDOS (selenophene-dioxy) `monomer_eox` + dimerization fail across 110 triads (RDKit embedding vs xTB SCF on [se] systems?); PF6 `anion_eox` fails across 45 triads in propylene carbonate / DMSO / sulfolane, all high-dielectric and all using ALPB proxies (PC/sulfolane -> dmso) — likely a -1 anion non-convergence under a proxy ALPB. Related: whether the 4 ALPB proxy solvents are acceptable or we move to ddCOSMO with manual epsilon (PI sign-off).
- **Resolution (both are INPUT/settings issues, not a method problem)**:
  - EDOS `monomer_eox` + `dimerization` failures were RDKit force-field geometry corruption, NOT xTB/SCF. `geometry.py` ran UFF whenever MMFF lacked params, but for Se BOTH MMFF and UFF fail to type the atom ("Unrecognized atom type: Se2+2"); UFF then collapsed the clean ETKDG embedding to a ~0.26 Å atom clash, so xTB aborted geometry optimization ("|grad| > 500, something is totally wrong!", exit 128). The single-point `optical_gap` only "succeeded" because it ran `--no-opt` on the clashed geometry, so its cached value was also garbage. Fixed by skipping FF pre-optimization when no classical FF can type every atom and handing the clean ETKDG geometry (~1.0 Å min distance) to xTB, whose GFN2 optimizer handles Se.
  - PF6 / high-dielectric `anion_eox` failures were already resolved by the SCF-robustness flags (`--iterations 500 --etemp 400`): the real-xTB harvest shows 0 anion_eox failures.
- **Conclusion**: No move to ddCOSMO is needed for these clusters; both are addressed without changing the method.
- **Resolved (2026-06-17)**: The first fully-clean real-xTB Tier-1 harvest on the SCS Lop cluster (cache rebuilt from scratch after the EDOS/Se geometry fix) ran 1650 triads with ZERO calculation failures across all seven per-property stages (`monomer_Eox`, `solvation`, `optical_gap`, `dimerization`, `solvent_anodic_limit`, `solvent_cathodic_limit`, `anion_Eox`) and 1007 surviving triads. EDOS now computes (calibrated Eox ~1.47 V), confirming 0 EDOS geometry failures; and 0 anion failures confirms the SCF-robustness flags already fixed the PF6/high-ε cluster. Both clusters are closed without a method change.
- **Links**: [STATUS open debts #7, #8, and #9](STATUS.md#open-debts); [CHANGELOG 2026-06-16](CHANGELOG.md#2026-06-16); [src/eps/structures/geometry.py](src/eps/structures/geometry.py).

## T11 — Should the computed solvent anodic limit share the monomer calibration / live on the same scale?
- **Status**: decided (group will be informed, not blocking)
- **Forum**: group-meeting
- **Cost**: scope/policy
- **Question**: Should the newly computed solvent anodic limit be put through the same calibrated linear model as monomer Eox so the two sit on one scale, or stay raw?
- **Why it matters**: The Tier-1 window filter compares the two directly — `window_margin_V = solvent_anodic_limit_V − monomer_Eox_filter_V_vs_AgAgCl`. If one side is calibrated and the other is raw, the margin (and the 0.3 V gate, the spec §4.1 constraint ①) is computed across a scale mismatch.
- **Decision**: Apply the SINGLE oxidation calibration in `configs/tier1.yaml` (slope=0.725837, intercept=-3.145372) to ALL computed OXIDATION potentials — monomer Eox, solvent ANODIC limit, and anion Eox — so every oxidation potential in the screen lives on one calibrated V-vs-Ag/AgCl scale (option (a), generalized to monomer+solvent+anion). This is what spec §4.1 directs ("apply the SAME calibrated linear model to monomers AND solvents"). The solvent CATHODIC limit is a REDUCTION potential and is explicitly EXCLUDED — it stays raw/informational.
- **Rationale**: In every margin the intercept cancels (both `window_margin` and `anion_stability_margin` are differences of calibrated potentials), so the filter decisions are governed by raw IP differences and are robust to the extrapolation. This also resolves a latent no-op: the anion Eox was previously raw while monomer Eox was calibrated, so `anion_stability_margin` mixed scales and the anion-stability filter was effectively inert; putting the anion on the shared calibration makes that filter LIVE. The window filter is likewise now on one scale.
- **Caveat (preserved in docs)**: The calibration was fit on monomer data only, so the ABSOLUTE calibrated solvent/anion numbers are screening-grade extrapolations. A future solvent/anion benchmark is the eventual refinement (deferred), not a blocker for the screen.
- **Resolved**: 2026-06-17 — implemented; the group will be informed at the next meeting (decision is not blocking).
- **Links**: [T5](#t5--which-placeholder-axis-to-make-real-first); [T9](#t9--the-mock-preview-trap-after-real-xtb-calibration-is-pinned); [configs/tier1.yaml](configs/tier1.yaml); spec §4.1.

## Decision log

- 2026-06-17 — [T1](#t1--screening-calibration-anchor-peak-vs-onset) advanced: `configs/tier1.yaml` was pinned to a real GFN2-xTB `agagcl_peak_strict` fit (slope=0.725837, intercept=-3.145372, LOO-CV MAE=0.197 V) as the screening anchor; PROVISIONAL / pending PI sign-off.
- 2026-06-17 — [T5](#t5--which-placeholder-axis-to-make-real-first) advanced and corrected: solvent anodic/cathodic limits are now COMPUTED per spec §3.2 (adiabatic ΔSCF on the solvent molecule via the cached Engine), not a literature curation; the residual scale question was split out as the new [T11](#t11--should-the-computed-solvent-anodic-limit-share-the-monomer-calibration--live-on-the-same-scale).
- 2026-06-17 — [T11](#t11--should-the-computed-solvent-anodic-limit-share-the-monomer-calibration--live-on-the-same-scale) opened: the computed solvent anodic limit is left RAW while monomer Eox is calibrated, so `window_margin_V` currently mixes scales; spec §4.1 vs the monomer-only calibration fit is unresolved.
- 2026-06-17 — [T11](#t11--should-the-computed-solvent-anodic-limit-share-the-monomer-calibration--live-on-the-same-scale) DECIDED: apply the single `configs/tier1.yaml` oxidation calibration to all computed oxidation potentials (monomer Eox, solvent anodic limit, anion Eox); intercept cancels in every margin, so filters are governed by raw IP differences (spec §4.1). Solvent cathodic/reduction limit stays raw. Also makes the previously inert anion-stability filter LIVE. Absolute calibrated solvent/anion values are screening-grade extrapolations pending a future benchmark; group to be informed, not blocking.
- 2026-06-17 — [T10](#t10--xtb-failure-clusters-data-problem-or-engine-problem) advanced (open → exploring): both smoke/harvest failure clusters explained as INPUT/settings issues, not a method problem. EDOS `monomer_eox`/`dimerization` failures were RDKit FF geometry corruption (MMFF/UFF cannot type Se → UFF collapsed the ETKDG geometry to a ~0.26 Å clash → xTB geometry-opt abort); fixed in `geometry.py` by skipping FF pre-optimization when no FF has params and handing the clean ETKDG geometry to xTB. PF6/high-ε `anion_eox` failures were already cured by `--iterations 500 --etemp 400` (0 anion failures in the real-xTB harvest). No ddCOSMO move needed; full "decided" pending a cluster re-run confirming 0 EDOS failures.
- 2026-06-17 — [T10](#t10--xtb-failure-clusters-data-problem-or-engine-problem) DECIDED: the first fully-clean real-xTB Tier-1 harvest on Lop (cache rebuilt from scratch) ran 1650 triads with 0 calculation failures across all seven per-property stages and 1007 survivors. EDOS computes (calibrated Eox ~1.47 V) → 0 EDOS geometry failures confirmed; 0 anion failures confirmed. Both clusters closed without a method change; no ddCOSMO needed.
- 2026-06-17 — [T3](#t3--potential-type-mismatch-sets-the-accuracy-ceiling) supported (no decision change): validation now reports LOO-CV MAE alongside residual std, within-group spread, Spearman ρ, worst-5, and per-family MAE, and `docs/validation_memo_<date>.md` carries the "never claim < 0.3 V" caveat — making the accuracy-ceiling limitation visible where the numbers are reported.

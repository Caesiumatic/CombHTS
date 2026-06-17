# THINK

THINK.md is the register of OPEN SCIENTIFIC / RESEARCH / DECISION questions for this project — the "why and what-if" layer. It is distinct from STATUS.md (a mutable snapshot of current state) and CHANGELOG.md (append-only history). THINK.md holds only items that require genuine scientific judgment, a tradeoff, or a sign-off — NOT routine engineering debt (those stay in STATUS.md). Entries are opened, updated as thinking evolves, and marked `decided`/`parked` with a resolution; this file is neither a snapshot nor append-only.

_Last updated: 2026-06-17_

## How to read this

Each entry is a question we have not fully resolved. The `Forum` field says who decides: self = objective/rigor call we make and merely report at group meeting; group-meeting = a tradeoff to surface for discussion; PI sign-off = a resource/scope/policy call. The `Cost` field says how expensive resolution is.

| ID | Title | Status | Forum | Cost |
| --- | --- | --- | --- | --- |
| T1 | Screening calibration anchor: peak vs onset | open | group-meeting then PI sign-off | scope/policy |
| T2 | Master reference scale: Ag/AgCl vs Fc/Fc+ | open | PI sign-off | scope/policy |
| T3 | Potential-type mismatch sets the accuracy ceiling | open | self (rigor) | lit-curation (no compute) |
| T4 | What ">=30 clean groups" actually validates | open | group-meeting | scope/policy |
| T5 | Which placeholder axis to make real first | open | self (rigor) | scope/policy |
| T6 | Band gap: fake oligomer assembly vs an ML model | open | group-meeting | compute-heavy |
| T7 | What is the real deliverable? | open | group-meeting | scope/policy |
| T8 | Chemical-space coverage vs weight tuning | open | group-meeting / PI sign-off | compute-heavy |
| T9 | The mock-preview trap after real-xTB calibration is pinned | open | self (rigor) | lit-curation (no compute) |
| T10 | xTB failure clusters: data problem or engine problem? | open | self (rigor) | one xTB round |

## T1 — Screening calibration anchor: peak vs onset
- **Status**: open
- **Forum**: group-meeting then PI sign-off
- **Cost**: scope/policy
- **Question**: Which calibration profile should convert every xTB Eox in the screen — `agagcl_peak_strict` (Epa) or `agagcl_onset_relaxed` (Eonset)?
- **Why it matters**: This single line defines the Eox the whole 50k-triad screen believes; it feeds the constraint-① window filter and the highest composite weight (0.30). Peak vs onset shifts BOTH slope and intercept, so it reshapes the ranking, not just offsets it.
- **Thinking / options**: Onset is physically closer to where electropolymerization initiates (more faithful to "Eox inside solvent window"); peak has wider chemical diversity (n=19 vs 13), so the linear fit is better conditioned. xTB adiabatic IP is conceptually an E1/2, sitting between onset and peak, so neither matches perfectly.
- **Current lean**: `agagcl_peak_strict` (current `tier1.yaml` default), pending sign-off.
- **Resolves when**: The group discusses peak vs onset and the PI signs off on the screening calibration anchor.
- **Links**: [STATUS open debt #3](STATUS.md#open-debts); [configs/calibration_profiles.yaml](configs/calibration_profiles.yaml); [configs/tier1.yaml](configs/tier1.yaml).

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
- **Thinking / options**: The brief's design is two-stage — calibrate xTB->DFT (self-generated y-values, no reference-electrode heterogeneity, unlimited points), then validate the whole pipeline against experimental CV (>=30 rows, MAE + qualitative rank-order). Because Tier-2 DFT is not built yet, we collapsed calibration to xTB->experimental, which wrongly pushed the >=30 reference-purity burden onto the calibration training set.
- **Current lean**: Record this as the framing to raise; treat current xTB->experimental fit as an explicit interim stand-in until the DFT tier exists.
- **Resolves when**: The group agrees whether >=30 governs calibration purity, validation coverage, or both, and whether the interim xTB->experimental fit remains acceptable.
- **Links**: [STATUS open debt #12](STATUS.md#open-debts); [configs/tier1.yaml](configs/tier1.yaml).

## T5 — Which placeholder axis to make real first
- **Status**: open
- **Forum**: self (rigor)
- **Cost**: scope/policy
- **Question**: Four of the five ranking axes are placeholders — which to upgrade first?
- **Why it matters**: STATUS already warns ranked output is not a recommendation while these are fake; the composite is contaminated by them.
- **Thinking / options**: Solvent anodic limits feed the top weight (0.30) and are the cheapest fix (literature curation, zero compute, no PI) — best ROI, lights up the other half of constraint ①. `anion_Eox` needs its own benchmark + one xTB round. `optical_gap` and `dimerization_dG` are the hard, structure-aware upgrades (see T6).
- **Current lean**: Solvent anodic limits next, then anion benchmark.
- **Resolves when**: The next placeholder upgrade is selected and either opened as concrete work or explicitly parked behind another priority.
- **Links**: [STATUS open debts #6 and #11](STATUS.md#open-debts); [data/solvents.csv](data/solvents.csv); [src/eps/properties/calculators.py](src/eps/properties/calculators.py).

## T6 — Band gap: fake oligomer assembly vs an ML model
- **Status**: open
- **Forum**: group-meeting
- **Cost**: compute-heavy
- **Question**: Reach the polymer band gap via real oligomer assembly -> TD/sTDA, or via a trained ML/GNN predictor?
- **Why it matters**: `optical_gap` is currently a monomer MMFF HOMO-LUMO gap — not an optical gap, not an oligomer. It directly drives the `band_gap_deviation` scoring term.
- **Thinking / options**: Oligomer assembly (`stk` + geometry + excited-state) is heavy and approximate; the mentors' direction (polymer structure/property DB + generative/ML) suggests a learned predictor may be the more durable route for the AI-foundation goal.
- **Current lean**: None yet; flag as a strategic fork for the meeting.
- **Resolves when**: The group chooses an oligomer/TD-sTDA route, an ML/GNN route, or parks band-gap realism behind a nearer-term descriptor-table milestone.
- **Links**: [STATUS open debt #11](STATUS.md#open-debts).

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
- **Status**: open
- **Forum**: self (rigor)
- **Cost**: one xTB round
- **Question**: Are the 152 Tier-1 smoke failures a chemistry/data issue or an engine/method issue?
- **Why it matters**: Determines whether we fix inputs or the engine path before any large run.
- **Thinking / options**: Two clusters — EDOS (selenophene-dioxy) `monomer_eox` + dimerization fail across 110 triads (RDKit embedding vs xTB SCF on [se] systems?); PF6 `anion_eox` fails across 45 triads in propylene carbonate / DMSO / sulfolane, all high-dielectric and all using ALPB proxies (PC/sulfolane -> dmso) — likely a -1 anion non-convergence under a proxy ALPB. Related: whether the 4 ALPB proxy solvents are acceptable or we move to ddCOSMO with manual epsilon (PI sign-off).
- **Current lean**: Reproduce one minimal EDOS and one minimal PF6/high-ε case before scaling.
- **Resolves when**: Minimal reproductions show whether the failures come from inputs/structures, xTB convergence settings, ALPB proxy choices, or a need to move methods.
- **Links**: [STATUS open debts #7, #8, and #9](STATUS.md#open-debts); [CHANGELOG 2026-06-16](CHANGELOG.md#2026-06-16).

## Decision log

- None yet.

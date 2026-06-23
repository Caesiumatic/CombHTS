# CombHTS Code Structure

## 1. Project Purpose

CombHTS screens monomer-solvent-electrolyte triads for electropolymerization under
`Directive_CombHTS`. The production ranking enforces three hard constraints: monomer oxidation
potential inside the solvent electrochemical window, electrolyte anion stability at that potential,
and a solvation/solubility proxy for monomer-medium compatibility. It then ranks surviving triads
with a weighted composite score that includes secondary polymer quality descriptors such as optical
gap, dimerization/radical-coupling energy, and related diagnostic axes.

## 2. Current Scientific State

- A real Tier-1 xTB harvest exists for the current 36 x 13 x 16 library, and the corrected
  salt-role-fixed re-score is the current production ranking state.
- The salt-role supporting-electrolyte gate and measured-first conservative solvent-window gate are
  implemented. Measured windows may tighten production eligibility; sparse generic windows must not
  admit rows by widening a measured-safe gate.
- Section 7 validation workflow/reporting is integrated through `eps validate-directive`. The real
  validation package records active monomer Eox performance as passing the configured directive
  target, raw isolated-solvent ESW descriptors as failing practical-window accuracy, and qualitative
  feasibility as not yet testable from the small matched label set.
- Section 7 staging audit is integrated as review-only curation under `data/lit_curation/` and
  `docs/research/`; it does not promote rows into production CSVs.
- Tier-2 pilot orchestration is integrated as a mock-first, array-safe Gaussian scaffold with
  plan, one-task run, and harvest steps. No real Tier-2 scientific values are currently promoted.
- SGE 417587 completed the ORCA neutral-dimer optical baseline for six anchors, but the
  dimer-vs-polymer fits are weak. The optical axis remains diagnostic, and no optical scoring or
  calibration policy changed.

Do not overread the current state: the project has useful validation evidence and a real Tier-1
ranking, but several scientific axes remain diagnostic or underpowered.

## 3. Repository Top-Level Layout

| Path | Role |
| --- | --- |
| `src/` | Source-layout Python package root. `src/eps` is the installed package. |
| `tests/` | Pytest coverage for loaders, calculators, engines, workflows, validation, and CLI-adjacent behavior. |
| `data/` | Versioned production CSV libraries and benchmark tables. Treat production CSV edits as scientific changes. |
| `data/lit_curation/` | Staging and review curation data. These files can support later promotion decisions but are not production inputs by default. |
| `configs/` | YAML thresholds, weights, validation profiles, Tier-2/Tier-3 route settings, and pilot settings. Treat threshold/weight/calibration changes as scientific changes. |
| `scripts/` | SGE templates, local audit helpers, and one-off analysis runners. Scripts should preserve mock-first and run-manifest conventions. |
| `docs/` | Project documentation, route notes, audits, and maintenance records. |
| `docs/runs/` | Versioned facts for real and mock runs whose artifacts live in gitignored `outputs/`. |
| `docs/research/` | Scientific curation notes, literature rationale, validation plans, and research decisions. |
| `docs/maintenance/` | Engineering/integration reviews and repository hygiene records. |
| `outputs/` | Gitignored local and cluster artifacts: harvest CSVs, caches, plots, logs, and raw engine outputs. Never commit heavy outputs or caches. |

## 4. Python Package Map: `src/eps`

| Package/file | Purpose | Key files | Main public functions/classes | Must not decide scientifically |
| --- | --- | --- | --- | --- |
| `eps.cli` | Single argparse entrypoint for all command-line workflows. | `src/eps/cli.py` | `main`, `_engine_from_name`, `_dft_calibration_engines` | Should not hide policy changes in CLI defaults, rename public commands casually, or move scientific thresholds out of YAML/data files. |
| `eps.chemspace` | Typed loading and validation of monomer, solvent, and electrolyte libraries. | `chemspace/models.py`, `chemspace/loaders.py` | `Monomer`, `Solvent`, `Electrolyte`, `load_monomers`, `load_solvents`, `load_electrolytes` | Must not promote staging rows, invent missing chemistry, or silently reinterpret CSV units. |
| `eps.curation` | Importable helpers for staging/review-only literature curation audits. | `curation/staging_audit.py` | `audit_staging`, `canonicalize_smiles`, `StagingSpec` | Must not promote staging rows into production data or treat review classifications as scoring policy. |
| `eps.engines` | Engine abstraction and concrete mock/xTB/Gaussian/ORCA backends. | `engines/base.py`, `mock.py`, `xtb.py`, `gaussian.py`, `orca.py` | `Engine`, `CalcRequest`, `CalcResult`, `SpeciesSpec`, `MockEngine`, `XTBEngine`, `GaussianEngine`, `OrcaEngine` | Must not change cache identity, method labels, failure handling, or route settings without explicit scientific review. |
| `eps.properties` | Per-species property calculators and descriptor helpers. | `calculators.py`, `redox.py`, `solvent_windows.py`, `oligomer_series.py`, `optical_convergence.py`, `secondary_descriptors.py` | `monomer_eox_vs_AgAgCl`, `solvent_anodic_limit`, `anion_oxidation_potential`, `monomer_solvation`, `polymer_optical_gap`, `dimerization_dG`, `compute_oligomer_eox_series` | Must not define production weights, thresholds, or calibration policy outside config and pinned redox conversion functions. |
| `eps.structures` | RDKit structure generation, alpha-coupling oligomer assembly, and XYZ helpers. | `structures/geometry.py`, `structures/oligomer.py` | `ConformerSearchConfig`, `smiles_to_xyz`, `PolymerizationSpec`, `load_polymerization_specs`, `oligomer_smiles`, `oligomer_xyz` | Must not decide whether a candidate passes filters or receives scoring credit. |
| `eps.scoring` | Composite score arithmetic, Pareto flags, and salt/cation degeneracy collapse. | `scoring/composite.py` | `load_scoring_config`, `add_composite_score`, `collapse_cation_degenerate_rows`, `is_pareto_front` | Must not change weights, component meanings, or normalization behavior without an authorized scoring task. |
| `eps.workflow` | Stage orchestration that combines library rows, per-species calculations, joins, filters, and report outputs. | `workflow/tier1.py`, `tier1_rescore.py`, `dft_calibration.py`, `tier2.py`, `tier3.py`, `orca_pilots.py` | `run_tier1`, `rescore_tier1_harvest`, `run_dft_calibration`, `plan_tier2_pilot`, `run_tier2_task`, `harvest_tier2_results`, `run_tier2_refined_screen`, `write_tier3_dft_inputs`, ORCA pilot runners | Must preserve compute-per-species design; never run expensive engines per triad; never fill missing refined values with Tier-1 stand-ins unless an explicit workflow says so. |
| `eps.validation` | Benchmark, directive, feasibility, solvent-window, memo, and physical sanity reporting. | `validation/benchmark.py`, `directive.py`, `feasibility.py`, `solvent_benchmark.py`, `memo.py`, `sanity.py` | `run_benchmark_validation`, `run_directive_validation`, `compute_feasibility_metric`, `compute_solvent_esw_mae`, `write_validation_memo`, `run_physical_sanity_checks` | Must report evidence and caveats, not silently alter production scoring or promote diagnostic axes. |
| `eps.analysis` | Read-only post-processing for harvests: summaries, shortlists, plots, and chemical-space maps. | `analysis/summary.py`, `analysis/plots.py` | `run_analyze`, `compute_summary`, `build_shortlist`, plotting helpers | Must not modify harvests or turn diagnostic plots into production policy. |
| `eps.storage` | SQLite cache contract for idempotent engine calls. | `storage/cache.py` | `CacheKey`, `SQLiteCache`, `cached_run` | Must not cache incomplete/failed jobs as valid results or change key semantics casually. |
| `eps.provenance` | Git/config/data provenance recording for run artifacts. | `provenance.py` | `write_provenance`, `git_info`, `config_hashes`, `library_sizes` | Must not omit engine/method/config context for scientific artifacts. |
| `eps.doctor` | Local environment/config preflight checks. | `doctor.py` | `run_doctor`, `DoctorCheck`, `DoctorReport` | Must not be treated as scientific validation; it is an environment and configuration health check. |

## 5. Workflow Map

| Workflow | Input files | Output files | Engine use | Mock capable | Classification |
| --- | --- | --- | --- | --- | --- |
| `eps doctor` | Project root, configs, optional local binaries | Terminal report | No engine execution | Not applicable | Environment/docs hygiene |
| `eps run-tier1` | `data/monomers.csv`, `data/solvents.csv`, `data/electrolytes.csv`, `data/polymerization.csv`, `configs/tier1.yaml`, `configs/scoring.yaml` | `outputs/tier1_ranked.csv` by default, optional all-triads CSV, descriptor artifacts, provenance sidecars | Mock or xTB through `Engine` | Yes | Production screen when real xTB; smoke when mock |
| `eps rescore-tier1` | Existing all-triads harvest CSV, `configs/tier1.yaml`, `configs/scoring.yaml` | Re-ranked CSVs and report | None | Not applicable | CSV-only production policy replay |
| `eps validate` | `data/benchmark.csv`, production libraries, calibration profiles/configs | Benchmark report CSV/Markdown/JSON outputs | Mock or xTB | Yes | Scientific validation/reporting |
| `eps validate-directive` | Existing harvest, production libraries, `configs/validation.yaml`, `configs/tier1.yaml`, calibration profiles, benchmark/ESW/feasibility data | `validation_summary.json`, `validation_report.md`, Eox/ESW/feasibility CSVs, `provenance.json` | Mock or xTB | Yes | Directive Section 7 validation/reporting |
| `eps memo` | Harvest path plus validation inputs/configs | Dated validation memo | Mock or xTB when validation is run | Yes | Reporting/documentation |
| `eps analyze` | Existing harvest CSV | Summary CSV, shortlist CSV, optional plots | None | Not applicable | Read-only analysis |
| `eps calibrate-dft` | Calibration monomers/benchmark/configs, cache | DFT calibration CSV/JSON/Markdown artifacts | Mock or Gaussian plus xTB descriptors | Yes | Calibration research/reporting; not an automatic policy update |
| `eps tier2` / `eps tier2-screen` | Tier-1 selection/harvest, `configs/tier2.yaml`, optional refined DFT CSV | Dry-run Gaussian inputs or refined ranking artifacts | `tier2` dry run writes inputs; `tier2-screen` is CSV-only | Dry-run path can be no-engine/mock-adjacent | Tier-2 planning/refined diagnostic |
| `eps tier2-plan` | Selection CSV, `configs/tier2.yaml` | `task_manifest.csv`, plan summary/report, provenance | None | Not applicable | Tier-2 staging/orchestration |
| `eps tier2-run-task` | One manifest task, `configs/tier2.yaml` | Task-local `result.json`, `status.txt`, Gaussian input/log dirs, cache | Mock or Gaussian for one task | Yes | Tier-2 pilot execution; task-local and array-safe |
| `eps tier2-harvest` | Manifest plus task result directories | Harvest CSV, summary/report | None | Not applicable | Tier-2 result combiner |
| ORCA solvation pilots | `configs/orca_pilots.yaml` and/or `configs/solvation_cosmors_pilot.yaml`, pilot anchor selections | Solvation points, fit/report artifacts, cache | Mock or ORCA/openCOSMO-RS | Yes | Diagnostic solvation route validation |
| ORCA optical pilots | `configs/orca_pilots.yaml`, optical anchors/staging selections | Optical points, calibration fit/report, cache | Mock or ORCA sTDA/TDA | Yes | Diagnostic optical route validation |
| Solvation pilot scripts | `scripts/analyze_solvation_cosmors_pilot.py`, `configs/solvation_cosmors_pilot.yaml`, pilot outputs | Analysis report/CSV artifacts | Analysis script is no-engine; runner can call ORCA through workflow | Mock where workflow supports it | Diagnostic route validation |
| Staging audit scripts | `data/lit_curation/*`, production CSVs for duplicate checks | Review tables under `data/lit_curation/`, report under `docs/research/` | None | Not applicable | Staging/review-only data hygiene. Reusable logic lives in `eps.curation.staging_audit`; `scripts/audit_lit_curation_staging.py` is the command wrapper. |

The most important workflow invariant is architectural: expensive calculations depend on one
species in one solvent/method setting, never on a full triad. Triad scoring is a join and arithmetic
layer over precomputed tables.

## 6. Data/Config Ownership

| File or family | State | Consumers | Common pitfalls | Change type |
| --- | --- | --- | --- | --- |
| `data/monomers.csv` | Production library | Loaders, Tier-1, validation, analysis | SMILES canonicalization, duplicate structures, missing polymerization spec links | Scientific unless only metadata typo with proof |
| `data/solvents.csv` | Production library | Loaders, Tier-1, solvent descriptors | Window units, GBSA names, dielectric values, measured-window fallbacks | Scientific unless purely descriptive typo |
| `data/electrolytes.csv` | Production library | Loaders, Tier-1 anion/cation tables, salt-role gate | Salt role, anion/cation split, duplicate anions with different cations | Scientific |
| `data/benchmark.csv` | Production Eox benchmark | `eps validate`, calibration profiles, directive validation | Reference scales, onset vs peak labels, duplicate groups, eligibility flags | Scientific |
| `data/solvent_windows.csv` | Production measured ESW table | Measured-first ESW gate and validation diagnostics | Exact formulation vs solvent-only rows, anodic/cathodic units, conservative selection | Scientific |
| `data/solvent_benchmark.csv` | Production ESW benchmark | Solvent ESW validation | Comparing isolated descriptors to practical windows; condition mismatch | Scientific |
| `data/polymerizability_labels.csv` | Production feasibility labels | Directive feasibility validation | Small matched set, generic vs exact anion labels, condition relevance | Scientific |
| `data/polymerization.csv` | Production polymerization specs | Oligomer assembly, optical/dimerization/Eox series | Coupling-site assumptions, side-chain truncation, missing family assignments | Scientific |
| `data/lit_curation/*` | Staging/research | `eps.curation.staging_audit`, audit script wrapper, human review, future ingest proposals | Treating staging rows as production, source-quality ambiguity, duplicate promotion | Staging; promotion is scientific |
| `configs/tier1.yaml` | Production thresholds/calibration and compute policy | Tier-1, rescore, directive validation | Hard filters, pinned calibration coefficients, measured-first gate settings | Scientific |
| `configs/scoring.yaml` | Production composite weights/components | Tier-1, rescore, analysis | Weight changes alter rankings; component direction matters | Scientific |
| `configs/tier2.yaml` | Tier-2 route/orchestration settings | Gaussian engine, Tier-2 plan/run/harvest/screen | Method labels must encode route settings; task hash mismatch should block harvest | Scientific when route changes, mechanical for comments |
| `configs/tier3.yaml` | Tier-3 exploratory route settings | Tier-3 input writer/hooks | Optional hooks are placeholders; avoid implying production readiness | Scientific/planning |
| `configs/orca_pilots.yaml` | ORCA route pilot settings | ORCA solvation/optical pilots | Built-in solvent availability, serial-vs-parallel cluster behavior, diagnostic status | Scientific route-validation |
| `configs/solvation_cosmors_pilot.yaml` | Solvation-grid pilot settings | ORCA solvation grid workflow/scripts | Confusing dGsolv proxy with measured solubility, unsupported solvent profiles | Scientific route-validation |
| `configs/calibration_profiles.yaml` | Validation profile definitions | Eox benchmark validation and directive validation | Reference scale, fit eligibility, profile selection | Scientific |
| `configs/validation.yaml` | Directive validation thresholds/report settings | `eps validate-directive` | Reporting thresholds vs production filters; bootstrap seeds | Scientific/reporting |

Documentation-only changes can describe these files, but changes to values consumed by production
ranking, validation thresholds, calibration fits, or route identities need explicit authorization in
the task scope.

## 7. Engine/Cache Contract

All expensive chemistry goes through the `Engine` interface in `eps.engines.base`. A calculator
constructs a `CalcRequest` containing a `SpeciesSpec`, quantity, method label, and solvent context;
the engine returns a `CalcResult` with values, units, stdout/stderr, and metadata.

- `MockEngine` is deterministic and non-physical. It keeps workflows testable before real engines
  exist or before cluster access is available. Mock outputs are never scientific evidence.
- `XTBEngine` provides the Tier-1 real-engine path for GFN2-xTB descriptors, including redox,
  frontier orbitals, spin populations, solvation-like quantities, and sTDA-style optical helpers.
- `GaussianEngine` supports Tier-2 monomer-Eox refinement and DFT calibration routes. It keeps
  inputs/logs, checks Normal termination, records SCF/Gibbs energy basis, and should be run through
  task-local caches for array jobs.
- `OrcaEngine` supports diagnostic solvation and optical route pilots, including openCOSMO-RS
  dGsolv and sTDA/TDA/TD-DFT excitation parsing.
- `SQLiteCache` keys cached results by canonical SMILES, charge state, method, solvent name, and
  quantity. This is the repo's idempotence boundary.

Method/config labels must encode scientifically relevant settings: level of theory, solvent model,
conformer strategy, frequency treatment, route version, and any setting that changes the meaning of
the number. Failed, incomplete, hash-mismatched, or non-terminated jobs must not be cached or
harvested as valid scientific values.

## 8. Scientific Axes and Implementation Locations

| Axis | Where computed/reported | Hard filter? | Composite? | Current reliability | Main caveats |
| --- | --- | --- | --- | --- | --- |
| Monomer Eox | `eps.properties.calculators.monomer_eox_vs_AgAgCl`, redox conversion in `properties/redox.py`, Tier-1/validation workflows | Yes, inside anodic solvent window | Yes, through margin/score components | Active validation profile passes the configured directive target but is bounded by reference-quality floor | Do not change pinned constants or calibration coefficients casually. |
| Solvent anodic/cathodic limit | `solvent_anodic_limit`, `solvent_cathodic_limit`, CSV measured windows | Anodic limit gates monomer oxidation; cathodic limit is mostly reporting/context | Indirectly through window/margin components | Measured-first gate is safety-validated; raw isolated descriptor accuracy is poor | Practical ESW depends strongly on conditions and salt. |
| Measured-first ESW gate | `properties/solvent_windows.py`, `workflow/tier1.py`, `data/solvent_windows.csv` | Yes | Indirectly | Safety invariant passes on the salt-fixed harvest | Exact formulation coverage remains sparse. |
| Anion oxidation/stability | `anion_oxidation_potential`, `compute_anion_solvent_table`, `annotate_tier1_filters` | Yes, supporting-electrolyte gate | Yes/indirectly through compatibility terms | Implemented and salt-role aware | Cation deposition, ion pairing, conductivity, and condition-specific anion chemistry are not fully modeled. |
| Solvation affinity dGsolv proxy | `monomer_solvation`, ORCA solvation pilots, solvation descriptors | Yes through configured solvation/affinity threshold in Tier-1 | Yes as solvation-affinity component | Useful proxy, not measured solubility | Must not claim true solubility calibration without external anchors. |
| Dimerization/radical-coupling energy | `dimerization_dG`, Tier-1 monomer table | No | Yes | Ranking-safe as a relative axis because the proton-reference offset is common under min-max normalization | Absolute chemistry is not calibrated. |
| Optical gap | `polymer_optical_gap`, `optical_gap_oligomer`, ORCA optical pilots, optical convergence helpers | No | Yes as diagnostic band-gap deviation | 417587 real ORCA baseline is weak against experimental polymer gaps | No optical scoring policy change is authorized. |
| Oligomer Eox series | `compute_oligomer_eox_series`, Tier-1 artifact writer | No | Not production ranking by default | Reported descriptor artifact | Extrapolation depends on oligomer construction and side-chain truncation. |
| Secondary descriptors | `secondary_descriptors.py`, Tier-1 descriptor artifact writer | No | Mostly supporting/diagnostic | Useful for analysis and future model features | Do not introduce them into scoring without a scoring task. |
| Feasibility validation | `validation/feasibility.py`, `validation/directive.py`, `data/polymerizability_labels.csv` | No | No | Not yet testable at directive target; matched set is small | Needs better condition-relevant negatives and exact-anion labels. |
| Tier-2 refined window/Eox | `workflow/tier2.py`, `engines/gaussian.py`, `configs/tier2.yaml` | Potential refined screen when real values exist | Potential refined screen | Orchestration exists; no promoted real Tier-2 pilot values yet | Do not fill missing Tier-2 values with Tier-1 values or treat mock results as science. |

## 9. Run-Manifest and Provenance Convention

Run artifacts live under gitignored `outputs/` and cluster scratch/work directories. The durable
record in git is a run manifest under `docs/runs/`, indexed by `docs/runs/README.md`, using
`docs/runs/TEMPLATE.md` as the shape.

For every real run, record:

- engine and method explicitly, including mock vs real;
- scope, job id, status, exit code, failed flag, node, slots, wall time, memory, and key `qacct`
  facts when available;
- git commit/branch or isolated clone path;
- input data/config paths and output artifact paths;
- headline numbers and caveats;
- whether outputs are production, diagnostic, staging, or smoke-only.

Mock runs are plumbing evidence only. They can prove route wiring, schemas, and file creation, but
they cannot support scientific claims. Cluster artifact paths should be concrete enough that a
future maintainer can locate the ignored outputs without committing them.

## 10. Developer Onboarding Path

Recommended reading order for a new coding agent:

1. `AGENTS.md`
2. `STATUS.md`
3. `docs/code_structure.md`
4. `configs/tier1.yaml` and `configs/scoring.yaml`
5. `src/eps/workflow/tier1.py`
6. `src/eps/properties/calculators.py`
7. `src/eps/validation/*`
8. `docs/runs/README.md`
9. `docs/maintenance/pre_cleanup_merge_report_20260623.md`

After that, read the specific workflow/test pair you plan to modify. For example, Tier-2 work
should start with `src/eps/workflow/tier2.py`, `src/eps/engines/gaussian.py`, and
`tests/test_tier2_pilot.py`.

## 11. Do-Not-Touch List

Do not change the following unless the task explicitly authorizes that exact scientific or
interface change:

- production calibration coefficients;
- scoring weights and component directions;
- pinned redox constants and conversion formulas;
- production CSV libraries and benchmark tables;
- SQLite cache-key semantics;
- generated output schemas consumed by downstream commands or run manifests;
- optical-axis policy and the diagnostic-only interpretation of 417587;
- solvent-window and measured-first gate policy;
- public CLI command names, defaults, and expected output columns.

## 12. Known Engineering Debts

Engineering debt, separate from scientific debt:

- The previously noted `ruff` I001 import-ordering issue in `tests/test_orca_pilots.py` is fixed in
  the integrated branch; `ruff check src tests` passed before this document was written.
- `src/eps/cli.py` is large and mixes parser setup, command dispatch, and reporting. A future
  command-module split may improve maintainability, but should preserve public command names and
  defaults.
- Status, changelog, THINK, run manifests, and maintenance docs can duplicate facts. Keep
  `STATUS.md` as current state, `CHANGELOG.md` as append-only history, `THINK.md` as scientific
  decision register, and `docs/runs/` as run facts.
- Run-manifest consistency is manual. A lightweight manifest linter could catch missing engine,
  scope, qacct, and caveat fields.
- Validation/orchestration follow-up tests could add more no-engine end-to-end coverage for
  `validate-directive` report shape and Tier-2 plan/run/harvest fixture flows.
- `eps.validation.directive` is necessarily broad after Section 7 closure. Future cleanup could
  extract table rendering, bootstrap helpers, and provenance helpers without changing metrics.
- Audit and code-generation scripts in `scripts/` are useful but unevenly packaged. Future cleanup
  could move reusable logic into importable helpers while keeping command behavior stable.
- Output schema documentation is scattered across tests, run manifests, and workflow code. A small
  schema/data-dictionary page would reduce accidental downstream breakage.

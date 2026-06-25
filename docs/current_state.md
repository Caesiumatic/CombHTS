# Current State Snapshot - 2026-06-25

This snapshot is the short operating view for maintainers. It is not the full project history; use
`STATUS.md`, `THINK.md`, and `docs/runs/README.md` for the longer record and exact run facts.

## Scope

- Project: high-throughput virtual screen ranking for electropolymerization triads.
- Current library: 36 monomers x 13 solvents x 16 electrolytes = 7,488 triads.
- Eventual directive target remains larger than the current library.
- The current 7,488-triad scale is a validated iteration scale, not a failed run.
- Expensive calculations remain per species or per species-solvent, never per triad.
- Triad construction, filtering, scoring, and analysis remain no-engine joins over precomputed
  descriptor tables.

## Production Truth

- Real Tier-1 ranking exists for the current 7,488-triad library.
- Production library data live in versioned CSVs under `data/`.
- Production thresholds, hard-filter settings, and scoring weights live under `configs/`.
- `configs/tier1.yaml` is the current Tier-1 screening-policy surface.
- `configs/scoring.yaml` is the current composite-score weight surface.
- `data/solvent_windows.csv` is consumed by the measured-first conservative solvent-window gate.
- Production measured solvent-window rows can tighten eligibility.
- Sparse generic or computed windows must not admit a row by widening measured evidence.
- Supporting-electrolyte role metadata guards reference-only and acid rows from production
  supporting-electrolyte treatment.
- The active Tier-1 monomer-Eox production coefficient source is
  `agagcl_peak_strict_2026_06_17_xtb_v3`.
- The production Tier-1 calibration profile is `agagcl_peak_strict`.
- The configured validation default profile is `agagcl_peak_relaxed`.
- The strict-vs-relaxed divergence is declared in `configs/calibration_operational.yaml`.
- That manifest is a pointer/role manifest only; it does not duplicate or change coefficients.

## Validation State

- Directive Section-7 validation is integrated as `eps validate-directive`.
- The required Section-7 package includes:
  `validation_summary.json`, `validation_report.md`, `eox_profile_summary.csv`, `eox_points.csv`,
  `esw_descriptor_points.csv`, `esw_gate_diagnostics.csv`, `feasibility_matches.csv`, and
  `provenance.json`.
- The authoritative real Section-7 run is recorded in `docs/runs/README.md` and its manifest.
- Current Tier-1 monomer-Eox validation passes the configured directive gate for the active
  profile, while preserving the reference/measurement floor caveat.
- Solvent ESW molecular descriptor accuracy remains weak and must not be treated as a universal
  electrochemical-window calibration.
- Production ESW gate safety is evaluated separately from raw isolated-solvent descriptor quality.
- Qualitative electropolymerization feasibility validation is underpowered.
- Feasibility labels are not yet enough to claim the directive target.
- Mock validation remains nonphysical smoke evidence only.

## Diagnostic State

- Optical and other soft axes remain diagnostic.
- The optical axis still needs correctness/route closure before new values are treated as route
  evidence.
- This snapshot does not incorporate any later optical smoke-test outcome.
- Dimerization/radical-coupling energy is ranking-safe only as a relative normalized axis.
- The absolute dimerization scale remains diagnostic.
- Solvation-affinity `dGsolv` is a proxy, not measured solubility.
- Secondary descriptors are reported-only unless a future scoring task explicitly promotes them.
- ORCA and Gaussian route pilots are diagnostic unless a reviewed workflow promotes their outputs.
- No real Tier-2 scientific values are currently promoted.

## Staging And Review-Only Data

- `data/lit_curation/` contains staging and review curation artifacts.
- Staging rows are not production data by default.
- G1.2 and R11-R21 Eox audit outputs are review-only evidence packages.
- Source-conflicted rows remain fail-closed until scientific/source reconciliation happens.
- Production ingest from staging data requires a separate reviewed promotion task.
- Review-only documents may propose changes without changing production truth.

## Tier-2 State

- Tier-2 monomer-Eox orchestration exists as a mock-first pilot scaffold.
- Public commands include `eps tier2-plan`, `eps tier2-run-task`, and `eps tier2-harvest`.
- Planning deduplicates by monomer-solvent-method identity before any engine call.
- Task execution is one task per result directory/cache by default.
- Harvest is no-engine and rejects missing, failed, duplicate, or hash-mismatched results.
- The scaffold is ready for controlled pilot use, but no real Tier-2 production values are
  promoted.

## Important Limitations

- ESW descriptor physics remains weak.
- Feasibility validation is underpowered.
- Optical and other soft axes remain diagnostic.
- The library is below the eventual directive size.
- No real Tier-2 scientific values are currently promoted.
- The strict-vs-relaxed peak calibration choice is still pending recorded evidence.
- Staging/review-only audit rows are not production rows.
- Mock outputs are never scientific evidence.

## Safe Local Commands

```bash
python -m eps.cli doctor
python -m eps.cli run-tier1 --engine mock --cache /tmp/combhts_mock_tier1.sqlite --output /tmp/combhts_tier1_ranked.csv --all-output /tmp/combhts_tier1_all.csv
python -m eps.cli validate --engine mock --cache /tmp/combhts_validation.sqlite --report /tmp/combhts_validation_report.csv
python -m pytest -q
```

## Run Facts

- Exact cluster run facts belong in `docs/runs/` manifests and `docs/runs/README.md`.
- Real calculations must name their engine explicitly.
- Mock runs must be labeled nonphysical.
- Heavy output artifacts, caches, logs, and raw cluster directories stay out of git.
- Scheduler templates should be used for chemistry calculations.
- Chemistry calculations must not run on a login/head node.
- No credentials or host passwords belong in the repository.

## Maintenance Guidance

- Preserve public CLI names, defaults, and artifact schemas before decomposing large modules.
- Use `docs/output_contracts.md` as the output data dictionary for downstream stability.
- Keep production, diagnostic, staging/review-only, and mock outputs classified explicitly.
- Keep scientific policy changes in CSV/YAML/data surfaces or clearly reviewed route configs.
- Do not hide scientific decisions in orchestration code.
- For future parallelization, preserve compute-per-species architecture and no-engine triad joins.

# Output Contracts And Data Dictionary

This document describes public output surfaces that future refactors must preserve unless a
reviewed interface change intentionally updates downstream consumers. It is documentation, not an
executable source of truth for coefficients, thresholds, or scoring policy.

## Stability Classes

| Class | Meaning | Change rule |
| --- | --- | --- |
| Public/stable | Files and columns consumed by CLI users, validation reports, run manifests, or downstream analysis. | Preserve required columns, units, and semantics across refactors. Additive columns are allowed. |
| Diagnostic | Files that support interpretation, route validation, or scientific caveats. | Preserve labels and provenance, but do not treat values as production truth. |
| Staging-only | Review/curation outputs that may support future ingest decisions. | Keep separate from production CSVs until a reviewed promotion task occurs. |
| Mock/nonphysical | Deterministic smoke outputs from mock engines. | Preserve schemas, never claim scientific meaning. |

## Public Tier-1 Artifacts

| Artifact | Stability | Purpose |
| --- | --- | --- |
| `tier1_ranked.csv` | Public/stable | Presentation view of surviving triads after cation-degenerate score-class collapse. |
| `tier1_all.csv` or inferred all-triads audit path | Public/stable | Full per-salt audit table, including failures and non-survivors. |
| `oligomer_buildingblocks.csv` | Diagnostic | Human-reviewable oligomer assembly metadata. |
| `oligomer_eox_series.csv` | Diagnostic | Reported-only oligomer Eox-vs-length descriptor. |
| `secondary_descriptors.csv` | Diagnostic | Reported-only Section-3 descriptor families. |
| Provenance sidecars | Public/stable | Engine, method, command, and git/config/data context for emitted CSVs. |

The ranked CSV and all-triads CSV are different views. `tier1_all.csv` preserves every monomer x
solvent x salt row and is the audit source for filters, failures, measured-window provenance, and
analysis. `tier1_ranked.csv` is a sorted survivor presentation view where cation-only exact score
duplicates can be collapsed into `salts_tied` and `n_tied`.

## Core Tier-1 Column Groups

| Group | Required examples | Units and semantics |
| --- | --- | --- |
| Triad identity | `monomer_name`, `monomer_canonical_smiles`, `solvent_name`, `salt`, `cation_smiles`, `anion_smiles` | Row identity for joins and audit. |
| Raw monomer Eox | `monomer_Eox_raw_V_vs_AgAgCl` | Raw engine oxidation potential descriptor, V vs Ag/AgCl. |
| Calibrated monomer Eox | `monomer_Eox_calibrated_V_vs_AgAgCl` | Linear calibrated Eox using configured Tier-1 calibration when enabled. |
| Filter monomer Eox | `monomer_Eox_filter_V_vs_AgAgCl`, `monomer_Eox_V` | Value used by hard filters. `monomer_Eox_V` is a backward-compatible alias. |
| Anion Eox | `anion_Eox_raw_V_vs_AgAgCl`, `anion_Eox_calibrated_V_vs_AgAgCl`, `anion_Eox_filter_V_vs_AgAgCl`, `anion_Eox_V` | Same raw/calibrated/filter pattern for anion oxidation. |
| Solvent window | `solvent_anodic_limit_V`, `solvent_cathodic_limit_V`, `solvent_window_condition_match`, `solvent_window_measurement_anodic_V` | Selected practical anodic gate and provenance. Cathodic edge is context/diagnostic. |
| Measured-window provenance | `solvent_window_measurement_source`, `solvent_window_measurement_tier`, `solvent_window_measurement_electrode`, `solvent_window_measurement_electrolyte`, `solvent_window_measurement_reference` | Source and condition metadata for measured windows. |
| Conservative cap | `solvent_window_conservative_cap_source`, `solvent_window_cap_applied`, `solvent_window_limit_set_by_electrolyte` | Shows why the final gate can only tighten measured evidence. |
| Hard-filter booleans | `pass_window_margin`, `pass_anion_stability`, `pass_solvation`, `pass_supporting_electrolyte_role`, `passes_all_tier1_filters` | Boolean gate outcomes. |
| Hard-filter reasons | `failed_filter_reasons`, `supporting_electrolyte_calc_status`, `supporting_electrolyte_reason` | Semicolon-separated audit reasons for failure/exclusion. |
| Scores | `composite_score`, `pareto_front`, `band_gap_deviation_eV`, `norm_window_margin`, `norm_anion_stability`, `norm_solubility`, `norm_dimerization`, `norm_band_gap` | Composite score and normalized component values. Ranking is by descending `composite_score`; no separate rank column is required. |
| Optical gap | `optical_gap_eV`, `optical_gap_method`, `optical_gap_calc_status`, `optical_gap_calc_error` | Reported optical/soft-axis descriptor, eV. Diagnostic unless explicitly promoted later. |
| Dimerization | `dimerization_dG_kcal_mol`, `dimerization_reaction`, `dimerization_calc_status`, `dimerization_calc_error` | Radical-coupling/dimerization free-energy proxy, kcal/mol. |
| Solvation affinity | `solvation_dG_kcal_mol`, `solvation_calc_status`, `solvation_calc_error` | Solvation-affinity proxy, kcal/mol; not measured solubility. |
| Status/error convention | `*_calc_status`, `*_calc_error` | `ok` values are usable; `failed` values are NaN or blank and must not abort row-level audit. |

## Raw vs Calibrated vs Filter Eox

- `*_raw_V_vs_AgAgCl` is the direct engine descriptor in V vs Ag/AgCl.
- `*_calibrated_V_vs_AgAgCl` applies the configured linear oxidation calibration when enabled.
- `*_filter_V_vs_AgAgCl` is the value actually used by the hard filter.
- Backward-compatible aliases such as `monomer_Eox_V` and `anion_Eox_V` equal the filter value.
- Calibration coefficients live in config surfaces, not in this document.

## Solvent-Window Semantics

The measured-first conservative gate chooses exact `(solvent, salt)` measured rows first when
available, otherwise solvent-only measured evidence, and then applies a conservative cap from
curated CSV or computed descriptor policy. The final `solvent_anodic_limit_V` must not widen a
conditioned measurement. Provenance columns are part of the public audit contract.

## Score Component Directions

Higher `window_margin_V`, `anion_stability_margin_V`, and solubility score are better. Lower
`dimerization_dG_kcal_mol` and lower `band_gap_deviation_eV` are better after transformation into
normalized score components. Weight values and target gaps remain in YAML configs.

## Per-Species Tables

| Table | Required column families |
| --- | --- |
| Monomer table | Monomer identity; optical gap value/method/status/error; dimerization value/reaction/status/error; oligomer Eox series columns; monomer secondary descriptor values/status/error; optical convergence columns when enabled. |
| Monomer-solvent table | Monomer and solvent identity; raw/calibrated/filter Eox; solvation value/status/error. |
| Solvent table | Solvent identity; computed/calibrated/CSV/selected anodic limit; cathodic limit; source/status/error; secondary solvent descriptor columns when enabled. |
| Anion-solvent table | Anion and solvent identity; raw/calibrated/filter Eox; alias; status/error; anion volume columns when enabled. |
| Cation-solvent table | Cation and solvent identity; cation reduction descriptor columns when enabled. |
| Ion-pair table | Salt identity; ion-pair dissociation descriptor columns when enabled. |

## Dynamic Column Families

Dynamic columns are stable by prefix and semantics:

- `oligomer_Eox_raw_n{n}`: raw oligomer Eox descriptor at chain length `n`.
- `optical_gap_n{n}_eV`: optical gap descriptor at chain length `n`.
- `*_95ci_*` JSON-ish strings: bootstrap confidence interval records with low/high/n fields.
- Future additive descriptor families must include status/error columns and explicit units in names
  where values carry physical units.

## Section-7 Validation Package

Required artifact filenames:

- `validation_summary.json`
- `validation_report.md`
- `eox_profile_summary.csv`
- `eox_points.csv`
- `esw_descriptor_points.csv`
- `esw_gate_diagnostics.csv`
- `feasibility_matches.csv`
- `provenance.json`

Stable top-level `validation_summary.json` keys include engine/method labels, mock flag, bootstrap
settings, numeric tolerance, reference floor, harvest path, directive status table, Eox/ESW/feasibility
sections, and artifact paths.

Stable `provenance.json` keys include engine, method, mock flag, git info, config hashes, library
sizes, inputs, input hashes, bootstrap seed, numeric tolerance, and directive status table.

Core CSV purposes:

| CSV | Purpose |
| --- | --- |
| `eox_profile_summary.csv` | One row per configured calibration profile, fit/skipped status, profile role flags, point counts, fit metrics, bootstrap summaries, applicability-domain summary, and reference-floor note. |
| `eox_points.csv` | Calibration point residuals plus library applicability-domain rows. |
| `esw_descriptor_points.csv` | Raw isolated-solvent descriptor comparison against practical ESW benchmark rows. |
| `esw_gate_diagnostics.csv` | Existing harvest audit for conditioned measured-window safety and conservatism. |
| `feasibility_matches.csv` | Matched qualitative electropolymerization feasibility labels and predictions. |

## Nullable And NaN Semantics

- Numeric failures should be empty/NaN, not fabricated fallback values, unless the column name and
  source/status columns explicitly describe a configured fallback.
- Blank strings are acceptable for nonnumeric metadata that is not applicable.
- `*_calc_status` and `*_calc_error` explain missing descriptor values.
- A partial diagnostic artifact can be useful only when missingness is auditable.

## Backward Compatibility

Deprecated aliases remain part of the public contract until a reviewed deprecation removes them:

- `monomer_Eox_V` equals `monomer_Eox_filter_V_vs_AgAgCl`.
- `anion_Eox_V` equals `anion_Eox_filter_V_vs_AgAgCl`.

Future refactors must preserve command names, default paths, required arguments, required artifact
filenames, required column families, units in column names, and mock/nonphysical labeling.

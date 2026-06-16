# Benchmark Curation Protocol

Last updated: 2026-06-16

## Clean Calibration Labels

A calibration row must be a measured monomer oxidation potential for a well-defined monomer or small oligomer in a reported solvent/electrolyte system. The label should describe oxidation of the soluble molecular precursor, not growth of a polymer film and not redox switching of an already formed polymer.

Use `calibration_eligible=true` only when all of these are true:

- `label_type` is `monomer_oxidation_peak` or `monomer_oxidation_onset`.
- The paper reports enough conditions to identify solvent, electrolyte, reference electrode, and potential type.
- `exp_Eox_V_vs_AgAgCl` is present after a documented conversion.
- `reported_reference_electrode`, `converted_reference_electrode`, and `conversion_method` are populated.
- The row has a source DOI and locator, unless it is deliberately marked low-confidence/provisional and excluded.

## Labels To Keep Separate

Do not use electropolymerization growth/setpoint potentials, polymer doping onset, polymer-film redox peaks, or unknown/mixed labels as calibration y-values. These quantities can be useful audit rows, but they answer different physical questions:

- `monomer_oxidation_peak`: anodic peak for molecular monomer oxidation, usually Epa.
- `monomer_oxidation_onset`: onset for molecular monomer oxidation before film-growth ambiguity dominates.
- `electropolymerization_onset`: onset of film growth; related to initiation but includes nucleation and electrode effects.
- `electropolymerization_growth_setpoint`: an applied deposition potential, not a measured oxidation label.
- `polymer_doping_onset`: redox onset of the polymer film, not monomer oxidation.
- `unknown_or_mixed`: source is unclear or combines incompatible labels.

## Reference Electrode Conversion

Always record both the reported and converted reference scales:

- `reported_reference_electrode`: exactly what the paper reports.
- `converted_reference_electrode`: the scale used by this CSV, currently `Ag/AgCl`.
- `conversion_method`: signed offset and source/convention, including whether the conversion is source-calibrated or table-based.
- `native_potential_V`, `conversion_to_AgAgCl_V`, and `exp_Eox_V_vs_AgAgCl`: must satisfy `native + conversion = converted` within 0.005 V.

For nonaqueous data, note liquid-junction uncertainty. Prefer source-internal Fc/Fc+ referencing where possible in future curation.

## Excluded And Low-Confidence Rows

Excluded rows should remain in the CSV when they are useful for provenance or sanity checks, but set:

- `calibration_eligible=false`
- `exclusion_reason=<specific reason>`
- `label_type` to the closest non-calibration label, or `unknown_or_mixed`
- `source_confidence=low` or `provisional` when the DOI/locator or conditions are incomplete

Rows with `calibration_eligible=false` must never enter calibration. The validation harness reports a `calibration_exclusion_reason` for each excluded row.

## Strict Benchmark V1 Status

Strict benchmark v1 contains 14 calibration-eligible collapsed groups after grouping by canonical SMILES, `solvent_name`, and `label_type`. The original target of >=30 clean groups was not achieved under the current strict reference-electrode and label-ontology rules.

Demoted, excluded, and unresolved provenance rows are kept in `data/benchmark_candidates.csv`. The final curation report supporting strict v1 is archived at `docs/literature/deep_research_benchmark_finalization_20260616.md`. Candidate rows are not used by default calibration and should be promoted only after a PI policy decision or source-level recovery of the missing reference, locator, solvent, structure, or label metadata.

Onset and peak labels must not be averaged together. For example, thiophene/acetonitrile has both peak-like and onset-like retained labels, and those remain separate calibration groups.

## Acceptable Rows

Acceptable calibration examples:

- A paper reports monomer Epa in MeCN with electrolyte, working electrode, scan rate, and SCE; the row records SCE as reported and converts to Ag/AgCl only when the conversion is source-internal, source-calibrated, or explicitly PI-approved. Generic nonaqueous SCE table conversion is not automatically acceptable.
- A paper reports monomer oxidation onset against an internally calibrated pseudo-reference; the row records the pseudo-reference and source-provided offset.

Unacceptable calibration examples:

- A deposition potential chosen for electropolymerization growth.
- A polymer film doping onset measured after deposition.
- A cyclic voltammogram where the paper does not identify the reference electrode.
- A review-table value with no primary locator, unless retained as `calibration_eligible=false`.

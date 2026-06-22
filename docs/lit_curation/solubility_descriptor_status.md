# Solubility descriptor status: openCOSMO-RS dGsolv is NOT solubility

Status: descriptor note. **Recommendation only — this note changes no code, weight, or axis.**

## What the Tier-1 20% "solubility" axis actually is

The composite score's solubility term is computed in
[`src/eps/scoring/composite.py`](../../src/eps/scoring/composite.py):

```python
scored["norm_solubility"] = _minmax(-scored["solvation_dG_kcal_mol"])
```

with weight `solubility: 0.20` in [`configs/scoring.yaml`](../../configs/scoring.yaml). So the axis
is a **min-max-normalized negative solvation free energy**: the monomer with the most negative
dGsolv in the candidate set scores 1.0, the least negative scores 0.0, and the term contributes
20% of the composite. It is a *solvation-affinity ranking*, nothing more.

`solvation_dG_kcal_mol` is the openCOSMO-RS dGsolv (ORCA 6.1 / openCOSMO-RS 24a, BP86/def2-TZVPD).
Real pilot values (MeCN): thiophene −4.13, EDOT −7.91, pyrrole −6.98 kcal/mol
([2026-06-22_orca-solvation-real-417544](../runs/2026-06-22_orca-solvation-real-417544.md)).

## What dGsolv DOES capture

dGsolv is the free energy of transferring **one** neutral solute molecule from the gas phase into
**dilute** solution. It captures, at a continuum-COSMO-RS level:

- electrostatic/polarization stabilization of the solute by the solvent dielectric;
- hydrogen-bonding and polar-surface (sigma-profile) interactions between solute and solvent;
- a cavity-formation / dispersion balance for the solute in that specific solvent.

It is therefore a defensible **relative solvation-affinity descriptor**: across monomers in one
solvent, a more negative dGsolv does mean "this solvent likes this molecule more."

## What dGsolv does NOT capture (why it is not solubility)

Equilibrium solubility is governed by the free energy of dissolving the **condensed phase** of the
solute up to a **saturating concentration**. dGsolv omits every one of these terms:

- **Lattice / fusion enthalpy of the pure solute.** Solubility needs ΔG to break the solid (or
  self-associated liquid) phase, ≈ dGsolv − ΔG_fusion/sublimation. A molecule can solvate well yet
  be nearly insoluble because its crystal is very stable (e.g. carbazole: 1.2–1.8 mg/L in water —
  see [`solubility_staging.csv`](../../data/lit_curation/solubility_staging.csv) — despite an
  aromatic surface that solvates fine).
- **Finite / saturating concentration.** dGsolv is the infinite-dilution limit; it says nothing
  about the concentration at which the solution saturates.
- **Aggregation and self-association.** Oligomers and planar fused donors π-stack; dGsolv treats an
  isolated monomer, so it misses concentration-dependent aggregation that caps real solubility.
- **Protonation / charge state.** Anilines, pyrroles, carbazoles change protonation with pH; the
  neutral dGsolv ignores the dissolved ionic equilibria that dominate aqueous solubility.
- **Electrolyte / salt compatibility.** The actual screening medium is monomer + solvent + a
  supporting-electrolyte salt; salting-in/out and ion pairing are entirely outside dGsolv.
- **Solute geometry / conformer ensemble** beyond the single RDKit-embedded structure fed to ORCA.

Net: **dGsolv ≠ solubility.** It is one (cavity+electrostatic+H-bond) contribution to it, with the
dominant solid-state term absent.

## Recommendation for the 20% axis (recommendation only — not applied)

1. **Keep dGsolv as the axis input for now, but RELABEL it.** Rename the score component from
   "solubility" to "solvation affinity (dGsolv proxy)" in docs and column headers so no reader
   mistakes it for measured solubility. This is a labeling/documentation fix, not a weight change.
2. **Do NOT re-weight without an experimental anchor.** Re-weighting (or dropping) the axis should
   wait until the dGsolv ranking is checked against the curated experimental solubilities in
   `data/lit_curation/solubility_staging.csv`. Most of those rows are aqueous; the relevant
   process solvents (PC, MeCN, nitromethane, NMP) have little/no quantitative solubility data, so
   there is currently no basis for a calibrated solubility weight.
3. **If a future calibration is wanted,** the minimal honest upgrade is dGsolv + an estimated
   fusion/sublimation term (e.g. a melting-point-based ΔG_fus estimate) to approximate
   log S, validated against the staged experimental values — a separate, scored work item, not a
   silent change to this axis.

Until then the axis stays a **diagnostic proxy**: useful for relative ranking within the screen,
explicitly not an absolute solubility prediction. The expansion pilot in
[`configs/solvation_cosmors_pilot.yaml`](../../configs/solvation_cosmors_pilot.yaml) exists to test
how the dGsolv descriptor behaves across chemistries and solvents — it does not change this axis.

# Dimerization proton-offset diagnosis and anchoring plan

Date: 2026-06-22
Scope: local, read-only analysis of the existing implementation and harvested real-GFN2-xTB
values. No quantum-chemistry engine or cluster job was run. The 15% dimerization weight and
scoring implementation are unchanged.

## Executive verdict

The implemented reaction is

\[
2\,M^{+\bullet} \rightarrow D^0 + 2\,H^+,
\]

where \(D^0\) is the neutral, rearomatized coupled dimer. The stored descriptor is

\[
d_{i,0}=\left[E_i(D^0)-2E_i(M^{+\bullet})+2G_0(H^+)\right]
            (23.06054783\ {\rm kcal\ mol^{-1}\ eV^{-1}}),
\]

with `G_0(H+) = 0.0 eV`. The **offending absolute-reference term is
`2 * proton_gibbs_eV`**, not either monomer-dependent electronic energy.

Setting a bare proton's electronic energy to zero is internally valid for an electronic-energy
origin, but it does not supply the standard chemical potential of a proton in a specified solvent,
temperature, concentration standard state, and proton-solvation convention. The current quantity
is consequently a proton-referenced **electronic coupling energy**, not an absolute solution
standard Gibbs free energy.

For the current fixed stoichiometry, changing the proton convention from \(g_0\) to \(g_1\) gives

\[
d_{i,1}=d_{i,0}+2(g_1-g_0)(23.06054783).
\]

That is one additive constant for every monomer: 1 eV per-proton changes every value by
46.1211 kcal/mol. It cannot change pairwise differences, ordering, or the current min-max score.
The proton offset therefore **does not distort ranking**. This narrow verdict does not remove
monomer-dependent errors from omitted solvation, thermal/ZPE, standard-state, acid/base/speciation,
conformation, or coupling-regiochemistry effects.

## 1. What the code actually computes

The current implementation defines `PROTON_GIBBS_EV = 0.0`, constructs the same neutral n=2
coupled oligomer used by the structure route, evaluates that dimer as a closed-shell singlet and
each monomer radical cation as a +1 doublet, and returns
`(g_dimer_neutral + 2*proton_gibbs_eV - 2*g_monomer_cation) * EV_TO_KCAL_MOL`.
See [`calculators.py`](../src/eps/properties/calculators.py) and the formula/charge-state regression
tests in [`test_dimerization.py`](../tests/test_dimerization.py).

Charge is balanced: the left side is +2 and the neutral dimer plus two protons is +2. Electron
count is also balanced. This supersedes the earlier, charge-imbalanced dication description still
visible in the historical section of the Step-1 report; the report's post-harvest correction gives
the operative neutral-dimer reaction. See
[`step1_real_bandgap_dimerization_report.md`](step1_real_bandgap_dimerization_report.md).

The name `dimerization_dG_kcal_mol` is therefore aspirational in an absolute thermodynamic sense:
the engine inputs are gas-phase electronic energies, and the docstring explicitly records missing
thermal/ZPE and proton-solvation terms. A physical solution reaction would require, consistently
for **all** participants,

\[
\Delta G^\circ_{\rm soln} = G^\circ_{\rm soln}(D^0)
 +2\mu^\circ_{\rm soln}(H^+) -2G^\circ_{\rm soln}(M^{+\bullet}),
\]

including thermal and standard-state corrections. Inserting only a literature proton-solvation
number into the present gas-phase electronic-energy expression would mix thermodynamic cycles and
would not create a defensible absolute solution free energy.

## 2. Constant-versus-monomer-dependent evidence

Three independent pieces of evidence establish that the **proton-reference part** is constant:

1. The code contains the proton term exactly twice for every call and has no monomer, solvent, or
   electrolyte dependence in that term.
2. `test_dimerization_relative_ordering_invariant_to_proton_constant` changes the proton value
   from 0 to 5 eV, verifies that the thiophene-minus-pyrrole difference is unchanged, and verifies
   the common `2 * delta_proton * conversion` shift.
3. The completed real-GFN2-xTB 7,488-triad harvest contains exactly one dimerization value for each
   of 36 monomers, repeated across its 13 solvents and 16 salts. The current local harvest ranges
   from furan −42.094 through thiophene −20.115, pyrrole −3.908, EDOT +24.489, carbazole +53.440,
   to terthiophene +73.839 kcal/mol (span 115.933 kcal/mol). Its provenance and engine identity are
   recorded in [`2026-06-21_tier1-harvest-real-7488.md`](runs/2026-06-21_tier1-harvest-real-7488.md).
   The spread comes from `E(D0) - 2E(M+.)`; an unknown common vertical translation cannot explain
   or alter that spread.

The scorer applies `_minmax(-dimerization_dG_kcal_mol)` before the unchanged 0.15 weight
([`composite.py`](../src/eps/scoring/composite.py), [`scoring.yaml`](../configs/scoring.yaml)). For
any constant \(C\), min-max normalization of \(-(d_i+C)\) equals that of \(-d_i\). Thus anchoring
the intercept alone will leave the present 15% axis byte-equivalent apart from floating-point
roundoff.

This is not evidence that the **model error** is constant. In particular, neutral-dimer and
radical-cation solvation do not generally cancel uniformly across monomer classes, and some
coupling structures are explicitly approximate. Those effects may distort ranking and must be
validated separately from the proton-offset question. The chemically surprising raw order (for
example, furan much more favorable than EDOT, while longer thiophene oligomers are positive) is a
reason to retain the axis's diagnostic label, not evidence that the proton constant varies.

## 3. Existing benchmark coverage

`data/benchmark.csv` contains oxidation peaks/onsets and reference-electrode conversions,
including thiophene/oligothiophene rows. It has no measured equilibrium constant or standard free
energy for the exact `2 M+ radical -> D0 + 2 H+` reaction. The repository's curated
polymerization sources establish mechanisms, products, film outcomes, and in some cases coupling
rate constants, but a kinetic dimerization rate, irreversible CV onset/peak, or observation of a
film is **not** an equilibrium reaction free energy. None can be used as the missing intercept
without an additional thermodynamic cycle and matched proton activity.

## 4. Anchoring options, ranked

### 1. Matched multi-anchor experimental intercept — recommended target

Curate at least three chemically diverse monomers with an experimental \(\Delta G^\circ\) for the
exact reaction in one solvent (preferably MeCN), at one temperature and standard state. A direct
equilibrium constant with controlled proton activity gives \(\Delta G^\circ=-RT\ln K\); a Hess
cycle is acceptable only if all formal potentials, acid/base equilibria, speciation, and standard
states close to the same net reaction. Thiophene and EDOT are sensible search targets, but their
well-known irreversible electropolymerization behavior alone is not an anchor.

Fit **intercept only**, keeping slope fixed at one:

\[
C=\operatorname{weighted\ mean}_j(\Delta G^\circ_{j,\rm exp}-d_{j,0}),\qquad
d_{i,\rm abs}=d_{i,0}+C.
\]

Equivalently, the implied proton convention is
`G(H+) = C / (2 * 23.06054783)` eV relative to the current origin. Report leave-one-anchor-out MAE,
class residuals, and uncertainty on \(C\). This preserves every rank and the 15% score exactly.
Expected accuracy: the intercept uncertainty can be a few kcal/mol if true equilibrium data are
available, but cross-class descriptor accuracy is presently unknown and should be reported from
held-out residuals rather than assumed; a single global intercept cannot repair slope or
monomer-dependent errors.

### 2. Consistent absolute solution thermodynamic cycle

Adopt one published single-ion proton convention for the target solvent and compute
`Gsoln(D0)`, `Gsoln(M+ radical)`, and thermal/standard-state corrections at the same level. Absolute
single-ion solvation values are convention-dependent (an extrathermodynamic issue), so the chosen
convention and standard state must be pinned in versioned configuration. Tissandier et al.
(J. Phys. Chem. A 1998, DOI `10.1021/jp982638r`) is an example of an explicitly documented
absolute proton hydration convention; a solvent-specific source is required for MeCN or any other
production medium.

Data/compute needed: a vetted solvent-specific proton chemical potential, consistent solution
free energies for every neutral dimer and radical cation, frequencies or a stated thermal
approximation, and 1 atm-to-1 M corrections. This is scientifically cleaner than adding a proton
number alone, but it would make the absolute descriptor solvent-specific. Expected accuracy is
method- and convention-limited and cannot be established from current data; validate against the
multi-anchor set. It removes reference ambiguity, not electronic-structure/model error.

### 3. One experimental anchor (thiophene or EDOT)

If exactly one defensible matched \(\Delta G^\circ_{\rm exp}\) becomes available, set
`C = DeltaG_exp(anchor) - d_0(anchor)` and apply it globally with unit slope. This is concrete and
rank-preserving, but it is exact only for that anchor. Expected transfer accuracy is unknown and
likely class-dependent; report it as a provisional absolute convention, not a calibrated model.
Using an irreversible oxidation potential, coupling rate, or qualitative "polymerizes" label as
that number is not acceptable.

### 4. Relative-only convention

Retain `G(H+) = 0`, rename/document the output as proton-referenced electronic coupling energy,
and interpret only differences. This needs no data or compute and has exact invariance to the
proton offset, but supplies no absolute thermodynamic accuracy. It is the honest fallback until
Option 1 has valid anchors.

## 5. Recommendation for the live 15% axis

Keep the 15% axis unchanged. It is **safe with respect to the unknown proton-reference offset for
ranking now**, because the offset is a common intercept and the score is min-max normalized.
Nevertheless, keep the axis **diagnostic, not recommendation-grade**, because proton-offset
invariance does not validate the monomer-dependent chemistry.

For an absolute descriptor, pursue Option 1 with a fixed unit slope and multiple matched solution
thermodynamic anchors; use Option 2 to define and audit the underlying solvent/proton convention.
Do not force thiophene/EDOT kinetics or oxidation onsets into a thermodynamic anchor. Until at
least one exact-reaction anchor exists—and preferably a held-out multi-anchor residual is
available—publish the existing values only as relative, proton-referenced electronic coupling
energies.

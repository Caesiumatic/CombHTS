# Benchmark Methods And Reliability Memo

Last updated: 2026-06-16

## Scope

`data/benchmark.csv` now contains a deep-research benchmark nucleus: 11 rows from four source families (Alakhras 2015 thiophene/selenophene; Cocuk 2025 EDOT; Contal 2019 carbazole; VNUHCM 2023 3-hexylthiophene). Tiers are 2 Tier A rows (aqueous EDOT with an explicitly Ag/AgCl-calibrated pseudo-reference), 8 Tier B rows (nonaqueous values with documented caveats), and 1 Tier C row (3-hexylthiophene, downgraded for internal condition/reference inconsistencies). The default validation nucleus is nonaqueous Tier A/B, giving 8 rows collapsed to 5 monomer-solvent calibration points across 4 families.

## Reference Conversions

| Native reference | Add to native value to report V vs aqueous Ag/AgCl sat. KCl | Source and caveat |
| --- | ---: | --- |
| Ag/AgCl sat. KCl | +0.000 V | No conversion. Only Tier A if the paper explicitly reports aqueous Ag/AgCl sat. KCl. |
| SCE | +0.047 V | Standard aqueous potentials: SCE = +0.244 V vs SHE and Ag/AgCl sat. KCl = +0.197 V vs SHE, so E(Ag/AgCl) = E(SCE) + 0.047 V. See Bard and Faulkner, Electrochemical Methods, 2nd ed. |
| Ag/Ag+ in MeCN | Source-specific | Do not apply a universal constant unless the paper internally reports Fc/Fc+ or a measured cross-reference. Groenendaal et al. list conversion factors used in their PXDOT review, but these remain convention-dependent (DOI: 10.1002/adma.200300376). |
| Fc/Fc+ in MeCN | Source-specific | Prefer retaining Fc/Fc+ as the master nonaqueous scale. If forced to Ag/AgCl, cite the exact convention used by the paper or a conversion table such as Pavlishchuk and Addison, Inorg. Chim. Acta 2000, DOI: 10.1016/S0020-1693(00)00127-6. |

## Recommendation On Master Scale

For this project, migrate the experimental benchmark master scale to Fc/Fc+ for nonaqueous data and keep aqueous Ag/AgCl only for truly aqueous rows. Most electropolymerizable monomers are measured in MeCN, DCM, propylene carbonate, or similar media. Converting those values onto aqueous Ag/AgCl hides an ill-defined liquid-junction potential and can introduce solvent/reference offsets that are comparable to the target model error. The code can still export V vs Ag/AgCl for compatibility, but calibration should be stratified by medium and native reference.

## Potential Type Mismatch

GFN2-xTB adiabatic IP converted to voltage is a thermodynamic one-electron oxidation estimate and is conceptually closest to a reversible E1/2. Electropolymerization onset and Epa values are kinetic and mechanism-laden: radical-cation follow-up chemistry, electrode passivation, monomer adsorption, scan rate, and film nucleation shift them. For screening initiation, onset is chemically useful, but it should not be mixed with E1/2 without a label. The benchmark therefore records `potential_type` and should fit separate calibrations for onset/Epa/Ehalf once enough primary rows exist.

## Accuracy Expectation

Roth, Romero, and Nicewicz collected over 180 common organic redox potentials and explicitly warned that peak or half-peak values can deviate from true thermodynamic E1/2, especially for irreversible oxidations (Synlett 2016, DOI: 10.1055/s-0035-1561297). They used B3LYP and M06-2X with CPCM(MeCN) and reported moderate agreement that is limited by experimental heterogeneity. McNeill et al. validated a computational redox screening workflow on diverse organic redox molecules and provide a better modern reference point for setting screening expectations (J. Phys. Chem. C 2020, DOI: 10.1021/acs.jpcc.0c07591). Until this project has a primary, medium-consistent benchmark, a 0.30 V Tier-1 MAE target should be treated as an aspirational gate, not a demonstrated accuracy claim. A defensible near-term target is 0.3-0.5 V MAE for onset/Epa-heavy nonaqueous data, with tighter targets reserved for Fc-referenced E1/2 subsets.

## Deliberately Excluded Or Downgraded

- 3-hexylthiophene is retained but downgraded to Tier C because the VNUHCM 2023 methods text has internal reference/electrolyte inconsistencies and an implausible 0.1 mV/s scan rate; it is excluded from default calibration.
- The EDOT/methanol row was deliberately omitted so the benchmark nucleus does not require modifying the solvent library.
- Missing target families remain out of the nucleus until primary, condition-complete rows are recovered: pyrrole, aniline, furan, ProDOT, EDOP, fluorene, CPDT, bithiophene, terthiophene, and donor-acceptor thiophene-benzothiadiazole units.

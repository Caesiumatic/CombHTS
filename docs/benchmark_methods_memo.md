# Benchmark Methods And Reliability Memo

Last updated: 2026-06-17

## Scope

`data/benchmark.csv` is strict benchmark v3: 32 calibration-eligible rows collapsing to 32 groups
under canonical SMILES + `solvent_name` + `label_type`. Every row is a native aqueous Ag/AgCl
measurement (`conversion_to_AgAgCl_V` = 0.000 V, `reference_frame` = agagcl) in a nonaqueous medium
that is present in the repo solvent library. The split is 19 `monomer_oxidation_peak` groups and 13
`monomer_oxidation_onset` groups. Source families are: Cihaner and Onal 2007 (substituted
thiophenes, peak, MeCN); Camarada et al. 2011 (thiophene oligomers, onset, MeCN and DCM);
Icli-Ozkut et al. 2013 and Kalcik et al. 2022 (furan-flanked benzochalcogenadiazole/anthracene
FSeF/FSF/DFA, peak, MeCN) plus the DCM benzoselenadiazole set OSeO/SSeS/SeSeSe from Karabay et al.
2016 (peak); Cakal et al. 2020 (thieno[3,4-c]pyrrole-4,6-dione D-A-D monomers FTPF/TTPT/STPS, peak
and onset, DCM); Oguzturk et al. 2015 (di(2-furyl)carbazoles M1-M4, peak, MeCN); and Algi et al.
2017 (pyrrolo[3,4-d]pyridazinedione compounds 5 and 6, peak, MeCN). The calibration profiles draw
`agagcl_peak_strict` = 9 (tier A), `agagcl_peak_relaxed` = 19 (tier A+B), and `agagcl_onset_relaxed`
= 13 (tier A+B); the Fc/Fc+ profiles are empty and skipped pending PI approval.

Because every retained v3 row already reports on an aqueous Ag/AgCl-type scale, the nonaqueous
liquid-junction conversion problem discussed below is sidestepped in the current benchmark: all 32
rows use an identity (0.000 V) conversion rather than a table-based or cross-solvent offset.

The earlier nucleus described in prior versions of this memo (Alakhras 2015 thiophene/selenophene,
Cocuk 2025 EDOT, Contal 2019 carbazole, VNUHCM 2023 3-hexylthiophene) is fully superseded. None of
those rows met the strict native-Ag/AgCl, label-hygiene, and exact-locator rules, and they now live
in `data/benchmark_candidates.csv` as demoted/excluded/unresolved provenance rather than in the
benchmark.

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

All non-benchmark rows are retained in `data/benchmark_candidates.csv` with an explicit
`curation_status` and `curation_blocker`. The current blockers are:

- Asil et al. 2009 TTT-Lum: native Ag/AgCl and structure confirmed (C14H8N2O2S3 matches the paper
  HRMS), but the oxidation peak was measured in 0.1 M LiClO4/MeCN + 5% BF3-Et2O, a Lewis-acid-
  modified medium that is not clean acetonitrile and is not representable in the repo solvent list.
- Alakhras 2015 thiophene/selenophene and Contal 2019 carbazole: threshold/onset values that depend
  on a nonaqueous SCE to aqueous Ag/AgCl conversion the strict policy does not accept without a
  same-medium justification; exact locators were also not recovered.
- Cocuk 2025 EDOT (five rows): source-calibrated Ag pseudo-reference looks promising, but the exact
  figure/table/page locator and clean monomer-versus-growth-feature classification are unresolved.
- VNUHCM 2023 3-hexylthiophene: internal reference/electrolyte inconsistencies and an implausible
  0.1 mV/s scan rate; retained for transparency only.
- Ergun 2013 fluorene-flanked monomers: mixed-solvent media (MeCN/DCM and DCM/BF3-Et2O) outside the
  repo solvent list.
- Demirboga 1999 furan/2-methylfuran: reported versus Ag0/Ag+ with no recovered same-medium anchor
  to Ag/AgCl.
- Patra 2008 EDOS/EDOT comparison: reference electrode not recoverable from the accessible text.
- 3'-carboxyl-terthiophene (Anal. Chem. ac015572w): value reported to one significant figure with an
  incomplete citation; structure resolved but provenance too weak to promote.

The EDOT/methanol row remains deliberately omitted so the benchmark does not require modifying the
solvent library.

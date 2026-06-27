# Directive §4.1 / §4.2 compliance audit (2026-06-26)

Binary audit of the Multi-Tier Computational Workflow (`Directive_CombHTS.pdf` §4.1 Tier-1, §4.2 Tier-2)
against the actual implementation. Trigger: the IPEA-xTB deviation (T18) raised the question "what else
deviates?". Verdict per line: **COMPLIANT** / **DEVIATION** / **NOT YET IMPLEMENTED**. No hedging.

## §4.1 Tier 1 — Rapid Pre-Screen

| directive line | required | implemented | verdict |
|---|---|---|---|
| Structure: SMILES→3D | RDKit | RDKit ETKDG | **COMPLIANT** |
| Structure: oligomer assembly | **stk** (Supramolecular Toolkit) | RDKit `RWMol` assembly (`structures/oligomer.py`; stk absent in env) | **DEVIATION** (substitute) |
| Structure: conformer search | MMFF94, 50–200 confs, lowest-E | MMFF94, n=100, lowest-E | **COMPLIANT** (Se monomers skipped — MMFF94 has no Se, T10 → limitation) |
| Geometry engine | GFN2-xTB, vacuum | GFN2-xTB, vacuum | **COMPLIANT** |
| IP/EA engine | **IPEA-xTB** (vertical + adiabatic) | **GFN2-xTB adiabatic ΔSCF** | **DEVIATION** (engine; T18) |
| IP/EA calibration | Zwijnenburg linear model → **B3LYP-quality** | own linear fit → **experimental Ag/AgCl** | **DEVIATION** (calibration target) |
| IP/EA solvation | GBSA implicit, each solvent's dielectric | **ALPB implicit, each solvent's dielectric** (`calculators.py:49` passes `solvent_eps_r`, `xtb_gbsa_name`) | **COMPLIANT** (ALPB ≈ GBSA, per-solvent) |
| Solvation ΔGsolv | **COSMO-RS** (COSMOtherm or openCOSMO-RS) | **ALPB ΔGsolv affinity proxy** | **DEVIATION** (method) |
| Solvation filter threshold | ΔGsolv < −3 kcal/mol | `max_solvation_dG_kcal_mol: -3.0` | **COMPLIANT** |
| Optical gap engine | sTDA-xTB on hexamers | sTDA-xTB on hexamers (real, post-install) | **COMPLIANT** |
| Optical calibration | **calibrate against a TD-DFT reference set** | **uncalibrated 15% diagnostic; no TD-DFT reference set built** (calibration *attempted* vs experimental anchors → cannot graduate, T6) | **DEVIATION** (no TD-DFT calibration) |
| Filter: window margin | monomer AIP < solvent anodic − 0.3 V | `min_window_margin_V: 0.3` | **COMPLIANT** |
| Filter: anion margin | anion ox > monomer AIP + 0.2 V | `min_anion_stability_margin_V: 0.2` | **COMPLIANT** |
| Filter: solubility | ΔGsolv < −3 kcal/mol | −3.0 | **COMPLIANT** |

**§4.1 deviations: 4** — (1) IP/EA engine GFN2 vs IPEA-xTB; (2) IP calibration to experiment vs Zwijnenburg→B3LYP;
(3) solvation ALPB-proxy vs COSMO-RS; (4) optical uncalibrated vs TD-DFT-calibrated. Plus stk→RDKit (structure)
and Se-conformer skip (structure-level limitation). **Compliant: solvation-of-IP (per-solvent ALPB), all three
numeric filter thresholds (0.3 / 0.2 / −3), geometry engine, conformer search, optical engine.**

## §4.2 Tier 2 — DFT Refinement

**Status: NOT YET EXECUTED at scale** (gated behind the freeze + Tier-1 survivors). Only a DFT *calibration*
batch (SGE 417442) has run.

| directive line | required | implemented | verdict |
|---|---|---|---|
| DFT optimization | B3LYP/6-31G(d,p) + **SMD** | calibration batch 417442 ran **gas-phase** B3LYP/6-31G(d,p) (v1, per `tier2.yaml`); tier2 config *supports* SMD but the run was gas | **DEVIATION (calibration batch) / NOT YET RUN (Tier-2 proper)** |
| Adiabatic ΔSCF redox | E = [G(cat)−G(neu)]/F − E°(ref); SHE 4.28 V, −0.197 shift | constants pinned (ABS_SHE 4.28; SHE→Ag/AgCl −0.197) | **COMPLIANT (constants)**; full Tier-2 redox **NOT YET RUN** |
| Spin density (radical cation) | **Hirshfeld**, DFT | xTB **Mulliken** spin now available (just fixed); no DFT/Hirshfeld | **NOT YET IMPLEMENTED (DFT/Hirshfeld)** |
| Dimerization ΔG | **B3LYP/6-31G(d,p)/SMD** | **GFN2-xTB** ΔG (B1, size-confounded) | **NOT YET IMPLEMENTED (DFT level)** |
| Oligomer band-gap convergence | **TD-B3LYP/CAM-B3LYP**, n=1–6 | **sTDA-xTB** n=1–6 | **NOT YET IMPLEMENTED (TD-DFT)** |
| Reorganization energy λ (solvent) | λ = E(vIP)−E(aIP), DFT | computed at GFN2 (`solvent_lambda_ox`, report-only) | **NOT YET IMPLEMENTED (DFT)** |
| Refined filter | AIP < anodic − 0.5 V; composite §5 | composite §5 implemented; tighter margin not applied (no Tier-2 run) | **NOT YET RUN** |

## Classification — none of the §4.1 deviations is physically impossible

Per the directive-adherence priority, every deviation is either *correctable* or must be *explicitly PI-accepted*;
**none is in the "physically impossible" class** (unlike §3.2 ΔSCF-ESW or §8 <0.15 V, which are genuine walls):

- **IPEA-xTB**: available on Lop (`param_ipea-xtb.txt`; `xtb --vipea`). → correct (T18, in progress).
- **COSMO-RS**: openCOSMO-RS via ORCA 6.1 (on Lop) is directive-sanctioned. → correctable (currently proxy).
- **Optical TD-DFT calibration**: build a TD-DFT reference set on the hexamers. → correctable (note: optical still can't graduate per T6, but the directive step itself is doable).
- **stk**: pip-installable. → correctable (or justify RDKit assembly is structurally equivalent + PI-accept).
- **Se conformer skip**: use UFF/xtb geometry for Se. → correctable.
- **DFT SMD (Tier-2)**: tier2 config supports SMD; the gas-phase was a v1 calibration choice. → correct when Tier-2 runs.

**Bottom line:** §4.1's numeric filters and solvation-dielectric handling are compliant; the 4 deviations are
all method substitutions (IPEA-xTB, COSMO-RS, optical-TD-DFT, stk) made for environment/effort reasons, none
documented as decisions until now. Restoring §4.1 compliance (at minimum IPEA-xTB + COSMO-RS) before the freeze
is the directive-faithful path; each substitution we keep must be an explicit PI-accepted deviation, not silent.

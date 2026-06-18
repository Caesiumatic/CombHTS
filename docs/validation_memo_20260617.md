# Experimental validation memo — 2026-06-17

> Generated from a real run (method: `gfn2-xtb`).

## 1. Monomer Eox accuracy by calibration profile

| Profile | n | MAE-after (V) | LOO-CV MAE (V) | Residual std (V) | Spearman ρ | R² | PASS/FAIL vs 0.30 V |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| agagcl_peak_strict | 9 | 0.144 | 0.197 | 0.158 | 0.833 | 0.889 | PASS |
| agagcl_peak_relaxed | 19 | 0.167 | 0.217 | 0.246 | 0.860 | 0.592 | PASS |
| agagcl_onset_relaxed | 13 | 0.109 | 0.145 | 0.135 | 0.926 | 0.693 | PASS |
| fc_peak_strict | 0 | — | — | — | — | — | skipped (fewer than 2 calibration points) |
| fc_onset_relaxed | 0 | — | — | — | — | — | skipped (fewer than 2 calibration points) |

The 0.30 V gate is a PROVISIONAL engineering target, not an established accuracy (see caveat). LOO-CV MAE is the headline; report it with the residual spread.

## 2. Where the model fails

Worst-predicted calibration monomers (profile `agagcl_peak_relaxed`):

| Monomer | Family | Predicted Eox (V) | Experimental Eox (V) | Signed error (V) |
| --- | --- | ---: | ---: | ---: |
| 3,4-dibromothiophene | thiophene | 1.795 | 2.460 | -0.665 |
| STPS (5-(2-ethylhexyl)-1,3-di(selenophen-2-yl)-thieno[3,4-c]pyrrole-4,6-dione) | selenophene | 2.180 | 1.520 | +0.660 |
| thiophene | thiophene | 1.808 | 2.050 | -0.242 |
| 3,4-dimethoxythiophene | thiophene | 1.241 | 1.450 | -0.209 |
| FSeF (4,7-di(furan-2-yl)benzo[c][1,2,5]selenadiazole) | furan | 1.235 | 1.060 | +0.175 |

MAE-after by coarse chemical family (best-effort SMILES substructure bucketing):

| Family | MAE-after (V) | n |
| --- | ---: | ---: |
| carbazole | 0.082 | 4 |
| furan | 0.108 | 4 |
| selenophene | 0.333 | 2 |
| thiophene | 0.195 | 9 |

## 3. Physical sanity checks (directional monomer Eox, within one solvent)

Solvent: `acetonitrile`; harvest: `outputs/tier1_all_xtb.csv`.

| Check | Result | Detail |
| --- | :---: | --- |
| Eox(EDOT) < Eox(thiophene) — dioxy substitution lowers Eox | PASS | Eox(EDOT)=1.541 V < Eox(thiophene)=2.235 V |
| Eox(3-hexylthiophene) < Eox(thiophene) — alkyl substitution lowers Eox | PASS | Eox(3-hexylthiophene)=1.737 V < Eox(thiophene)=2.235 V |
| Eox(EDOP) < Eox(pyrrole) — dioxy substitution lowers Eox | PASS | Eox(EDOP)=1.183 V < Eox(pyrrole)=1.845 V |
| Eox(EDOS) < Eox(selenophene) — dioxy substitution lowers Eox | PASS | Eox(EDOS)=1.467 V < Eox(selenophene)=2.013 V |
| Eox(bithiophene) < Eox(thiophene) — extended conjugation lowers Eox | PASS | Eox(bithiophene)=1.476 V < Eox(thiophene)=2.235 V |

Summary: 5 PASS, 0 FAIL, 0 SKIP.

## 4. What we CANNOT validate yet

- **Solvent ESW MAE (< 0.30 V)** — not computable yet: there is no solvent electrochemical-window experimental benchmark in the repo. The computed solvent anodic/cathodic limits cannot be scored against measured values until such a benchmark is curated. No number is reported here.
- **Qualitative feasibility yes/no accuracy (> 85%)** — not computable yet: `data/benchmark.csv` holds continuous Eox values, not binary "does it polymerize yes/no" labels. Computing this first requires DEFINING a label source (a curation/PI decision), so no accuracy is reported here.

## 5. Caveats (THINK T3, T4)

The 0.30 V target is a provisional engineering gate, not an established accuracy. xTB computes an adiabatic one-electron potential while the benchmark mixes irreversible Epa/onset values shifted by follow-up chemistry, so a residual spread on the order of ~0.2 V is an irreducible label/medium noise floor — always report LOO-CV MAE together with the within-group spread, and do not claim < 0.3 V as demonstrated. The current fit is an INTERIM xTB→experimental stand-in: the brief's design calibrates xTB→DFT and then validates the pipeline against experiment, but the Tier-2 DFT tier is not built yet, so the >=30-group reference-purity burden currently sits on the calibration set. Treat these numbers as screening-grade.

## 6. Regenerate with real numbers (cluster)

```bash
# On the SCS Lop cluster via qsub (real GFN2-xTB; do NOT run on a head node):
eps validate --engine xtb --all-profiles
eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv
eps sanity --harvest outputs/tier1_all_xtb.csv --solvent acetonitrile
eps memo --engine xtb --harvest outputs/tier1_all_xtb.csv
```

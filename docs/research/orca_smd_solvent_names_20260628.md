# ORCA 6.1 SMD solvent-name verification for §4.2 Tier-2

**Date:** 2026-06-28 · **Job:** SGE 417994 (Lop, `orca/6.1.0-418`)

The §4.2 Tier-2 ORCA redox path applies per-triad SMD via `%cpcm / smd true / SMDsolvent "<name>"`
(`build_orca_redox_input`). The name must be a string ORCA's SMD database recognizes, so the
`orca_smd_name` column in `data/solvents.csv` was **verified, not guessed**: a tiny H₂ B3LYP/def2-SVP
SMD single point was run per candidate name; ORCA terminating normally ⇒ valid, the
`solv_defs.cpp:4766 "Solvent name not found"` error ⇒ invalid.

## Result — 10/13 library solvents have a built-in ORCA SMD name

| library solvent | orca_smd_name | 417994 |
|---|---|---|
| acetonitrile | `Acetonitrile` | PASS |
| DCM | `CH2Cl2` (also `DiChloroMethane`) | PASS |
| DMF | `DMF` (also `N,N-DiMethylFormamide`) | PASS |
| DMSO | `DMSO` (also `DiMethylSulfoxide`) | PASS |
| THF | `THF` (also `TetraHydroFuran`) | PASS |
| nitromethane | `Nitromethane` | PASS |
| water | `Water` | PASS |
| sulfolane | `Sulfolane` | PASS |
| nitrobenzene | `NitroBenzene` | PASS |
| benzonitrile | `BenzoNitrile` | PASS |
| **propylene carbonate** | *(empty)* | FAIL (`PropyleneCarbonate`, `Propylene Carbonate`) |
| **GBL** | *(empty)* | FAIL (`g-Butyrolactone`, `GammaButyrolactone`) |
| **NMP** | *(empty)* | FAIL (`NMP`, `N-MethylPyrrolidone`) |

Control: a deliberate junk name (`ZZZINVALIDSOLVENT`) FAILed, confirming the probe discriminates.

## Consequence

- The 10 PASS solvents run §4.2 Tier-2 with directive-faithful per-solvent SMD.
- **propylene carbonate, GBL, NMP are NOT in ORCA's built-in SMD set.** Those triads currently fall
  back to **gas phase** (`orca_smd_name` empty → `solvent_model_name=None` → no CPCM block). Before a
  production Tier-2 batch over these three solvents, either supply explicit SMD descriptors
  (custom-solvent `%cpcm` with Eps/Refrac/Abraham parameters) or accept the gas-phase deviation and
  record it. Flagged here so it is not a silent gap.

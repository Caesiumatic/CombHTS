# Tier-1 IP engine: GFN2-xTB → IPEA-xTB (directive §4.1 compliance, T18) — 2026-06-26

Restores directive §4.1, which mandates **IPEA-xTB** for Tier-1 monomer/solvent IP/EA (the project had
used GFN2-xTB adiabatic IP — a silent deviation; see `tier1_directive_compliance_audit_20260626.md`).

## What changed (code)
- `XTBEngine._run_ipea` runs `xtb --vipea` (IPEA-xTB = GFN1 Hamiltonian + empirical IP/EA shift), with
  ALPB at each solvent's dielectric (§4.1), and auto-sets `XTBPATH` from the binary's `share/xtb` dir so
  `param_ipea-xtb.txt` is found without SGE-env wiring. New quantities `ipea_ip` / `ipea_ea`;
  `parse_ipea_value` reads `delta SCC IP/EA (eV)` (final value, empirical shift already applied).
- `monomer_eox_vs_AgAgCl` + `solvent_anodic_limit` → `ipea_ip`; `solvent_cathodic_limit` → `ipea_ea`.
- **Unchanged (per their directive sections):** anion oxidation (§3.3 adiabatic ΔSCF), oligomer Eox
  (§3.1 AIP), reorganization λ (vertical − adiabatic). These keep `adiabatic_ip` / `adiabatic_ea`.

## Re-calibration (SGE 417986, 49-row benchmark, real IPEA-xTB)

| profile | n | slope | intercept (V) | R² | in-sample MAE (V) | LOO-CV (V) |
|---|---:|---:|---:|---:|---:|---:|
| **agagcl_peak_strict** (tier A) — **PINNED** | 9 | 0.931164 | −0.083599 | 0.772 | 0.177 | **0.246** |
| agagcl_peak_relaxed (A+B) | 29 | 0.730448 | +0.092948 | 0.559 | 0.182 | 0.198 |
| agagcl_onset_relaxed (A+B) | 19 | 0.411543 | +0.488252 | 0.730 | 0.106 | 0.119 |

`configs/tier1.yaml` re-pinned to the strict IPEA line; `CALIBRATION_ACTIVE.md` + snapshot tests updated.

## Honest findings (no hedging)

1. **IPEA-xTB is slightly WORSE on the strict headline than GFN2-adiabatic was.** Strict LOO-CV rose
   0.197 → **0.246 V** and R² fell 0.889 → 0.772. Both sit inside the honest-floor band 0.20–0.35 V (T3).
   The switch is made for **directive compliance** (§4.1 mandates IPEA-xTB), which is the deciding factor —
   not a claimed accuracy gain. (Mechanism: IPEA-xTB gives a *vertical* IP; for this n=9 experimental-peak
   set, GFN2 *adiabatic* IP happened to correlate marginally better. The directive's intent is IPEA-xTB at
   Tier-1, DFT-adiabatic at Tier-2.)
2. **The strict-vs-relaxed verdict reverses under IPEA.** With GFN2, strict won (LOO 0.197 < 0.232). With
   IPEA, **relaxed LOO 0.198 < strict 0.246** — but strict keeps the higher R² (0.772 vs 0.559) and tier-A
   purity. Strict is pinned (purity + R² + continuity); **strict-vs-relaxed re-confirmation under IPEA is a
   freeze-time item** (T1/T18) — not silently resolved here.
3. **Se monomers:** IPEA-xTB (GFN1-based) runs on selenophene/EDOS/EDOP (the run completed for all 49 rows);
   the RDKit `UFFTYPER: Se2+2` warnings are geometry-embedding noise, not IPEA failures.

## Status
T18 remediation **DONE** for the IP engine. Remaining §4.1 deviations (DECISIONS_PENDING B5): COSMO-RS
(solubility), TD-DFT optical calibration, stk oligomer assembly.

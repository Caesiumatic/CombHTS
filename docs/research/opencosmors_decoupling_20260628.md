# openCOSMO-RS on ORCA 6.1 — σ-profile export/reuse & the decoupling (2026-06-28)

Answers the scoping question for the §4.1 COSMO-RS deviation (DECISIONS_PENDING B5(b)): **does ORCA 6.1
support σ-profile export/reuse for the COSMO-RS decoupling, or is a standalone openCOSMO-RS package needed?**

## Answer: ORCA 6.1 supports it natively — no external package required

ORCA `6.1.0-418` on Lop (`/share/apps/orca/orca_6_1_0/`) ships a standalone **`openCOSMORS` executable**
(`/share/apps/orca/orca_6_1_0/openCOSMORS`, 1.7 MB ELF). The σ-profiles are real, reusable files. The
integrated `! COSMORS(solvent)` keyword internally runs the full per-pair pipeline; the pieces it leaves on
disk are exactly what's needed to decouple:

- per species: `!BP86 def2-TZVPD` (gas energy) + `!BP86 def2-TZVPD CPCM / %cpcm cosmorscalc true` (COSMO
  σ-surface) → a **`.orcacosmo`** σ-profile file (+ the species' gas-phase `FINAL SINGLE POINT ENERGY`).
- per pair: an input **`.json`** with fixed openCOSMO-RS-24a parameters (Aeff, ln_alpha, SigmaHB, dGsolv_tau
  per-element, …), the solute-specific `dGsolv_E_gas` and `dGsolv_numberOfAtomsInRing`, and
  `componentPaths: [solute.orcacosmo, solvent.orcacosmo]`. Running `openCOSMORS in.json out.json` yields
  `{"dGsolv": [[[ <kcal/mol>, 0.0 ]]]}` — a **millisecond** statistical integration, **no DFT**.

This is exactly the decoupling: the DFT cost is **one σ-profile per species** (N_monomers + N_solvents),
not one per (monomer × solvent) pair; the pairwise ΔGsolv is free.

## Cost (real benchmarks, this project)
- thiophene (5 heavy atoms): full per-pair COSMORS = **126 s** (1 core; dGsolv −4.132 kcal/mol, reproduces
  pilot SGE 417544 exactly). The σ-profile (solute vac+cpcm) is the dominant part.
- tris(4-methoxyphenyl)amine (25 heavy atoms): **2723 s ≈ 45 min** (SGE 417988; dGsolv −16.728 kcal/mol) —
  per-species COSMO DFT scales steeply (~O(N³)). Large monomers are the cost driver.
- **Decoupling is REQUIRED, not just nice-to-have** (quantified with the two real points):
  - decoupled (one σ-profile per species): ~30 large (45 min) + ~100 small/medium (~10 min) + ~25 solvents
    ≈ **~44 CPU-hours one-time**, embarrassingly parallel → a few wall-hours. **Feasible** (≤ §9 Tier-1
    budget of ~50–500 CPU-hr, and one-time).
  - per-pair (the current pilot path): the large monomers alone, 30 × 25 solvents × 45 min ≈ **~560
    CPU-hours** — exceeds the entire §9 Tier-1 budget. **Infeasible.** This is why the decoupled
    σ-profile-reuse implementation (not the per-pair `! COSMORS(solvent)` call) is the correct one.

## Correction of an earlier error
My initial framing ("openCOSMO-RS via ORCA ≈ DFT CPU-hours/species, infeasible at 50k Tier-1; A/B resource
trade-off") was **wrong and unbenchmarked**: I assumed per-pair DFT and pattern-matched "DFT = CPU-hours".
Real cost is ~2 min (small) to tens of min (large) per **species** σ-profile, decoupled and reusable. The
A/B dilemma is void — openCOSMO-RS at Tier-1 is the directive-faithful and feasible path.

## Implementation plan (decoupled; low-risk on the hard-constraint axis)
1. **Per-species σ-profile**, cached as a file: generate the `.orcacosmo` (+ gas E) once per monomer and per
   solvent. The solute-specific json fields (`dGsolv_E_gas`, `dGsolv_numberOfAtomsInRing`) are taken
   **verbatim from ORCA's own generated json** (extract + cache) — not reverse-engineered — to avoid any
   risk of a subtly-wrong hard-constraint descriptor.
2. **Per-pair combine**: fill the fixed-parameter template with the cached solute fields +
   `componentPaths=[solute.orcacosmo, solvent.orcacosmo]`, run the bundled `openCOSMORS` binary, parse
   `dGsolv[0][0][0]`.
3. **Validate**: the decoupled thiophene/acetonitrile result must reproduce the per-pair **−4.132 kcal/mol**
   to the digit before wiring into the screen.
4. **Wire**: per-quantity engine routing in Tier-1 — `solvation_free_energy` → openCOSMO-RS, all other
   quantities → IPEA-xTB/GFN2-xTB. Replaces the ALPB ΔGsolv affinity proxy (the §4.1 deviation).

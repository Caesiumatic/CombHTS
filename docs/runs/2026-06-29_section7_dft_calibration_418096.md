# Run: 2026-06-29 — directive §7 fix: xTB→DFT calibration launch + partial Tier-2 harvest

Goal: make §7 directive-literal. Three code deviations were closed (committed: 8f20f80, f9f59b4,
227ddc8, 60d9971), then the live DFT numbers were launched.

## §7 code (directive-literal, committed, 385+ tests green)
1. **Validation, both legs** — `directive.py` grades the **original DFT vs experiment** MAE
   (< 0.15 V), no longer hard-coded `OUT_OF_SCOPE`; calibrated-xTB-vs-exp (< 0.3 V) retained.
   `dft_calibration.py` now computes DFT Eox in V vs Ag/AgCl (per-solvent SMD) + both RAW MAEs +
   the screen-ready `xtb_to_dft_V` anchor. CLI `validate-directive --dft-benchmark`.
2. **Production anchor** — `tier1.yaml calibration.xtb_to_dft.monomer_oxidation` (anchor=dft) +
   `_oxidation_calibration` PREFERS it when enabled; legacy xTB→experiment kept as the labeled
   interim until pinned.
3. **Launchable DFT** — `calibrate-dft --engine orca` (B3LYP/6-31G(d,p)/SMD/Freq ΔG, same redox
   path/cache key as Tier-2) + `--n-shards/--shard-index`; `scripts/run_dftcal_orca_array.sge` +
   `scripts/harvest_dftcal_orca.py`.

## Partial Tier-2 harvest (taken before re-prioritizing)
- `tier2-harvest` on the in-flight sweep: **71 validated successes** of 651 (558 missing/queued,
  22 failed) → `outputs/tier2_full/redox_harvest_partial.csv`: 43 monomer (49 IP + 22 EA) +
  28 electrolyte_anion, all finite. Dimer/bandgap: 0 shards (queued, not started).
- Partial DFT-refined screen: 2718 Tier-1 survivors → **2354 Tier-2-refined** (monomer Eox + anion
  DFT only; no dimer f4 / bandgap f5 yet) → `outputs/tier2_full/tier2_refined_partial.csv`.
  Harvest pulled locally to `outputs/tier2_full_redox_harvest_partial.csv`.

## Re-prioritization (user-directed)
The Tier-2 sweep was STILL running (earlier "stopped" read was a masked `qstat` — SGE not on PATH
under the non-login shell + `2>/dev/null`; fixed by sourcing
`/opt/gridengine/default/common/settings.sh`). Under `maxujobs=30` the §7 array sat behind the
whole sweep. Per user instruction: harvest current results → **qhold the sweep** (418031/032/033;
running tasks finish as `hr`, pending held) → run §7 fastest.
- §7 array `418096.1-37` (one benchmark monomer per task; ORCA serial). Task 1 running on first
  freed slot; 2-37 ramp up to 30 as the held sweep drains. Held for later release: 418031 (tail),
  418032 (dimer), 418033 (bandgap), 418034 (finalize), 418037 (post-redox).

## Next (when 418096 completes)
`python scripts/harvest_dftcal_orca.py` → pin `xtb_to_dft_V` slope/intercept into
`tier1.yaml calibration.xtb_to_dft.monomer_oxidation` + `enabled: true` → re-harvest Tier-1
(new survivor set) → re-run `validate-directive --dft-benchmark` for the §7 DFT-vs-exp PASS/FAIL.
Then `qrls` the sweep.

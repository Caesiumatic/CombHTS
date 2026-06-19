# Overnight report — 2026-06-18 (batch 3): Step-2 live DFT-calibration batch

First LIVE g16 DFT-calibration session on Lop, plus a literature-review intake (research3/4/5).
This is a **documentation-only** sync — no code/config/data changed in this commit; the live batch
itself ran on the cluster outside the repo. THINK.md (T13 new; T1/T4/T6 advanced), STATUS.md, and
three `docs/research/` reviews were updated/added; this note records what ran and what is now open.

## Result at a glance

| Item | State |
| --- | --- |
| Gas-phase thiophene DFT smoke (job 417289) | OK — `dft_Eox` ≈ 8.51 eV |
| Solvated+freq DFT smoke (job 417296) + full batch (job 417297) | RUNNING overnight (slow on big molecules) |
| Config-blind DFT cache bug | FOUND → new THINK **T13** (fix specified; workaround in place) |
| Strict-vs-relaxed screening anchor | tiebreaker planned (empirical LOO-CV) → THINK **T1** |
| Literature reviews research3/4/5 | added under `docs/research/` and linked from THINK T1/T4/T6 + STATUS |

No pinned config/data changed (`configs/tier1.yaml`, `tier2.yaml`, `scoring.yaml`, `redox.py`,
`data/*.csv` untouched). The xTB→DFT (and the composed xTB→V) calibration remains a NEW artifact;
the pinned screening default is UNCHANGED pending the completed batch + PI sign-off.

## What ran on Lop

- **Gas-phase smoke (417289):** one-monomer/gas-phase B3LYP/6-31G(d,p) ΔSCF `adiabatic_ip`;
  thiophene `dft_Eox` ≈ **8.51 eV**. Confirms the live `--engine gaussian` path works end-to-end.
- **Solvated + Freq batch (417296 smoke, 417297 full):** B3LYP/6-31G(d,p) targeting
  SMD(acetonitrile) with the thermal/Freq toggle on. This is **slow** because the
  calibration-eligible benchmark is dominated by LARGE exotic molecules (α-sexithiophene; di-aryl
  benzothiadiazole/selenadiazole D-A; ethylhexyl thieno[3,4-c]pyrrole-diones FTPF/TTPT/STPS;
  di-furyl carbazoles; DPP-pyridazinediones) — opt+freq on these is impractically fast-turnaround,
  which is exactly what justified the **opt-only / gas-phase v1** Tier-2 pragmatic choice. Running
  overnight; numbers pending.

## T13 — config-blind DFT cache bug (found this session)

`outputs/dft_calibration_cache.sqlite` keys on `(canonical_smiles, charge, method, solvent_name,
quantity)`, but `method` is the static string `"b3lyp-6-31g(d,p)-smd"` and `_dft_eox_eV` passes
`solvent_name=None` — so the **SMD solvent, the Freq toggle, and the basis/functional are NOT in the
key**. Editing `configs/tier2.yaml` (gas → SMD, `use_freq` false → true) does not change the key.

- **Evidence:** the gas-phase smoke (417289) cached thiophene's gas-phase `dft_Eox` = 8.51 eV; the
  later solvated+freq runs (417296/417297) **reused** that 8.51 eV for thiophene instead of
  recomputing solvated. So thiophene's "solvated" point is stale gas-phase; other monomers (absent
  from the gas-phase smoke cache) compute fresh.
- **Workaround until fixed:** wipe `outputs/dft_calibration_cache.sqlite` on any `tier2.yaml` change.
- **Fix (specified, not yet applied — this is a docs commit):** encode the full DFT config in the
  cache key (or the `method` label) — at minimum SMD solvent + Freq toggle + basis/functional.

## T1 — empirical strict-vs-relaxed anchor tiebreaker (planned)

The strict fit's in-sample → LOO-CV MAE jump (**0.144 → 0.197 V, +37%**) is itself evidence that
n=9 is too thin/point-sensitive, pushing the lean toward `agagcl_peak_relaxed` (n=19) on
CONDITIONING grounds over `agagcl_peak_strict` (purity). Plan: once the live DFT batch lands, fit
DFT→experiment (Fit 2) on BOTH the peak_strict and peak_relaxed eligible sets, compare LOO-CV MAE,
and adopt the better-generalizing anchor (self/group call — the directive is the authority, not a PI
gate), then reconcile `tier1.yaml` + `calibration_profiles.yaml`.

## Literature reviews intake (research3/4/5)

Added under `docs/research/` and linked from THINK:

- **`new_monomer_eox_benchmark_extraction.md`** (new-monomer Eox): clean small-monomer anchors —
  terthiophene **+0.880 V vs Ag/AgCl** (Camarada 2011), DTP **~0.52 V**, 3-methylthiophene ~1.55 V
  vs SCE — that PARTIALLY rebalance the big-molecule-skewed calibration-eligible set toward the
  simple monomers the screen targets (→ T4). Most furan/fluorothiophene/aniline values are
  BFEE/aqueous-acid/pseudo-ref and stay excluded.
- **`polymer_optical_gap_experimental_anchors.md`** (polymer optical gaps): a vetted NEUTRAL-state
  optical-gap anchor set for the eventual TD-DFT/sTDA calibration — P3HT ~1.9, neutral PEDOT ~1.6,
  PEDOS ~1.4, polyselenophene ~1.9, PFO ~2.9–3.0, PCPDTBT ~1.4 eV. Validate against the neutral
  π–π* gap ONLY (not the doped state, not CV gaps); exclude polyaniline (→ T6).
- **`solvent_windows_and_solvation_reference.md`** (solvent windows): per-solvent Pt/GC windows +
  SMD-readiness; confirms the IL/DES/BFEE exclusion (continuum-invalid) and gives a benzonitrile
  cross-check for its provisional ESW fallback (Pt, 0.1 M TBAP: anodic ≈ +1.8 V, cathodic ≈ −1.95 V
  vs SCE) and a nitrobenzene window (≈ +1.6 to +2.0 / −1.0 to −1.1 V vs SCE).

## Open after this session

- **Live batch:** let the solvated+freq batch finish; then populate the xTB→DFT + DFT→experiment
  fits (and the composed xTB→V drop-in) with real numbers.
- **T13:** apply the cache-key fix (config in key) so a `tier2.yaml` change forces a recompute;
  until then, wipe the cache on any config change.
- **T1:** run the empirical peak_strict-vs-peak_relaxed Fit-2 LOO-CV comparison once numbers exist;
  reconcile `tier1.yaml` + `calibration_profiles.yaml`.
- **T4:** decide whether to curate the research3 small-monomer Eox anchors into the eligible set to
  shrink the big-molecule domain gap.
- **Benchmark/solvent curation:** fold the research5 benzonitrile/nitrobenzene window cross-checks
  into `data/solvents.csv` notes (a future data commit, not this docs sync).
- Standing items unchanged: PI sign-off on the screening anchor; whether the xTB→DFT (composed)
  calibration ever replaces the pinned default.

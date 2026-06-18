# Step 1 report — band gap + dimerization made real (directive's oligomer route)

The two placeholder Tier-1 scoring axes (`optical_gap`, `dimerization_dG`) are now real,
screening-grade physics, computed the directive's way. All five composite axes are now real;
the composite ranking is no longer "placeholder-contaminated" — but it is **screening-grade,
not validated**. Strictly xTB / Tier-1; no Tier-2 DFT was built or run.

## Commits (separate, focused, on `main`)

| Deliverable | Commit |
| --- | --- |
| A — reusable oligomer assembly | `7a2d6b5` |
| B — real optical (band) gap | `4c4dc7c` |
| C — real dimerization | `09b1425` |
| Docs + honesty labels + SGE + this report | (this commit) |

`pytest -q`: **111 passed, 3 skipped** (the 3 skips are the live xtb/g16/stda smokes — they
skip when the binary is absent). `ruff check`: clean.

## What changed

**A — oligomer assembly** (`src/eps/structures/oligomer.py`, `data/polymerization.csv`)
- General n-mer assembly: data-driven ditopic `[1*]/[2*]` building blocks → RDKit head-to-tail
  α-coupling → H-capped linear n-mer. `detect_alpha_carbons` auto-derives the two α sites for
  the clean 5-membered heteroaromatics; explicit building blocks cover the rest.
- **Deviation (documented):** the directive names `stk`; `stk` is not installable/usable in
  this env, so an equivalent RDKit α-coupling was implemented. `stk` was therefore **not** added
  to `pyproject.toml`.
- **Verification artifact:** `eps run-tier1` writes `outputs/oligomer_buildingblocks.csv`
  (per-monomer building block + assembled dimer/hexamer SMILES + α-autodetect cross-check) for
  human review — do not trust auto sites blindly.

**B — optical (band) gap** (`polymer_optical_gap`, `XTBEngine`)
- `optical_gap_eV` = optical gap of the assembled **n=6** oligomer: the **sTDA-xTB** lowest
  singlet excitation when `stda` is on PATH, else the oligomer **GFN2-xTB HOMO–LUMO gap** as a
  clearly-labeled proxy (`optical_gap_method = homo_lumo_hexamer_fallback`). Per-monomer, cached
  by oligomer SMILES. RAW/uncalibrated vs TD-DFT (Step-2 calibration hook).
- `n` is config (`configs/tier1.yaml` → `oligomer.n: 6`; pinned calibration untouched).

**C — dimerization** (`dimerization_dG`)
- `dimerization_dG` = xTB radical–radical coupling ΔG: `2 M+. → [M–M]2+ + 2 H+`, i.e.
  `ΔG = G([M–M]2+) + 2·G(H+) − 2·G(M+.)` via the cached engine (dimer dication +2 singlet;
  monomer radical cation +1 doublet). The proton free energy is one fixed convention
  (`PROTON_GIBBS_EV`) that cancels across monomers and under min–max, so the **absolute** ΔG is
  screening-grade while the **relative** ordering the w4 score uses is sound. Not a hard filter.

The composite formula, weights, `target_gap_eV`, the pinned oxidation calibration, and the
redox function were **not** touched — only the two INPUT axes became real.

## Honesty / flagged approximations (also in STATUS + column metadata)

- Optical gap is **uncalibrated** vs TD-DFT; if `stda` is unavailable it is the **HOMO–LUMO
  hexamer proxy** (flagged per-row in `optical_gap_method`).
- Dimerization **absolute** value is set up to the proton constant; relative ordering is sound.
- Approximate coupling regiochemistry (flagged in `data/polymerization.csv` and the
  `*_coupling_approximate` columns): **aniline** (N→para, not a clean C–C α) and the
  **benzothiadiazole–thiophene D–A** (linkage simplification).
- **Data-curation item — RESOLVED (2026-06-18):** the stored `data/monomers.csv` SMILES for
  **EDOT/ProDOT/EDOP/EDOS** previously encoded the **2,3-dioxy** isomer (one α blocked); they
  have been corrected to the directive §2.1 **3,4-dioxy** isomer (both α free). Their
  `data/polymerization.csv` rows are now `alpha` (clean auto-derived 2,5 coupling) with
  `approximate=False`, and a regression test asserts both α-carbons stay free. The calibration
  is unaffected (none of these four appear in `data/benchmark.csv`); their previously harvested
  `Eox`/`optical_gap`/`dimerization_dG` are stale and will be recomputed by the next cluster run.

## Acceptance criteria

1. `eps run-tier1 --engine mock` runs end-to-end; tests + ruff green. ✓
2. On the cluster with real xtb (+ stda or documented fallback): `optical_gap_eV` and
   `dimerization_dG` are real, per-monomer, cached, non-placeholder. ✓ (code ready; see commands)
3. The human-reviewable building-blocks artifact exists. ✓ (`outputs/oligomer_buildingblocks.csv`)
4. STATUS / analyze labels say "screening-grade — all five axes real", no
   "placeholder-contaminated" for these two axes, no overclaim of validation. ✓
5. This report lists exact cluster commands and flags every approximate/uncalibrated choice. ✓

## Exact cluster commands (SCS Lop; via qsub, never the head node)

```bash
# (a) Rebuild the env if needed (RDKit/pandas/numpy/matplotlib/scikit-learn; no stk):
cd "$HOME/CombHTS"
conda activate combhts            # or: conda env create -f environment.yml / pip install -e .[dev]
pip install -e .

# (b) Run the real-xTB Tier-1 harvest (assembles n=6 oligomers + dimer dications per monomer).
#     Loads stda if the module exists; otherwise the optical gap uses the HOMO-LUMO hexamer proxy.
qsub scripts/run_oligomer.sge
#     (equivalently: eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv)

# (c) Confirm the new columns are populated and the old placeholders are gone:
python - <<'PY'
import pandas as pd
df = pd.read_csv("outputs/tier1_all_xtb.csv")
cols = ["monomer_name","optical_gap_eV","optical_gap_method","optical_gap_oligomer_n",
        "dimerization_dG_kcal_mol","dimerization_coupling_approximate"]
print(df[cols].drop_duplicates("monomer_name").to_string(index=False))
print("optical_gap_method values:", sorted(df["optical_gap_method"].unique()))
# Expect optical_gap_method in {stda-xtb, homo_lumo_hexamer_fallback}; NOT 'mock-deterministic'.
PY

# (d) Review the coupling chemistry before trusting the new axes:
column -s, -t outputs/oligomer_buildingblocks.csv | less -S
```

## Out of scope (untouched, per the task)

No Tier-2 DFT / Gaussian runs; no spin-density or oligomer-Eox(n) sweep (Deliverable A makes
both trivial follow-ups); no library expansion; no changes to calibration constants, scoring
weights, the composite formula, or the redox function.

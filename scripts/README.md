# Cluster job templates (SGE / Grid Engine)

Version-controlled `qsub` templates for running CombHTS on the SCS Lop cluster. They are
**templates** — review and adjust resources (`-pe smp`, `-l h_rt`) before submitting, and do
not submit them blindly from CI or an overnight agent.

`audit_lit_curation_staging.py` is a local, no-engine staging-data audit wrapper. Its reusable
logic lives in `eps.curation.staging_audit`; the script preserves the historical command-line
defaults and writes review-only audit CSVs under `data/lit_curation/`.

| Script | Command | Engine module |
| --- | --- | --- |
| `run_tier1.sge` | `eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv` | xTB |
| `run_tier1_rescore.sge` | `python -m eps.cli rescore-tier1 ...` | none (CSV-only) |
| `run_validate.sge` | `eps validate --engine xtb --all-profiles` | xTB |
| `run_validate_directive.sge` | `python -m eps.cli validate-directive --engine xtb ...` | xTB |
| `run_memo.sge` | `eps memo --engine xtb --harvest outputs/tier1_all_xtb.csv` | xTB |
| `run_analyze.sge` | `eps analyze --harvest outputs/tier1_all_xtb.csv --outdir outputs/analysis/` | none (read-only) |
| `run_oligomer.sge` | `eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv` | xTB |
| `run_dft_calibration.sge` | `eps calibrate-dft --engine gaussian --config configs/tier2.yaml` | xTB + Gaussian 16 |
| `run_tier2_pilot_array.sge` | `python -m eps.cli tier2-run-task ...` | mock or Gaussian 16 |
| `run_tier2_pilot_harvest.sge` | `python -m eps.cli tier2-harvest ...` | none (read-only) |
| `run_orca_solvation_pilot.sge` | `python -m eps.cli orca-pilot-solvation --engine orca` | ORCA 6.1/openCOSMO-RS |
| `run_orca_optical_pilot.sge` | `python -m eps.cli orca-pilot-optical --engine orca` | ORCA 6.1 sTDA + TDA/TD-DFT |
| `run_optical_calibration_n6.sge` | `python scripts/run_optical_calibration_n6.py --engine orca` | ORCA 6.1 sTDA + TDA/TD-DFT |

`run_dft_calibration.sge` is the only template that loads **Gaussian 16** (`module load
gaussian/g16`). It runs the SMALL xTB->DFT calibration batch (~32 unique monomers x neutral+cation
gas-phase opts), which is DISTINCT from the full Tier-2 production screen (a separate PI decision).
It sets a NODE-LOCAL `GAUSS_SCRDIR` (Gaussian's large scratch files must not land on the networked
home dir) and cleans it up on exit.

The two ORCA templates are deliberately small, serial route-validation pilots. Lop's older compute
nodes expose an OpenMPI/hwloc topology crash when ORCA 6.1 starts parallel workers, so these pilots
request one slot. They retain raw ORCA inputs/outputs under the matching gitignored `outputs/`
directory and never present failed calculations or mock values as scientific results.

The n=6 optical template is also serial. It reads the six HIGH experimental anchors directly from
the staging-derived selection CSV, writes to `outputs/optical_calibration_n6/`, and keeps its cache
separate from the corrected n=3 pilot. Its analysis is diagnostic and cannot update scoring.

`run_validate_directive.sge` writes the authoritative directive section-7 package:
`validation_summary.json`, `validation_report.md`, `eox_profile_summary.csv`, `eox_points.csv`,
`esw_descriptor_points.csv`, `esw_gate_diagnostics.csv`, `feasibility_matches.csv`, and
`provenance.json`. Run it from a separate cluster clone/worktree and set `VALIDATE_HARVEST` to the
read-only salt-role-fixed real harvest resolved from the run manifests. It uses xTB only; do not
submit ORCA/Gaussian work through this template.

`run_tier2_pilot_array.sge` is the array-safe Tier-2 monomer-Eox pilot template. It requires
absolute `TIER2_MANIFEST` and `TIER2_OUTPUT_ROOT` values, maps `SGE_TASK_ID` to one manifest
`task_id`, and writes a task-local SQLite cache plus persistent Gaussian input/log directories.
It loads Gaussian only when `TIER2_ENGINE=gaussian`; mock mode is plumbing-only and non-scientific.

`run_tier2_pilot_harvest.sge` is the separate no-engine harvest step. It validates per-task
`result.json` files against the manifest and never fills missing/failed Tier-2 values from Tier-1.

`run_tier1_rescore.sge` is the safe path for a policy/threshold/weight change after a real harvest.
It reads the existing all-triads CSV and recomputes only conditioned joins, filters, Pareto flags,
and arithmetic scores; it accepts no Engine and never opens the expensive SQLite cache.

## The `#$ -S /bin/bash` requirement

Every script's **first SGE directive is `#$ -S /bin/bash`**. This is mandatory: without it the
scheduler can fall back to the user's login shell (csh on this cluster) and misparse the
`bash` syntax in the body, causing confusing failures. Keep it as the first `#$` line.

## Usage

> **Lop gotcha:** in an interactive login shell, `qsub`/`qstat` need the scheduler env first —
> `source /opt/gridengine/default/common/settings.sh` (the qmaster is on port **536**, not the SGE
> default, so a bare `qstat` otherwise fails with `commlib ... connection refused`).

```bash
# From the repo checkout on the cluster ($HOME/CombHTS):
source /opt/gridengine/default/common/settings.sh  # required once per login shell (port 536)
qsub scripts/run_tier1.sge        # real GFN2-xTB Tier-1 harvest
qsub scripts/run_validate.sge     # benchmark validation across calibration profiles
qsub scripts/run_memo.sge         # dated real-data validation memo
qsub scripts/run_analyze.sge      # directive §8 post-processing (no xtb)

# Monitor / inspect:
qstat                              # job status
qstat -j <job_id>                  # detailed job info
# Combined stdout+stderr lands in <job_name>.o<job_id> (we use `#$ -j y`).
```

## Shared preamble (what every script does)

- `set -uo pipefail` — fail on unset vars / pipe errors.
- Source `/etc/profile.d/modules.sh` (guarded) so `module` is available, then load Anaconda and
  the matching engine module (xTB, Gaussian, or ORCA/OpenMPI).
- Activate the conda env: `conda activate combhts`.
- `OMP_NUM_THREADS` is tied to the granted slots (four for xTB templates, one for ORCA pilots);
  `OMP_STACKSIZE=4G` and `ulimit -s unlimited` avoid stack-overflow crashes on larger systems.
- `cd "$HOME/CombHTS"` then run the matching command. The ORCA pilots and directive validation
  template optionally accept an alternate checkout through `COMBHTS_ROOT` (used for isolated
  pre-commit cluster snapshots).

Do **not** run production calculations in an interactive login session — submit via `qsub`.

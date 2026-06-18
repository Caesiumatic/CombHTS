# Cluster job templates (SGE / Grid Engine)

Version-controlled `qsub` templates for running CombHTS on the SCS Lop cluster. They are
**templates** — review and adjust resources (`-pe smp`, `-l h_rt`) before submitting, and do
not submit them blindly from CI or an overnight agent.

| Script | Command | Loads xtb? |
| --- | --- | :---: |
| `run_tier1.sge` | `eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv` | yes |
| `run_validate.sge` | `eps validate --engine xtb --all-profiles` | yes |
| `run_memo.sge` | `eps memo --engine xtb --harvest outputs/tier1_all_xtb.csv` | yes |
| `run_analyze.sge` | `eps analyze --harvest outputs/tier1_all_xtb.csv --outdir outputs/analysis/` | no (read-only) |
| `run_oligomer.sge` | `eps run-tier1 --engine xtb --all-output outputs/tier1_all_xtb.csv` | yes |
| `run_dft_calibration.sge` | `eps calibrate-dft --engine gaussian --config configs/tier2.yaml` | yes (+ **g16**) |

`run_dft_calibration.sge` is the only template that loads **Gaussian 16** (`module load
gaussian/g16`). It runs the SMALL xTB->DFT calibration batch (~32 unique monomers x neutral+cation
gas-phase opts), which is DISTINCT from the full Tier-2 production screen (a separate PI decision).
It sets a NODE-LOCAL `GAUSS_SCRDIR` (Gaussian's large scratch files must not land on the networked
home dir) and cleans it up on exit.

## The `#$ -S /bin/bash` requirement

Every script's **first SGE directive is `#$ -S /bin/bash`**. This is mandatory: without it the
scheduler can fall back to the user's login shell (csh on this cluster) and misparse the
`bash` syntax in the body, causing confusing failures. Keep it as the first `#$` line.

## Usage

```bash
# From the repo checkout on the cluster ($HOME/CombHTS):
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
- Source `/etc/profile.d/modules.sh` (guarded) so `module` is available, then
  `module load anaconda/3-2023.09` and (except `run_analyze`) `module load xtb/6.4.1`.
- Activate the conda env: `conda activate combhts`.
- `OMP_NUM_THREADS="${NSLOTS:-4}"` ties xTB's threads to the granted slots;
  `OMP_STACKSIZE=4G` and `ulimit -s unlimited` avoid stack-overflow crashes on larger systems.
- `cd "$HOME/CombHTS"` then the matching `eps ...` command.

Do **not** run production calculations in an interactive login session — submit via `qsub`.

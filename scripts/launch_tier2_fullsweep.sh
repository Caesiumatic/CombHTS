#!/bin/bash
# RUN ON THE LOGIN / SUBMIT NODE (NOT via qsub) — compute nodes on Lop are not submit hosts, so an
# SGE job cannot qsub child jobs (that was the run_tier2_orchestrate.sge failure mode). This plain
# login-node script fires the entire §4.2 Tier-2 DFT sweep over the Tier-1 survivors.
#
# Usage:   bash scripts/launch_tier2_fullsweep.sh [TIER1_JOBID]
#   With TIER1_JOBID: the arrays are submitted with -hold_jid so they wait for Tier-1 to finish.
#   Without it: submits immediately (use once Tier-1 has already produced tier1_all.csv).
# No `set -u`: the optional empty HOLDOPT array trips "unbound variable" on Lop's older bash.
set -o pipefail
HOLD="${1:-}"
# Activate the project env — the login shell's default `python` is system python2.7, which cannot
# even parse the py3 CLI (the tier2-plan step ran under it and SyntaxError'd).
if [ -f /etc/profile.d/modules.sh ]; then source /etc/profile.d/modules.sh; fi
module load anaconda/3-2023.09 2>/dev/null || true
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate combhts
cd "$HOME/CombHTS"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
NSHARDS=32
SURV="$PWD/outputs/tier1_ipea_cosmors/survivors.csv"
PLANDIR="$PWD/outputs/tier2_full_plan"
MANIFEST="$PLANDIR/task_manifest.csv"
RESULTS="$PWD/outputs/tier2_full_task_results"
WORKROOT="$PWD/outputs/tier2_full_work"
OUTDIR="$PWD/outputs/tier2_full"
mkdir -p "$OUTDIR"

HOLDOPT=(); [ -n "$HOLD" ] && HOLDOPT=(-hold_jid "$HOLD")

# Filter Tier-1 survivors + plan the full §4.2 scope (needs tier1_all.csv to exist, or hold on Tier-1
# and run this script's plan step separately once it lands). Here we assume tier1_all.csv is ready.
ALL="$PWD/outputs/tier1_ipea_cosmors/tier1_all.csv"
if [ -f "$ALL" ] && [ ! -f "$MANIFEST" ]; then
    python - "$ALL" "$SURV" <<'PY'
import sys, pandas as pd
t = pd.read_csv(sys.argv[1]); col = "passes_all_tier1_filters"
(t[t[col] == True] if col in t.columns else t).to_csv(sys.argv[2], index=False)  # noqa: E712
PY
    python -m eps.cli tier2-plan --selection "$SURV" --config configs/tier2_orca.yaml \
        --scope full --allow-large-scale --outdir "$PLANDIR"
fi

N=$(( $(wc -l < "$MANIFEST") - 1 ))
REDOX=$(qsub "${HOLDOPT[@]}" -t 1-"$N" -v MANIFEST="$MANIFEST",RESULTS="$RESULTS",WORKROOT="$WORKROOT",T2CONFIG=configs/tier2_orca.yaml scripts/run_tier2_array.sge | grep -oE '[0-9]+' | head -1)
DIMER=$(qsub "${HOLDOPT[@]}" -t 1-"$NSHARDS" -v SURV="$SURV",OUTDIR="$OUTDIR",NSHARDS="$NSHARDS",T2CONFIG=configs/tier2_orca.yaml scripts/run_tier2_dimer_array.sge | grep -oE '[0-9]+' | head -1)
BG=$(qsub "${HOLDOPT[@]}" -t 1-"$NSHARDS" -v SURV="$SURV",OUTDIR="$OUTDIR",NSHARDS="$NSHARDS" scripts/run_tier2_bandgap_array.sge | grep -oE '[0-9]+' | head -1)
qsub -hold_jid "$REDOX,$DIMER,$BG" -v OUTDIR="$OUTDIR",SURV="$SURV",PLANDIR="$PLANDIR",RESULTS="$RESULTS" scripts/run_tier2_finalize.sge
echo "launched: redox=$REDOX ($N) dimer=$DIMER bandgap=$BG finalize held on all three"

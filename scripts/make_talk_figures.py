"""Generate talk figures (progress + directive compliance) into outputs/presentation/talk/."""
from __future__ import annotations
import math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path("/Users/shichen/GitHub/CombHTS")
OUT = ROOT / "outputs" / "presentation" / "talk"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 13, "axes.titlesize": 15, "axes.titleweight": "bold",
                     "figure.dpi": 150, "savefig.bbox": "tight", "axes.grid": True,
                     "grid.alpha": 0.25, "axes.axisbelow": True})

NAVY, TEAL, AMBER, RED, GREEN, GREY = "#1f3a5f", "#2a9d8f", "#e9a13b", "#c0392b", "#2e8b57", "#9aa3ab"

def save(fig, name):
    p = OUT / name
    fig.savefig(p); plt.close(fig); print("wrote", p)

# ---------------------------------------------------------------- 1. progress funnel
def funnel():
    stages = [
        ("Directive design space  (~100×25×20, §9)", 50000, GREY, "aspiration"),
        ("Frozen validated scale  (36 mon × 13 solv × 16 elec)", 7488, NAVY, "scale_guard"),
        ("Tier-1 survivors  (xTB: window + anion + solubility)", 3275, TEAL, "§4.1"),
        ("Tier-2 refined, partial  (DFT window −0.5 V)", 2906, AMBER, "§4.2"),
        ("Recommended shortlist for CV", 40, GREEN, "§8"),
    ]
    fig, ax = plt.subplots(figsize=(12, 5.8))
    logmax = math.log10(max(v for _, v, _, _ in stages))
    for i, (label, val, color, tag) in enumerate(stages):
        y = len(stages) - 1 - i
        w = math.log10(val) / logmax          # log width so small tiers stay readable
        ax.add_patch(FancyBboxPatch((0.0, y - 0.34), w, 0.68, boxstyle="round,pad=0.004",
                     fc=color, ec="white", lw=1.5))
        ax.text(0.012, y, f"{tag}", ha="left", va="center", color="white", fontsize=10.5, fontweight="bold")
        ax.text(w - 0.012, y, f"{val:,}", ha="right", va="center", fontsize=14,
                fontweight="bold", color="white")            # count INSIDE the bar (right-aligned)
        ax.text(1.04, y, label, ha="left", va="center", fontsize=11.5, color="#222")  # desc at fixed column
        if i > 0:
            pct = 100 * val / stages[i - 1][1]
            ax.text(0.0, y + 0.46, f"↓ {pct:.0f}% retained", ha="left", va="center",
                    fontsize=9.5, color="#666", style="italic")
    ax.set_xlim(0, 2.05); ax.set_ylim(-0.7, len(stages) - 0.15); ax.axis("off")
    ax.set_title("Screening cascade — progress through the 3-tier pipeline  (bar ∝ log count)", pad=12)
    fig.text(0.5, 0.015, "Frozen-then-scale: 7,488 validated (freeze); full 50k gated on PI sign-off. "
             "Tier-2 partial = 71 DFT redox done so far.", ha="center", fontsize=9, color="#666")
    save(fig, "01_progress_funnel.png")

# ---------------------------------------------------------------- 2. Tier-1 validation
def tier1_validation():
    df = pd.read_csv(ROOT / "outputs" / "validate_ipea_relaxed.csv")
    ok = df[df["monomer_eox_calc_status"] == "ok"].copy()
    incal = ok[ok["in_calibration_set"] == True]  # noqa: E712
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4))
    # parity: calibrated vs experiment
    ax = axes[0]
    ax.scatter(ok["exp_Eox_V_vs_AgAgCl"], ok["calibrated_Eox_V_vs_AgAgCl"],
               s=28, c=GREY, alpha=0.5, label=f"all benchmark (n={len(ok)})")
    ax.scatter(incal["exp_Eox_V_vs_AgAgCl"], incal["calibrated_Eox_V_vs_AgAgCl"],
               s=70, c=NAVY, edgecolor="white", label=f"calibration set (n={len(incal)})", zorder=3)
    lo = float(min(ok["exp_Eox_V_vs_AgAgCl"].min(), ok["calibrated_Eox_V_vs_AgAgCl"].min())) - 0.1
    hi = float(max(ok["exp_Eox_V_vs_AgAgCl"].max(), ok["calibrated_Eox_V_vs_AgAgCl"].max())) + 0.1
    ax.plot([lo, hi], [lo, hi], "--", c=RED, lw=1.5, label="y = x")
    for d in (0.3, -0.3):
        ax.plot([lo, hi], [lo + d, hi + d], ":", c=AMBER, lw=1, alpha=0.8)
    ax.set_xlabel("Experimental $E_{ox}$ (V vs Ag/AgCl)")
    ax.set_ylabel("Calibrated xTB $E_{ox}$ (V)")
    ax.set_title("Calibrated xTB vs experiment")
    ax.legend(fontsize=10, loc="upper left"); ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.text(0.97, 0.05, "dotted = ±0.3 V directive band", transform=ax.transAxes,
            ha="right", fontsize=9, color=AMBER)
    # MAE bars vs target
    ax = axes[1]
    cmp = pd.read_csv(ROOT / "outputs" / "validate_ipea_profile_comparison.csv")
    s = cmp[cmp["profile_name"] == "agagcl_peak_relaxed"].iloc[0]
    vals = {"MAE before\ncalibration": float((ok["residual_before_V"].abs().mean())),
            "MAE after\ncalibration": float(s["mae_after_V"]),
            "LOO-CV MAE\n(headline)": float(s["loo_mae_after_V"])}
    colors = [GREY, TEAL, NAVY]
    bars = ax.bar(list(vals), list(vals.values()), color=colors, width=0.6)
    ax.axhline(0.30, ls="--", c=RED, lw=1.8, label="directive Tier-1 target < 0.30 V")
    ax.axhspan(0.20, 0.35, color=AMBER, alpha=0.12, label="honest accuracy floor 0.20–0.35 V")
    for b, v in zip(bars, vals.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005, f"{v:.3f}", ha="center", fontweight="bold")
    ax.set_ylabel("MAE (V)"); ax.set_ylim(0, 0.42)
    ax.set_title(f"Tier-1 calibrated $E_{{ox}}$ accuracy (relaxed peak, n={int(s['n_points'])}, R²={s['r2']:.2f})")
    ax.legend(fontsize=9, loc="upper right")
    fig.suptitle("Tier-1 — calibration validated against experiment (directive §7)",
                 fontsize=15, fontweight="bold", y=1.02)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    save(fig, "02_tier1_validation.png")

# ---------------------------------------------------------------- 3. Tier-2 output (partial)
def tier2_output():
    h = pd.read_csv(ROOT / "outputs" / "tier2_full_redox_harvest_partial.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    # left: DFT success breakdown
    ax = axes[0]
    counts = h.groupby(["entity_type", "quantity"]).size().unstack(fill_value=0)
    counts.plot(kind="bar", stacked=True, ax=ax, color=[NAVY, TEAL], width=0.6)
    ax.set_title(f"Tier-2 DFT redox done so far (n={len(h)})")
    ax.set_xlabel(""); ax.set_ylabel("count"); ax.tick_params(axis="x", rotation=20)
    ax.legend(title="quantity", fontsize=10)
    for c in ax.containers:
        ax.bar_label(c, label_type="center", fontsize=9, color="white", fmt=lambda v: int(v) if v else "")
    # right: DFT monomer Eox distribution
    ax = axes[1]
    mono = h[(h["entity_type"] == "monomer") & (h["quantity"] == "adiabatic_ip")]
    eox = pd.to_numeric(mono["dft_monomer_Eox_V_vs_AgAgCl"], errors="coerce").dropna()
    ax.hist(eox, bins=12, color=AMBER, edgecolor="white")
    ax.axvline(eox.median(), c=RED, ls="--", lw=1.6, label=f"median {eox.median():.2f} V")
    ax.set_xlabel("DFT monomer $E_{ox}$ (V vs Ag/AgCl)"); ax.set_ylabel("count")
    ax.set_title(f"B3LYP/SMD/ΔG monomer $E_{{ox}}$ (n={len(eox)})"); ax.legend(fontsize=10)
    fig.suptitle("Tier-2 — partial DFT refinement (B3LYP/6-31G(d,p)/SMD/Freq, §4.2)",
                 fontsize=15, fontweight="bold")
    save(fig, "03_tier2_output_partial.png")

# ---------------------------------------------------------------- 4. §7 scorecard
def section7_scorecard():
    rows = [
        ("Calibration anchor", "xTB → DFT", "xTB→DFT preferred (computing)", "in_progress"),
        ("Tier-1 calibrated $E_{ox}$ vs exp", "MAE < 0.30 V", "LOO-CV 0.198 V (n=29)", "pass"),
        ("Tier-2 DFT $E_{ox}$ vs exp", "MAE < 0.15 V", "graded; DFT computing", "in_progress"),
        ("Solvent ESW vs exp", "MAE < 0.30 V", "benchmark rows pending", "pending"),
        ("Feasibility yes/no", "> 85% bal. acc.", "wired; coverage-gated", "partial"),
    ]
    cmap = {"pass": GREEN, "in_progress": AMBER, "partial": "#b07d2b", "pending": GREY}
    sym = {"pass": "PASS", "in_progress": "IN PROGRESS", "partial": "PARTIAL", "pending": "NOT YET"}
    fig, ax = plt.subplots(figsize=(12, 5.4)); ax.axis("off")
    ax.set_title("Directive §7 — validation scorecard (code complete; numbers landing)", pad=18)
    headers = ["Metric", "Directive target", "Current status", ""]
    xcol = [0.02, 0.32, 0.52, 0.99]
    yhead = 0.92
    for x, hd in zip(xcol, headers):
        ax.text(x, yhead, hd, fontsize=12, fontweight="bold", color=NAVY,
                ha="right" if hd == "" else "left")
    ax.plot([0, 1], [yhead - 0.03, yhead - 0.03], color=NAVY, lw=1.2)
    for i, (m, t, st, k) in enumerate(rows):
        y = yhead - 0.12 - i * 0.15
        ax.text(xcol[0], y, m, fontsize=11.5, va="center")
        ax.text(xcol[1], y, t, fontsize=11, va="center", color="#333")
        ax.text(xcol[2], y, st, fontsize=10.5, va="center", color="#333")
        ax.add_patch(FancyBboxPatch((0.86, y - 0.045), 0.135, 0.09, boxstyle="round,pad=0.004",
                     fc=cmap[k], ec="none"))
        ax.text(0.9275, y, sym[k], fontsize=9.5, fontweight="bold", color="white", ha="center", va="center")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.text(0.5, 0.02, "Both experiment legs now graded in code (DFT-vs-exp no longer OUT_OF_SCOPE); "
             "production prefers xTB→DFT once the benchmark DFT (37-monomer ORCA run) lands.",
             ha="center", fontsize=9, color="#666")
    save(fig, "04_section7_scorecard.png")

# ---------------------------------------------------------------- 5. directive compliance map
def compliance_map():
    items = [
        ("§2 Library (mon/solv/elec)", "done"),
        ("§3 Properties (IP/EA, spin, ΔG_dim, ΔGsolv, gap)", "done"),
        ("§4.1 Tier-1 xTB (GFN2+IPEA+sTDA+COSMO-RS)", "done"),
        ("§4.2 Tier-2 DFT (B3LYP/SMD/Freq, redox/dimer/gap)", "running"),
        ("§4.3 Tier-3 high-accuracy (CAM-B3LYP, AIMD)", "pending"),
        ("§5 Composite score (5-term weighted)", "done"),
        ("§7 Validation (xTB→DFT + dual exp MAE)", "running"),
        ("§8 Outputs (ranked DB, Pareto, t-SNE, shortlist)", "done"),
    ]
    cmap = {"done": GREEN, "running": AMBER, "pending": GREY}
    lab = {"done": "implemented", "running": "in progress", "pending": "planned"}
    fig, ax = plt.subplots(figsize=(11, 5.6)); ax.axis("off")
    ax.set_title("Directive compliance map — section-by-section", pad=16)
    for i, (name, k) in enumerate(items):
        y = len(items) - 1 - i
        ax.add_patch(FancyBboxPatch((0.0, y - 0.32), 0.07, 0.64, boxstyle="round,pad=0.003",
                     fc=cmap[k], ec="none"))
        ax.text(0.1, y, name, fontsize=12, va="center")
        ax.text(0.99, y, lab[k], fontsize=10.5, va="center", ha="right",
                color=cmap[k], fontweight="bold")
    ax.set_xlim(0, 1); ax.set_ylim(-0.6, len(items) - 0.3)
    fig.text(0.5, 0.02, "Green = implemented & tested · amber = compute in progress · grey = planned (Tier-3 optional).",
             ha="center", fontsize=9.5, color="#666")
    save(fig, "05_directive_compliance.png")

# ---------------------------------------------------------------- 6. relaxed calibration parity (standalone, overwrite strict)
def calibration_parity():
    df = pd.read_csv(ROOT / "outputs" / "validate_ipea_relaxed.csv")
    ok = df[df["monomer_eox_calc_status"] == "ok"].copy()
    incal = ok[ok["in_calibration_set"] == True]  # noqa: E712
    cmp = pd.read_csv(ROOT / "outputs" / "validate_ipea_profile_comparison.csv")
    s = cmp[cmp["profile_name"] == "agagcl_peak_relaxed"].iloc[0]
    fig, ax = plt.subplots(figsize=(7.2, 6.6))
    ax.scatter(ok["exp_Eox_V_vs_AgAgCl"], ok["calibrated_Eox_V_vs_AgAgCl"], s=26,
               facecolors="none", edgecolors=NAVY, alpha=0.5, label=f"applied to all (n={len(ok)})")
    ax.scatter(incal["exp_Eox_V_vs_AgAgCl"], incal["calibrated_Eox_V_vs_AgAgCl"], s=85, c=RED,
               edgecolor="black", zorder=3, label=f"relaxed peak fit (n={int(s['n_points'])})")
    lo, hi = 0.6, 2.7
    ax.plot([lo, hi], [lo, hi], "--", c="gray", label="y = x")
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_xlabel("Experimental $E_{ox}$ (V vs Ag/AgCl)")
    ax.set_ylabel("Calibrated IPEA-xTB $E_{ox}$ (V vs Ag/AgCl)")
    ax.set_title("Tier-1 monomer $E_{ox}$ calibration — IPEA-xTB → Ag/AgCl\n(relaxed tier-A+B peak anchor, PRODUCTION)")
    ax.text(0.03, 0.97, f"relaxed fit (n={int(s['n_points'])}):\nslope {s['slope']:.3f}, intercept {s['intercept']:.3f}\n"
            f"R² {s['r2']:.2f}   Spearman ρ {s['spearman_rho']:.2f}\nin-sample MAE {s['mae_after_V']:.2f} V\n"
            f"LOO-CV MAE {s['loo_mae_after_V']:.2f} V\nhonest floor 0.20–0.35 V",
            transform=ax.transAxes, va="top", fontsize=10,
            bbox=dict(boxstyle="round", fc="white", ec="gray"))
    ax.legend(loc="lower right", fontsize=10)
    p = ROOT / "outputs" / "presentation" / "ipea_calibration_parity.png"
    fig.savefig(p); plt.close(fig); print("wrote", p)

# ---------------------------------------------------------------- 7. relaxed clean Pareto (standalone, overwrite strict)
def pareto_clean():
    d = pd.read_csv(ROOT / "outputs" / "tier1_relaxed" / "survivors.csv", low_memory=False)
    x = pd.to_numeric(d["window_margin_V"], errors="coerce")
    y = -pd.to_numeric(d["solvation_dG_kcal_mol"], errors="coerce")  # more positive = more soluble
    m = x.notna() & y.notna()
    x, y = x[m].to_numpy(), y[m].to_numpy()
    # Pareto front: maximize both
    order = np.argsort(-x)
    pareto, best = [], -np.inf
    for i in order:
        if y[i] >= best:
            pareto.append(i); best = y[i]
    pareto = np.array(pareto)
    fig, ax = plt.subplots(figsize=(9, 6.2))
    ax.scatter(x, y, s=10, c=GREY, alpha=0.45, label=f"survivors (n={len(x)})")
    ax.scatter(x[pareto], y[pareto], s=70, c=RED, edgecolor="black", zorder=3,
               label=f"Pareto-optimal (n={len(pareto)})")
    ax.set_xlabel("Window margin  $E_{ox}$(solvent) − $E_{ox}$(monomer)  (V)")
    ax.set_ylabel("Solubility score  (−ΔG$_{solv}$, kcal/mol)")
    ax.set_title("Tier-1 Pareto front — electrochemical window vs solubility\n"
                 f"CombHTS: {len(x):,} survivors of 7,488 (IPEA-xTB relaxed + openCOSMO-RS)")
    ax.legend(loc="lower right", fontsize=10)
    ax.text(0.02, 0.97, "Pareto front is 5-D (window/anion/solubility/dimer/gap), projected to 2 axes.",
            transform=ax.transAxes, va="top", fontsize=8.5, color="#666")
    p = ROOT / "outputs" / "presentation" / "real" / "pareto_clean.png"
    fig.savefig(p); plt.close(fig); print("wrote", p)

funnel(); tier1_validation(); tier2_output(); section7_scorecard(); compliance_map()
calibration_parity(); pareto_clean()
print("\nDONE ->", OUT)

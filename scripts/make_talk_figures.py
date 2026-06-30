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
    ax.scatter(incal["exp_Eox_V_vs_AgAgCl"], incal["calibrated_Eox_V_vs_AgAgCl"],
               s=70, c=NAVY, edgecolor="white", label=f"experimental CV anchors (n={len(incal)})", zorder=3)
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
    # two validation legs vs experiment (the directive's two accuracy targets)
    ax = axes[1]
    cmp = pd.read_csv(ROOT / "outputs" / "validate_ipea_profile_comparison.csv")
    s = cmp[cmp["profile_name"] == "agagcl_peak_relaxed"].iloc[0]
    labels = ["xTB→exp\nLOO-CV (n=29)", "DFT→exp\nraw (n=10)", "DFT→exp\noffset-corrected"]
    vals = [float(s["loo_mae_after_V"]), 0.496, 0.151]
    colors = [NAVY, GREY, TEAL]
    bars = ax.bar(labels, vals, color=colors, width=0.62)
    ax.axhline(0.30, ls="--", c=AMBER, lw=1.6, label="Tier-1 xTB target < 0.30 V")
    ax.axhline(0.15, ls="--", c=RED, lw=1.6, label="Tier-2 DFT target < 0.15 V")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.008, f"{v:.3f}", ha="center", fontweight="bold")
    ax.set_ylabel("MAE vs experiment (V)"); ax.set_ylim(0, 0.56)
    ax.set_title("Validation against experiment (peak)")
    ax.legend(fontsize=8.5, loc="upper center")
    fig.suptitle("Tier-1/2 — two validation legs against experiment (directive §7)",
                 fontsize=15, fontweight="bold", y=1.02)
    fig.text(0.5, -0.02, "DFT carries a ~0.5 V systematic reference offset (raw); a linear DFT→exp fit removes it "
             "→ 0.15 V residual. xTB→exp (direct) already meets the Tier-1 target.", ha="center", fontsize=8.5, color="#666")
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
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
        ("Calibration anchor (xTB→DFT)", "xTB → DFT", "fitted: R² 0.88, n=15 (partial)", "in_progress"),
        ("Validation: xTB→exp", "MAE < 0.30 V", "LOO-CV 0.198 V (n=29)", "pass"),
        ("Validation: DFT→exp", "MAE < 0.15 V", "raw 0.50; offset-corrected 0.15 (n=10)", "in_progress"),
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
def xtb_to_dft_calibration():
    """Directive §7 CALIBRATION figure: xTB descriptor -> DFT Eox (the calibration of record)."""
    p = pd.read_csv(ROOT / "outputs" / "dftcal_orca_points.csv")
    ok = p[p["dft_calc_status"] == "ok"].copy()
    x = pd.to_numeric(ok["xtb_descriptor"], errors="coerce")
    y = pd.to_numeric(ok["dft_Eox_V_vs_AgAgCl"], errors="coerce")
    m = x.notna() & y.notna(); x, y = x[m].to_numpy(), y[m].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    r2 = 1 - float(np.sum((y - yhat) ** 2)) / float(np.sum((y - y.mean()) ** 2))
    mae = float(np.mean(np.abs(y - yhat)))
    fig, ax = plt.subplots(figsize=(7.4, 6.6))
    ax.scatter(x, y, s=80, c=TEAL, edgecolor="black", zorder=3, label=f"benchmark monomers (n={len(x)})")
    xs = np.array([x.min() - 0.1, x.max() + 0.1])
    ax.plot(xs, slope * xs + intercept, "-", c=NAVY, lw=2, label="xTB→DFT fit")
    ax.set_xlabel("IPEA-xTB descriptor $E_{ox}$ (V vs Ag/AgCl)")
    ax.set_ylabel("DFT $E_{ox}$  (B3LYP/6-31G(d,p)/SMD, V vs Ag/AgCl)")
    ax.set_title("Tier-1 CALIBRATION — IPEA-xTB → DFT  (directive §7, step 1)")
    ax.text(0.03, 0.97, f"xTB→DFT (n={len(x)}, partial):\nslope {slope:.3f}, intercept {intercept:.3f}\n"
            f"R² {r2:.2f}   MAE {mae:.2f} V",
            transform=ax.transAxes, va="top", fontsize=11,
            bbox=dict(boxstyle="round", fc="white", ec="gray"))
    ax.legend(loc="lower right", fontsize=10)
    out = ROOT / "outputs" / "presentation" / "xtb_to_dft_calibration.png"
    fig.savefig(out); plt.close(fig); print("wrote", out)

# ---------------------------------------------------------------- 7. relaxed clean Pareto (standalone, overwrite strict)
def pareto_clean():
    d = pd.read_csv(ROOT / "outputs" / "tier1_relaxed" / "survivors.csv", low_memory=False)
    mcol = "monomer_name" if "monomer_name" in d.columns else "monomer_canonical_smiles"
    # Collapse the cation-permutation degeneracy: window & solubility are (monomer, solvent)
    # properties, so one point per distinct (monomer, solvent) — no piled-up duplicate red dots.
    d = d.drop_duplicates(subset=[mcol, "solvent_name"]).copy()
    d["_x"] = pd.to_numeric(d["window_margin_V"], errors="coerce")
    d["_y"] = -pd.to_numeric(d["solvation_dG_kcal_mol"], errors="coerce")  # more positive = more soluble
    d = d[d["_x"].notna() & d["_y"].notna()]
    x = d["_x"].to_numpy(); y = d["_y"].to_numpy()
    order = np.argsort(-x)
    pareto, best = [], -np.inf
    for i in order:
        if y[i] >= best:
            pareto.append(i); best = y[i]
    pareto = np.array(pareto)
    pf = d.iloc[pareto].sort_values("_x")

    fig, ax = plt.subplots(figsize=(9.2, 6.3))
    ax.scatter(x, y, s=14, c=GREY, alpha=0.5, label=f"distinct monomer×solvent (n={len(x)})")
    # stepped frontier line so it reads as a trade-off front, not scattered outliers
    ax.step(pf["_x"], pf["_y"], where="post", c=RED, lw=1.6, alpha=0.7, zorder=2)
    ax.scatter(pf["_x"], pf["_y"], s=80, c=RED, edgecolor="black", zorder=3,
               label=f"Pareto-optimal (n={len(pf)})")
    # annotate the (few) distinct monomers that own the frontier
    seen = set()
    for _, r in pf.iterrows():
        name = str(r[mcol])
        if name not in seen:
            seen.add(name)
            ax.annotate(name, (r["_x"], r["_y"]), xytext=(8, 6), textcoords="offset points",
                        fontsize=10, fontweight="bold", color=NAVY)
    ax.set_xlabel("Window margin  $E_{ox}$(solvent) − $E_{ox}$(monomer)  (V)")
    ax.set_ylabel("Solvation-affinity score  (−ΔG$_{solv}$, kcal/mol)")
    ax.set_title("Tier-1 trade-off front — electrochemical window vs solvation affinity\n"
                 f"CombHTS: {len(x):,} distinct monomer×solvent of 3,275 survivors")
    ax.legend(loc="lower left", fontsize=10)
    ax.set_ylim(top=float(y.max()) + 1.4)
    fig.subplots_adjust(bottom=0.20)
    fig.text(0.5, 0.045,
             "2-D projection of the 5-D screen (window/anion/solubility/dimer/gap); the durable ranking is the §5 composite.",
             ha="center", fontsize=8.4, color="#666")
    fig.text(0.5, 0.015,
             "Solvation-affinity (−ΔG$_{solv}$) is size-confounded → the largest/most-alkylated monomers own the high-affinity edge; read as diagnostic.",
             ha="center", fontsize=8.4, color="#666")
    p = ROOT / "outputs" / "presentation" / "real" / "pareto_clean.png"
    fig.savefig(p); plt.close(fig); print("wrote", p)

funnel(); tier1_validation(); tier2_output(); section7_scorecard(); compliance_map()
xtb_to_dft_calibration(); pareto_clean()
print("\nDONE ->", OUT)

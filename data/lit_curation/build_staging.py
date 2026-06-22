#!/usr/bin/env python3
"""Build the four STAGING literature-curation CSVs from the deep-research JSON.

Provenance / auditability helper for ``data/lit_curation/``.  Reads the raw
source-verified research output (``_raw_curation.json``) and emits the four
staging tables.  Every reference-electrode -> Ag/AgCl conversion uses ONLY the
project-pinned additive shifts and is recorded in a ``conversion`` column so each
converted value is reproducible from (orig value, reference, shift):

    E(vs Ag/AgCl) = E(vs ref) + SHIFT

Pinned shifts (V), consistent with src/eps/properties/redox.py (AGAGCL_SHIFT_V =
-0.197 for SHE) and the spec values already used in data/solvent_windows.csv:
    SCE     -> Ag/AgCl  : +0.045
    Fc/Fc+  -> Ag/AgCl  : +0.445   (PINNED ONLY IN MeCN/acetonitrile)
    SHE/NHE -> Ag/AgCl  : -0.197
    Ag/AgCl -> Ag/AgCl  :  0.000
References without a pinned shift (Ag/Ag+, Li/Li+, decamethylferrocene, pseudo
wires, Fc outside MeCN) are NOT converted: the converted cell is left EMPTY and
the reason is recorded in ``flags`` / ``conversion``.  Nothing is hand-rolled.

These are STAGING values; needs_review=true on every row.  Run from repo root:
    python3 data/lit_curation/build_staging.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / "_raw_curation.json"
MONOMERS_CSV = ROOT / "data" / "monomers.csv"

SHIFT_SCE = 0.045
SHIFT_FC_MECN = 0.445
SHIFT_SHE = -0.197

MECN_NAMES = {"acetonitrile", "mecn", "acn", "ch3cn"}


def load_library_smiles() -> dict[str, str]:
    out: dict[str, str] = {}
    with MONOMERS_CSV.open() as fh:
        for row in csv.DictReader(fh):
            out[row["name"].strip()] = row["smiles"].strip()
    return out


def classify_ref(ref_raw: str, solvent: str | None):
    """Return (shift_or_None, resolved_label, conversion_text, flag_text)."""
    r = (ref_raw or "").strip().lower()
    sol = (solvent or "").strip().lower()
    # decamethylferrocene first (contains 'ferrocene' but is NOT Fc/Fc+)
    if "decamethyl" in r or r.startswith("dmfc"):
        return (None, "DMFc0/+",
                "no pinned DMFc->Ag/AgCl shift", "decamethylferrocene reference; no pinned shift -> converted omitted")
    if r.startswith("she") or "vs she" in r:
        return (SHIFT_SHE, "SHE", f"SHE->Ag/AgCl: orig + ({SHIFT_SHE})", "")
    if r.startswith("nhe"):
        return (SHIFT_SHE, "NHE", f"NHE->Ag/AgCl: orig + ({SHIFT_SHE})", "")
    if r.startswith("sce"):
        return (SHIFT_SCE, "SCE", f"SCE->Ag/AgCl: orig + ({SHIFT_SCE})", "")
    if r.startswith("ag/agcl"):
        if "wire" in r or "pseudo" in r:
            return (None, "Ag/AgCl pseudo-wire",
                    "pseudo-wire != true Ag/AgCl", "Ag/AgCl pseudo-wire is not a true Ag/AgCl ref; no pinned shift -> converted omitted")
        return (0.0, "Ag/AgCl", "already vs Ag/AgCl (shift 0)", "")
    if "ag/agno3" in r or "ag/ag+" in r or r.startswith("ag/ag"):
        return (None, "Ag/Ag+", "no pinned Ag/Ag+->Ag/AgCl shift",
                "Ag/Ag+ (Ag/AgNO3) reference; no pinned shift -> converted omitted")
    if r.startswith("li/li") or "li/li+" in r:
        return (None, "Li/Li+", "no pinned Li/Li+->Ag/AgCl shift",
                "Li/Li+ reference; no pinned shift -> converted omitted")
    if r.startswith("fc") or "ferrocen" in r:
        if sol in MECN_NAMES or sol.startswith("aceto"):
            return (SHIFT_FC_MECN, "Fc/Fc+", f"Fc/Fc+->Ag/AgCl (MeCN): orig + ({SHIFT_FC_MECN})", "")
        return (None, "Fc/Fc+",
                "Fc->Ag/AgCl +0.445 pinned ONLY in MeCN",
                f"Fc/Fc+ ref but solvent={solvent or 'unknown'} (not MeCN); +0.445 V shift not pinned here -> converted omitted")
    return (None, ref_raw[:30], "reference not resolvable",
            f"reference '{ref_raw[:40]}' not cleanly resolvable to a pinned shift -> converted omitted")


def conv(orig, shift):
    if orig is None or shift is None:
        return ""
    return round(float(orig) + shift, 3)


def fnum(x):
    return "" if x is None else x


def window_flag(an, cat):
    if an is None or cat is None:
        return ""
    try:
        w = float(an) - float(cat)
    except (TypeError, ValueError):
        return ""
    if float(an) < float(cat):
        return "OUTLIER: anodic < cathodic (possible swap)"
    if w > 7.0:
        return f"OUTLIER: implausibly wide window ({w:.2f} V > 7 V; likely formulation-limited)"
    if w < 1.0:
        return f"check: narrow window ({w:.2f} V)"
    return ""


def main() -> None:
    raw = json.loads(RAW.read_text())
    lib = load_library_smiles()

    # -------- Priority A: solvent ESW --------
    esw_cols = ["solvent", "anodic_limit_orig_V", "cathodic_limit_orig_V", "reference_electrode",
                "supporting_electrolyte", "working_electrode", "cutoff_criterion",
                "anodic_limit_vs_AgAgCl_V", "cathodic_limit_vs_AgAgCl_V", "conversion",
                "source_doi", "citation", "confidence", "flags", "needs_review"]
    esw_rows = []
    esw_gaps = []
    for e in raw["esw"]:
        sol = e["solvent"]
        if not e["candidates"]:
            esw_gaps.append(sol)
            continue
        vd = {v["index"]: v for v in e.get("verdicts", [])}
        for i, c in enumerate(e["candidates"]):
            v = vd.get(i, {})
            if v.get("keep") is False:
                continue
            shift, label, conv_txt, ref_flag = classify_ref(c["reference_electrode"], sol)
            an_c = conv(c["anodic_limit_orig_V"], shift)
            cat_c = conv(c["cathodic_limit_orig_V"], shift)
            flags = [f for f in (window_flag(c["anodic_limit_orig_V"], c["cathodic_limit_orig_V"]), ref_flag) if f]
            # targeted cross-check: the Gong/Ue nitromethane window is +2.9/-1.0 V vs SHE (nitro group
            # reduces easily -> narrow cathodic). A row with |cathodic| > anodic for nitromethane is the
            # anodic/cathodic columns swapped; flag rather than silently trust.
            if sol.lower().startswith("nitromethane") and c["anodic_limit_orig_V"] is not None \
                    and c["cathodic_limit_orig_V"] is not None \
                    and float(c["anodic_limit_orig_V"]) < abs(float(c["cathodic_limit_orig_V"])):
                flags.append("CROSS-CHECK: anodic/cathodic likely SWAPPED vs Ue/production "
                             "(nitromethane window is +2.9/-1.0 V vs SHE); verify primary 10.1149/1.2059270")
            esw_rows.append({
                "solvent": sol,
                "anodic_limit_orig_V": fnum(c["anodic_limit_orig_V"]),
                "cathodic_limit_orig_V": fnum(c["cathodic_limit_orig_V"]),
                "reference_electrode": c["reference_electrode"],
                "supporting_electrolyte": c["supporting_electrolyte"],
                "working_electrode": c["working_electrode"],
                "cutoff_criterion": c["cutoff_criterion"],
                "anodic_limit_vs_AgAgCl_V": an_c,
                "cathodic_limit_vs_AgAgCl_V": cat_c,
                "conversion": conv_txt,
                "source_doi": c["source_doi"],
                "citation": c["citation"],
                "confidence": v.get("confidence_final", c["confidence"]),
                "flags": "; ".join(flags),
                "needs_review": "true",
            })
    write_csv(HERE / "solvent_esw_staging.csv", esw_cols, esw_rows)

    # -------- Priority B: polymerization outcomes --------
    poly_cols = ["monomer", "smiles", "outcome", "conditions", "source_doi", "citation",
                 "confidence", "name_in_library", "needs_review"]
    poly_rows = []
    seen = set()
    for x in raw["polymerization"]:
        key = (x["monomer"].lower(), x["outcome"], x["source_doi"], x["citation"][:40])
        if key in seen:
            continue
        seen.add(key)
        in_lib = x["monomer"].strip() in lib
        smiles = lib.get(x["monomer"].strip(), x["smiles"])
        poly_rows.append({
            "monomer": x["monomer"], "smiles": smiles, "outcome": x["outcome"],
            "conditions": x["conditions"], "source_doi": x["source_doi"], "citation": x["citation"],
            "confidence": x["confidence"], "name_in_library": str(in_lib).lower(), "needs_review": "true",
        })
    write_csv(HERE / "polymerization_outcomes_staging.csv", poly_cols, poly_rows)

    # -------- Priority C: solubility --------
    solu_cols = ["monomer", "solvent", "solubility_value", "units", "temperature_C", "value_type",
                 "source_doi", "citation", "needs_review"]
    solu_rows = []
    for x in raw["solubility"]:
        solu_rows.append({
            "monomer": x["monomer"], "solvent": x["solvent"],
            "solubility_value": fnum(x["solubility_value"]), "units": x["units"],
            "temperature_C": fnum(x["temperature_C"]), "value_type": x["value_type"],
            "source_doi": x["source_doi"], "citation": x["citation"], "needs_review": "true",
        })
    write_csv(HERE / "solubility_staging.csv", solu_cols, solu_rows)

    # -------- Priority D: optical gap + doping onset --------
    opt_cols = ["polymer", "monomer_smiles", "optical_gap_eV", "gap_method", "doping_onset_orig_V",
                "reference_electrode", "doping_onset_vs_AgAgCl_V", "conversion", "source_doi",
                "citation", "flags", "needs_review"]
    opt_rows = []
    for x in raw["optical"]:
        shift, label, conv_txt, ref_flag = classify_ref(x["reference_electrode"], None)
        dop_c = conv(x["doping_onset_orig_V"], shift)
        flags = [ref_flag] if ref_flag else []
        opt_rows.append({
            "polymer": x["polymer"], "monomer_smiles": x["monomer_smiles"],
            "optical_gap_eV": fnum(x["optical_gap_eV"]), "gap_method": x["gap_method"],
            "doping_onset_orig_V": fnum(x["doping_onset_orig_V"]),
            "reference_electrode": x["reference_electrode"],
            "doping_onset_vs_AgAgCl_V": dop_c, "conversion": conv_txt if x["doping_onset_orig_V"] is not None else "",
            "source_doi": x["source_doi"], "citation": x["citation"],
            "flags": "; ".join(flags), "needs_review": "true",
        })
    write_csv(HERE / "optical_doping_staging.csv", opt_cols, opt_rows)

    # -------- summary to stdout --------
    print("ESW staging rows:", len(esw_rows), "| ESW gaps (no source):", esw_gaps)
    print("Polymerization rows:", len(poly_rows),
          "| not-in-library names:", sorted({r["monomer"] for r in poly_rows if r["name_in_library"] == "false"}))
    print("Solubility rows:", len(solu_rows))
    print("Optical rows:", len(opt_rows),
          "| converted doping onsets:", sum(1 for r in opt_rows if r["doping_onset_vs_AgAgCl_V"] != ""))


def write_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


if __name__ == "__main__":
    main()

"""Build staging + quarantine + dedup review tables for the 2026-06-25 research ingest.

Review-only curation (Directive Section 7). This script parses four primary-literature
deliverables (markdown tables) into NEW staging CSVs under ``data/lit_curation/`` and
companion quarantine/review tables. It NEVER edits production data, configs, or scoring.

Source markdown deliverables (read-only inputs, not committed):
  research1 (ESW windows)      compass_artifact_wf-751e1391-...md
  research2 (Eox calibration)  compass_artifact_wf-5c3ddb24-...md
  research3 (feasibility)      compass_artifact_wf-30096375-...md
  research4 (optical anchors)  compass_artifact_wf-8cfddcf5-...md

Every numeric value is preserved verbatim on the Ag/AgCl (sat'd KCl) master-scale
convention already in the repo. Confidence flags, conversion notes, and track/observable
labels are carried through unchanged; missing fields stay blank (no invention, no re-derivation).

Quarantine policy (T2): a SMILES-bearing row is quarantined (NOT placed in the clean
staging file) when its SMILES fails RDKit parsing, OR the source flagged it hand-constructed
(EDOT-flanked trimer, An-EDOT-An), OR it is a '*'-attachment repeat-unit SMILES (all
research4 repeat units; the PCDTBT/PCPDTBT/F8BT D-A approximations), OR it contains the
selenophene aromatic '[se]' token (toolkit-sensitive; flagged for cheminformatics check).
"""

from __future__ import annotations

import csv
from pathlib import Path

from rdkit import Chem

STAMP = "20260625"
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DOWNLOADS = Path.home() / "Downloads"

SOURCES = {
    "research1_esw": DOWNLOADS / "compass_artifact_wf-751e1391-e232-448e-9dbf-f7272be4c6da_text_markdown.md",
    "research2_eox": DOWNLOADS / "compass_artifact_wf-5c3ddb24-f03a-49ca-ba4a-e57e43d0b97f_text_markdown.md",
    "research3_feasibility": DOWNLOADS / "compass_artifact_wf-30096375-8dab-4f31-9977-39dedadc2fe4_text_markdown.md",
    "research4_optical": DOWNLOADS / "compass_artifact_wf-8cfddcf5-0fc0-4eef-b4d3-c790a29af618_text_markdown.md",
}

PRODUCTION_LABELS = REPO_ROOT / "data" / "polymerizability_labels.csv"


# --------------------------------------------------------------------------- helpers


def canonical_smiles(smiles: str) -> tuple[str, str]:
    """Return (canonical_smiles, error). Empty canonical + message on parse failure."""
    text = (smiles or "").strip()
    if not text:
        return "", "empty SMILES"
    mol = Chem.MolFromSmiles(text, sanitize=True)
    if mol is None:
        return "", f"RDKit could not parse SMILES: {text}"
    return Chem.MolToSmiles(mol, canonical=True), ""


def parse_markdown_table(path: Path, header_signature: str) -> list[dict[str, str]]:
    """Parse the pipe-delimited markdown table whose header row contains ``header_signature``.

    Returns a list of row dicts keyed by the (raw) header cell text. Stops at the first
    line after the table that is not a pipe row.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] | None = None
    rows: list[dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        is_pipe_row = stripped.startswith("|") and stripped.endswith("|")
        if header is None:
            if is_pipe_row and header_signature in stripped:
                header = [c.strip() for c in stripped.strip("|").split("|")]
            continue
        # we are inside the table
        if not is_pipe_row:
            break
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        # skip the markdown separator row (---|---|...)
        if all(set(c) <= {"-", ":", " "} and c for c in cells):
            continue
        if len(cells) != len(header):
            # ragged row: pad/truncate defensively but keep going
            cells = (cells + [""] * len(header))[: len(header)]
        rows.append(dict(zip(header, cells)))
    if header is None:
        raise RuntimeError(f"table with signature {header_signature!r} not found in {path}")
    return rows


def clean_cell(value: str) -> str:
    """Strip markdown emphasis/backticks/footnote asterisks from a cell value."""
    text = (value or "").strip()
    text = text.replace("`", "")
    # drop a trailing markdown note like " *(constructed)*"
    if "*(" in text:
        text = text.split("*(")[0].strip()
    return text.strip().strip("*").strip()


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in columns})


def norm_blank(value: str) -> str:
    """Map source 'n/a' / 'not measured' style placeholders to a true blank."""
    text = (value or "").strip()
    if text.lower() in {"n/a", "na", "—", "-", "not measured", "not measured (anodic)", ""}:
        return ""
    return text


def numify(value: str) -> str:
    """Normalize a converted master-scale value to a bare ASCII float string.

    Only the sign characters and leading '+' are normalized (U+2212 / en / em dash -> '-');
    the magnitude is preserved verbatim. The original reported value (incl. scale annotation)
    is kept untouched in the companion ``*_orig_V`` column. Returns '' for blanks.
    """
    text = norm_blank(value)
    if not text:
        return ""
    for dash in ("−", "–", "—"):
        text = text.replace(dash, "-")
    text = text.replace("+", "").strip()
    return text


# --------------------------------------------------------------------------- research1 ESW


def build_esw() -> None:
    src = parse_markdown_table(
        SOURCES["research1_esw"], "anodic_limit_reported"
    )
    columns = [
        "solvent",
        "anodic_limit_orig_V",
        "cathodic_limit_orig_V",
        "reference_electrode",
        "supporting_electrolyte",
        "electrolyte_conc",
        "working_electrode",
        "cutoff_criterion",
        "anodic_limit_vs_AgAgCl_V",
        "cathodic_limit_vs_AgAgCl_V",
        "conversion",
        "water_purity_note",
        "source_doi",
        "citation",
        "confidence",
        "flags",
        "needs_review",
    ]
    rows = []
    for r in src:
        rows.append(
            {
                "solvent": clean_cell(r["solvent"]),
                "anodic_limit_orig_V": clean_cell(r["anodic_limit_reported"]),
                "cathodic_limit_orig_V": clean_cell(r["cathodic_limit_reported"]),
                "reference_electrode": clean_cell(r["reference_electrode"]),
                "supporting_electrolyte": clean_cell(r["supporting_electrolyte"]),
                "electrolyte_conc": clean_cell(r["electrolyte_conc"]),
                "working_electrode": clean_cell(r["working_electrode"]),
                "cutoff_criterion": clean_cell(r["current_cutoff_criterion"]),
                "anodic_limit_vs_AgAgCl_V": numify(clean_cell(r["anodic_vs_AgAgCl"])),
                "cathodic_limit_vs_AgAgCl_V": numify(clean_cell(r["cathodic_vs_AgAgCl"])),
                "conversion": clean_cell(r["conversion_note"]),
                "water_purity_note": clean_cell(r["water/purity_note"]),
                "source_doi": clean_cell(r["primary_source(DOI)"]),
                "citation": clean_cell(r["primary_source(DOI)"]),
                "confidence": clean_cell(r["confidence"]),
                "flags": "",
                "needs_review": "true",
            }
        )
    out = HERE / f"esw_windows_staging_{STAMP}.csv"
    write_csv(out, columns, rows)
    print(f"[research1 ESW] clean rows: {len(rows)} -> {out.name} (no SMILES; no quarantine)")


# --------------------------------------------------------------------------- research2 Eox


def track_from_observable(observable: str) -> str:
    text = observable.lower()
    if "formal" in text:
        return "reversible_formal_E"
    if "onset" in text:
        return "onset"
    if "peak" in text:
        return "peak"
    return "unspecified"


def build_eox() -> None:
    src = parse_markdown_table(SOURCES["research2_eox"], "value_reported")
    clean_columns = [
        "monomer",
        "smiles",
        "canonical_smiles",
        "track",
        "value_reported",
        "observable",
        "reference_electrode",
        "solvent",
        "electrolyte",
        "electrode",
        "scan_rate",
        "value_vs_AgAgCl_V",
        "conversion_note",
        "source_doi",
        "confidence",
        "needs_review",
    ]
    quar_columns = clean_columns + ["parse_status", "quarantine_reason"]
    clean: list[dict[str, str]] = []
    quar: list[dict[str, str]] = []
    for r in src:
        smiles = clean_cell(r["SMILES"])
        can, err = canonical_smiles(smiles)
        row = {
            "monomer": clean_cell(r["monomer"]),
            "smiles": smiles,
            "canonical_smiles": can,
            "track": track_from_observable(clean_cell(r["observable"])),
            "value_reported": clean_cell(r["value_reported"]),
            "observable": clean_cell(r["observable"]),
            "reference_electrode": clean_cell(r["reference_electrode"]),
            "solvent": clean_cell(r["solvent"]),
            "electrolyte": clean_cell(r["electrolyte"]),
            "electrode": clean_cell(r["electrode"]),
            "scan_rate": clean_cell(r["scan_rate"]),
            "value_vs_AgAgCl_V": norm_blank(clean_cell(r["value_vs_AgAgCl"])),
            "conversion_note": clean_cell(r["conversion_note"]),
            "source_doi": clean_cell(r["primary_source (DOI)"]),
            "confidence": clean_cell(r["confidence"]),
            "needs_review": "true",
        }
        reason = quarantine_reason(smiles, err, constructed=False)
        if reason:
            row["parse_status"] = "fail" if err else "parsed_but_flagged"
            row["quarantine_reason"] = reason
            quar.append(row)
        else:
            clean.append(row)
    out = HERE / f"eox_calibration_staging_{STAMP}.csv"
    qout = HERE / f"eox_calibration_quarantine_{STAMP}.csv"
    write_csv(out, clean_columns, clean)
    write_csv(qout, quar_columns, quar)
    tracks: dict[str, int] = {}
    for row in clean:
        tracks[row["track"]] = tracks.get(row["track"], 0) + 1
    print(
        f"[research2 Eox] clean rows: {len(clean)} -> {out.name}; "
        f"quarantine: {len(quar)} -> {qout.name}; tracks(clean): {tracks}"
    )


# --------------------------------------------------------------------------- quarantine rule


def quarantine_reason(smiles: str, parse_error: str, *, constructed: bool) -> str:
    """Return a non-empty quarantine reason if the row must be quarantined, else ''."""
    text = (smiles or "").strip()
    if not text:
        return "no_smiles_provided"
    if parse_error:
        return "rdkit_parse_failed"
    if constructed:
        return "hand_constructed_smiles"
    if "[se]" in text.lower():
        return "selenophene_se_token_toolkit_check"
    if "*" in text:
        return "star_attachment_repeat_unit"
    # descriptive non-SMILES (spaces / dashes / leading paren)
    if " " in text or "–" in text or text.startswith("("):
        return "no_parseable_smiles_descriptive"
    return ""


# --------------------------------------------------------------------------- research3 feasibility


def baseline_medium(solvent: str, electrolyte: str) -> str:
    s = solvent.lower()
    e = electrolyte.lower()
    if "bfee" in s or "bfee" in e:
        return "FALSE"
    if any(tok in s for tok in ("aqueous", "h2o", "water", "acid")):
        return "FALSE"
    if "acid" in e:
        return "FALSE"
    if any(tok in s for tok in ("mecn", "acetonitrile", "dcm", "dichloromethane", "pc", "propylene carbonate")):
        return "TRUE"
    return "FALSE"


def build_feasibility() -> list[dict[str, str]]:
    src = parse_markdown_table(SOURCES["research3_feasibility"], "evidence_summary")
    clean_columns = [
        "monomer",
        "smiles",
        "canonical_smiles",
        "outcome",
        "NO_type",
        "baseline_medium",
        "solvent",
        "electrolyte",
        "electrode",
        "method",
        "evidence_summary",
        "source_doi",
        "confidence",
        "needs_review",
    ]
    quar_columns = clean_columns + ["parse_status", "quarantine_reason"]
    clean: list[dict[str, str]] = []
    quar: list[dict[str, str]] = []
    all_rows: list[dict[str, str]] = []
    for r in src:
        raw_smiles_cell = r["SMILES"]
        constructed = "construct" in raw_smiles_cell.lower()
        smiles = clean_cell(raw_smiles_cell)
        can, err = canonical_smiles(smiles)
        solvent = clean_cell(r["solvent"])
        electrolyte = clean_cell(r["electrolyte"])
        row = {
            "monomer": clean_cell(r["monomer"]),
            "smiles": smiles,
            "canonical_smiles": can,
            "outcome": clean_cell(r["outcome"]).upper(),
            "NO_type": clean_cell(r["NO_type"]),
            "baseline_medium": baseline_medium(solvent, electrolyte),
            "solvent": solvent,
            "electrolyte": electrolyte,
            "electrode": clean_cell(r["electrode"]),
            "method": clean_cell(r["method"]),
            "evidence_summary": clean_cell(r["evidence_summary"]),
            "source_doi": clean_cell(r["primary_source (DOI)"]),
            "confidence": clean_cell(r["confidence"]),
            "needs_review": "true",
        }
        all_rows.append(row)
        reason = quarantine_reason(smiles, err, constructed=constructed)
        if reason:
            row_q = dict(row)
            row_q["parse_status"] = "fail" if err else "parsed_but_flagged"
            row_q["quarantine_reason"] = reason
            quar.append(row_q)
        else:
            clean.append(row)
    out = HERE / f"feasibility_labels_staging_{STAMP}.csv"
    qout = HERE / f"feasibility_quarantine_{STAMP}.csv"
    write_csv(out, clean_columns, clean)
    write_csv(qout, quar_columns, quar)
    yes = sum(1 for r in all_rows if r["outcome"] == "YES")
    no = sum(1 for r in all_rows if r["outcome"] == "NO")
    print(
        f"[research3 feasibility] total: {len(all_rows)} (YES={yes}, NO={no}); "
        f"clean: {len(clean)} -> {out.name}; quarantine: {len(quar)} -> {qout.name}"
    )
    return all_rows


# --------------------------------------------------------------------------- research4 optical


def derivation_kind(derivation: str) -> str:
    text = derivation.lower()
    if "onset" in text and "max" in text:
        return "mixed"
    if "onset" in text:
        return "onset"
    if "max" in text or "λmax" in text or "lambda_max" in text:
        return "lambda_max"
    if "calc" in text or "computed" in text or "band structure" in text:
        return "calculated"
    if "tauc" in text:
        return "onset_tauc"
    return "other"


def build_optical() -> None:
    src = parse_markdown_table(SOURCES["research4_optical"], "repeat_unit_SMILES")
    clean_columns = [
        "polymer",
        "repeat_unit_smiles",
        "canonical_smiles",
        "optical_gap_eV",
        "derivation",
        "film_state_neutral_confirmed",
        "chemical_class",
        "source_doi",
        "confidence",
        "needs_review",
    ]
    quar_columns = clean_columns + ["parse_status", "quarantine_reason"]
    clean: list[dict[str, str]] = []
    quar: list[dict[str, str]] = []
    for r in src:
        smiles = clean_cell(r["repeat_unit_SMILES"])
        can, err = canonical_smiles(smiles)
        film_state = clean_cell(r["film_state"])
        row = {
            "polymer": clean_cell(r["polymer"]),
            "repeat_unit_smiles": smiles,
            "canonical_smiles": can,
            "optical_gap_eV": clean_cell(r["optical_gap_eV"]),
            "derivation": derivation_kind(clean_cell(r["derivation"])),
            "film_state_neutral_confirmed": "TRUE" if "neutral" in film_state.lower() else "FALSE",
            "chemical_class": clean_cell(r["class"]),
            "source_doi": clean_cell(r["source (DOI)"]),
            "confidence": clean_cell(r["conf."]),
            "needs_review": "true",
        }
        reason = quarantine_reason(smiles, err, constructed=False)
        if reason:
            row_q = dict(row)
            row_q["parse_status"] = "fail" if err else "parsed_but_flagged"
            row_q["quarantine_reason"] = reason
            quar.append(row_q)
        else:
            clean.append(row)
    out = HERE / f"optical_anchors_staging_{STAMP}.csv"
    qout = HERE / f"optical_anchors_quarantine_{STAMP}.csv"
    write_csv(out, clean_columns, clean)
    write_csv(qout, quar_columns, quar)
    print(
        f"[research4 optical] clean rows: {len(clean)} -> {out.name}; "
        f"quarantine: {len(quar)} -> {qout.name}"
    )


# --------------------------------------------------------------------------- T3 dedup


def solvent_norm(value: str) -> str:
    s = value.lower()
    if "bfee" in s:
        return "bfee"
    if "propylene carbonate" in s or s.strip() == "pc" or " pc" in s:
        return "pc"
    if "dichloromethane" in s or "dcm" in s:
        return "dcm"
    if "dmf" in s:
        return "dmf"
    if any(tok in s for tok in ("aqueous", "h2o", "water")):
        return "h2o"
    if "acetonitrile" in s or "mecn" in s:
        return "mecn"
    return s.strip()


def build_dedup(feasibility_rows: list[dict[str, str]]) -> None:
    # Load production labels (READ ONLY).
    prod: list[dict[str, str]] = []
    with PRODUCTION_LABELS.open(newline="", encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            can, _ = canonical_smiles(r.get("monomer_smiles", ""))
            prod.append(
                {
                    "name": (r.get("monomer_name", "") or "").strip().lower(),
                    "canonical": can,
                    "solvent_norm": solvent_norm(r.get("solvent", "")),
                    "outcome": (r.get("outcome", "") or "").strip().upper(),
                    "solvent": (r.get("solvent", "") or "").strip(),
                    "electrolyte": (r.get("electrolyte", "") or "").strip(),
                }
            )
    prod_names = {p["name"] for p in prod if p["name"]}

    columns = [
        "monomer",
        "canonical_smiles",
        "solvent",
        "solvent_norm",
        "electrolyte",
        "outcome",
        "match_status",
        "production_match_detail",
        "note",
    ]
    out_rows: list[dict[str, str]] = []
    counts = {"NEW": 0, "DUPLICATE": 0, "CONFLICT": 0}
    for row in feasibility_rows:
        can = row["canonical_smiles"]
        snorm = solvent_norm(row["solvent"])
        outcome = row["outcome"]
        note_parts: list[str] = []
        if not can:
            status = "NEW"
            detail = "no canonical SMILES (unparseable/empty) -> cannot match production"
        else:
            same_smiles = [p for p in prod if p["canonical"] == can]
            same_cond = [p for p in same_smiles if p["solvent_norm"] == snorm]
            if not same_smiles:
                status = "NEW"
                detail = "monomer SMILES not present in production labels"
                if row["monomer"].strip().lower() in prod_names:
                    note_parts.append(
                        "trivial name matches a production row but canonical SMILES differs -> structure check"
                    )
            elif not same_cond:
                status = "NEW"
                prod_solvs = sorted({p["solvent_norm"] for p in same_smiles})
                detail = f"same monomer in production but only under medium(s) {prod_solvs}; this medium ({snorm}) is new"
            else:
                outcomes = {p["outcome"] for p in same_cond}
                if outcome in outcomes:
                    status = "DUPLICATE"
                    detail = f"production has same monomer+medium+outcome ({outcome}); electrolyte/electrode may differ"
                else:
                    status = "CONFLICT"
                    detail = f"production outcome(s) {sorted(outcomes)} vs staged {outcome} at medium {snorm}"
        counts[status] += 1
        out_rows.append(
            {
                "monomer": row["monomer"],
                "canonical_smiles": can,
                "solvent": row["solvent"],
                "solvent_norm": snorm,
                "electrolyte": row["electrolyte"],
                "outcome": outcome,
                "match_status": status,
                "production_match_detail": detail,
                "note": "; ".join(note_parts),
            }
        )
    out = HERE / f"feasibility_dedup_review_{STAMP}.csv"
    write_csv(out, columns, out_rows)
    print(
        f"[T3 dedup] rows compared: {len(out_rows)} -> {out.name}; "
        f"NEW={counts['NEW']} DUPLICATE={counts['DUPLICATE']} CONFLICT={counts['CONFLICT']}"
    )


# --------------------------------------------------------------------------- main


def main() -> None:
    for key, path in SOURCES.items():
        if not path.exists():
            raise FileNotFoundError(f"source for {key} not found: {path}")
    build_esw()
    build_eox()
    feasibility_rows = build_feasibility()
    build_optical()
    build_dedup(feasibility_rows)


if __name__ == "__main__":
    main()

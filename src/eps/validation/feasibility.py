"""Directive §7 qualitative yes/no electropolymerization-feasibility metric (DIAGNOSTIC).

This compares the Tier-1 screen's binary prediction (survivor = predicted-YES; filtered-out =
predicted-NO) against the vetted binary experimental labels in ``data/polymerizability_labels.csv``
(curated from ``docs/research/electropolymerization_feasibility_binary_labels.md``).

HONESTY CONTRACT — the screen's own research doc is explicit that the >85% target is NOT yet
defensible (only 9 negatives, ~67% class balance so a trivial always-YES classifier already scores
~67%). So this path:
  - NEVER returns a single raw-accuracy figure and NEVER emits a >85% PASS;
  - reports BALANCED accuracy (mean of per-class recall) + the full 2x2 confusion matrix, on the
    MATCHED IN-SCOPE subset only;
  - reports coverage (how many of the labels matched a screen triad) and the out-of-scope count
    (BFEE / aqueous-acid / Ag-pseudo-reference media the screen does not model);
  - with no harvest -> "no harvest to score against"; with zero matches ->
    "0 matched — metric not computable on current library". It never fabricates a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from rdkit import Chem

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LABELS_PATH = PROJECT_ROOT / "data" / "polymerizability_labels.csv"

LABEL_COLUMNS = (
    "monomer_name",
    "monomer_smiles",
    "solvent",
    "electrolyte",
    "electrode",
    "outcome",
    "negative_type",
    "experimental_basis",
    "reference_electrode",
    "source_doi",
    "source_locator",
    "reliability_tier",
    "medium_class",
    "flags",
)

# The §7 qualitative-feasibility STATUS line (verbatim caveat; PRELIMINARY, never a >85% claim).
FEASIBILITY_STATUS_NOTE = (
    "§7 qualitative yes/no feasibility: PRELIMINARY. Labeled set = 18 YES / 9 NO (research3). "
    "The >85% target is NOT claimed: only 9 negatives (< the ~20-25 needed in the baseline "
    "MeCN/TBAPF6-on-Pt regime), and a trivial always-YES baseline already scores ~67%. Reporting "
    "balanced accuracy + confusion matrix on the matched in-scope subset only."
)

# Harvest triad-identity / survivor columns (see eps.workflow.tier1).
HARVEST_SMILES_COLUMN = "monomer_canonical_smiles"
HARVEST_SOLVENT_COLUMN = "solvent_name"
HARVEST_SALT_COLUMN = "salt"
HARVEST_SURVIVOR_COLUMN = "passes_all_tier1_filters"

# Map the label CSV's solvent text to a library solvent name (data/solvents.csv). Mixed or
# non-library media map to None and cannot be matched.
SOLVENT_ALIASES: dict[str, str | None] = {
    "MeCN": "acetonitrile",
    "DMF": "DMF",
    "DCM": "DCM",
    "H2O": "water",
    "H2O (+MeOH)": "water",
    "H2O (aqueous)": "water",
    "H2O, neutral pH": "water",
    "MeCN/THF": None,
    "MeCN/DCM": None,
    "aqueous acid / MeCN": None,
    "BFEE + Et2O": None,
    "pure BFEE": None,
}

# Map the label CSV's electrolyte text (after dropping a trailing "(anion)") to a library salt
# (data/electrolytes.csv). Anything not a concrete library salt -> None (generic/unspecified/absent).
SALT_ALIASES: dict[str, str] = {
    "TBAPF6": "TBAPF6",
    "TBABF4": "TBABF4",
    "TBAClO4": "TBAClO4",
    "Bu4NClO4": "TBAClO4",
    "LiClO4": "LiClO4",
    "H2SO4": "H2SO4",
    "2 M H2SO4": "H2SO4",
}


@dataclass
class FeasibilityResult:
    """Outcome of the §7 qualitative-feasibility diagnostic (never a single raw-accuracy pass)."""

    computable: bool
    message: str
    status_note: str = FEASIBILITY_STATUS_NOTE
    n_labels: int = 0
    n_yes: int = 0
    n_no: int = 0
    n_out_of_scope: int = 0
    out_of_scope_breakdown: dict[str, int] = field(default_factory=dict)
    n_in_scope: int = 0
    n_matched: int = 0
    # Confusion matrix with predicted-YES := screen survivor.
    tp: int = 0  # outcome YES, predicted YES
    fn: int = 0  # outcome YES, predicted NO
    tn: int = 0  # outcome NO, predicted NO
    fp: int = 0  # outcome NO, predicted YES
    recall_yes: float | None = None
    recall_no: float | None = None
    balanced_accuracy: float | None = None
    trivial_always_yes_note: str = ""
    matched_detail: list[dict[str, object]] = field(default_factory=list)


def load_polymerizability_labels(path: str | Path = DEFAULT_LABELS_PATH) -> pd.DataFrame:
    """Load the binary feasibility labels, validating the schema (blank cells preserved)."""

    frame = pd.read_csv(path, keep_default_na=False)
    missing = set(LABEL_COLUMNS).difference(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")
    return frame


def _canonical(smiles: str) -> str | None:
    smiles = str(smiles).strip()
    if not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def _out_of_scope_reason(row: pd.Series) -> str | None:
    """Out-of-scope reason for a label, or None if the screen's baseline regime can score it.

    Out of scope (the screen does not model these media): BFEE Lewis-acid medium, aqueous-acid
    (protonation is not modeled), and Ag-pseudo-reference rows (not comparable to the Ag/AgCl
    baseline). Stated explicitly so they are reported, not silently dropped.
    """

    medium_class = str(row.get("medium_class", "")).strip()
    if medium_class == "BFEE":
        return "BFEE (Lewis-acid medium not modeled)"
    if medium_class == "aqueous_acid":
        return "aqueous-acid (protonation not modeled)"
    reference = str(row.get("reference_electrode", ""))
    flags = str(row.get("flags", ""))
    if "Ag pseudo" in reference or "Ag pseudo" in flags:
        return "Ag pseudo-reference (not comparable to Ag/AgCl baseline)"
    return None


def _normalize_triad(row: pd.Series) -> tuple[str, str, str] | None:
    """Map a label row to a harvest triad key (canonical_smiles, solvent_name, salt), or None."""

    canonical = _canonical(row["monomer_smiles"])
    if canonical is None:
        return None
    solvent = SOLVENT_ALIASES.get(str(row["solvent"]).strip())
    if solvent is None:
        return None
    salt_text = str(row["electrolyte"]).split("(")[0].strip()
    salt = SALT_ALIASES.get(salt_text)
    if salt is None:
        return None
    return canonical, solvent, salt


def _harvest_survivor_index(harvest: pd.DataFrame) -> dict[tuple[str, str, str], bool]:
    required = {
        HARVEST_SMILES_COLUMN,
        HARVEST_SOLVENT_COLUMN,
        HARVEST_SALT_COLUMN,
        HARVEST_SURVIVOR_COLUMN,
    }
    missing = required.difference(harvest.columns)
    if missing:
        raise ValueError(
            "harvest CSV is missing triad/survivor columns: " + ", ".join(sorted(missing))
        )
    index: dict[tuple[str, str, str], bool] = {}
    for _, row in harvest.iterrows():
        canonical = _canonical(str(row[HARVEST_SMILES_COLUMN]))
        if canonical is None:
            continue
        key = (canonical, str(row[HARVEST_SOLVENT_COLUMN]), str(row[HARVEST_SALT_COLUMN]))
        index[key] = bool(row[HARVEST_SURVIVOR_COLUMN])
    return index


def compute_feasibility_metric(
    *,
    labels: pd.DataFrame | None = None,
    labels_path: str | Path = DEFAULT_LABELS_PATH,
    harvest_path: str | Path | None = None,
    harvest: pd.DataFrame | None = None,
) -> FeasibilityResult:
    """Score the screen's survivor predictions against the binary feasibility labels (DIAGNOSTIC).

    Predicted-YES := triad is a Tier-1 survivor (``passes_all_tier1_filters``). Only labels whose
    (canonical monomer SMILES, solvent, electrolyte) match a harvest triad AND are in the screen's
    baseline regime are scored; out-of-scope media are counted and reported, never silently dropped.
    Returns balanced accuracy + the 2x2 confusion matrix — never a single raw-accuracy pass/fail.
    """

    labels = load_polymerizability_labels(labels_path) if labels is None else labels
    n_labels = int(len(labels))
    n_yes = int((labels["outcome"] == "YES").sum())
    n_no = int((labels["outcome"] == "NO").sum())
    trivial = (
        f"Trivial always-YES baseline would score raw accuracy ~{n_yes / n_labels:.2%} "
        f"({n_yes}/{n_labels}); balanced accuracy of always-YES = 50%."
        if n_labels
        else ""
    )

    base = FeasibilityResult(
        computable=False,
        message="",
        n_labels=n_labels,
        n_yes=n_yes,
        n_no=n_no,
        trivial_always_yes_note=trivial,
    )

    # Resolve the harvest (explicit frame > path > none). No harvest -> nothing to score against.
    if harvest is None:
        if harvest_path is None or not Path(harvest_path).exists():
            base.message = "no harvest to score against"
            return base
        harvest = pd.read_csv(harvest_path, keep_default_na=False, low_memory=False)

    survivor_index = _harvest_survivor_index(harvest)

    out_of_scope_breakdown: dict[str, int] = {}
    in_scope_rows: list[pd.Series] = []
    for _, row in labels.iterrows():
        reason = _out_of_scope_reason(row)
        if reason is not None:
            out_of_scope_breakdown[reason] = out_of_scope_breakdown.get(reason, 0) + 1
        else:
            in_scope_rows.append(row)

    base.n_out_of_scope = sum(out_of_scope_breakdown.values())
    base.out_of_scope_breakdown = out_of_scope_breakdown
    base.n_in_scope = len(in_scope_rows)

    matched_detail: list[dict[str, object]] = []
    tp = fn = tn = fp = 0
    for row in in_scope_rows:
        key = _normalize_triad(row)
        if key is None or key not in survivor_index:
            continue
        predicted_yes = survivor_index[key]
        outcome_yes = str(row["outcome"]) == "YES"
        if outcome_yes and predicted_yes:
            tp += 1
        elif outcome_yes and not predicted_yes:
            fn += 1
        elif (not outcome_yes) and (not predicted_yes):
            tn += 1
        else:
            fp += 1
        matched_detail.append(
            {
                "monomer_name": row["monomer_name"],
                "triad": key,
                "outcome": "YES" if outcome_yes else "NO",
                "predicted": "YES" if predicted_yes else "NO",
            }
        )

    n_matched = len(matched_detail)
    base.n_matched = n_matched
    base.tp, base.fn, base.tn, base.fp = tp, fn, tn, fp
    base.matched_detail = matched_detail

    if n_matched == 0:
        base.computable = False
        base.message = "0 matched — metric not computable on current library"
        return base

    # Per-class recall; balanced accuracy needs BOTH classes present in the matched set.
    recall_yes = tp / (tp + fn) if (tp + fn) else None
    recall_no = tn / (tn + fp) if (tn + fp) else None
    base.recall_yes = recall_yes
    base.recall_no = recall_no
    if recall_yes is None or recall_no is None:
        base.computable = False
        base.balanced_accuracy = None
        base.message = (
            f"{n_matched} matched but a class is empty (matched YES={tp + fn}, NO={tn + fp}); "
            "balanced accuracy not computable — need >=1 matched label in each class"
        )
        return base

    base.balanced_accuracy = (recall_yes + recall_no) / 2.0
    base.computable = True
    base.message = (
        f"{n_matched} matched (in-scope); balanced accuracy "
        f"{base.balanced_accuracy:.2%} (per-class recall YES={recall_yes:.2%}, NO={recall_no:.2%})"
    )
    return base


def format_feasibility_report(result: FeasibilityResult) -> str:
    """One-block human-readable §7 feasibility report (diagnostic; never a single accuracy pass)."""

    lines = ["§7 qualitative feasibility (DIAGNOSTIC; balanced accuracy + confusion matrix only):"]
    lines.append(f"  {result.status_note}")
    if result.message == "no harvest to score against":
        lines.append(f"  Labels: {result.n_labels} ({result.n_yes} YES / {result.n_no} NO)")
        lines.append(f"  Result: {result.message} (pass --harvest <tier1 all-triads CSV> to score)")
        return "\n".join(lines)
    lines.append(
        f"  Labels: {result.n_labels} ({result.n_yes} YES / {result.n_no} NO); "
        f"coverage: {result.n_matched} matched a screen triad; "
        f"out-of-scope: {result.n_out_of_scope} rows"
    )
    if result.out_of_scope_breakdown:
        breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(result.out_of_scope_breakdown.items()))
        lines.append(f"  Out-of-scope breakdown: {breakdown}")
    if not result.computable:
        lines.append(f"  Result: {result.message}")
        if result.trivial_always_yes_note:
            lines.append(f"  {result.trivial_always_yes_note}")
        return "\n".join(lines)
    lines.append(
        "  Confusion (predicted-YES = survivor): "
        f"TP={result.tp} FN={result.fn} FP={result.fp} TN={result.tn}"
    )
    lines.append(
        f"  Per-class recall: YES={result.recall_yes:.2%}, NO={result.recall_no:.2%} -> "
        f"BALANCED accuracy = {result.balanced_accuracy:.2%} (NOT raw accuracy)"
    )
    if result.trivial_always_yes_note:
        lines.append(f"  {result.trivial_always_yes_note}")
    return "\n".join(lines)

"""Load and validate versioned chemical-space CSV assets."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable, TypeVar

import pandas as pd
from pydantic import BaseModel
from rdkit import Chem

from eps.chemspace.models import Electrolyte, Monomer, Solvent

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

T = TypeVar("T", bound=BaseModel)


def load_monomers(path: str | Path | None = None) -> list[Monomer]:
    """Load monomers with RDKit canonical SMILES for neutral repeat-unit precursors."""

    csv_path = Path(path) if path is not None else DATA_DIR / "monomers.csv"
    rows = _read_csv(csv_path, {"name", "monomer_class", "smiles", "notes"})
    return _records_from_rows(rows, Monomer, ("smiles",))


def load_solvents(path: str | Path | None = None) -> list[Solvent]:
    """Load solvents with dielectric constant eps_r and ESW limits in V vs Ag/AgCl."""

    csv_path = Path(path) if path is not None else DATA_DIR / "solvents.csv"
    rows = _read_csv(
        csv_path,
        {
            "name",
            "smiles",
            "eps_r",
            "esw_anodic_V",
            "esw_cathodic_V",
            "potential_reference",
            "xtb_gbsa_name",
            "notes",
        },
    )
    for row in rows:
        if row.get("xtb_gbsa_name") == "":
            row["xtb_gbsa_name"] = None
    solvents = _records_from_rows(rows, Solvent, ("smiles",))
    _warn_implausible_solvent_windows(solvents)
    return solvents


def load_electrolytes(path: str | Path | None = None) -> list[Electrolyte]:
    """Load electrolyte salts with canonical cation and anion SMILES."""

    csv_path = Path(path) if path is not None else DATA_DIR / "electrolytes.csv"
    rows = _read_csv(
        csv_path,
        {
            "salt",
            "cation_smiles",
            "anion_smiles",
            "salt_class",
            "notes",
            "electrolyte_role",
            "supporting_electrolyte_ok",
            "electrolyte_role_justification",
        },
    )
    return _records_from_rows(rows, Electrolyte, ("cation_smiles", "anion_smiles"))


def _read_csv(path: Path, required_columns: set[str]) -> list[dict[str, object]]:
    frame = pd.read_csv(path, keep_default_na=False)
    missing = required_columns.difference(frame.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required columns: {missing_list}")
    return frame.to_dict(orient="records")


def _records_from_rows(
    rows: Iterable[dict[str, object]],
    model: type[T],
    smiles_columns: tuple[str, ...],
) -> list[T]:
    records: list[T] = []
    failures: list[str] = []

    for one_based_index, row in enumerate(rows, start=2):
        canonical: dict[str, str] = {}
        for column in smiles_columns:
            smiles = str(row[column])
            canonical_smiles = _canonicalize_smiles(smiles)
            if canonical_smiles is None:
                label = row.get("name") or row.get("salt") or "<unnamed>"
                failures.append(f"row {one_based_index} ({label}), column {column}: {smiles}")
            else:
                canonical[_canonical_field_name(column)] = canonical_smiles

        if not failures:
            records.append(model(**row, **canonical))

    if failures:
        details = "\n".join(f"  - {failure}" for failure in failures)
        raise ValueError(f"RDKit failed to sanitize SMILES:\n{details}")

    return records


def _canonicalize_smiles(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles, sanitize=True)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def _canonical_field_name(smiles_column: str) -> str:
    if smiles_column == "smiles":
        return "canonical_smiles"
    return f"canonical_{smiles_column}"


def _warn_implausible_solvent_windows(solvents: Iterable[Solvent]) -> None:
    """Warn when solvent ESW limits look like widths rather than Ag/AgCl limits."""

    for solvent in solvents:
        if solvent.potential_reference == "Ag/AgCl" and solvent.esw_anodic_V > 4.0:
            warnings.warn(
                (
                    f"{solvent.name} has esw_anodic_V={solvent.esw_anodic_V} V vs "
                    "Ag/AgCl, which is unusually high and may be an ESW width."
                ),
                UserWarning,
                stacklevel=2,
            )

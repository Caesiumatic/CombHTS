"""Directive §8: non-obvious solvent-electrolyte pairing analysis for under-explored monomers."""
from __future__ import annotations

import pandas as pd

from eps.analysis import non_obvious_pairings


def _frame() -> pd.DataFrame:
    return pd.DataFrame([
        # selenophene (under-explored): best non-MeCN pairing beats its MeCN pairing
        {"monomer_name": "selenophene", "monomer_class": "alkylselenophene", "solvent_name": "acetonitrile",
         "salt": "TBAPF6", "composite_score": 0.40, "solvent_eps_r": 37.5, "passes_all_tier1_filters": True},
        {"monomer_name": "selenophene", "monomer_class": "alkylselenophene", "solvent_name": "propylene carbonate",
         "salt": "TBABF4", "composite_score": 0.72, "solvent_eps_r": 64.9, "passes_all_tier1_filters": True},
        # thiophene (NOT under-explored): only MeCN -> no non-obvious pairing emitted
        {"monomer_name": "thiophene", "monomer_class": "alkylthiophene", "solvent_name": "acetonitrile",
         "salt": "TBAPF6", "composite_score": 0.80, "solvent_eps_r": 37.5, "passes_all_tier1_filters": True},
        # a non-survivor must be excluded
        {"monomer_name": "furan", "monomer_class": "alkylfuran", "solvent_name": "DMSO",
         "salt": "LiClO4", "composite_score": 0.99, "solvent_eps_r": 46.7, "passes_all_tier1_filters": False},
    ])


def test_non_obvious_surfaces_under_explored_beating_acetonitrile() -> None:
    out = non_obvious_pairings(_frame())
    assert out is not None and not out.empty
    top = out.iloc[0]
    assert top["monomer_name"] == "selenophene"
    assert top["solvent_name"] == "propylene carbonate"
    assert bool(top["beats_acetonitrile"]) is True
    assert bool(top["under_explored_class"]) is True
    assert top["solvent_eps_r_conductivity_proxy"] == 64.9
    # thiophene has only an acetonitrile pairing -> not surfaced
    assert "thiophene" not in set(out["monomer_name"])
    # the non-survivor furan row is excluded
    assert "furan" not in set(out["monomer_name"])


def test_non_obvious_returns_none_without_columns() -> None:
    assert non_obvious_pairings(pd.DataFrame({"x": [1]})) is None

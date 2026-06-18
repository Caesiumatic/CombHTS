from __future__ import annotations

from pathlib import Path

import pytest

from eps.engines import CalcRequest, MockEngine, SpeciesSpec
from eps.properties.calculators import EV_TO_KCAL_MOL, _gas_energy_eV, dimerization_dG
from eps.storage import SQLiteCache
from eps.structures.oligomer import DIMER_N, load_polymerization_specs, oligomer_smiles


def _mock_gas_energy(smiles: str, charge: int) -> float:
    return MockEngine().run(
        CalcRequest(SpeciesSpec(smiles, charge, 1), "mock-gfn2", None, "gas_energy")
    ).value


def test_dimerization_reproduces_the_reaction_formula(tmp_path: Path) -> None:
    spec = load_polymerization_specs()["thiophene"]
    monomer = next(m for m in __import__("eps.chemspace", fromlist=["load_monomers"]).load_monomers()
                   if m.name == "thiophene")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()

    dimer_smiles = oligomer_smiles(monomer.canonical_smiles, spec, DIMER_N)
    # The dimer is evaluated NEUTRAL (charge 0): 2 M+. -> M-M(neutral) + 2 H+.
    g_dimer = _mock_gas_energy(dimer_smiles, 0)
    g_cation = _mock_gas_energy(monomer.canonical_smiles, 1)
    expected = (g_dimer + 2 * 0.0 - 2 * g_cation) * EV_TO_KCAL_MOL

    value = dimerization_dG(monomer, engine, cache, spec=spec, proton_gibbs_eV=0.0)
    assert value == pytest.approx(expected)


def test_dimerization_relative_ordering_invariant_to_proton_constant(tmp_path: Path) -> None:
    from eps.chemspace import load_monomers

    specs = load_polymerization_specs()
    monomers = {m.name: m for m in load_monomers()}
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()

    def dG(name: str, proton: float) -> float:
        return dimerization_dG(
            monomers[name], engine, cache, spec=specs[name], proton_gibbs_eV=proton
        )

    # A different proton convention shifts every monomer by the SAME constant, so the
    # cross-monomer DIFFERENCE (what the w4 score uses after min-max) is unchanged.
    diff_p0 = dG("thiophene", 0.0) - dG("pyrrole", 0.0)
    diff_p5 = dG("thiophene", 5.0) - dG("pyrrole", 5.0)
    assert diff_p0 == pytest.approx(diff_p5)

    # The absolute value DOES shift by 2 * Δproton * conversion (screening-grade absolute).
    shift = dG("thiophene", 5.0) - dG("thiophene", 0.0)
    assert shift == pytest.approx(2 * 5.0 * EV_TO_KCAL_MOL)


def test_dimerization_uses_neutral_dimer_and_monomer_cation_charges(tmp_path: Path) -> None:
    # The reaction is charge-balanced: NEUTRAL dimer (charge 0) + 2 H+ from 2 monomer cations.
    spec = load_polymerization_specs()["pyrrole"]
    from eps.chemspace import load_monomers

    monomer = next(m for m in load_monomers() if m.name == "pyrrole")
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()
    dimer_smiles = oligomer_smiles(monomer.canonical_smiles, spec, DIMER_N)

    g_dimer = _gas_energy_eV(engine, cache, dimer_smiles, charge=0, multiplicity=1, method="mock-gfn2")
    g_cation = _gas_energy_eV(engine, cache, monomer.canonical_smiles, charge=1, multiplicity=2, method="mock-gfn2")
    assert g_dimer == pytest.approx(_mock_gas_energy(dimer_smiles, 0))
    assert g_cation == pytest.approx(_mock_gas_energy(monomer.canonical_smiles, 1))

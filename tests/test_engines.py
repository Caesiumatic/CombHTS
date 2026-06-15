from __future__ import annotations

from eps.engines import CalcRequest, MockEngine, SpeciesSpec


def test_mock_engine_is_deterministic_for_same_request() -> None:
    engine = MockEngine()
    req = CalcRequest(
        species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
        method="mock-gfn2",
        solvent_eps_r=37.5,
        quantity="adiabatic_ip",
    )

    first = engine.run(req)
    second = engine.run(req)

    assert first == second
    assert first.unit == "eV"


def test_mock_engine_solvent_lowers_adiabatic_ip() -> None:
    engine = MockEngine()
    species = SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1)
    gas_req = CalcRequest(
        species=species,
        method="mock-gfn2",
        solvent_eps_r=None,
        quantity="adiabatic_ip",
    )
    solvent_req = CalcRequest(
        species=species,
        method="mock-gfn2",
        solvent_eps_r=37.5,
        quantity="adiabatic_ip",
    )

    assert engine.run(solvent_req).value < engine.run(gas_req).value


def test_calc_request_rejects_unknown_quantity() -> None:
    try:
        CalcRequest(
            species=SpeciesSpec(canonical_smiles="c1ccsc1", charge=0, multiplicity=1),
            method="mock-gfn2",
            solvent_eps_r=None,
            quantity="not_a_property",
        )
    except ValueError as exc:
        assert "Unsupported quantity" in str(exc)
    else:
        raise AssertionError("CalcRequest accepted an unsupported quantity")

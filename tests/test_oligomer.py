from __future__ import annotations

from pathlib import Path

import pytest
from rdkit import Chem

from eps.chemspace import load_monomers
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    alpha_building_block_smiles,
    assemble_oligomer,
    detect_alpha_carbons,
    load_polymerization_specs,
    oligomer_smiles,
    write_building_block_artifact,
)


def _idx_to_symbol(smiles: str, idxs: list[int]) -> list[str]:
    mol = Chem.MolFromSmiles(smiles)
    return [mol.GetAtomWithIdx(i).GetSymbol() for i in idxs]


@pytest.mark.parametrize(
    "smiles",
    ["c1ccsc1", "c1cc[nH]c1", "c1ccoc1", "c1cc[se]c1", "CCCCCCc1ccsc1"],
)
def test_alpha_detection_finds_two_alpha_carbons_on_clean_heteroaromatics(smiles: str) -> None:
    mol = Chem.MolFromSmiles(smiles)
    alpha = detect_alpha_carbons(mol)

    assert len(alpha) == 2
    # Every detected site is a carbon directly bonded to the ring heteroatom.
    assert all(sym == "C" for sym in _idx_to_symbol(smiles, alpha))
    hetero = {7, 8, 16, 34}
    for idx in alpha:
        neighbors = {nb.GetAtomicNum() for nb in mol.GetAtomWithIdx(idx).GetNeighbors()}
        assert neighbors & hetero


def test_alpha_building_block_has_two_isotope_dummies() -> None:
    bb = alpha_building_block_smiles("c1ccsc1")
    mol = Chem.MolFromSmiles(bb)
    dummies = [a for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
    assert len(dummies) == 2
    assert {d.GetIsotope() for d in dummies} == {1, 2}


def test_alpha_building_block_rejects_non_clean_ring() -> None:
    # A 2,3-dioxythiophene has one α-carbon blocked, so auto-derivation must refuse it
    # (this is the WRONG isomer; the library now stores the 3,4-dioxy form, see
    # test_alkylenedioxy_monomers_have_two_free_alpha_carbons).
    with pytest.raises(ValueError, match="exactly 2 α-carbons"):
        alpha_building_block_smiles("c1cc2c(s1)OCCO2")


def test_alkylenedioxy_monomers_have_two_free_alpha_carbons() -> None:
    """Regression: EDOT/ProDOT/EDOP/EDOS must be the 3,4-dioxy isomer with BOTH α-carbons
    (adjacent to the ring heteroatom) free (bearing an H) for clean 2,5 coupling. Guards
    against silently regressing to the 2,3-dioxy isomer (one α blocked)."""

    library = {m.name: m for m in load_monomers()}
    for name in ("EDOT", "ProDOT", "EDOP", "EDOS"):
        mol = Chem.MolFromSmiles(library[name].canonical_smiles)
        assert mol is not None
        alpha = detect_alpha_carbons(mol)
        assert len(alpha) == 2, f"{name}: expected 2 α-carbons, got {len(alpha)}"
        for idx in alpha:
            atom = mol.GetAtomWithIdx(idx)
            assert atom.GetTotalNumHs() >= 1, f"{name}: α-carbon {idx} is blocked (no H)"
            assert any(nb.GetAtomicNum() in {7, 8, 16, 34} for nb in atom.GetNeighbors())
        # And the spec is now clean α-coupling, not an approximate explicit block.
        spec = load_polymerization_specs()[name]
        assert spec.coupling_mode == "alpha"
        assert spec.approximate is False


def test_assemble_thiophene_hexamer_atom_count_and_connectivity() -> None:
    hexamer = assemble_oligomer("[1*]c1ccc([2*])s1", 6)
    # Single connected fragment (no leftover dummies, no disconnected pieces).
    assert len(Chem.GetMolFrags(hexamer)) == 1
    assert not any(a.GetAtomicNum() == 0 for a in hexamer.GetAtoms())
    assert hexamer.GetNumAtoms() == 30  # 6 thiophenes x 5 heavy atoms, α,α'-coupled
    assert Chem.AddHs(hexamer).GetNumAtoms() == 44


def test_assemble_dimer_of_thiophene_is_bithiophene() -> None:
    dimer = assemble_oligomer("[1*]c1ccc([2*])s1", 2)
    assert Chem.MolToSmiles(dimer) == Chem.MolToSmiles(Chem.MolFromSmiles("c1ccc(-c2cccs2)s1"))


def test_every_library_monomer_has_a_spec_that_assembles() -> None:
    specs = load_polymerization_specs()
    monomers = load_monomers()
    assert set(specs) >= {m.name for m in monomers}

    for monomer in monomers:
        spec = specs[monomer.name]
        for n in (2, DEFAULT_OLIGOMER_N):
            smiles = oligomer_smiles(monomer.canonical_smiles, spec, n)
            mol = Chem.MolFromSmiles(smiles)
            assert mol is not None
            assert len(Chem.GetMolFrags(mol)) == 1  # connected
            assert not any(a.GetAtomicNum() == 0 for a in mol.GetAtoms())  # no dummies


def test_truncate_inert_alkyl_to_methyl_shortens_side_chains_but_keeps_backbone() -> None:
    from eps.structures.oligomer import truncate_inert_alkyl_to_methyl

    # Dioctylfluorene -> 9,9-dimethylfluorene; 3-hexylthiophene -> 3-methylthiophene.
    dioctyl = "CCCCCCCCC1(CCCCCCCC)c2ccccc2-c2ccccc21"
    truncated, changed = truncate_inert_alkyl_to_methyl(dioctyl)
    assert changed
    assert truncated == Chem.MolToSmiles(Chem.MolFromSmiles("CC1(C)c2ccccc2-c2ccccc21"))

    hexyl, changed2 = truncate_inert_alkyl_to_methyl("CCCCCCc1ccsc1")
    assert changed2
    assert hexyl == Chem.MolToSmiles(Chem.MolFromSmiles("Cc1ccsc1"))

    # No inert alkyl -> unchanged; the aromatic backbone (and dioxy bridge) is preserved.
    for clean in ("c1ccsc1", "C1COc2cscc2O1"):
        out, changed3 = truncate_inert_alkyl_to_methyl(clean)
        assert changed3 is False
        assert Chem.MolFromSmiles(out).GetNumAtoms() == Chem.MolFromSmiles(clean).GetNumAtoms()


def test_optical_gap_oligomer_truncates_only_when_side_chains_present() -> None:
    from eps.properties.calculators import optical_gap_oligomer

    specs = load_polymerization_specs()
    monomers = {m.name: m for m in load_monomers()}

    fluorene_smiles, fluorene_truncated = optical_gap_oligomer(
        monomers["fluorene 9,9-dioctyl"], specs["fluorene 9,9-dioctyl"], DEFAULT_OLIGOMER_N
    )
    assert fluorene_truncated is True
    assert "CCCCCCCC" not in fluorene_smiles  # the octyl tails are gone

    _, thiophene_truncated = optical_gap_oligomer(
        monomers["thiophene"], specs["thiophene"], DEFAULT_OLIGOMER_N
    )
    assert thiophene_truncated is False


def test_polymer_optical_gap_is_computed_on_the_oligomer_not_the_monomer(tmp_path: Path) -> None:
    from eps.engines import CalcRequest, MockEngine, SpeciesSpec
    from eps.properties.calculators import (
        OPTICAL_GAP_BACKEND_MOCK,
        OPTICAL_GAP_METHOD_REVISION,
        polymer_optical_gap,
        polymer_optical_gap_method,
    )
    from eps.storage import SQLiteCache

    specs = load_polymerization_specs()
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = specs["thiophene"]
    cache = SQLiteCache(tmp_path / "c.sqlite")
    engine = MockEngine()

    gap = polymer_optical_gap(monomer, engine, cache, spec=spec, n=DEFAULT_OLIGOMER_N)

    # The value matches the engine's optical_gap of the assembled hexamer SMILES, not the monomer.
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, DEFAULT_OLIGOMER_N)
    optical_cache_method = f"mock-gfn2{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_MOCK}"
    expected = MockEngine().run(
        CalcRequest(SpeciesSpec(hexamer, 0, 1), optical_cache_method, None, "optical_gap")
    ).value
    monomer_value = MockEngine().run(
        CalcRequest(
            SpeciesSpec(monomer.canonical_smiles, 0, 1),
            optical_cache_method,
            None,
            "optical_gap",
        )
    ).value
    assert gap == pytest.approx(expected)
    assert gap != pytest.approx(monomer_value)
    assert polymer_optical_gap_method(monomer, engine, cache, spec=spec) == "mock-deterministic"


def test_optical_gap_cache_revision_bypasses_old_key_and_reuses_new_key(tmp_path: Path) -> None:
    from eps.engines import CalcResult, Engine
    from eps.properties.calculators import (
        OPTICAL_GAP_BACKEND_GENERIC,
        OPTICAL_GAP_METHOD_REVISION,
        polymer_optical_gap,
        polymer_optical_gap_method,
    )
    from eps.storage import CacheKey, SQLiteCache
    from eps.storage.cache import GAS_SOLVENT_NAME

    specs = load_polymerization_specs()
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = specs["thiophene"]
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, DEFAULT_OLIGOMER_N)
    method = "mock-gfn2"
    revised_method = f"{method}{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_GENERIC}"
    cache = SQLiteCache(tmp_path / "c.sqlite")
    old_key = CacheKey(hexamer, 0, method, GAS_SOLVENT_NAME, "optical_gap")
    cache.put(
        old_key,
        CalcResult(
            value=999.0,
            unit="eV",
            method=method,
            raw={"optical_gap_method": "old-sentinel"},
        ),
    )
    metadata = {
        "optical_gap_method": "stda-xtb",
        "optical_gap_geometry_source": "xtbopt.xyz",
        "optimized_geometry_available": True,
        "optimized_geometry_sha256": "abc123",
        "stda_available": True,
        "stda_attempted": True,
        "stda_status": "success",
        "fallback_used": False,
        "stda_failure_type": "",
        "stda_failure_message": "",
    }

    class CountingOpticalEngine(Engine):
        def __init__(self) -> None:
            self.requests = []

        def run(self, req):
            self.requests.append(req)
            assert req.quantity == "optical_gap"
            return CalcResult(value=2.75, unit="eV", method=req.method, raw=dict(metadata))

    engine = CountingOpticalEngine()

    first = polymer_optical_gap(monomer, engine, cache, method=method, spec=spec)
    assert first == pytest.approx(2.75)
    assert len(engine.requests) == 1
    assert engine.requests[0].method == revised_method
    assert cache.get(old_key).value == pytest.approx(999.0)

    new_key = CacheKey(hexamer, 0, revised_method, GAS_SOLVENT_NAME, "optical_gap")
    cached = cache.get(new_key)
    assert cached is not None
    assert cached.value == pytest.approx(2.75)
    assert cached.method == revised_method
    assert cached.raw == metadata

    second = polymer_optical_gap(monomer, engine, cache, method=method, spec=spec)
    assert second == pytest.approx(2.75)
    assert len(engine.requests) == 1
    assert polymer_optical_gap_method(monomer, engine, cache, method=method, spec=spec) == "stda-xtb"
    assert len(engine.requests) == 1
    assert cache.count() == 2


def test_optical_gap_backend_tag_separates_stda_from_cached_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from eps.engines import CalcResult
    from eps.engines.xtb import XTBEngine
    from eps.properties import calculators as calculators_module
    from eps.properties.calculators import (
        OPTICAL_GAP_BACKEND_HL_FALLBACK,
        OPTICAL_GAP_BACKEND_STDA,
        OPTICAL_GAP_METHOD_REVISION,
        polymer_optical_gap,
        polymer_optical_gap_method,
    )
    from eps.storage import CacheKey, SQLiteCache
    from eps.storage.cache import GAS_SOLVENT_NAME

    specs = load_polymerization_specs()
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = specs["thiophene"]
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, DEFAULT_OLIGOMER_N)
    method = "gfn2-xtb"
    fallback_method = f"{method}{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_HL_FALLBACK}"
    stda_method = f"{method}{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_STDA}"
    cache = SQLiteCache(tmp_path / "c.sqlite")
    fallback_key = CacheKey(hexamer, 0, fallback_method, GAS_SOLVENT_NAME, "optical_gap")
    cache.put(
        fallback_key,
        CalcResult(
            value=9.99,
            unit="eV",
            method=fallback_method,
            raw={
                "optical_gap_method": "homo_lumo_hexamer_fallback",
                "stda_available": False,
                "fallback_used": True,
            },
        ),
    )

    class CountingXTBEngine(XTBEngine):
        def __init__(self) -> None:
            super().__init__(binary="xtb", stda_binary="stda")
            self.requests = []

        def run(self, req):
            self.requests.append(req)
            return CalcResult(
                value=2.25,
                unit="eV",
                method=req.method,
                raw={
                    "optical_gap_method": "stda-xtb",
                    "stda_available": True,
                    "fallback_used": False,
                },
            )

    fallback_engine = CountingXTBEngine()
    monkeypatch.setattr(calculators_module.shutil, "which", lambda binary: None)
    assert polymer_optical_gap(monomer, fallback_engine, cache, method=method, spec=spec) == pytest.approx(9.99)
    assert polymer_optical_gap(monomer, fallback_engine, cache, method=method, spec=spec) == pytest.approx(9.99)
    assert fallback_engine.requests == []

    stda_engine = CountingXTBEngine()
    monkeypatch.setattr(
        calculators_module.shutil,
        "which",
        lambda binary: "/fake/stda" if binary == "stda" else None,
    )
    assert polymer_optical_gap(monomer, stda_engine, cache, method=method, spec=spec) == pytest.approx(2.25)
    assert len(stda_engine.requests) == 1
    assert stda_engine.requests[0].method == stda_method
    assert polymer_optical_gap(monomer, stda_engine, cache, method=method, spec=spec) == pytest.approx(2.25)
    assert len(stda_engine.requests) == 1
    assert polymer_optical_gap_method(monomer, stda_engine, cache, method=method, spec=spec) == "stda-xtb"
    assert len(stda_engine.requests) == 1

    stda_key = CacheKey(hexamer, 0, stda_method, GAS_SOLVENT_NAME, "optical_gap")
    assert cache.get(fallback_key).value == pytest.approx(9.99)
    assert cache.get(fallback_key).raw["optical_gap_method"] == "homo_lumo_hexamer_fallback"
    assert cache.get(stda_key).value == pytest.approx(2.25)
    assert cache.get(stda_key).raw["optical_gap_method"] == "stda-xtb"
    assert cache.count() == 2


def test_optical_gap_cache_method_suffixing_is_idempotent() -> None:
    from eps.engines import MockEngine
    from eps.properties.calculators import (
        OPTICAL_GAP_BACKEND_MOCK,
        OPTICAL_GAP_METHOD_REVISION,
        _optical_gap_cache_method,
    )

    engine = MockEngine()
    versioned = f"mock-gfn2{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_MOCK}"

    assert _optical_gap_cache_method("mock-gfn2", engine) == versioned
    assert _optical_gap_cache_method(f"mock-gfn2{OPTICAL_GAP_METHOD_REVISION}", engine) == versioned
    assert _optical_gap_cache_method(versioned, engine) == versioned


def test_optical_gap_cache_revision_does_not_touch_non_optical_keys(tmp_path: Path) -> None:
    from eps.engines import CalcResult, Engine
    from eps.properties.calculators import (
        OPTICAL_GAP_BACKEND_MOCK,
        OPTICAL_GAP_METHOD_REVISION,
        oligomer_eox_raw_eV,
    )
    from eps.storage import CacheKey, SQLiteCache
    from eps.storage.cache import GAS_SOLVENT_NAME

    specs = load_polymerization_specs()
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = specs["thiophene"]
    hexamer = oligomer_smiles(monomer.canonical_smiles, spec, DEFAULT_OLIGOMER_N)
    cache = SQLiteCache(tmp_path / "c.sqlite")
    key = CacheKey(hexamer, 0, "mock-gfn2", GAS_SOLVENT_NAME, "adiabatic_ip")
    cache.put(
        key,
        CalcResult(value=12.5, unit="eV", method="mock-gfn2", raw={"sentinel": "non-optical"}),
    )

    class FailingEngine(Engine):
        def run(self, req):
            raise AssertionError(f"engine should not run for cached non-optical key: {req}")

    value = oligomer_eox_raw_eV(
        monomer,
        FailingEngine(),
        cache,
        method="mock-gfn2",
        spec=spec,
        n=DEFAULT_OLIGOMER_N,
    )

    assert value == pytest.approx(12.5)
    assert cache.count() == 1
    assert cache.get(key).raw == {"sentinel": "non-optical"}
    assert (
        cache.get(
            CacheKey(
                hexamer,
                0,
                f"mock-gfn2{OPTICAL_GAP_METHOD_REVISION}{OPTICAL_GAP_BACKEND_MOCK}",
                GAS_SOLVENT_NAME,
                "adiabatic_ip",
            )
        )
        is None
    )


def test_building_block_artifact_is_written_with_review_columns(tmp_path: Path) -> None:
    specs = load_polymerization_specs()
    monomers = load_monomers()
    artifact = write_building_block_artifact(monomers, specs, DEFAULT_OLIGOMER_N, tmp_path / "bb.csv")

    assert artifact.exists()
    import pandas as pd

    frame = pd.read_csv(artifact)
    assert {"monomer_name", "building_block_smiles", "coupling_mode", "approximate",
            "dimer_smiles", "oligomer_n6_smiles", "notes"}.issubset(frame.columns)
    assert len(frame) == len(monomers)
    # No assembly errors leaked into the artifact.
    assert not frame["oligomer_n6_smiles"].astype(str).str.contains("ASSEMBLY_ERROR").any()


def test_oligomer_eox_monotonic_status() -> None:
    """Directive §3.1 reported-only monotonicity diagnostic on the oligomer Eox-vs-n series."""
    from eps.properties.oligomer_series import _monotonic_decreasing_status

    # Eox decreases with chain length (physical expectation) -> monotonic
    assert _monotonic_decreasing_status({1: 1.50, 2: 1.15, 3: 0.95, 6: 0.80}) == "monotonic_decreasing"
    # a genuine rise beyond the noise tolerance -> non-monotonic
    assert _monotonic_decreasing_status({1: 1.0, 2: 1.4, 3: 0.9}) == "non_monotonic"
    # within-tolerance wobble is still called monotonic (screening-grade noise)
    assert _monotonic_decreasing_status({1: 1.0, 2: 1.03, 3: 0.8}, tol=0.05) == "monotonic_decreasing"
    # fewer than two finite points -> insufficient
    assert _monotonic_decreasing_status({2: 1.0}) == "insufficient_points"

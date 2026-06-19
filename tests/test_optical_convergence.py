from __future__ import annotations

from pathlib import Path

import yaml

from eps.chemspace import load_monomers
from eps.engines import MockEngine
from eps.properties.optical_convergence import compute_optical_gap_convergence
from eps.storage import SQLiteCache
from eps.structures.oligomer import load_polymerization_specs
from eps.workflow.tier1 import run_tier1


def test_optical_gap_convergence_columns_and_delta(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    spec = load_polymerization_specs()["thiophene"]
    d = compute_optical_gap_convergence(
        monomer, spec, MockEngine(), SQLiteCache(tmp_path / "c.sqlite"),
        method="mock-gfn2", lengths=(1, 2, 3, 4, 5, 6), threshold_eV=0.1,
    )
    assert d["optical_gap_convergence_calc_status"] == "ok"
    for n in range(1, 7):
        assert f"optical_gap_n{n}_eV" in d
        assert d[f"optical_gap_n{n}_eV"] == d[f"optical_gap_n{n}_eV"]  # not NaN
    # delta = |gap(6) - gap(5)|, converged is a bool against the threshold.
    expected_delta = abs(d["optical_gap_n6_eV"] - d["optical_gap_n5_eV"])
    assert abs(d["optical_gap_convergence_delta_eV"] - expected_delta) < 1e-12
    assert isinstance(d["optical_gap_converged"], bool)
    assert d["optical_gap_converged"] == (d["optical_gap_convergence_delta_eV"] <= 0.1)


def test_optical_gap_convergence_no_spec_is_failure_tolerant(tmp_path: Path) -> None:
    monomer = next(m for m in load_monomers() if m.name == "thiophene")
    d = compute_optical_gap_convergence(
        monomer, None, MockEngine(), SQLiteCache(tmp_path / "c.sqlite"), method="mock-gfn2",
    )
    assert d["optical_gap_convergence_calc_status"] == "failed"
    assert d["optical_gap_n6_eV"] != d["optical_gap_n6_eV"]  # NaN, did not crash


def _run(enabled: bool, tmp_path: Path):
    cfg = yaml.safe_load(Path("configs/tier1.yaml").read_text())
    cfg["bandgap_convergence"] = {"enabled": enabled, "lengths": [1, 2, 3, 4, 5, 6], "threshold_eV": 0.1}
    cfg_path = tmp_path / f"tier1_{enabled}.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    return run_tier1(
        engine=MockEngine(),
        cache_path=tmp_path / f"c_{enabled}.sqlite",
        output_path=tmp_path / f"r_{enabled}.csv",
        tier1_config_path=cfg_path,
    )


def test_bandgap_convergence_is_strictly_additive(tmp_path: Path) -> None:
    on = _run(True, tmp_path)
    off = _run(False, tmp_path)

    assert on.total_triads == off.total_triads
    assert on.surviving_triads == off.surviving_triads

    key = ["monomer_name", "solvent_name", "salt"]
    a = on.ranked.set_index(key)["composite_score"].sort_index()
    b = off.ranked.set_index(key)["composite_score"].sort_index()
    assert a.index.equals(b.index)
    assert float((a - b).abs().max()) == 0.0

    for column in ("optical_gap_n1_eV", "optical_gap_n6_eV",
                   "optical_gap_convergence_delta_eV", "optical_gap_converged"):
        assert column in on.all_triads.columns
        assert column not in off.all_triads.columns

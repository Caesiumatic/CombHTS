from __future__ import annotations

import itertools
import math
from pathlib import Path

import yaml

from eps.engines import CalcRequest, CalcResult, Engine, MockEngine
from eps.structures.geometry import (
    ConformerSearchConfig,
    conformer_method_suffix,
    smiles_to_xyz,
)
from eps.workflow.tier1 import run_tier1


class CountingEngine(Engine):
    def __init__(self) -> None:
        self.calls = 0
        self.delegate = MockEngine()

    def run(self, req: CalcRequest) -> CalcResult:
        self.calls += 1
        return self.delegate.run(req)


def _coords(xyz: str):
    return [tuple(map(float, line.split()[1:4])) for line in xyz.strip().splitlines()[2:]]


def test_conformer_search_produces_valid_geometry() -> None:
    cfg = ConformerSearchConfig(enabled=True, n_conformers=8, method="mmff94")
    xyz = smiles_to_xyz("c1ccsc1", conformer_search=cfg)
    assert int(xyz.splitlines()[0]) == 9  # thiophene + Hs
    # No atom clash.
    assert min(math.dist(a, b) for a, b in itertools.combinations(_coords(xyz), 2)) > 0.7


def test_conformer_search_preserves_se_skip() -> None:
    # EDOS (Se): MMFF cannot type Se, so the conformer search falls back to the single hardened
    # ETKDG embed and MUST NOT FF-collapse the geometry (T10 Se-skip preserved).
    cfg = ConformerSearchConfig(enabled=True, n_conformers=8, method="mmff94")
    xyz = smiles_to_xyz("C1COc2cc[se]c2O1", charge=0, conformer_search=cfg)
    assert int(xyz.splitlines()[0]) == 15
    assert min(math.dist(a, b) for a, b in itertools.combinations(_coords(xyz), 2)) > 0.7


def test_conformer_method_suffix() -> None:
    assert conformer_method_suffix(ConformerSearchConfig(True, 100, "mmff94")) == "+conf-mmff94-n100"
    assert conformer_method_suffix(ConformerSearchConfig()) == ""
    assert conformer_method_suffix(None) == ""


def test_default_single_conformer_path_unchanged() -> None:
    # With no override and the module default (disabled), the geometry is the historical
    # single-conformer embed (regression guard for test_geometry expectations).
    assert int(smiles_to_xyz("c1ccsc1").splitlines()[0]) == 9


def _cfg_path(tmp_path: Path, enabled: bool) -> Path:
    cfg = yaml.safe_load(Path("configs/tier1.yaml").read_text())
    cfg["conformer_search"] = {"enabled": enabled, "n_conformers": 100, "method": "mmff94"}
    p = tmp_path / f"tier1_{enabled}.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return p


def test_conformer_setting_is_in_the_cache_key(tmp_path: Path) -> None:
    # Same cache, single-conformer first then conformer-search: the second run MUST recompute
    # (different method suffix → different cache key), never reuse the single-conformer values.
    cache = tmp_path / "shared.sqlite"
    e1 = CountingEngine()
    run_tier1(engine=e1, cache_path=cache, output_path=tmp_path / "off.csv",
              tier1_config_path=_cfg_path(tmp_path, False))
    assert e1.calls > 0
    e2 = CountingEngine()
    run_tier1(engine=e2, cache_path=cache, output_path=tmp_path / "on.csv",
              tier1_config_path=_cfg_path(tmp_path, True))
    assert e2.calls > 0  # conformer-search run is NOT served from the single-conformer cache


def test_conformer_search_run_still_produces_survivors(tmp_path: Path) -> None:
    result = run_tier1(engine=MockEngine(), cache_path=tmp_path / "c.sqlite",
                       output_path=tmp_path / "r.csv", tier1_config_path=_cfg_path(tmp_path, True))
    assert result.total_triads == 36 * 13 * 15
    assert result.surviving_triads > 0

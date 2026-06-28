"""Wiring tests: Tier-2 uses ORCA (directive §4.2) with per-triad SMD, Freq, engine-pinned cache.

No real ORCA is invoked here — these check config loading, the cache method label, engine
selection, the engine/config consistency guard, and per-solvent SMD-name threading.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from eps.engines.gaussian import load_tier2_config
from eps.engines.orca import OrcaEngine
from eps.workflow.tier2 import _task_request, _tier2_engine

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_production_orca_config_loads_directive_compliant() -> None:
    cfg = load_tier2_config(_PROJECT_ROOT / "configs" / "tier2_orca.yaml")
    assert cfg.engine == "orca"
    assert cfg.use_smd is True  # per-triad SMD
    assert cfg.use_freq is True  # ΔG with thermal + ZPE
    assert cfg.method == "B3LYP"
    assert cfg.basis == "6-31G(d,p)"


def test_orca_cache_method_label_is_engine_specific() -> None:
    cfg = load_tier2_config(_PROJECT_ROOT / "configs" / "tier2_orca.yaml")
    assert cfg.cache_method_label() == "orca6.1/b3lyp/6-31g(d,p)/smd/freq:on"
    # the legacy gaussian config keeps its own label shape (no orca6.1 prefix)
    gauss = load_tier2_config(_PROJECT_ROOT / "configs" / "tier2.yaml")
    assert not gauss.cache_method_label().startswith("orca")


def test_tier2_engine_builds_orca_from_config(tmp_path: Path) -> None:
    cfg = load_tier2_config(_PROJECT_ROOT / "configs" / "tier2_orca.yaml")
    engine = _tier2_engine("orca", config=cfg, work_dir=tmp_path)
    assert isinstance(engine, OrcaEngine)
    assert engine.config.redox_smd is True
    assert engine.config.redox_use_freq is True
    assert engine.config.redox_functional == "B3LYP"
    assert engine.config.redox_basis == "6-31G(d,p)"
    assert engine.config.redox_hirshfeld is True


def test_engine_name_must_match_config_engine(tmp_path: Path) -> None:
    cfg = load_tier2_config(_PROJECT_ROOT / "configs" / "tier2_orca.yaml")
    with pytest.raises(ValueError, match="disagrees with config engine"):
        _tier2_engine("gaussian", config=cfg, work_dir=tmp_path)


def test_task_request_threads_per_solvent_orca_smd_name() -> None:
    # acetonitrile has a non-empty orca_smd_name; propylene carbonate is intentionally empty (gas).
    task_mecn = {
        "canonical_smiles": "c1ccsc1", "initial_charge": 0, "initial_multiplicity": 1,
        "method_label": "orca6.1/b3lyp/6-31g(d,p)/smd/freq:on",
        "solvent_name": "acetonitrile", "quantity": "adiabatic_ip",
    }
    req = _task_request(task_mecn)
    assert req.solvent_model_name == "Acetonitrile"

    task_pc = {**task_mecn, "solvent_name": "propylene carbonate"}
    req_pc = _task_request(task_pc)
    assert req_pc.solvent_model_name is None  # empty orca_smd_name -> gas-phase fallback

from __future__ import annotations

from pathlib import Path

import pandas as pd

from eps.workflow.tier3 import (
    AIMD_RADICAL_STABILITY,
    EXPLICIT_SOLVATION,
    SLAB_ADSORPTION,
    TIER3_NOT_RUN_STATUS,
    TIER3_OPTIONAL_HOOK_METHODS,
    load_tier3_config,
    run_tier3_optional_hook,
    write_tier3_dft_inputs,
)


def test_tier3_config_is_range_separated_dft() -> None:
    config = load_tier3_config()
    assert config.method == "CAM-B3LYP"
    assert config.basis == "6-311+G(d,p)"
    assert config.smd_solvent == "acetonitrile"
    assert config.use_freq is True
    label = config.method_label()
    assert "CAM-B3LYP/6-311+G(d,p)" in label
    assert "SMD(acetonitrile)" in label
    assert "opt+freq" in label


def test_tier3_range_separated_dft_inputs_are_real(tmp_path: Path) -> None:
    survivors = tmp_path / "refined.csv"
    pd.DataFrame(
        {"monomer_name": ["thiophene", "pyrrole"], "monomer_canonical_smiles": ["c1ccsc1", "c1cc[nH]c1"]}
    ).to_csv(survivors, index=False)

    result = write_tier3_dft_inputs(survivors, tmp_path / "tier3_inputs")
    assert result.n_unique_monomers == 2
    assert len(result.input_paths) == 4  # neutral + cation per monomer
    # The range-separated functional + diffuse basis + SMD actually reach the .gjf (real config).
    text = result.input_paths[0].read_text()
    assert "CAM-B3LYP/6-311+G(d,p)" in text
    assert "SCRF=(SMD,Solvent=acetonitrile)" in text
    assert "Freq" in text


def test_tier3_optional_hooks_are_flagged_not_run() -> None:
    for method in (EXPLICIT_SOLVATION, AIMD_RADICAL_STABILITY, SLAB_ADSORPTION):
        hook = run_tier3_optional_hook(method)
        assert hook.ran is False
        assert hook.status == TIER3_NOT_RUN_STATUS
        assert "DOCUMENTED HOOK" in hook.note
    assert set(TIER3_OPTIONAL_HOOK_METHODS) == {
        EXPLICIT_SOLVATION, AIMD_RADICAL_STABILITY, SLAB_ADSORPTION
    }


def test_tier3_optional_hook_rejects_unknown_method() -> None:
    import pytest

    with pytest.raises(ValueError, match="Unknown Tier-3 optional method"):
        run_tier3_optional_hook("not_a_method")

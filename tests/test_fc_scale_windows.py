"""Tests for the Fc/Fc+ -> Ag/AgCl solvent-window bridge (T3 Fc track)."""

from __future__ import annotations

import pandas as pd

from eps.properties.solvent_windows import (
    DEFAULT_FC_WINDOWS_PATH,
    FC_BRIDGE_TIER,
    fc_windows_to_agagcl_rows,
    load_fc_to_agagcl_offsets,
    load_solvent_window_measurements,
)


def test_offsets_load_and_mecn_matches_pinned_constant():
    offsets = load_fc_to_agagcl_offsets()
    # THF bridge offset = Fc 0.56 vs SCE + 0.045
    assert offsets["THF"] == 0.605
    # The MeCN bridge offset must reproduce the project-pinned Fc->Ag/AgCl constant (+0.445),
    # which validates the whole Connelly-Geiger + SCE->Ag/AgCl bridge chain.
    assert offsets["acetonitrile"] == 0.445


def test_nmp_and_sulfolane_have_no_sourced_offset():
    # Connelly & Geiger Table 1 contains neither NMP nor sulfolane; they MUST be absent so
    # they can never be silently bridged onto the aqueous gate.
    offsets = load_fc_to_agagcl_offsets()
    assert "NMP" not in offsets
    assert "sulfolane" not in offsets


def test_fc_windows_bridge_only_thf_among_targets():
    offsets = load_fc_to_agagcl_offsets()
    fc = pd.read_csv(DEFAULT_FC_WINDOWS_PATH, keep_default_na=False)
    bridged = fc_windows_to_agagcl_rows(fc, offsets)
    # Only THF is bridgeable (NMP/sulfolane dropped for lack of a sourced offset).
    assert list(bridged["solvent"]) == ["THF"]
    row = bridged.iloc[0]
    assert row["reference"] == "Ag/AgCl"
    assert row["tier"] == FC_BRIDGE_TIER
    assert bool(row["use_for_gate"]) is True
    # THF Izutsu window +1.6 / -3.85 vs Fc, +0.605 offset.
    assert row["anodic_limit_V_vs_AgAgCl"] == 2.205
    assert row["cathodic_limit_V_vs_AgAgCl"] == -3.245


def test_committed_thf_row_matches_converter():
    # The committed solvent_windows.csv THF Fc-bridge row must equal the converter output,
    # so the gate's source-of-truth CSV stays in sync with the documented bridge.
    offsets = load_fc_to_agagcl_offsets()
    fc = pd.read_csv(DEFAULT_FC_WINDOWS_PATH, keep_default_na=False)
    generated = fc_windows_to_agagcl_rows(fc, offsets)
    gen_thf = generated[generated["solvent"] == "THF"].iloc[0]

    measurements = load_solvent_window_measurements()
    committed = measurements[
        (measurements["solvent"] == "THF") & (measurements["tier"] == FC_BRIDGE_TIER)
    ]
    assert len(committed) == 1
    com_thf = committed.iloc[0]
    assert com_thf["anodic_limit_V_vs_AgAgCl"] == gen_thf["anodic_limit_V_vs_AgAgCl"]
    assert com_thf["cathodic_limit_V_vs_AgAgCl"] == gen_thf["cathodic_limit_V_vs_AgAgCl"]
    assert com_thf["reference"] == "Ag/AgCl"
    assert bool(com_thf["use_for_gate"]) is True

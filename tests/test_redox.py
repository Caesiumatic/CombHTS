from __future__ import annotations

import pytest

from eps.properties.redox import (
    ABS_SHE_V,
    AGAGCL_SHIFT_V,
    ip_eV_to_potential_vs_AgAgCl,
    potential_vs_AgAgCl_to_ip_eV,
)


def test_redox_constants_are_pinned() -> None:
    assert ABS_SHE_V == 4.28
    assert AGAGCL_SHIFT_V == -0.197


def test_ip_to_potential_vs_agagcl_conversion_is_pinned() -> None:
    assert ip_eV_to_potential_vs_AgAgCl(6.0) == pytest.approx(1.523, abs=1e-6)


def test_redox_conversion_round_trips() -> None:
    ip_eV = 6.35
    potential_V = ip_eV_to_potential_vs_AgAgCl(ip_eV)

    assert potential_vs_AgAgCl_to_ip_eV(potential_V) == pytest.approx(ip_eV, abs=1e-12)

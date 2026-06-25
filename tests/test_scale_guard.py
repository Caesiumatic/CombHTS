"""freeze-then-scale guard: block accidental full-scale (~50k) Tier-1 / full Tier-2 launches."""

import pytest

from eps.workflow.tier1 import (
    DEFAULT_MAX_TRIADS,
    ScaleGuardError,
    enforce_scale_guard,
)
from eps.workflow.tier2 import DEFAULT_MAX_TIER2_TASKS


def test_under_ceiling_passes():
    # current validated scale 36x13x16 = 7,488 is below the default 12,000 ceiling
    enforce_scale_guard(7488, max_units=DEFAULT_MAX_TRIADS, allow_large_scale=False)


def test_at_ceiling_passes():
    enforce_scale_guard(DEFAULT_MAX_TRIADS, max_units=DEFAULT_MAX_TRIADS, allow_large_scale=False)


def test_above_ceiling_raises_without_flag():
    with pytest.raises(ScaleGuardError) as exc:
        enforce_scale_guard(50000, max_units=DEFAULT_MAX_TRIADS, allow_large_scale=False)
    msg = str(exc.value)
    assert "50000" in msg and "freeze-then-scale" in msg and "--allow-large-scale" in msg


def test_above_ceiling_allowed_with_flag():
    # explicit authorization (the documented full-scale switch) lets it through
    enforce_scale_guard(50000, max_units=DEFAULT_MAX_TRIADS, allow_large_scale=True)


def test_tier2_default_ceiling_blocks_full_survivor_batch():
    # ~2,143 survivors (the directive §0 #2 forbidden full Tier-2) exceeds the 500-task pilot ceiling
    with pytest.raises(ScaleGuardError):
        enforce_scale_guard(
            2143, max_units=DEFAULT_MAX_TIER2_TASKS, allow_large_scale=False, kind="Tier-2 unique tasks"
        )
    enforce_scale_guard(
        2143, max_units=DEFAULT_MAX_TIER2_TASKS, allow_large_scale=True, kind="Tier-2 unique tasks"
    )

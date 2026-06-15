from __future__ import annotations

import numpy as np
import pytest

from eps.calibration import fit_linear_calibration


def test_linear_calibration_recovers_synthetic_parameters() -> None:
    x = np.array([-1.0, 0.0, 1.0, 2.0, 3.0])
    y = 2.5 * x - 0.4

    calibration = fit_linear_calibration(x, y)

    assert calibration.slope == pytest.approx(2.5, abs=1e-12)
    assert calibration.intercept == pytest.approx(-0.4, abs=1e-12)
    assert calibration.r2 == pytest.approx(1.0, abs=1e-12)
    assert calibration.mae == pytest.approx(0.0, abs=1e-12)
    assert calibration.apply(4.0) == pytest.approx(9.6, abs=1e-12)

"""Linear xTB-to-reference calibration utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LinearCalibration:
    """Linear calibration ``y_reference = slope * x_prediction + intercept``.

    Attributes:
        slope: Multiplicative correction factor, dimensionless.
        intercept: Additive correction in the same unit as y.
        r2: Coefficient of determination on the fit data, dimensionless.
        mae: Mean absolute error on the fit data in the same unit as y.
    """

    slope: float
    intercept: float
    r2: float
    mae: float

    def apply(self, x: float | np.ndarray) -> float | np.ndarray:
        """Apply the linear calibration to a scalar or numpy array."""

        return self.slope * x + self.intercept


def fit_linear_calibration(x: np.ndarray, y: np.ndarray) -> LinearCalibration:
    """Fit a least-squares linear calibration from cheap predictions to references."""

    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if x_values.shape != y_values.shape:
        raise ValueError("x and y must have the same shape")
    if x_values.ndim != 1:
        raise ValueError("x and y must be one-dimensional")
    if len(x_values) < 2:
        raise ValueError("at least two calibration points are required")

    design = np.column_stack([x_values, np.ones_like(x_values)])
    slope, intercept = np.linalg.lstsq(design, y_values, rcond=None)[0]
    predicted = slope * x_values + intercept
    residuals = predicted - y_values
    mae = float(np.mean(np.abs(residuals)))
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y_values - np.mean(y_values)) ** 2))
    r2 = 1.0 if ss_tot == 0.0 and ss_res == 0.0 else 1.0 - ss_res / ss_tot
    return LinearCalibration(
        slope=float(slope),
        intercept=float(intercept),
        r2=float(r2),
        mae=mae,
    )

"""Calibration models for mapping lower-tier predictions to references."""

from eps.calibration.linear import LinearCalibration, fit_linear_calibration

__all__ = ["LinearCalibration", "fit_linear_calibration"]

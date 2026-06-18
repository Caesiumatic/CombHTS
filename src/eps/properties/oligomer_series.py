"""Oligomer Eox-vs-chain-length descriptor (REPORTED ONLY; additive).

RATIONALE (directive): the monomer oxidation potential overestimates the oxidation potential of
the actual growing/polymerizing species, which DROPS as the conjugation length increases. This
module reports the raw xTB adiabatic ionization energy of the assembled n-mer for a configurable
set of lengths, plus a classic 1/n extrapolation to the infinite-chain ("polymer") limit.

This is a DESCRIPTOR ONLY: nothing here enters any hard Tier-1 filter or the composite score, so
survivor counts and composite scores are unchanged.

HONESTY ON EXTRAPOLATION (Zade & Bendikov, Org. Lett. 2006 / Acc. Chem. Res. 2011; band-gap
review §A.2): a naive LINEAR 1/n extrapolation from SHORT oligomers (n<=6) is unreliable — the
property saturates and deviates below the 1/n line, and reliable convergence needs >=20-mers or
periodic boundary conditions. We therefore report BOTH a linear 1/n fit and a 2nd-order
polynomial 1/n fit, but NEITHER extrapolated value may be presented as a converged polymer Eox.
The DURABLE screening signal is the per-n RAW Eox trend and the longest available (n=6) raw Eox;
the extrapolations are flagged non-converged (``oligomer_Eox_extrap_caveat``) and the calibrated
infinite value is additionally flagged out-of-domain (the pinned monomer calibration was NOT fit
on oligomers).
"""

from __future__ import annotations

import numpy as np

from eps.calibration import fit_linear_calibration
from eps.chemspace.models import Monomer
from eps.engines.base import Engine
from eps.properties.calculators import oligomer_eox_raw_eV, oligomer_eox_sidechain_truncated
from eps.properties.redox import ip_eV_to_potential_vs_AgAgCl
from eps.storage.cache import SQLiteCache
from eps.structures.oligomer import PolymerizationSpec

DEFAULT_EOX_OLIGOMER_LENGTHS = (2, 3, 4, 6)
MONOMER_ANCHOR_N = 1
EXTRAP_CAVEAT = (
    "non-converged: naive 1/n from short oligomers; true convergence needs >=20-mer or PBC"
)


def extrapolate_infinite_chain(eox_by_n: dict[int, float]) -> tuple[float, float]:
    """Classic LINEAR 1/n extrapolation of raw Eox to the infinite-chain limit.

    Fits ``Eox(n) = slope * (1/n) + intercept`` over the finite points; the infinite-chain value
    is the intercept (the 1/n -> 0 limit) and the returned r2 is the fit quality. Returns
    ``(nan, nan)`` when fewer than two finite points are available.

    NOTE: from short oligomers (n<=6) this linear estimate is NOT a converged polymer value (see
    module docstring); pair it with the poly2 estimate and treat both as non-converged.
    """

    points = [(n, value) for n, value in eox_by_n.items() if value is not None and np.isfinite(value)]
    if len(points) < 2:
        return float("nan"), float("nan")
    x = np.array([1.0 / n for n, _ in points], dtype=float)
    y = np.array([value for _, value in points], dtype=float)
    fit = fit_linear_calibration(x, y)
    return float(fit.intercept), float(fit.r2)


def extrapolate_infinite_chain_poly2(eox_by_n: dict[int, float]) -> tuple[float, float]:
    """2nd-order polynomial 1/n extrapolation: ``Eox(1/n) = a*(1/n)^2 + b*(1/n) + c``.

    The infinite-chain estimate is ``c`` (the 1/n -> 0 limit). Zade, Zamoshchik & Bendikov
    (Acc. Chem. Res. 2011) recommend the quadratic-in-1/n fit over the naive linear one because
    the property saturates below the 1/n line for long chains. Needs >= 3 finite points (we have
    n in {1,2,3,4,6} = 5); returns ``(nan, nan)`` otherwise. Still non-converged from short
    oligomers — reported alongside the linear estimate, not as a converged polymer Eox.
    """

    points = [(n, value) for n, value in eox_by_n.items() if value is not None and np.isfinite(value)]
    if len(points) < 3:
        return float("nan"), float("nan")
    x = np.array([1.0 / n for n, _ in points], dtype=float)
    y = np.array([value for _, value in points], dtype=float)
    coeffs = np.polyfit(x, y, 2)
    infinite = float(np.polyval(coeffs, 0.0))  # value at 1/n = 0 == the constant term c
    predicted = np.polyval(coeffs, x)
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 if (ss_tot == 0.0 and ss_res == 0.0) else 1.0 - ss_res / ss_tot
    return infinite, float(r2)


def compute_oligomer_eox_series(
    monomer: Monomer,
    spec: PolymerizationSpec | None,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str,
    lengths: tuple[int, ...] = DEFAULT_EOX_OLIGOMER_LENGTHS,
    calibration: dict[str, float | bool] | None = None,
) -> dict[str, object]:
    """Return the per-monomer oligomer-Eox column dict (failure-tolerant; never raises).

    For each n in ``[1] + lengths`` the gas-phase raw xTB adiabatic IP (eV) is computed and
    cached; n=1 is the monomer anchor. A per-n failure is recorded and skipped — the series
    still extrapolates from whatever points survive (>= 2). The infinite-chain raw value is also
    passed through the pinned monomer calibration (projected to V vs Ag/AgCl first, then the
    linear correction) and flagged out-of-domain.
    """

    calibration = calibration or {"enabled": False, "slope": 1.0, "intercept": 0.0}
    requested = sorted({MONOMER_ANCHOR_N, *lengths})
    columns: dict[str, object] = {}

    if spec is None:
        for n in lengths:
            columns[f"oligomer_Eox_raw_n{n}"] = float("nan")
        columns[f"oligomer_Eox_raw_n{MONOMER_ANCHOR_N}"] = float("nan")
        return _finalize(
            columns,
            eox_by_n={},
            errors=["no polymerization spec for monomer"],
            truncated="",
            lengths=lengths,
            calibration=calibration,
            requested=requested,
        )

    eox_by_n: dict[int, float] = {}
    errors: list[str] = []
    for n in requested:
        try:
            value = float(oligomer_eox_raw_eV(monomer, engine, cache, method=method, spec=spec, n=n))
        except Exception as exc:  # noqa: BLE001 - one bad oligomer must never abort the monomer.
            value = float("nan")
            errors.append(f"n={n}: {_concise(exc)}")
        columns[f"oligomer_Eox_raw_n{n}"] = value
        if np.isfinite(value):
            eox_by_n[n] = value

    try:
        truncated: bool | str = oligomer_eox_sidechain_truncated(monomer, spec, max(requested))
    except Exception as exc:  # noqa: BLE001 - the flag is best-effort metadata.
        truncated = ""
        errors.append(f"truncation_flag: {_concise(exc)}")

    return _finalize(
        columns,
        eox_by_n=eox_by_n,
        errors=errors,
        truncated=truncated,
        lengths=lengths,
        calibration=calibration,
        requested=requested,
    )


def _finalize(
    columns: dict[str, object],
    *,
    eox_by_n: dict[int, float],
    errors: list[str],
    truncated: bool | str,
    lengths: tuple[int, ...],
    calibration: dict[str, float | bool],
    requested: list[int],
) -> dict[str, object]:
    infinite_raw, r2 = extrapolate_infinite_chain(eox_by_n)
    infinite_raw_poly2, poly2_r2 = extrapolate_infinite_chain_poly2(eox_by_n)

    if np.isfinite(infinite_raw):
        # Project the raw infinite-chain IP (eV) to the V-vs-Ag/AgCl descriptor (the domain the
        # pinned monomer calibration was fit on), THEN apply the linear correction.
        descriptor_V = ip_eV_to_potential_vs_AgAgCl(infinite_raw)
        calibrated_V = float(calibration["slope"]) * descriptor_V + float(calibration["intercept"])
    else:
        calibrated_V = float("nan")

    n_points = len(eox_by_n)
    if n_points >= len(requested) and not errors:
        status = "ok"
    elif n_points >= 2:
        status = "partial"
    else:
        status = "failed"

    columns.update(
        {
            "oligomer_Eox_lengths": "|".join(str(n) for n in lengths),
            "oligomer_Eox_fit_n_points": n_points,
            "oligomer_Eox_infinite_raw_eV": infinite_raw,
            "oligomer_Eox_extrap_r2": r2,
            # 2nd-order polynomial 1/n fit (>=3 pts); Zade/Bendikov-recommended over the linear one.
            "oligomer_Eox_infinite_raw_poly2_eV": infinite_raw_poly2,
            "oligomer_Eox_poly2_r2": poly2_r2,
            "oligomer_Eox_infinite_calibrated_V_vs_AgAgCl": calibrated_V,
            # The monomer-fit calibration was NOT fit on oligomers: always out-of-domain.
            "oligomer_Eox_calibration_out_of_domain": True,
            # Neither extrapolation is a converged polymer Eox from short oligomers.
            "oligomer_Eox_extrap_caveat": EXTRAP_CAVEAT,
            "oligomer_Eox_sidechain_truncated": truncated,
            "oligomer_Eox_calc_status": status,
            "oligomer_Eox_calc_error": "; ".join(errors)[:240],
        }
    )
    return columns


def _concise(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:160]

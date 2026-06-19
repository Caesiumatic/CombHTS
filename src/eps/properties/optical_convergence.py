"""Directive §4.2 oligomer band-gap convergence check — additive, reported-only.

Computes the optical gap (sTDA-xTB when available, else the GFN2-xTB HOMO–LUMO proxy on the
assembled n-mer) at increasing oligomer length n=1..6 per monomer, and reports the
last-step convergence delta |gap(n_max) − gap(n_max−1)| against a threshold (directive §4.2:
verify convergence at n≈4–6 for D–A, n≈6 for homopolymers). PURELY REPORTED: none of these
columns enters a hard filter or the composite score. Reuses the existing oligomer assembly +
side-chain truncation + optical-gap calculation; per-monomer, cached, failure-tolerant.
"""

from __future__ import annotations

from eps.engines.base import Engine
from eps.properties.calculators import polymer_optical_gap
from eps.storage.cache import SQLiteCache
from eps.structures.oligomer import PolymerizationSpec

DEFAULT_CONVERGENCE_LENGTHS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
DEFAULT_CONVERGENCE_THRESHOLD_EV = 0.1


def _concise(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:240]


def compute_optical_gap_convergence(
    monomer,
    spec: PolymerizationSpec | None,
    engine: Engine,
    cache: SQLiteCache,
    *,
    method: str,
    lengths: tuple[int, ...] = DEFAULT_CONVERGENCE_LENGTHS,
    threshold_eV: float = DEFAULT_CONVERGENCE_THRESHOLD_EV,
) -> dict[str, object]:
    """Per-monomer optical gap at each n in ``lengths`` + last-step convergence delta/flag.

    Returns ``optical_gap_n{n}_eV`` for each n, ``optical_gap_convergence_delta_eV`` =
    |gap(largest) − gap(second-largest)|, ``optical_gap_converged`` (delta ≤ threshold), plus
    a status/error. The n=6 gap reuses the same cache key as the main ``optical_gap_eV`` axis,
    so it is not recomputed. Reported-only, screening-grade (uncalibrated vs TD-DFT).
    """

    ordered = sorted(set(int(n) for n in lengths if int(n) >= 1))
    gaps: dict[int, float] = {}
    errors: list[str] = []

    if spec is None:
        result: dict[str, object] = {f"optical_gap_n{n}_eV": float("nan") for n in ordered}
        result.update(
            {
                "optical_gap_convergence_delta_eV": float("nan"),
                "optical_gap_converged": "",
                "optical_gap_convergence_threshold_eV": threshold_eV,
                "optical_gap_convergence_lengths": "|".join(str(n) for n in ordered),
                "optical_gap_convergence_calc_status": "failed",
                "optical_gap_convergence_calc_error": "no polymerization spec for monomer",
            }
        )
        return result

    for n in ordered:
        try:
            gaps[n] = float(
                polymer_optical_gap(monomer, engine, cache, method=method, spec=spec, n=n)
            )
        except Exception as exc:  # noqa: BLE001 - one bad length must not abort the series.
            gaps[n] = float("nan")
            errors.append(f"n{n}: {_concise(exc)}")

    delta = float("nan")
    converged: object = ""
    finite = [n for n in ordered if gaps[n] == gaps[n]]  # drop NaN  # noqa: PLR0124
    if len(finite) >= 2:
        last, prev = finite[-1], finite[-2]
        delta = abs(gaps[last] - gaps[prev])
        converged = bool(delta <= threshold_eV)

    result = {f"optical_gap_n{n}_eV": gaps[n] for n in ordered}
    result.update(
        {
            "optical_gap_convergence_delta_eV": delta,
            "optical_gap_converged": converged,
            "optical_gap_convergence_threshold_eV": threshold_eV,
            "optical_gap_convergence_lengths": "|".join(str(n) for n in ordered),
            "optical_gap_convergence_calc_status": "ok" if not errors else "failed",
            "optical_gap_convergence_calc_error": "; ".join(errors),
        }
    )
    return result

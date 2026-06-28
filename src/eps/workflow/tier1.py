"""Tier-1 mock workflow: per-species calculations, triad join, filters, scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml

from eps.chemspace import (
    Electrolyte,
    Monomer,
    Solvent,
    load_electrolytes,
    load_monomers,
    load_solvents,
)
from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.properties import (
    anion_oxidation_potential,
    dimerization_dG,
    monomer_eox_vs_AgAgCl,
    monomer_solvation,
    load_cosmors_solvation_table,
    optical_gap_oligomer,
    polymer_optical_gap,
    polymer_optical_gap_method,
    solvent_anodic_limit,
    solvent_anodic_limit_csv,
    solvent_cathodic_limit,
    solvent_cathodic_limit_csv,
)
from eps.properties.oligomer_series import (
    DEFAULT_EOX_OLIGOMER_LENGTHS,
    compute_oligomer_eox_series,
)
from eps.properties.optical_convergence import (
    DEFAULT_CONVERGENCE_LENGTHS,
    DEFAULT_CONVERGENCE_THRESHOLD_EV,
    compute_optical_gap_convergence,
)
from eps.properties.secondary_descriptors import (
    anion_vdw_volume_descriptors,
    cation_reduction_descriptors,
    ionpair_descriptors,
    monomer_secondary_descriptors,
    solvent_secondary_descriptors,
)
from eps.properties.solvent_windows import (
    apply_condition_aware_solvent_windows,
    load_solvent_window_measurements,
)
from eps.scoring import add_composite_score, collapse_cation_degenerate_rows, load_scoring_config
from eps.storage import SQLiteCache
from eps.structures.geometry import (
    ConformerSearchConfig,
    conformer_method_suffix,
    conformer_search_active,
)
from eps.structures.oligomer import (
    DEFAULT_OLIGOMER_N,
    DIMER_N,
    PolymerizationSpec,
    load_polymerization_specs,
    oligomer_smiles,
    write_building_block_artifact,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIER1_CONFIG = PROJECT_ROOT / "configs" / "tier1.yaml"
DEFAULT_SCORING_CONFIG = PROJECT_ROOT / "configs" / "scoring.yaml"
DEFAULT_CACHE_PATH = PROJECT_ROOT / "outputs" / "tier1_cache.sqlite"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "tier1_ranked.csv"


@dataclass(frozen=True)
class Tier1Result:
    """Tier-1 workflow outputs and retention statistics."""

    ranked: pd.DataFrame
    all_triads: pd.DataFrame
    total_triads: int
    surviving_triads: int
    retention_fraction: float
    output_path: Path
    all_output_path: Path
    cache_path: Path


DEFAULT_MAX_TRIADS = 12000


class ScaleGuardError(RuntimeError):
    """Raised when a run would exceed the freeze-then-scale triad/task ceiling."""


def enforce_scale_guard(
    n_units: int,
    *,
    max_units: int = DEFAULT_MAX_TRIADS,
    allow_large_scale: bool = False,
    kind: str = "Tier-1 triads",
) -> None:
    """Block an accidental full-scale (~50k) launch unless explicitly authorized.

    freeze-then-scale (AGENTS.md / directive §2, §0): the full ~50,000-triad Tier-1 harvest and the
    full Tier-2 DFT batch are method-frozen, sign-off-gated actions. A swapped or expanded library
    CSV must never silently trigger them. Exceeding ``max_units`` requires an explicit
    ``allow_large_scale`` (CLI ``--allow-large-scale``) — the documented full-scale switch.
    """

    if not allow_large_scale and n_units > max_units:
        raise ScaleGuardError(
            f"{kind} count {n_units} exceeds the scale-guard ceiling {max_units}. This looks like a "
            "full-scale run, which is freeze-then-scale gated (AGENTS.md / directive §2 and §0): "
            "freeze every per-species method first, then re-run with --allow-large-scale (or raise "
            "scale_guard.max_triads in configs/tier1.yaml) to explicitly authorize it."
        )


def run_tier1(
    *,
    engine: Engine | None = None,
    method: str = "mock-gfn2",
    cache_path: str | Path = DEFAULT_CACHE_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    all_output_path: str | Path | None = None,
    tier1_config_path: str | Path = DEFAULT_TIER1_CONFIG,
    scoring_config_path: str | Path = DEFAULT_SCORING_CONFIG,
    allow_large_scale: bool = False,
) -> Tier1Result:
    """Run Tier-1 over seed libraries with per-species cached MockEngine calls."""

    engine = engine or MockEngine()
    cache = SQLiteCache(cache_path)
    monomers = load_monomers()
    solvents = load_solvents()
    electrolytes = load_electrolytes()
    tier1_config = load_tier1_config(tier1_config_path)
    scale_guard_cfg = tier1_config.get("scale_guard", {}) or {}
    enforce_scale_guard(
        len(monomers) * len(solvents) * len(electrolytes),
        max_units=int(scale_guard_cfg.get("max_triads", DEFAULT_MAX_TRIADS)),
        allow_large_scale=allow_large_scale,
        kind="Tier-1 triads",
    )
    solvent_window_config = tier1_config.get("solvent_window_gate", {}) or {}
    solvent_window_measurements = None
    if bool(solvent_window_config.get("enabled", False)):
        window_path = Path(
            solvent_window_config.get("measurements_path", "data/solvent_windows.csv")
        )
        if not window_path.is_absolute():
            window_path = PROJECT_ROOT / window_path
        solvent_window_measurements = load_solvent_window_measurements(window_path)

    # Decoupled openCOSMO-RS ΔGsolv table (directive §4.1, COSMO-RS). Read cosmors-first; the screen
    # falls back to the ALPB ΔGsolv proxy for any (monomer, solvent) absent from the table. Loading an
    # empty/missing table is the safe default (pure-ALPB behaviour, e.g. mock tests).
    # Only for a REAL engine: the cosmors ΔGsolv values are physical, so mixing them with MockEngine's
    # synthetic Eox would make the mock end-to-end tests inconsistent. MockEngine stays pure-mock (ALPB).
    solvation_config = tier1_config.get("solvation", {}) or {}
    solvation_table: dict[tuple[str, str], float] = {}
    if bool(solvation_config.get("prefer_cosmors", False)) and not isinstance(engine, MockEngine):
        cosmors_path = Path(solvation_config.get("cosmors_table_path", "data/solvation_cosmors.csv"))
        if not cosmors_path.is_absolute():
            cosmors_path = PROJECT_ROOT / cosmors_path
        solvation_table = load_cosmors_solvation_table(cosmors_path)

    oligomer_config = tier1_config.get("oligomer", {})
    oligomer_n = int(oligomer_config.get("n", DEFAULT_OLIGOMER_N))
    dimer_n = int(oligomer_config.get("dimer_n", DIMER_N))
    eox_oligomer_lengths = _eox_oligomer_lengths(oligomer_config)
    secondary_on = bool(tier1_config.get("secondary_descriptors", {}).get("enabled", False))
    bandgap_convergence = tier1_config.get("bandgap_convergence", {})
    # Directive §4.1 conformer search (config-toggleable; CHANGES geometries, not additive). The
    # setting is folded into the cache-key method so a single-conformer cache is never reused, and
    # scoped onto geometry generation via the context manager below (the real xTB path reads it
    # through smiles_to_xyz; MockEngine ignores geometry, so only the method-suffix matters there).
    conformer_cfg = _conformer_search_config(tier1_config)
    method = method + conformer_method_suffix(conformer_cfg)
    polymerization_specs = load_polymerization_specs()
    with conformer_search_active(conformer_cfg):
        monomer_table = compute_monomer_table(
            monomers, engine, cache, method=method,
            oligomer_n=oligomer_n, dimer_n=dimer_n, specs=polymerization_specs,
            eox_oligomer_lengths=eox_oligomer_lengths,
            calibration_config=tier1_config.get("calibration", {}),
            secondary_descriptors=secondary_on,
            bandgap_convergence=bandgap_convergence,
        )
        monomer_solvent_table = compute_monomer_solvent_table(
            monomers,
            solvents,
            engine,
            cache,
            method=method,
            calibration_config=tier1_config.get("calibration", {}),
            solvation_table=solvation_table,
        )
        solvent_table = compute_solvent_table(
            solvents,
            engine,
            cache,
            method=method,
            calibration_config=tier1_config.get("calibration", {}),
            secondary_descriptors=secondary_on,
        )
        anion_table = compute_anion_solvent_table(
            electrolytes,
            solvents,
            engine,
            cache,
            method=method,
            calibration_config=tier1_config.get("calibration", {}),
            secondary_descriptors=secondary_on,
        )
        cation_table = (
            compute_cation_solvent_table(electrolytes, solvents, engine, cache, method=method)
            if secondary_on else None
        )
        pair_table = (
            compute_electrolyte_pair_table(electrolytes, engine, cache, method=method)
            if secondary_on else None
        )

    triads = build_triad_table(
        monomer_table=monomer_table,
        monomer_solvent_table=monomer_solvent_table,
        solvent_table=solvent_table,
        anion_table=anion_table,
        electrolytes=electrolytes,
        cation_table=cation_table,
        pair_table=pair_table,
        solvent_window_measurements=solvent_window_measurements,
        solvent_window_config=solvent_window_config,
    )
    all_triads = annotate_tier1_filters(triads, tier1_config)
    filtered = apply_tier1_filters(all_triads, tier1_config)
    scored_survivors = add_composite_score(filtered, load_scoring_config(scoring_config_path))
    all_triads = attach_scoring_columns(all_triads, scored_survivors)
    ranked = collapse_cation_degenerate_rows(scored_survivors)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(output, index=False)

    all_output = Path(all_output_path) if all_output_path is not None else infer_all_output_path(output)
    all_output.parent.mkdir(parents=True, exist_ok=True)
    all_triads.to_csv(all_output, index=False)

    # Verification artifact: human-reviewable per-monomer coupling chemistry + assembled SMILES.
    try:
        write_building_block_artifact(
            monomers, polymerization_specs, oligomer_n, output.parent / "oligomer_buildingblocks.csv"
        )
    except Exception:  # noqa: BLE001 - the artifact must never break the screen.
        pass

    # Verification artifact: human-reviewable per-monomer oligomer Eox-vs-length series.
    try:
        write_oligomer_eox_series_artifact(
            monomer_table, eox_oligomer_lengths, output.parent / "oligomer_eox_series.csv"
        )
    except Exception:  # noqa: BLE001 - the reported-only descriptor must never break the screen.
        pass

    # Verification artifact: human-reviewable per-monomer §3 secondary descriptors.
    if secondary_on:
        try:
            write_secondary_descriptors_artifact(
                monomer_table, output.parent / "secondary_descriptors.csv"
            )
        except Exception:  # noqa: BLE001 - the reported-only descriptor must never break the screen.
            pass

    total = len(all_triads)
    # Survival is a hard-filter count over full per-salt rows; ranked is a de-duplicated view.
    survived = len(scored_survivors)
    retention = survived / total if total else 0.0
    return Tier1Result(
        ranked=ranked,
        all_triads=all_triads,
        total_triads=total,
        surviving_triads=survived,
        retention_fraction=retention,
        output_path=output,
        all_output_path=all_output,
        cache_path=Path(cache_path),
    )


def compute_monomer_table(
    monomers: list[Monomer],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    oligomer_n: int = DEFAULT_OLIGOMER_N,
    dimer_n: int = DIMER_N,
    specs: dict[str, PolymerizationSpec] | None = None,
    eox_oligomer_lengths: tuple[int, ...] = DEFAULT_EOX_OLIGOMER_LENGTHS,
    calibration_config: dict | None = None,
    secondary_descriptors: bool = False,
    bandgap_convergence: dict | None = None,
) -> pd.DataFrame:
    """Compute monomer-only properties once per monomer.

    The optical gap is now the sTDA-xTB (or HOMO–LUMO proxy) gap of the assembled n-mer
    oligomer, and dimerization is the real radical–radical coupling ΔG (directive §3.1/§4.2)
    — neither is a single-monomer placeholder any longer.

    Additionally reports the oligomer Eox-vs-length trend + 1/n infinite-chain extrapolation as
    a REPORTED descriptor (reused oligomer assembly + side-chain truncation). These columns are
    purely additive: none enters a hard filter or the composite score.
    """

    specs = specs if specs is not None else load_polymerization_specs()
    eox_calibration = _oxidation_calibration(calibration_config or {})
    rows = []
    for monomer in monomers:
        spec = specs.get(monomer.name)
        oligomer_eox_columns = compute_oligomer_eox_series(
            monomer, spec, engine, cache,
            method=method, lengths=eox_oligomer_lengths, calibration=eox_calibration,
        )
        if spec is None:
            optical_gap = _CalcOutcome(float("nan"), "failed", "no polymerization spec for monomer")
            dimerization = _CalcOutcome(float("nan"), "failed", "no polymerization spec for monomer")
            gap_method = "none"
            oligo_smiles = ""
            gap_truncated: bool | str = ""
        else:
            optical_gap = _safe_calculate(
                lambda: polymer_optical_gap(monomer, engine, cache, method=method, spec=spec, n=oligomer_n)
            )
            gap_method = _safe_str(
                lambda: polymer_optical_gap_method(monomer, engine, cache, method=method, spec=spec, n=oligomer_n)
            )
            try:
                oligo_smiles, gap_truncated = optical_gap_oligomer(monomer, spec, oligomer_n)
            except Exception as exc:  # noqa: BLE001 - keep audit metadata best-effort.
                oligo_smiles, gap_truncated = f"error: {_concise_error(exc)}", ""
            dimerization = _safe_calculate(
                lambda: dimerization_dG(monomer, engine, cache, method=method, spec=spec, dimer_n=dimer_n)
            )
        row = {
            "monomer_name": monomer.name,
            "monomer_class": monomer.monomer_class,
            "monomer_smiles": monomer.smiles,
            "monomer_canonical_smiles": monomer.canonical_smiles,
            "optical_gap_eV": optical_gap.value,
            "optical_gap_method": gap_method,
            "optical_gap_oligomer_n": oligomer_n,
            "optical_gap_oligomer_smiles": oligo_smiles,
            "optical_gap_sidechain_truncated": gap_truncated,
            "optical_gap_coupling_approximate": bool(spec.approximate) if spec else "",
            "optical_gap_calc_status": optical_gap.status,
            "optical_gap_calc_error": optical_gap.error,
            "dimerization_dG_kcal_mol": dimerization.value,
            "dimerization_reaction": "2 M+. -> M-M(neutral) + 2 H+ (xTB dG, screening-grade)",
            "dimerization_dimer_smiles": (
                _safe_str(lambda: oligomer_smiles(monomer.canonical_smiles, spec, dimer_n)) if spec else ""
            ),
            "dimerization_coupling_approximate": bool(spec.approximate) if spec else "",
            "dimerization_calc_status": dimerization.status,
            "dimerization_calc_error": dimerization.error,
        }
        # Additive, reported-only oligomer Eox-vs-length descriptor (NOT a filter / score input).
        row.update(oligomer_eox_columns)
        # Additive, reported-only §3.1 secondary descriptors (frontier orbitals, cation spin,
        # vertical IP / reorganization). NOT a filter / score input.
        if secondary_descriptors:
            row.update(monomer_secondary_descriptors(monomer, engine, cache, method=method))
        # Additive, reported-only §4.2 oligomer band-gap convergence (optical gap at n=1..6).
        # NOT a filter / score input.
        if bandgap_convergence and bool(bandgap_convergence.get("enabled", False)):
            row.update(
                compute_optical_gap_convergence(
                    monomer, spec, engine, cache, method=method,
                    lengths=_convergence_lengths(bandgap_convergence),
                    threshold_eV=float(
                        bandgap_convergence.get("threshold_eV", DEFAULT_CONVERGENCE_THRESHOLD_EV)
                    ),
                )
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _convergence_lengths(config: dict) -> tuple[int, ...]:
    """Read the §4.2 band-gap convergence lengths from config (default 1..6)."""

    raw = config.get("lengths", list(DEFAULT_CONVERGENCE_LENGTHS))
    try:
        lengths = tuple(int(n) for n in raw if int(n) >= 1)
    except (TypeError, ValueError):
        return DEFAULT_CONVERGENCE_LENGTHS
    return lengths or DEFAULT_CONVERGENCE_LENGTHS


def compute_monomer_solvent_table(
    monomers: list[Monomer],
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
    solvation_table: dict[tuple[str, str], float] | None = None,
) -> pd.DataFrame:
    """Compute monomer-in-solvent properties over monomer x solvent pairs.

    Solvation ΔGsolv is read **cosmors-first** from ``solvation_table`` (the precomputed decoupled
    openCOSMO-RS values, directive §4.1) when the (monomer, solvent) pair is present; otherwise it
    falls back to the ALPB ΔGsolv affinity proxy via ``monomer_solvation`` (measured-first discipline).
    """

    solvation_table = solvation_table or {}
    eox_calibration = _oxidation_calibration(calibration_config or {})
    rows = []
    for monomer in monomers:
        for solvent in solvents:
            eox = _safe_calculate(
                lambda: monomer_eox_vs_AgAgCl(
                    monomer,
                    solvent,
                    engine,
                    cache,
                    method=method,
                )
            )
            if eox.status == "ok":
                raw_eox = eox.value
                calibrated_eox = _apply_linear_calibration(raw_eox, eox_calibration)
                filter_eox = calibrated_eox if eox_calibration["enabled"] else raw_eox
            else:
                raw_eox = float("nan")
                calibrated_eox = float("nan")
                filter_eox = float("nan")
            cosmors_dG = solvation_table.get((monomer.canonical_smiles, solvent.name))
            if cosmors_dG is not None:
                solvation = _CalcOutcome(value=cosmors_dG, status="ok", error="")
                solvation_source = "opencosmors_csv"
            else:
                solvation = _safe_calculate(
                    lambda: monomer_solvation(
                        monomer,
                        solvent,
                        engine,
                        cache,
                        method=method,
                    )
                )
                solvation_source = "alpb_fallback"
            rows.append(
                {
                    "monomer_canonical_smiles": monomer.canonical_smiles,
                    "solvent_name": solvent.name,
                    "solvent_eps_r": solvent.eps_r,
                    "monomer_Eox_raw_V_vs_AgAgCl": raw_eox,
                    "monomer_Eox_calibrated_V_vs_AgAgCl": calibrated_eox,
                    "monomer_Eox_filter_V_vs_AgAgCl": filter_eox,
                    # Deprecated ambiguous alias; prefer the explicit raw/calibrated/filter columns.
                    "monomer_Eox_V": filter_eox,
                    "monomer_Eox_calc_status": eox.status,
                    "monomer_Eox_calc_error": eox.error,
                    "solvation_dG_kcal_mol": solvation.value,
                    "solvation_dG_source": solvation_source,
                    "solvation_calc_status": solvation.status,
                    "solvation_calc_error": solvation.error,
                }
            )
    return pd.DataFrame(rows)


def compute_solvent_table(
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
    secondary_descriptors: bool = False,
) -> pd.DataFrame:
    """Compute solvent anodic/cathodic limits per spec §3.2 once per solvent.

    The anodic and cathodic limits are computed via the cached engine (adiabatic ΔSCF
    oxidation/reduction of the solvent molecule in its own implicit solvent). If a calc
    fails, the row falls back to the stopgap CSV value so one solvent does not abort the
    screen. ``solvent_anodic_limit_V`` is the value used downstream.

    The shared oxidation calibration (T11) is applied to the ANODIC limit only (an
    oxidation potential); the CATHODIC limit is a reduction potential and stays raw.
    Calibration defaults to disabled when ``calibration_config`` is None, so direct
    callers/tests get raw computed values.
    """

    cal = _oxidation_calibration(calibration_config or {})
    rows = []
    for solvent in solvents:
        anodic = _safe_calculate(
            lambda: solvent_anodic_limit(solvent, engine, cache, method=method)
        )
        cathodic = _safe_calculate(
            lambda: solvent_cathodic_limit(solvent, engine, cache, method=method)
        )
        anodic_csv = solvent_anodic_limit_csv(solvent)
        cathodic_csv = solvent_cathodic_limit_csv(solvent)
        if anodic.status == "ok":
            anodic_calibrated = _apply_linear_calibration(anodic.value, cal)
            anodic_used = anodic_calibrated if cal["enabled"] else anodic.value
            anodic_source = "computed"
        else:
            # CSV stopgap is already in realistic units; do NOT calibrate it.
            anodic_calibrated = float("nan")
            anodic_used = anodic_csv
            anodic_source = "csv_fallback"
        cathodic_used = cathodic.value if cathodic.status == "ok" else cathodic_csv
        rows.append(
            {
                "solvent_name": solvent.name,
                "solvent_smiles": solvent.smiles,
                "solvent_canonical_smiles": solvent.canonical_smiles,
                "solvent_anodic_limit_computed_V": anodic.value,
                "solvent_anodic_limit_calibrated_V": anodic_calibrated,
                "solvent_anodic_limit_csv_V": anodic_csv,
                "solvent_anodic_limit_V": anodic_used,
                "solvent_anodic_limit_source": anodic_source,
                "solvent_anodic_limit_calc_status": anodic.status,
                "solvent_anodic_limit_calc_error": anodic.error,
                "solvent_cathodic_limit_computed_V": cathodic.value,
                "solvent_cathodic_limit_csv_V": cathodic_csv,
                "solvent_cathodic_limit_V": cathodic_used,
                "solvent_cathodic_limit_source": "computed" if cathodic.status == "ok" else "csv_fallback",
                "solvent_cathodic_limit_calc_status": cathodic.status,
                "solvent_cathodic_limit_calc_error": cathodic.error,
            }
        )
        # Additive, reported-only §3.2 secondary descriptors (oxidation/reduction reorganization).
        if secondary_descriptors:
            rows[-1].update(solvent_secondary_descriptors(solvent, engine, cache, method=method))
    return pd.DataFrame(rows)


def compute_anion_solvent_table(
    electrolytes: list[Electrolyte],
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
    calibration_config: dict | None = None,
    secondary_descriptors: bool = False,
) -> pd.DataFrame:
    """Compute anion-in-solvent oxidation potentials once per unique anion x solvent.

    The shared oxidation calibration (T11) is applied to the anion Eox, mirroring the
    monomer raw/calibrated/filter pattern. Calibration defaults to disabled when
    ``calibration_config`` is None. On a failed calc all three value columns are NaN
    (no CSV fallback for anions, mirroring monomer behavior).
    """

    cal = _oxidation_calibration(calibration_config or {})
    unique_by_anion = {electrolyte.canonical_anion_smiles: electrolyte for electrolyte in electrolytes}
    rows = []
    for electrolyte in unique_by_anion.values():
        # §3.3 anion vdW volume is solvent-independent: compute once per anion, repeat across rows.
        volume_columns = anion_vdw_volume_descriptors(electrolyte) if secondary_descriptors else {}
        for solvent in solvents:
            anion_eox = _safe_calculate(
                lambda: anion_oxidation_potential(
                    electrolyte,
                    solvent,
                    engine,
                    cache,
                    method=method,
                )
            )
            if anion_eox.status == "ok":
                raw_anion = anion_eox.value
                calibrated_anion = _apply_linear_calibration(raw_anion, cal)
                filter_anion = calibrated_anion if cal["enabled"] else raw_anion
            else:
                raw_anion = float("nan")
                calibrated_anion = float("nan")
                filter_anion = float("nan")
            rows.append(
                {
                    "anion_canonical_smiles": electrolyte.canonical_anion_smiles,
                    "solvent_name": solvent.name,
                    "anion_Eox_raw_V_vs_AgAgCl": raw_anion,
                    "anion_Eox_calibrated_V_vs_AgAgCl": calibrated_anion,
                    "anion_Eox_filter_V_vs_AgAgCl": filter_anion,
                    # Backward-compat alias; equals the filter value used downstream.
                    "anion_Eox_V": filter_anion,
                    "anion_Eox_calc_status": anion_eox.status,
                    "anion_Eox_calc_error": anion_eox.error,
                    **volume_columns,
                }
            )
    return pd.DataFrame(rows)


def compute_cation_solvent_table(
    electrolytes: list[Electrolyte],
    solvents: list[Solvent],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
) -> pd.DataFrame:
    """Per-(unique cation x solvent) §3.3 cation reduction potential (RAW V vs Ag/AgCl).

    Mirrors the anion table's granularity. RAW (a reduction potential — deliberately NOT on the
    oxidation calibration per T11). Reported-only, screening-grade.
    """

    unique_by_cation = {e.canonical_cation_smiles: e for e in electrolytes}
    rows = []
    for electrolyte in unique_by_cation.values():
        for solvent in solvents:
            rows.append(
                {
                    "cation_canonical_smiles": electrolyte.canonical_cation_smiles,
                    "solvent_name": solvent.name,
                    **cation_reduction_descriptors(electrolyte, solvent, engine, cache, method=method),
                }
            )
    return pd.DataFrame(rows)


def compute_electrolyte_pair_table(
    electrolytes: list[Electrolyte],
    engine: Engine,
    cache: SQLiteCache,
    method: str = "mock-gfn2",
) -> pd.DataFrame:
    """Per-salt §3.3 ion-pair dissociation ΔG (ALPB-proxy, APPROXIMATE). Reported-only."""

    rows = []
    for electrolyte in electrolytes:
        rows.append(
            {
                "salt": electrolyte.salt,
                **ionpair_descriptors(electrolyte, engine, cache, method=method),
            }
        )
    return pd.DataFrame(rows)


def build_triad_table(
    *,
    monomer_table: pd.DataFrame,
    monomer_solvent_table: pd.DataFrame,
    solvent_table: pd.DataFrame,
    anion_table: pd.DataFrame,
    electrolytes: list[Electrolyte],
    cation_table: pd.DataFrame | None = None,
    pair_table: pd.DataFrame | None = None,
    solvent_window_measurements: pd.DataFrame | None = None,
    solvent_window_config: dict | None = None,
) -> pd.DataFrame:
    """Build all monomer x solvent x electrolyte triads by joining precomputed tables.

    ``cation_table`` (per cation x solvent) and ``pair_table`` (per salt) carry the additive,
    reported-only §3.3 secondary descriptors; both are optional and, when None, the join is
    byte-for-byte the original triad build (so the secondary descriptors are strictly additive).
    """

    electrolyte_table = pd.DataFrame(
        [
            {
                "salt": electrolyte.salt,
                "salt_class": electrolyte.salt_class,
                "cation_smiles": electrolyte.cation_smiles,
                "anion_smiles": electrolyte.anion_smiles,
                "anion_canonical_smiles": electrolyte.canonical_anion_smiles,
                "cation_canonical_smiles": electrolyte.canonical_cation_smiles,
                "electrolyte_role": electrolyte.electrolyte_role,
                "supporting_electrolyte_ok": electrolyte.supporting_electrolyte_ok,
                "electrolyte_role_justification": electrolyte.electrolyte_role_justification,
            }
            for electrolyte in electrolytes
        ]
    )
    if pair_table is not None:
        electrolyte_table = electrolyte_table.merge(
            pair_table, on="salt", how="left", validate="many_to_one"
        )
    electrolyte_props = electrolyte_table.merge(
        anion_table,
        on="anion_canonical_smiles",
        how="left",
        validate="many_to_many",
    )
    if cation_table is not None:
        electrolyte_props = electrolyte_props.merge(
            cation_table,
            on=["cation_canonical_smiles", "solvent_name"],
            how="left",
            validate="many_to_one",
        )
    triads = (
        monomer_solvent_table.merge(
            monomer_table,
            on="monomer_canonical_smiles",
            how="left",
            validate="many_to_one",
        )
        .merge(solvent_table, on="solvent_name", how="left", validate="many_to_one")
        .merge(electrolyte_props, on="solvent_name", how="left", validate="many_to_many")
    )
    if solvent_window_measurements is not None:
        window_config = solvent_window_config or {}
        triads = apply_condition_aware_solvent_windows(
            triads,
            solvent_window_measurements,
            policy=str(window_config.get("policy", "measured_first_conservative")),
            fallback_policy=str(window_config.get("fallback_policy", "min_csv_computed")),
        )
    triads["window_margin_V"] = (
        triads["solvent_anodic_limit_V"] - triads["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    # Anion Eox is now on the shared oxidation calibration (T11); the intercept cancels in
    # this margin, so the filter is governed by raw IP differences (extrapolated, screening-grade).
    triads["anion_stability_margin_V"] = (
        triads["anion_Eox_filter_V_vs_AgAgCl"] - triads["monomer_Eox_filter_V_vs_AgAgCl"]
    )
    triads["solubility_score"] = -triads["solvation_dG_kcal_mol"]
    # Reported-only §3.3 flag: the cation reduces at a less-negative potential than the solvent
    # cathodic edge (i.e. the cation may be reduced inside the solvent window). NOT a filter.
    # IMPORTANT: this molecular reduction descriptor does not model metal deposition/plating.
    # Role metadata currently guards reference-only and acid entries while a calibrated cation /
    # deposition model remains scientific debt; never interpret this flag as plating protection.
    if {"cation_reduction_raw_V_vs_AgAgCl", "solvent_cathodic_limit_V"}.issubset(triads.columns):
        triads["cation_reduction_below_solvent_cathodic"] = (
            triads["cation_reduction_raw_V_vs_AgAgCl"] > triads["solvent_cathodic_limit_V"]
        )
    return triads


TRIAD_IDENTITY_COLUMNS = ("monomer_name", "solvent_name", "salt")
SCORING_CARRY_COLUMNS = (
    "composite_score",
    "pareto_front",
    "band_gap_deviation_eV",
    "norm_window_margin",
    "norm_anion_stability",
    "norm_solubility",
    "norm_dimerization",
    "norm_band_gap",
)


def attach_scoring_columns(all_triads: pd.DataFrame, ranked: pd.DataFrame) -> pd.DataFrame:
    """Left-join the survivors' scoring columns onto the full all-triads table by triad identity.

    Survivor rows carry IDENTICAL scoring values to the ranked CSV; non-survivors get NaN
    (and ``pareto_front`` False). This does NOT recompute the Pareto front or any score — it
    only copies the values ``add_composite_score`` already produced for the survivors, so
    ``eps analyze`` can produce every §8 output from the single all-triads file.
    """

    key = [column for column in TRIAD_IDENTITY_COLUMNS if column in all_triads.columns]
    carry = [column for column in SCORING_CARRY_COLUMNS if column in ranked.columns]
    if not key or not carry:
        return all_triads

    merged = all_triads.merge(
        ranked.loc[:, key + carry],
        on=key,
        how="left",
        validate="one_to_one",
    )
    if "pareto_front" in merged.columns:
        merged["pareto_front"] = merged["pareto_front"].fillna(False).astype(bool)
    return merged


def annotate_tier1_filters(triads: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Annotate each triad with Tier-1 hard-filter pass/fail booleans and reasons."""

    filters = config["filters"]
    annotated = triads.copy()
    annotated["pass_window_margin"] = annotated["window_margin_V"] > float(filters["min_window_margin_V"])
    annotated["pass_anion_stability"] = annotated["anion_stability_margin_V"] > float(
        filters["min_anion_stability_margin_V"]
    )
    annotated["pass_solvation"] = annotated["solvation_dG_kcal_mol"] < float(
        filters["max_solvation_dG_kcal_mol"]
    )
    role_gate = config.get("supporting_electrolyte_gate", {}) or {}
    role_enabled = bool(role_gate.get("enabled", False))
    role_results = annotated.apply(
        lambda row: _supporting_electrolyte_gate_result(row, enabled=role_enabled),
        axis=1,
        result_type="expand",
    )
    role_results.columns = [
        "pass_supporting_electrolyte_role",
        "supporting_electrolyte_calc_status",
        "supporting_electrolyte_reason",
    ]
    annotated[role_results.columns] = role_results
    annotated["has_calculation_failure"] = annotated.apply(_has_calculation_failure, axis=1)
    annotated["passes_all_tier1_filters"] = (
        annotated["pass_window_margin"]
        & annotated["pass_anion_stability"]
        & annotated["pass_solvation"]
        & annotated["pass_supporting_electrolyte_role"]
        & ~annotated["has_calculation_failure"]
    )
    annotated["failed_filter_reasons"] = annotated.apply(_failed_filter_reasons, axis=1)
    return annotated


def apply_tier1_filters(triads: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Return only triads passing all hard Tier-1 filters."""

    if "passes_all_tier1_filters" not in triads.columns:
        triads = annotate_tier1_filters(triads, config)
    return triads.loc[triads["passes_all_tier1_filters"]].reset_index(drop=True)


def load_tier1_config(path: str | Path = DEFAULT_TIER1_CONFIG) -> dict:
    """Load Tier-1 hard-filter thresholds from YAML."""

    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _conformer_search_config(tier1_config: dict) -> ConformerSearchConfig:
    """Build the §4.1 conformer-search config from tier1.yaml (default single conformer)."""

    section = tier1_config.get("conformer_search", {}) or {}
    return ConformerSearchConfig(
        enabled=bool(section.get("enabled", False)),
        n_conformers=int(section.get("n_conformers", 1)),
        method=str(section.get("method", "mmff94")),
    )


def _eox_oligomer_lengths(oligomer_config: dict) -> tuple[int, ...]:
    """Read the oligomer-Eox series lengths from config (default [2, 3, 4, 6]).

    Reported-only descriptor; an absent/invalid key falls back to the default rather than
    breaking the screen. n=1 (the monomer anchor) is always added inside the calculator.
    """

    raw = oligomer_config.get("eox_oligomer_lengths", list(DEFAULT_EOX_OLIGOMER_LENGTHS))
    try:
        lengths = tuple(int(n) for n in raw if int(n) >= 1)
    except (TypeError, ValueError):
        return DEFAULT_EOX_OLIGOMER_LENGTHS
    return lengths or DEFAULT_EOX_OLIGOMER_LENGTHS


def write_oligomer_eox_series_artifact(
    monomer_table: pd.DataFrame,
    lengths: tuple[int, ...],
    output_path: str | Path,
) -> Path:
    """Write a human-reviewable per-monomer oligomer Eox series CSV (verification artifact).

    Analogous to ``outputs/oligomer_buildingblocks.csv``: the per-n raw Eox values, the 1/n
    extrapolated infinite-chain value, the fit r2, and the status — for human inspection.
    """

    n_columns = [f"oligomer_Eox_raw_n{n}" for n in sorted({1, *lengths})]
    columns = (
        ["monomer_name", "monomer_canonical_smiles"]
        + [c for c in n_columns if c in monomer_table.columns]
        + [
            c
            for c in (
                "oligomer_Eox_infinite_raw_eV",
                "oligomer_Eox_extrap_r2",
                "oligomer_Eox_infinite_raw_poly2_eV",
                "oligomer_Eox_poly2_r2",
                "oligomer_Eox_infinite_calibrated_V_vs_AgAgCl",
                "oligomer_Eox_calibration_out_of_domain",
                "oligomer_Eox_extrap_caveat",
                "oligomer_Eox_sidechain_truncated",
                "oligomer_Eox_calc_status",
                "oligomer_Eox_calc_error",
            )
            if c in monomer_table.columns
        ]
    )
    present = [c for c in columns if c in monomer_table.columns]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    monomer_table.loc[:, present].to_csv(out, index=False)
    return out


def write_secondary_descriptors_artifact(
    monomer_table: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Write the human-reviewable per-monomer §3.1 secondary descriptors (verification artifact)."""

    columns = [
        "monomer_name",
        "monomer_canonical_smiles",
        "monomer_HOMO_eV",
        "monomer_LUMO_eV",
        "monomer_HL_gap_eV",
        "monomer_vertical_IP_eV",
        "monomer_adiabatic_IP_eV",
        "monomer_lambda_ox_eV",
        "monomer_cation_max_spin",
        "monomer_cation_max_spin_atom_idx",
        "monomer_cation_max_spin_is_alpha",
        "monomer_cation_alpha_spin_sum",
        "secondary_monomer_calc_status",
        "secondary_monomer_calc_error",
    ]
    present = [c for c in columns if c in monomer_table.columns]
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    monomer_table.loc[:, present].to_csv(out, index=False)
    return out


def infer_all_output_path(output_path: str | Path) -> Path:
    """Infer the all-triads audit CSV path from the ranked output path."""

    output = Path(output_path)
    if output.name.endswith("_ranked.csv"):
        return output.with_name(output.name.removesuffix("_ranked.csv") + "_all.csv")
    return output.with_name(f"{output.stem}_all{output.suffix or '.csv'}")


def _oxidation_calibration(config: dict) -> dict[str, float | bool]:
    # Single oxidation calibration shared by monomer Eox, solvent anodic limit, and anion Eox (T11).
    monomer_config = config.get("monomer_eox", {})
    return {
        "enabled": bool(monomer_config.get("enabled", False)),
        "slope": float(monomer_config.get("slope", 1.0)),
        "intercept": float(monomer_config.get("intercept", 0.0)),
    }


def _apply_linear_calibration(raw_value: float, calibration: dict[str, float | bool]) -> float:
    return float(calibration["slope"]) * raw_value + float(calibration["intercept"])


def _failed_filter_reasons(row: pd.Series) -> str:
    reasons: list[str] = []
    failed_calculations = _failed_calculation_reasons(row)
    if failed_calculations:
        reasons.append("calculation_failed")
        reasons.extend(failed_calculations)
    if not bool(row["pass_window_margin"]):
        reasons.append("window_margin")
    if not bool(row["pass_anion_stability"]):
        reasons.append("anion_stability")
    if not bool(row["pass_solvation"]):
        reasons.append("solvation")
    if not bool(row.get("pass_supporting_electrolyte_role", True)):
        reasons.append("supporting_electrolyte")
    return ";".join(reasons)


def _supporting_electrolyte_gate_result(
    row: pd.Series, *, enabled: bool
) -> tuple[bool, str, str]:
    """Return auditable role-gate pass/status/reason without aborting on bad metadata."""

    if not enabled:
        return True, "disabled", ""
    role = str(row.get("electrolyte_role", "")).strip()
    raw_ok = row.get("supporting_electrolyte_ok")
    if not role or pd.isna(raw_ok) or str(raw_ok).strip().lower() not in {"true", "false"}:
        return False, "failed", "supporting-electrolyte role metadata missing or invalid"
    if raw_ok is True or str(raw_ok).strip().lower() == "true":
        return True, "ok", ""
    return False, "excluded", f"salt not a supporting electrolyte: {role}"


@dataclass(frozen=True)
class _CalcOutcome:
    value: float
    status: str
    error: str


def _safe_calculate(calculate: Callable[[], float]) -> _CalcOutcome:
    try:
        return _CalcOutcome(value=float(calculate()), status="ok", error="")
    except Exception as exc:  # noqa: BLE001 - audit output must preserve per-property failures.
        return _CalcOutcome(value=float("nan"), status="failed", error=_concise_error(exc))


def _safe_str(produce: Callable[[], str]) -> str:
    """Best-effort string metadata (oligomer SMILES, method label); never aborts a row."""

    try:
        return str(produce())
    except Exception as exc:  # noqa: BLE001
        return f"error: {_concise_error(exc)}"


def _concise_error(exc: Exception) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return f"{exc.__class__.__name__}: {message}"[:240]


def _has_calculation_failure(row: pd.Series) -> bool:
    return bool(_failed_calculation_reasons(row))


def _failed_calculation_reasons(row: pd.Series) -> list[str]:
    labels = {
        "monomer_Eox_calc_status": "monomer_eox_failed",
        "solvation_calc_status": "solvation_failed",
        "anion_Eox_calc_status": "anion_eox_failed",
        "optical_gap_calc_status": "optical_gap_failed",
        "dimerization_calc_status": "dimerization_failed",
    }
    return [label for column, label in labels.items() if row.get(column, "ok") == "failed"]

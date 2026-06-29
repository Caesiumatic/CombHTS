"""Directive section 7 validation package orchestration.

This module gathers the existing validation calculators into one reproducible,
machine-readable workflow.  Expensive work remains per species through the Engine
interface and SQLite cache; triad-level checks read an existing harvest CSV only.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from eps.chemspace import load_monomers, load_solvents
from eps.engines.base import Engine
from eps.engines.mock import MockEngine
from eps.properties import monomer_eox_vs_AgAgCl
from eps.provenance import config_hashes, git_info, library_sizes
from eps.storage import SQLiteCache
from eps.structures.geometry import (
    ConformerSearchConfig,
    conformer_method_suffix,
    conformer_search_active,
)
from eps.validation.benchmark import (
    DEFAULT_BENCHMARK_PATH,
    DEFAULT_CALIBRATION_PROFILES_PATH,
    DEFAULT_VALIDATION_CONFIG,
    BenchmarkValidationResult,
    load_calibration_profiles,
    run_calibration_profile,
)
from eps.validation.feasibility import (
    DEFAULT_LABELS_PATH,
    compute_feasibility_metric,
)
from eps.validation.solvent_benchmark import (
    DEFAULT_SOLVENT_BENCHMARK_PATH,
    load_solvent_benchmark,
)
from eps.workflow.tier1 import DEFAULT_TIER1_CONFIG, compute_solvent_table

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIRECTIVE_OUTDIR = PROJECT_ROOT / "outputs" / "directive_validation"
DEFAULT_DIRECTIVE_CACHE = PROJECT_ROOT / "outputs" / "directive_validation_cache.sqlite"

BOOTSTRAP_SEED = 20260623
BOOTSTRAP_REPLICATES = 2000
REFERENCE_FLOOR_V = 0.15
NUMERICAL_TOLERANCE_V = 1e-9
FEASIBILITY_MIN_MATCHED_FOR_CLAIM = 20

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_YET_TESTABLE = "NOT_YET_TESTABLE"
STATUS_OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class DirectiveValidationResult:
    """Paths and headline records for a directive section 7 validation run."""

    outdir: Path
    summary_path: Path
    report_path: Path
    eox_profile_summary_path: Path
    eox_points_path: Path
    esw_descriptor_points_path: Path
    esw_gate_diagnostics_path: Path
    feasibility_matches_path: Path
    provenance_path: Path
    summary: dict[str, Any]
    metric_table: list[dict[str, Any]]


def run_directive_validation(
    *,
    engine: Engine | None = None,
    engine_name: str = "mock",
    method: str = "mock-gfn2",
    cache_path: str | Path = DEFAULT_DIRECTIVE_CACHE,
    harvest_path: str | Path | None,
    dft_benchmark_path: str | Path | None = None,
    outdir: str | Path = DEFAULT_DIRECTIVE_OUTDIR,
    benchmark_path: str | Path = DEFAULT_BENCHMARK_PATH,
    solvent_benchmark_path: str | Path = DEFAULT_SOLVENT_BENCHMARK_PATH,
    labels_path: str | Path = DEFAULT_LABELS_PATH,
    tier1_config_path: str | Path = DEFAULT_TIER1_CONFIG,
    validation_config_path: str | Path = DEFAULT_VALIDATION_CONFIG,
    profiles_path: str | Path = DEFAULT_CALIBRATION_PROFILES_PATH,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    generated_at_utc: str | None = None,
) -> DirectiveValidationResult:
    """Run the full directive section 7 validation package.

    Args:
        engine: Calculation engine used for per-species descriptors.
        engine_name: User-facing engine label, e.g. ``mock`` or ``xtb``.
        method: Base method label before the production conformer-search suffix.
        cache_path: Dedicated SQLite validation cache for idempotent per-species calls.
        harvest_path: Existing all-triads harvest CSV for ESW gate and feasibility checks.
        outdir: Directory for all required section 7 artifacts.
        benchmark_path: Literature monomer oxidation benchmark CSV.
        solvent_benchmark_path: Solvent ESW benchmark CSV.
        labels_path: Binary electropolymerization-feasibility label CSV.
        tier1_config_path: Tier-1 YAML used only to mirror production method/cache semantics.
        validation_config_path: YAML carrying directive target thresholds.
        profiles_path: Calibration-profile YAML.
        bootstrap_seed: Fixed seed recorded in summary/provenance for deterministic intervals.
        generated_at_utc: Optional fixed timestamp for deterministic tests.

    Returns:
        Artifact paths plus the in-memory summary.
    """

    engine = engine or MockEngine()
    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache = Path(cache_path)
    tier1_config = _load_yaml(tier1_config_path)
    validation_config = _load_yaml(validation_config_path)
    conformer_config = _conformer_config_from_tier1(tier1_config)
    production_method = method + conformer_method_suffix(conformer_config)
    is_mock = isinstance(engine, MockEngine) or "mock" in engine_name.lower() or "mock" in method.lower()
    generated_at_utc = generated_at_utc or datetime.now(timezone.utc).isoformat()

    with conformer_search_active(conformer_config):
        eox_profile_summary, eox_points, eox_meta = _run_eox_profiles(
            engine=engine,
            method=production_method,
            cache_path=cache,
            benchmark_path=benchmark_path,
            validation_config_path=validation_config_path,
            profiles_path=profiles_path,
            tier1_config=tier1_config,
            outdir=output_dir,
            bootstrap_seed=bootstrap_seed,
        )
        esw_descriptor_points, esw_descriptor_meta = _compute_esw_descriptor_points(
            engine=engine,
            method=production_method,
            cache_path=cache,
            benchmark_path=solvent_benchmark_path,
        )

    esw_gate_diagnostics, esw_gate_meta = _compute_esw_gate_diagnostics(harvest_path)
    feasibility_matches, feasibility_meta = _compute_feasibility_outputs(
        labels_path=labels_path,
        harvest_path=harvest_path,
        bootstrap_seed=bootstrap_seed,
    )
    # Directive §7 accuracy target: original DFT Eox vs experiment (< 0.15 V), graded from the
    # DFT-on-benchmark artifact (eps calibrate-dft points CSV). No artifact -> NOT_YET_TESTABLE.
    dft_eox_meta = _compute_dft_eox_validation(dft_benchmark_path)

    metric_table = _directive_metric_table(
        validation_config=validation_config,
        eox_meta=eox_meta,
        dft_eox_meta=dft_eox_meta,
        esw_descriptor_meta=esw_descriptor_meta,
        esw_gate_meta=esw_gate_meta,
        feasibility_meta=feasibility_meta,
    )
    artifacts = {
        "validation_summary_json": str(output_dir / "validation_summary.json"),
        "validation_report_md": str(output_dir / "validation_report.md"),
        "eox_profile_summary_csv": str(output_dir / "eox_profile_summary.csv"),
        "eox_points_csv": str(output_dir / "eox_points.csv"),
        "esw_descriptor_points_csv": str(output_dir / "esw_descriptor_points.csv"),
        "esw_gate_diagnostics_csv": str(output_dir / "esw_gate_diagnostics.csv"),
        "feasibility_matches_csv": str(output_dir / "feasibility_matches.csv"),
        "provenance_json": str(output_dir / "provenance.json"),
    }

    summary = {
        "generated_at_utc": generated_at_utc,
        "engine": engine_name,
        "base_method": method,
        "production_method": production_method,
        "mock_non_physical": is_mock,
        "bootstrap_seed": bootstrap_seed,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "numeric_tolerance_V": NUMERICAL_TOLERANCE_V,
        "reference_floor_V": REFERENCE_FLOOR_V,
        "harvest_path": str(harvest_path) if harvest_path is not None else None,
        "directive_status_table": metric_table,
        "eox": eox_meta,
        "dft_eox": dft_eox_meta,
        "esw_descriptor": esw_descriptor_meta,
        "esw_gate": esw_gate_meta,
        "feasibility": feasibility_meta,
        "artifacts": artifacts,
    }
    provenance = _provenance_record(
        summary=summary,
        engine_name=engine_name,
        method=production_method,
        cache_path=cache,
        harvest_path=harvest_path,
        benchmark_path=benchmark_path,
        solvent_benchmark_path=solvent_benchmark_path,
        labels_path=labels_path,
        tier1_config_path=tier1_config_path,
        validation_config_path=validation_config_path,
        profiles_path=profiles_path,
    )

    eox_profile_summary.to_csv(artifacts["eox_profile_summary_csv"], index=False)
    eox_points.to_csv(artifacts["eox_points_csv"], index=False)
    esw_descriptor_points.to_csv(artifacts["esw_descriptor_points_csv"], index=False)
    esw_gate_diagnostics.to_csv(artifacts["esw_gate_diagnostics_csv"], index=False)
    feasibility_matches.to_csv(artifacts["feasibility_matches_csv"], index=False)
    _write_json(Path(artifacts["validation_summary_json"]), summary)
    _write_json(Path(artifacts["provenance_json"]), provenance)
    Path(artifacts["validation_report_md"]).write_text(
        _render_report(summary, eox_profile_summary),
        encoding="utf-8",
    )

    return DirectiveValidationResult(
        outdir=output_dir,
        summary_path=Path(artifacts["validation_summary_json"]),
        report_path=Path(artifacts["validation_report_md"]),
        eox_profile_summary_path=Path(artifacts["eox_profile_summary_csv"]),
        eox_points_path=Path(artifacts["eox_points_csv"]),
        esw_descriptor_points_path=Path(artifacts["esw_descriptor_points_csv"]),
        esw_gate_diagnostics_path=Path(artifacts["esw_gate_diagnostics_csv"]),
        feasibility_matches_path=Path(artifacts["feasibility_matches_csv"]),
        provenance_path=Path(artifacts["provenance_json"]),
        summary=summary,
        metric_table=metric_table,
    )


def _run_eox_profiles(
    *,
    engine: Engine,
    method: str,
    cache_path: Path,
    benchmark_path: str | Path,
    validation_config_path: str | Path,
    profiles_path: str | Path,
    tier1_config: dict[str, Any],
    outdir: Path,
    bootstrap_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    profiles_config = load_calibration_profiles(profiles_path)
    profiles = profiles_config["profiles"]
    default_profile = str(profiles_config["default_screening_profile"])
    active_profile = _active_profile_from_tier1(tier1_config, profiles)
    raw_rows = _csv_row_count(benchmark_path)
    profile_report_dir = outdir / "_profile_reports"
    profile_report_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, Any]] = []
    point_rows: list[dict[str, Any]] = []
    fitted_profiles: dict[str, dict[str, Any]] = {}

    for profile_name, profile in profiles.items():
        try:
            result = run_calibration_profile(
                profile_name,
                engine=engine,
                method=method,
                cache_path=cache_path,
                benchmark_path=benchmark_path,
                validation_config_path=validation_config_path,
                report_path=profile_report_dir / f"{profile_name}.csv",
                profiles_path=profiles_path,
            )
        except ValueError as exc:
            status = _profile_skip_status(str(exc))
            summary_rows.append(
                _skipped_profile_row(
                    profile_name=profile_name,
                    profile=profile,
                    status=status,
                    raw_rows=raw_rows,
                    is_active=profile_name == active_profile,
                    is_default=profile_name == default_profile,
                    message=str(exc),
                )
            )
            continue

        profile_points, profile_point_meta = _eox_profile_points(
            result,
            profile_name=profile_name,
            bootstrap_seed=_seed_for(bootstrap_seed, profile_name),
        )
        ad_rows, ad_meta = _applicability_domain_rows(
            result,
            profile_name=profile_name,
            engine=engine,
            method=method,
            cache_path=cache_path,
        )
        point_rows.extend(profile_points.to_dict(orient="records"))
        point_rows.extend(ad_rows.to_dict(orient="records"))
        fitted_profiles[profile_name] = {
            "profile_name": profile_name,
            "is_active_production_profile": profile_name == active_profile,
            "is_config_default_profile": profile_name == default_profile,
            "n": result.n_calibration_points,
            "loo_mae_after_V": result.loo_mae_after_V,
            "mae_after_V": result.mae_after_V,
            "mae_before_V": result.mae_before_V,
            "r2": result.calibration.r2,
            "slope": result.calibration.slope,
            "intercept": result.calibration.intercept,
            "residual_std_after_V": result.residual_std_after_V,
            "spearman_rho": result.spearman_rho,
            "bootstrap": profile_point_meta["bootstrap"],
            "applicability_domain": ad_meta,
        }
        summary_rows.append(
            _fitted_profile_row(
                result=result,
                profile=profile,
                profile_point_meta=profile_point_meta,
                ad_meta=ad_meta,
                raw_rows=raw_rows,
                is_active=profile_name == active_profile,
                is_default=profile_name == default_profile,
            )
        )

    summary = pd.DataFrame(summary_rows)
    points = pd.DataFrame(point_rows)
    if not points.empty:
        points = points.sort_values(["profile_name", "point_kind", "monomer_name"]).reset_index(drop=True)

    active = fitted_profiles.get(active_profile) if active_profile is not None else None
    meta = {
        "active_production_profile": active_profile,
        "config_default_profile": default_profile,
        "profiles": list(fitted_profiles.values()),
        "raw_literature_row_count": raw_rows,
        "active_profile": active,
        "profile_report_dir": str(profile_report_dir),
        "reference_floor_note": (
            f"MAE values below {REFERENCE_FLOOR_V:.2f} V are observed fit errors only; "
            "they are not claimed below the reference/measurement floor."
        ),
    }
    return summary, points, meta


def _eox_profile_points(
    result: BenchmarkValidationResult,
    *,
    profile_name: str,
    bootstrap_seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = result.rows.loc[result.rows["in_calibration_set"]].copy()
    if rows.empty:
        empty = pd.DataFrame()
        return empty, {"bootstrap": _empty_bootstrap()}

    meta_cols = [
        "group_id",
        "monomer_name",
        "canonical_smiles",
        "solvent_name",
        "label_type",
        "medium_class",
        "medium",
        "reliability_tier",
        "reference_frame",
        "reported_potential_type",
        "source_confidence",
    ]
    available_meta = [column for column in meta_cols if column in rows.columns]
    first_meta = rows.groupby("group_id", as_index=False)[available_meta].first()
    grouped = rows.groupby("group_id", as_index=False).agg(
        pred_Eox_V_vs_AgAgCl=("pred_Eox_V_vs_AgAgCl", "first"),
        exp_Eox_V_vs_AgAgCl=("exp_Eox_V_vs_AgAgCl", "mean"),
        raw_label_row_count=("exp_Eox_V_vs_AgAgCl", "size"),
        exp_label_std_V=("exp_Eox_V_vs_AgAgCl", "std"),
    )
    points = grouped.merge(first_meta, on="group_id", how="left", validate="one_to_one")
    pred = points["pred_Eox_V_vs_AgAgCl"].to_numpy(dtype=float)
    exp = points["exp_Eox_V_vs_AgAgCl"].to_numpy(dtype=float)
    calibrated = result.calibration.apply(pred)
    residual = calibrated - exp
    loo_pred, loo_residual = _loo_predictions(pred, exp)
    leverage, cooks = _linear_influence(pred, residual)

    points["profile_name"] = profile_name
    points["point_kind"] = "calibration_point"
    points["calibrated_Eox_V_vs_AgAgCl"] = calibrated
    points["residual_after_V"] = residual
    points["abs_residual_after_V"] = np.abs(residual)
    points["loo_calibrated_Eox_V_vs_AgAgCl"] = loo_pred
    points["loo_residual_after_V"] = loo_residual
    points["loo_abs_residual_after_V"] = np.abs(loo_residual)
    points["leverage"] = leverage
    points["cooks_distance"] = cooks
    points["high_leverage_flag"] = _high_leverage_flags(leverage)
    points["applicability_domain_status"] = ""
    points["distance_outside_domain_V"] = ""

    mae_ci = _bootstrap_mean_ci(np.abs(residual), seed=bootstrap_seed)
    loo_ci = _bootstrap_mean_ci(np.abs(loo_residual), seed=bootstrap_seed + 17)
    bootstrap = {
        "seed": bootstrap_seed,
        "replicates": BOOTSTRAP_REPLICATES,
        "mae_after_V_95ci": mae_ci,
        "loo_mae_after_V_95ci": loo_ci,
        "n": int(len(points)),
        "small_n_caveat": "Exploratory interval; report n beside the interval and do not use it to hide small-n.",
    }
    return points, {"bootstrap": bootstrap}


def _applicability_domain_rows(
    result: BenchmarkValidationResult,
    *,
    profile_name: str,
    engine: Engine,
    method: str,
    cache_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    points = result.rows.loc[result.rows["in_calibration_set"]].copy()
    collapsed = points.groupby("group_id", as_index=False).agg(
        pred_Eox_V_vs_AgAgCl=("pred_Eox_V_vs_AgAgCl", "first")
    )
    finite = pd.to_numeric(collapsed["pred_Eox_V_vs_AgAgCl"], errors="coerce").dropna()
    if finite.empty:
        return pd.DataFrame(), {}
    low = float(finite.min())
    high = float(finite.max())
    solvent = next((item for item in load_solvents() if item.name == "acetonitrile"), load_solvents()[0])
    cache = SQLiteCache(cache_path)
    rows: list[dict[str, Any]] = []
    for monomer in load_monomers():
        try:
            descriptor = monomer_eox_vs_AgAgCl(monomer, solvent, engine, cache, method=method)
            calc_status = "ok"
            calc_error = ""
        except Exception as exc:  # noqa: BLE001 - AD audit must not abort the validation package
            descriptor = float("nan")
            calc_status = "failed"
            calc_error = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
        status, distance = _applicability_domain_status(descriptor, low, high)
        rows.append(
            {
                "profile_name": profile_name,
                "point_kind": "library_applicability_domain",
                "group_id": "",
                "monomer_name": monomer.name,
                "canonical_smiles": monomer.canonical_smiles,
                "monomer_class": monomer.monomer_class,
                "solvent_name": solvent.name,
                "pred_Eox_V_vs_AgAgCl": descriptor,
                "exp_Eox_V_vs_AgAgCl": "",
                "calibrated_Eox_V_vs_AgAgCl": "",
                "residual_after_V": "",
                "abs_residual_after_V": "",
                "loo_calibrated_Eox_V_vs_AgAgCl": "",
                "loo_residual_after_V": "",
                "loo_abs_residual_after_V": "",
                "leverage": "",
                "cooks_distance": "",
                "high_leverage_flag": "",
                "applicability_domain_status": status,
                "distance_outside_domain_V": distance,
                "calc_status": calc_status,
                "calc_error": calc_error,
            }
        )
    ad = pd.DataFrame(rows)
    by_class: dict[str, dict[str, Any]] = {}
    for monomer_class, group in ad.groupby("monomer_class", sort=True):
        ood = group["applicability_domain_status"].isin(["below-domain", "above-domain"])
        by_class[str(monomer_class)] = {
            "n": int(len(group)),
            "ood": int(ood.sum()),
            "ood_fraction": float(ood.mean()) if len(group) else None,
        }
    ood_all = ad["applicability_domain_status"].isin(["below-domain", "above-domain"])
    meta = {
        "descriptor_domain_min_V": low,
        "descriptor_domain_max_V": high,
        "library_descriptor_solvent": solvent.name,
        "library_monomer_count": int(len(ad)),
        "ood_count": int(ood_all.sum()),
        "ood_fraction": float(ood_all.mean()) if len(ad) else None,
        "ood_fraction_by_monomer_class": by_class,
    }
    return ad, meta


def _compute_esw_descriptor_points(
    *,
    engine: Engine,
    method: str,
    cache_path: Path,
    benchmark_path: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    benchmark = load_solvent_benchmark(benchmark_path)
    columns = [
        "solvent",
        "smiles",
        "reference",
        "electrolyte",
        "electrode",
        "source",
        "tier",
        "limit_set_by_electrolyte",
        "exp_anodic_V_vs_AgAgCl",
        "computed_anodic_descriptor_V_vs_AgAgCl",
        "anodic_abs_error_V",
        "anodic_engine_status",
        "exp_cathodic_V_vs_AgAgCl",
        "computed_cathodic_descriptor_V_vs_AgAgCl",
        "cathodic_abs_error_V",
        "cathodic_engine_status",
        "solvent_in_library",
        "comparison_label",
    ]
    if benchmark.empty:
        return pd.DataFrame(columns=columns), {
            "n_benchmark_rows": 0,
            "n_matched": 0,
            "anodic_mae_V": None,
            "cathodic_mae_V": None,
            "note": "no solvent ESW benchmark rows",
        }

    library = {solvent.name: solvent for solvent in load_solvents()}
    matched_solvents = [library[name] for name in dict.fromkeys(benchmark["solvent"]) if name in library]
    if matched_solvents:
        table = compute_solvent_table(
            matched_solvents,
            engine,
            SQLiteCache(cache_path),
            method=method,
            calibration_config=None,
        )
    else:
        table = pd.DataFrame(columns=["solvent_name"])
    merged = benchmark.merge(table, left_on="solvent", right_on="solvent_name", how="left")

    rows: list[dict[str, Any]] = []
    for _, row in merged.iterrows():
        exp_anodic = _finite(row.get("exp_anodic_V_vs_AgAgCl"))
        exp_cathodic = _finite(row.get("exp_cathodic_V_vs_AgAgCl"))
        comp_anodic = _finite(row.get("solvent_anodic_limit_computed_V"))
        comp_cathodic = _finite(row.get("solvent_cathodic_limit_computed_V"))
        anodic_status = str(row.get("solvent_anodic_limit_calc_status", "not_in_library") or "not_in_library")
        cathodic_status = str(row.get("solvent_cathodic_limit_calc_status", "not_in_library") or "not_in_library")
        rows.append(
            {
                "solvent": row.get("solvent", ""),
                "smiles": row.get("smiles", ""),
                "reference": row.get("reference", ""),
                "electrolyte": row.get("electrolyte", ""),
                "electrode": row.get("electrode", ""),
                "source": row.get("source", ""),
                "tier": row.get("tier", ""),
                "limit_set_by_electrolyte": row.get("limit_set_by_electrolyte", ""),
                "exp_anodic_V_vs_AgAgCl": exp_anodic,
                "computed_anodic_descriptor_V_vs_AgAgCl": comp_anodic,
                "anodic_abs_error_V": _abs_error(comp_anodic, exp_anodic),
                "anodic_engine_status": anodic_status,
                "exp_cathodic_V_vs_AgAgCl": exp_cathodic,
                "computed_cathodic_descriptor_V_vs_AgAgCl": comp_cathodic,
                "cathodic_abs_error_V": _abs_error(comp_cathodic, exp_cathodic),
                "cathodic_engine_status": cathodic_status,
                "solvent_in_library": row.get("solvent") in library,
                "comparison_label": "molecular DeltaSCF descriptor vs practical ESW",
            }
        )
    points = pd.DataFrame(rows, columns=columns)
    anodic_errors = pd.to_numeric(points["anodic_abs_error_V"], errors="coerce").dropna()
    cathodic_errors = pd.to_numeric(points["cathodic_abs_error_V"], errors="coerce").dropna()
    meta = {
        "n_benchmark_rows": int(len(benchmark)),
        "n_matched": int(points["solvent_in_library"].sum()),
        "anodic_n": int(len(anodic_errors)),
        "cathodic_n": int(len(cathodic_errors)),
        "anodic_mae_V": _mean_or_none(anodic_errors),
        "cathodic_mae_V": _mean_or_none(cathodic_errors),
        "label": "molecular DeltaSCF descriptor vs practical ESW",
    }
    return points, meta


def _compute_dft_eox_validation(dft_benchmark_path: str | Path | None) -> dict[str, Any]:
    """Directive §7 Tier-2 accuracy target: RAW MAE of B3LYP/SMD DFT Eox vs experimental peak.

    Reads the DFT-on-benchmark artifact written by ``eps calibrate-dft`` (its
    ``dft_calibration_points.csv``), keeps rows that computed successfully and carry the
    ``monomer_oxidation_peak`` label, and returns ``mean |dft_Eox_V - exp_Eox_V|`` — the original
    DFT error against experiment, NOT a fit residual. With no artifact (or no peak rows) the metric
    is honestly NOT_YET_TESTABLE rather than fabricated or silently out of scope.
    """

    not_testable = {
        "computable": False,
        "n_peak_points": 0,
        "dft_vs_exp_mae_V": None,
        "note": "no DFT-on-benchmark artifact supplied (--dft-benchmark); not yet testable.",
    }
    if dft_benchmark_path is None:
        return not_testable
    path = Path(dft_benchmark_path)
    if not path.exists():
        return {**not_testable, "note": f"DFT-on-benchmark artifact not found: {path}"}

    frame = pd.read_csv(path, keep_default_na=False)
    required = {"label_type", "dft_calc_status", "dft_Eox_V_vs_AgAgCl", "exp_Eox_V_vs_AgAgCl"}
    missing = required.difference(frame.columns)
    if missing:
        return {
            **not_testable,
            "note": f"DFT-on-benchmark artifact lacks columns: {', '.join(sorted(missing))}",
        }

    peak = frame[
        (frame["dft_calc_status"] == "ok") & (frame["label_type"] == "monomer_oxidation_peak")
    ].copy()
    dft = pd.to_numeric(peak["dft_Eox_V_vs_AgAgCl"], errors="coerce")
    exp = pd.to_numeric(peak["exp_Eox_V_vs_AgAgCl"], errors="coerce")
    mask = dft.notna() & exp.notna()
    n = int(mask.sum())
    if n == 0:
        return {**not_testable, "note": f"DFT-on-benchmark artifact has no usable peak rows ({path})."}
    mae = float((dft[mask] - exp[mask]).abs().mean())
    return {
        "computable": True,
        "n_peak_points": n,
        "dft_vs_exp_mae_V": mae,
        "artifact": str(path),
        "note": f"{n} peak monomer(s) from {path.name}.",
    }


def _compute_esw_gate_diagnostics(
    harvest_path: str | Path | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [
        "monomer_name",
        "solvent_name",
        "salt",
        "anion_smiles",
        "passes_all_tier1_filters",
        "selected_measured_anodic_V",
        "measurement_match",
        "exact_salt_match",
        "solvent_only_match",
        "measurement_source",
        "measurement_tier",
        "measurement_electrode",
        "measurement_electrolyte",
        "measurement_reference",
        "curated_csv_cap_V",
        "computed_cap_V",
        "final_gate_V",
        "cap_source",
        "cap_applied",
        "electrolyte_limited",
        "unsafe_widening",
        "unsafe_widening_amount_V",
        "conservatism_V",
    ]
    if harvest_path is None or not Path(harvest_path).exists():
        return pd.DataFrame(columns=columns), {
            "harvest_found": False,
            "n_rows": 0,
            "n_comparable": 0,
            "unsafe_widening_count": None,
            "status_note": "harvest missing; production-gate safety not testable",
        }

    harvest = pd.read_csv(harvest_path, keep_default_na=False, low_memory=False)
    required = {
        "solvent_name",
        "salt",
        "solvent_anodic_limit_V",
        "solvent_window_condition_match",
        "solvent_window_measurement_anodic_V",
        "solvent_anodic_limit_csv_V",
        "solvent_anodic_limit_calibrated_V",
        "solvent_window_conservative_cap_source",
        "solvent_window_cap_applied",
    }
    missing = required.difference(harvest.columns)
    if missing:
        return pd.DataFrame(columns=columns), {
            "harvest_found": True,
            "n_rows": int(len(harvest)),
            "n_comparable": 0,
            "unsafe_widening_count": None,
            "status_note": "harvest lacks conditioned solvent-window audit columns: "
            + ", ".join(sorted(missing)),
        }

    diag = pd.DataFrame()
    diag["monomer_name"] = harvest.get("monomer_name", "")
    diag["solvent_name"] = harvest["solvent_name"]
    diag["salt"] = harvest["salt"]
    diag["anion_smiles"] = harvest.get("anion_smiles", "")
    diag["passes_all_tier1_filters"] = harvest.get("passes_all_tier1_filters", False)
    diag["selected_measured_anodic_V"] = pd.to_numeric(
        harvest["solvent_window_measurement_anodic_V"], errors="coerce"
    )
    diag["measurement_match"] = harvest["solvent_window_condition_match"]
    diag["exact_salt_match"] = diag["measurement_match"].eq("exact_salt_conservative")
    diag["solvent_only_match"] = diag["measurement_match"].eq("solvent_only_conservative")
    diag["measurement_source"] = harvest.get("solvent_window_measurement_source", "")
    diag["measurement_tier"] = harvest.get("solvent_window_measurement_tier", "")
    diag["measurement_electrode"] = harvest.get("solvent_window_measurement_electrode", "")
    diag["measurement_electrolyte"] = harvest.get("solvent_window_measurement_electrolyte", "")
    diag["measurement_reference"] = harvest.get("solvent_window_measurement_reference", "")
    diag["curated_csv_cap_V"] = pd.to_numeric(harvest["solvent_anodic_limit_csv_V"], errors="coerce")
    diag["computed_cap_V"] = pd.to_numeric(
        harvest["solvent_anodic_limit_calibrated_V"], errors="coerce"
    )
    diag["final_gate_V"] = pd.to_numeric(harvest["solvent_anodic_limit_V"], errors="coerce")
    diag["cap_source"] = harvest["solvent_window_conservative_cap_source"]
    diag["cap_applied"] = harvest["solvent_window_cap_applied"].map(_as_bool)
    diag["electrolyte_limited"] = harvest.get("solvent_window_limit_set_by_electrolyte", "")

    comparable = diag["selected_measured_anodic_V"].notna()
    widening = diag["final_gate_V"] - diag["selected_measured_anodic_V"]
    diag["unsafe_widening"] = comparable & (widening > NUMERICAL_TOLERANCE_V)
    diag["unsafe_widening_amount_V"] = np.where(diag["unsafe_widening"], widening, 0.0)
    diag["conservatism_V"] = np.where(comparable, diag["selected_measured_anodic_V"] - diag["final_gate_V"], np.nan)
    diag = diag.loc[:, columns]

    unsafe = diag.loc[diag["unsafe_widening"]]
    comparable_rows = diag.loc[comparable]
    survivors = diag.loc[diag["passes_all_tier1_filters"].map(_as_bool)]
    coverage = _esw_coverage_summary(diag)
    meta = {
        "harvest_found": True,
        "n_rows": int(len(diag)),
        "n_comparable": int(len(comparable_rows)),
        "unsafe_widening_count": int(len(unsafe)),
        "maximum_unsafe_widening_V": _max_or_zero(unsafe["unsafe_widening_amount_V"]),
        "mean_conservatism_V": _mean_or_none(comparable_rows["conservatism_V"]),
        "maximum_conservatism_V": _max_or_none(comparable_rows["conservatism_V"]),
        "exact_formulation_coverage": coverage["exact"],
        "solvent_only_coverage": coverage["solvent_only"],
        "computed_csv_fallback_coverage": coverage["fallback"],
        "survivor_count": int(len(survivors)),
        "coverage_by_survivor_solvent_salt_anion": _survivor_coverage(survivors),
    }
    return diag, meta


def _compute_feasibility_outputs(
    *,
    labels_path: str | Path,
    harvest_path: str | Path | None,
    bootstrap_seed: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = compute_feasibility_metric(labels_path=labels_path, harvest_path=harvest_path)
    matches = pd.DataFrame(result.matched_detail)
    columns = [
        "monomer_name",
        "monomer_smiles",
        "solvent",
        "electrolyte",
        "match_basis",
        "outcome",
        "predicted",
        "reliability_tier",
        "medium_class",
        "negative_type",
        "source_doi",
    ]
    for column in columns:
        if column not in matches.columns:
            matches[column] = pd.Series(dtype=object)
    matches = matches.loc[:, columns]
    bootstrap = _feasibility_bootstrap_ci(matches, seed=bootstrap_seed)
    exact_anion = int((matches["match_basis"] == "specified-anion").sum()) if not matches.empty else 0
    generic = int((matches["match_basis"] == "monomer+solvent").sum()) if not matches.empty else 0
    meta = {
        "computable": result.computable,
        "message": result.message,
        "n_labels": result.n_labels,
        "n_yes": result.n_yes,
        "n_no": result.n_no,
        "n_out_of_scope": result.n_out_of_scope,
        "out_of_scope_breakdown": result.out_of_scope_breakdown,
        "n_in_scope": result.n_in_scope,
        "n_matched": result.n_matched,
        "exact_anion_matches": exact_anion,
        "generic_electrolyte_matches": generic,
        "tp": result.tp,
        "fn": result.fn,
        "tn": result.tn,
        "fp": result.fp,
        "recall_yes": result.recall_yes,
        "recall_no": result.recall_no,
        "balanced_accuracy": result.balanced_accuracy,
        "balanced_accuracy_bootstrap_95ci": bootstrap,
        "trivial_always_yes_baseline": result.trivial_always_yes_note,
        "breakdown_by_reliability_tier": _feasibility_breakdown(matches, "reliability_tier"),
        "breakdown_by_medium_class": _feasibility_breakdown(matches, "medium_class"),
        "breakdown_by_match_basis": _feasibility_breakdown(matches, "match_basis"),
    }
    return matches, meta


def _directive_metric_table(
    *,
    validation_config: dict[str, Any],
    eox_meta: dict[str, Any],
    dft_eox_meta: dict[str, Any],
    esw_descriptor_meta: dict[str, Any],
    esw_gate_meta: dict[str, Any],
    feasibility_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    tier1_target = float(validation_config.get("tier1_xtb_mae_target_V", 0.30))
    tier2_target = float(validation_config.get("tier2_dft_mae_target_V", 0.15))
    esw_target = float(validation_config.get("solvent_esw_mae_target_V", 0.30))
    active = eox_meta.get("active_profile") or {}
    active_loo = active.get("loo_mae_after_V")
    active_n = int(active.get("n", 0) or 0)
    eox_status = _threshold_status(active_loo, tier1_target, active_n)
    feasibility_ba = feasibility_meta.get("balanced_accuracy")
    feasibility_n = int(feasibility_meta.get("n_matched", 0) or 0)
    feasibility_status = _feasibility_status(feasibility_ba, feasibility_n, feasibility_meta)
    gate_unsafe = esw_gate_meta.get("unsafe_widening_count")
    gate_n = int(esw_gate_meta.get("n_comparable", 0) or 0)
    gate_status = STATUS_NOT_YET_TESTABLE
    if gate_unsafe is not None and gate_n > 0:
        gate_status = STATUS_PASS if int(gate_unsafe) == 0 else STATUS_FAIL

    return [
        {
            "metric": "Tier-1 monomer Eox active-profile LOO-CV MAE",
            "directive target": f"< {tier1_target:.2f} V",
            "observed value": _fmt(active_loo, " V"),
            "n": active_n,
            "status": eox_status,
            "caveat": (
                f"active production profile {eox_meta.get('active_production_profile')}; "
                "LOO-CV is headline, in-sample is diagnostic only; do not claim below "
                f"{REFERENCE_FLOOR_V:.2f} V reference floor"
            ),
        },
        {
            "metric": "Tier-2 DFT monomer Eox vs experiment MAE",
            "directive target": f"< {tier2_target:.2f} V",
            "observed value": _fmt(dft_eox_meta.get("dft_vs_exp_mae_V"), " V"),
            "n": int(dft_eox_meta.get("n_peak_points", 0) or 0),
            "status": _threshold_status(
                dft_eox_meta.get("dft_vs_exp_mae_V"),
                tier2_target,
                int(dft_eox_meta.get("n_peak_points", 0) or 0),
            ),
            "caveat": (
                "RAW B3LYP/SMD ΔSCF Eox vs experimental peak (V vs Ag/AgCl), no fit, from the "
                f"DFT-on-benchmark artifact. {dft_eox_meta.get('note', '')} Do not claim below "
                f"{REFERENCE_FLOOR_V:.2f} V reference floor."
            ),
        },
        {
            "metric": "Solvent ESW descriptor anodic MAE",
            "directive target": f"< {esw_target:.2f} V",
            "observed value": _fmt(esw_descriptor_meta.get("anodic_mae_V"), " V"),
            "n": int(esw_descriptor_meta.get("anodic_n", 0) or 0),
            "status": _threshold_status(
                esw_descriptor_meta.get("anodic_mae_V"),
                esw_target,
                int(esw_descriptor_meta.get("anodic_n", 0) or 0),
            ),
            "caveat": "molecular DeltaSCF descriptor vs practical ESW; not a universal solvent calibration",
        },
        {
            "metric": "Solvent ESW descriptor cathodic MAE",
            "directive target": f"< {esw_target:.2f} V",
            "observed value": _fmt(esw_descriptor_meta.get("cathodic_mae_V"), " V"),
            "n": int(esw_descriptor_meta.get("cathodic_n", 0) or 0),
            "status": _threshold_status(
                esw_descriptor_meta.get("cathodic_mae_V"),
                esw_target,
                int(esw_descriptor_meta.get("cathodic_n", 0) or 0),
            ),
            "caveat": "cathodic solvent-molecule EA is informational and especially screening-grade",
        },
        {
            "metric": "Production ESW gate unsafe widening",
            "directive target": "0 rows",
            "observed value": "not testable" if gate_unsafe is None else str(gate_unsafe),
            "n": gate_n,
            "status": gate_status,
            "caveat": "correctness invariant: final_gate must never exceed selected reliable measurement",
        },
        {
            "metric": "Qualitative electropolymerization feasibility balanced accuracy",
            "directive target": "> 85%",
            "observed value": _fmt_percent(feasibility_ba),
            "n": feasibility_n,
            "status": feasibility_status,
            "caveat": (
                "Only claim target when matched condition-relevant coverage is sufficient; "
                "otherwise NOT_YET_TESTABLE."
            ),
        },
    ]


def _render_report(summary: dict[str, Any], eox_profile_summary: pd.DataFrame) -> str:
    lines: list[str] = []
    lines.append("# Directive section 7 validation report")
    lines.append("")
    if summary["mock_non_physical"]:
        lines.append(
            "> ENGINE = MOCK. All numerical chemistry values in this report are NON-PHYSICAL; "
            "this is a deterministic workflow/test package only."
        )
        lines.append("")
    lines.append(f"- Engine: `{summary['engine']}`")
    lines.append(f"- Method: `{summary['production_method']}`")
    lines.append(f"- Harvest: `{summary['harvest_path']}`")
    lines.append(f"- Bootstrap seed: `{summary['bootstrap_seed']}`")
    lines.append("")
    lines.append("## Directive Metric Table")
    lines.append("")
    lines.append("| metric | directive target | observed value | n | status | caveat |")
    lines.append("| --- | --- | --- | ---: | --- | --- |")
    for row in summary["directive_status_table"]:
        lines.append(
            f"| {row['metric']} | {row['directive target']} | {row['observed value']} | "
            f"{row['n']} | {row['status']} | {row['caveat']} |"
        )
    lines.append("")
    lines.append("## Eox Profiles")
    lines.append("")
    lines.append(
        "| profile | active | default | n groups | LOO-CV MAE (V) | in-sample MAE (V) | R2 | status |"
    )
    lines.append("| --- | :---: | :---: | ---: | ---: | ---: | ---: | --- |")
    for _, row in eox_profile_summary.iterrows():
        lines.append(
            f"| {row.get('profile_name', '')} | {bool(row.get('is_active_production_profile', False))} | "
            f"{bool(row.get('is_config_default_profile', False))} | "
            f"{int(row.get('collapsed_calibration_group_count', 0) or 0)} | "
            f"{_fmt(row.get('loo_mae_after_V'))} | {_fmt(row.get('mae_after_V'))} | "
            f"{_fmt(row.get('r2'))} | {row.get('profile_status', '')} |"
        )
    lines.append("")
    lines.append("## ESW Gate")
    lines.append("")
    gate = summary["esw_gate"]
    lines.append(
        f"Unsafe widening count: {gate.get('unsafe_widening_count')} over "
        f"{gate.get('n_comparable')} comparable measured rows. "
        f"Maximum unsafe widening: {_fmt(gate.get('maximum_unsafe_widening_V'), ' V')}."
    )
    lines.append("")
    lines.append("## Feasibility")
    lines.append("")
    feas = summary["feasibility"]
    lines.append(
        f"Matched labels: {feas.get('n_matched')} of {feas.get('n_labels')} "
        f"({feas.get('n_yes')} YES / {feas.get('n_no')} NO total). "
        f"Confusion matrix TP={feas.get('tp')} FN={feas.get('fn')} "
        f"TN={feas.get('tn')} FP={feas.get('fp')}."
    )
    lines.append(
        f"Balanced accuracy: {_fmt_percent(feas.get('balanced_accuracy'))}; "
        f"bootstrap 95% interval: {feas.get('balanced_accuracy_bootstrap_95ci')}."
    )
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for label, path in summary["artifacts"].items():
        lines.append(f"- `{label}`: `{path}`")
    lines.append("")
    return "\n".join(lines)


def _fitted_profile_row(
    *,
    result: BenchmarkValidationResult,
    profile: dict[str, Any],
    profile_point_meta: dict[str, Any],
    ad_meta: dict[str, Any],
    raw_rows: int,
    is_active: bool,
    is_default: bool,
) -> dict[str, Any]:
    calibration_rows = result.rows.loc[result.rows["in_calibration_set"]].copy()
    worst = calibration_rows.assign(abs_residual=lambda df: df["residual_after_V"].abs()).sort_values(
        "abs_residual", ascending=False
    )
    worst_records = worst.head(5)[
        ["monomer_name", "solvent_name", "exp_Eox_V_vs_AgAgCl", "calibrated_Eox_V_vs_AgAgCl", "residual_after_V"]
    ].to_dict(orient="records")
    return {
        "profile_name": result.profile_name,
        "profile_status": "fit",
        "reference_frame": profile["reference_frame"],
        "label_types": "|".join(profile["label_types"]),
        "tiers": "|".join(profile["tiers"]),
        "media": "|".join(profile["media"]),
        "is_active_production_profile": is_active,
        "is_config_default_profile": is_default,
        "raw_literature_row_count": raw_rows,
        "calibration_eligible_row_count": int(calibration_rows.shape[0]),
        "benchmark_calibration_eligible_total": result.calibration_eligible_rows,
        "collapsed_calibration_group_count": result.n_calibration_points,
        "label_type_counts": _counts_json(calibration_rows, "label_type"),
        "medium_class_counts": _counts_json(calibration_rows, "medium_class"),
        "reliability_tier_counts": _counts_json(calibration_rows, "reliability_tier"),
        "chemical_family_coverage": _counts_json(calibration_rows, "chemical_family"),
        "slope": result.calibration.slope,
        "intercept": result.calibration.intercept,
        "r2": result.calibration.r2,
        "mae_before_V": result.mae_before_V,
        "mae_after_V": result.mae_after_V,
        "loo_mae_after_V": result.loo_mae_after_V,
        "residual_std_after_V": result.residual_std_after_V,
        "spearman_rho": result.spearman_rho,
        "within_group_spread_V": result.within_group_spread_V,
        "bootstrap_mae_after_95ci_V": _json_inline(profile_point_meta["bootstrap"]["mae_after_V_95ci"]),
        "bootstrap_loo_mae_after_95ci_V": _json_inline(
            profile_point_meta["bootstrap"]["loo_mae_after_V_95ci"]
        ),
        "bootstrap_n": profile_point_meta["bootstrap"]["n"],
        "worst_residuals": _json_inline(worst_records),
        "leverage_threshold_rule": "high_leverage_flag uses h_i > 2p/n for p=2 when n>2",
        "ad_descriptor_min_V": ad_meta.get("descriptor_domain_min_V"),
        "ad_descriptor_max_V": ad_meta.get("descriptor_domain_max_V"),
        "ad_library_solvent": ad_meta.get("library_descriptor_solvent"),
        "ad_ood_fraction_by_monomer_class": _json_inline(ad_meta.get("ood_fraction_by_monomer_class", {})),
        "reference_floor_note": (
            f"Observed MAE below {REFERENCE_FLOOR_V:.2f} V is not claimed below the "
            "reference/measurement floor."
        ),
    }


def _skipped_profile_row(
    *,
    profile_name: str,
    profile: dict[str, Any],
    status: str,
    raw_rows: int,
    is_active: bool,
    is_default: bool,
    message: str,
) -> dict[str, Any]:
    return {
        "profile_name": profile_name,
        "profile_status": status,
        "reference_frame": profile["reference_frame"],
        "label_types": "|".join(profile["label_types"]),
        "tiers": "|".join(profile["tiers"]),
        "media": "|".join(profile["media"]),
        "is_active_production_profile": is_active,
        "is_config_default_profile": is_default,
        "raw_literature_row_count": raw_rows,
        "calibration_eligible_row_count": 0,
        "benchmark_calibration_eligible_total": 0,
        "collapsed_calibration_group_count": 0,
        "label_type_counts": "{}",
        "medium_class_counts": "{}",
        "reliability_tier_counts": "{}",
        "chemical_family_coverage": "{}",
        "slope": None,
        "intercept": None,
        "r2": None,
        "mae_before_V": None,
        "mae_after_V": None,
        "loo_mae_after_V": None,
        "residual_std_after_V": None,
        "spearman_rho": None,
        "within_group_spread_V": None,
        "bootstrap_mae_after_95ci_V": "{}",
        "bootstrap_loo_mae_after_95ci_V": "{}",
        "bootstrap_n": 0,
        "worst_residuals": "[]",
        "leverage_threshold_rule": "",
        "ad_descriptor_min_V": None,
        "ad_descriptor_max_V": None,
        "ad_library_solvent": "",
        "ad_ood_fraction_by_monomer_class": "{}",
        "reference_floor_note": "",
        "skip_reason": message,
    }


def _profile_skip_status(message: str) -> str:
    if "benchmark validation requires at least two rows" in message:
        return "skipped_empty_benchmark"
    if "requires at least two calibration points" in message:
        return "skipped_insufficient_points"
    return "skipped_error"


def _active_profile_from_tier1(tier1_config: dict[str, Any], profiles: dict[str, Any]) -> str | None:
    source = str(tier1_config.get("calibration", {}).get("monomer_eox", {}).get("source", ""))
    for profile_name in profiles:
        if source.startswith(profile_name) or profile_name in source:
            return profile_name
    return None


def _conformer_config_from_tier1(tier1_config: dict[str, Any]) -> ConformerSearchConfig:
    section = tier1_config.get("conformer_search", {}) or {}
    return ConformerSearchConfig(
        enabled=bool(section.get("enabled", False)),
        n_conformers=int(section.get("n_conformers", 1)),
        method=str(section.get("method", "mmff94")),
    )


def _applicability_domain_status(value: float, low: float, high: float) -> tuple[str, float]:
    if not _is_finite(value):
        return "not-computable", float("nan")
    if value < low:
        return "below-domain", float(low - value)
    if value > high:
        return "above-domain", float(value - high)
    return "in-domain", 0.0


def _loo_predictions(predicted: np.ndarray, experimental: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if len(predicted) < 3:
        blank = np.full(len(predicted), np.nan)
        return blank, blank
    preds: list[float] = []
    for held_out in range(len(predicted)):
        mask = np.ones(len(predicted), dtype=bool)
        mask[held_out] = False
        fit = _linear_fit(predicted[mask], experimental[mask])
        preds.append(float(fit[0] * predicted[held_out] + fit[1]))
    pred_array = np.asarray(preds, dtype=float)
    return pred_array, pred_array - experimental


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    slope, intercept = np.polyfit(x, y, deg=1)
    return float(slope), float(intercept)


def _linear_influence(x: np.ndarray, residual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    if n == 0:
        return np.array([]), np.array([])
    centered = x - float(np.mean(x))
    denom = float(np.sum(centered**2))
    leverage = np.full(n, 1.0 / n)
    if denom > 0.0:
        leverage += (centered**2) / denom
    p = 2
    mse_denom = max(n - p, 1)
    mse = float(np.sum(residual**2) / mse_denom)
    if mse <= 0.0:
        cooks = np.zeros(n)
    else:
        cooks = (residual**2 / (p * mse)) * (leverage / np.maximum((1.0 - leverage) ** 2, 1e-12))
    return leverage, cooks


def _high_leverage_flags(leverage: np.ndarray) -> list[bool]:
    n = len(leverage)
    if n <= 2:
        return [False for _ in leverage]
    threshold = 4.0 / n
    return [bool(value > threshold) for value in leverage]


def _bootstrap_mean_ci(values: Any, *, seed: int) -> dict[str, Any]:
    finite = np.asarray(pd.to_numeric(pd.Series(values), errors="coerce").dropna(), dtype=float)
    finite = finite[np.isfinite(finite)]
    if len(finite) == 0:
        return _empty_bootstrap()
    rng = np.random.default_rng(seed)
    means = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    for idx in range(BOOTSTRAP_REPLICATES):
        sample = rng.choice(finite, size=len(finite), replace=True)
        means[idx] = float(np.mean(sample))
    return {
        "low": float(np.percentile(means, 2.5)),
        "high": float(np.percentile(means, 97.5)),
        "n": int(len(finite)),
    }


def _empty_bootstrap() -> dict[str, Any]:
    return {"low": None, "high": None, "n": 0}


def _feasibility_bootstrap_ci(matches: pd.DataFrame, *, seed: int) -> dict[str, Any]:
    if matches.empty:
        return _empty_bootstrap()
    yes = matches.loc[matches["outcome"] == "YES"].copy()
    no = matches.loc[matches["outcome"] == "NO"].copy()
    if yes.empty or no.empty:
        return _empty_bootstrap()
    rng = np.random.default_rng(seed)
    values = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    for idx in range(BOOTSTRAP_REPLICATES):
        y = yes.iloc[rng.integers(0, len(yes), size=len(yes))]
        n = no.iloc[rng.integers(0, len(no), size=len(no))]
        recall_yes = float((y["predicted"] == "YES").mean())
        recall_no = float((n["predicted"] == "NO").mean())
        values[idx] = (recall_yes + recall_no) / 2.0
    return {
        "low": float(np.percentile(values, 2.5)),
        "high": float(np.percentile(values, 97.5)),
        "n": int(len(matches)),
        "seed": seed,
        "replicates": BOOTSTRAP_REPLICATES,
        "stratified_by_outcome": True,
    }


def _feasibility_breakdown(matches: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    if matches.empty or column not in matches.columns:
        return []
    rows: list[dict[str, Any]] = []
    for value, group in matches.groupby(column, dropna=False, sort=True):
        rows.append({"group": str(value), **_confusion_from_matches(group)})
    return rows


def _confusion_from_matches(group: pd.DataFrame) -> dict[str, Any]:
    yes = group["outcome"] == "YES"
    predicted = group["predicted"] == "YES"
    tp = int((yes & predicted).sum())
    fn = int((yes & ~predicted).sum())
    tn = int((~yes & ~predicted).sum())
    fp = int((~yes & predicted).sum())
    recall_yes = tp / (tp + fn) if (tp + fn) else None
    recall_no = tn / (tn + fp) if (tn + fp) else None
    balanced = (recall_yes + recall_no) / 2.0 if recall_yes is not None and recall_no is not None else None
    return {
        "n": int(len(group)),
        "tp": tp,
        "fn": fn,
        "tn": tn,
        "fp": fp,
        "recall_yes": recall_yes,
        "recall_no": recall_no,
        "balanced_accuracy": balanced,
    }


def _esw_coverage_summary(diag: pd.DataFrame) -> dict[str, dict[str, Any]]:
    total = len(diag)
    exact = int((diag["measurement_match"] == "exact_salt_conservative").sum())
    solvent_only = int((diag["measurement_match"] == "solvent_only_conservative").sum())
    fallback = int((diag["measurement_match"] == "no_measurement_fallback").sum())
    return {
        "exact": _coverage_record(exact, total),
        "solvent_only": _coverage_record(solvent_only, total),
        "fallback": _coverage_record(fallback, total),
    }


def _coverage_record(count: int, total: int) -> dict[str, Any]:
    return {"count": count, "fraction": (count / total if total else None)}


def _survivor_coverage(survivors: pd.DataFrame) -> list[dict[str, Any]]:
    if survivors.empty:
        return []
    rows: list[dict[str, Any]] = []
    for keys, group in survivors.groupby(["solvent_name", "salt", "anion_smiles"], dropna=False, sort=True):
        solvent, salt, anion = keys
        rows.append(
            {
                "solvent_name": str(solvent),
                "salt": str(salt),
                "anion_smiles": str(anion),
                "n_survivor_rows": int(len(group)),
                "exact_salt_rows": int((group["measurement_match"] == "exact_salt_conservative").sum()),
                "solvent_only_rows": int((group["measurement_match"] == "solvent_only_conservative").sum()),
                "fallback_rows": int((group["measurement_match"] == "no_measurement_fallback").sum()),
            }
        )
    return rows


def _threshold_status(value: Any, target: float, n: int) -> str:
    if n <= 0 or not _is_finite(value):
        return STATUS_NOT_YET_TESTABLE
    return STATUS_PASS if float(value) <= target else STATUS_FAIL


def _feasibility_status(value: Any, n: int, meta: dict[str, Any]) -> str:
    if not meta.get("computable") or not _is_finite(value):
        return STATUS_NOT_YET_TESTABLE
    if n < FEASIBILITY_MIN_MATCHED_FOR_CLAIM:
        return STATUS_NOT_YET_TESTABLE
    return STATUS_PASS if float(value) >= 0.85 else STATUS_FAIL


def _provenance_record(
    *,
    summary: dict[str, Any],
    engine_name: str,
    method: str,
    cache_path: Path,
    harvest_path: str | Path | None,
    benchmark_path: str | Path,
    solvent_benchmark_path: str | Path,
    labels_path: str | Path,
    tier1_config_path: str | Path,
    validation_config_path: str | Path,
    profiles_path: str | Path,
) -> dict[str, Any]:
    inputs = {
        "benchmark_path": str(benchmark_path),
        "solvent_benchmark_path": str(solvent_benchmark_path),
        "labels_path": str(labels_path),
        "tier1_config_path": str(tier1_config_path),
        "validation_config_path": str(validation_config_path),
        "profiles_path": str(profiles_path),
        "harvest_path": str(harvest_path) if harvest_path is not None else None,
        "cache_path": str(cache_path),
    }
    hash_paths = [
        benchmark_path,
        solvent_benchmark_path,
        labels_path,
        tier1_config_path,
        validation_config_path,
        profiles_path,
    ]
    if harvest_path is not None:
        hash_paths.append(harvest_path)
    return {
        "engine": engine_name,
        "method": method,
        "mock_non_physical": summary["mock_non_physical"],
        "git": git_info(PROJECT_ROOT),
        "config_sha256": config_hashes(PROJECT_ROOT),
        "library_sizes": library_sizes(PROJECT_ROOT),
        "inputs": inputs,
        "input_sha256": {str(path): _sha256_or_missing(path) for path in hash_paths},
        "bootstrap_seed": summary["bootstrap_seed"],
        "numeric_tolerance_V": NUMERICAL_TOLERANCE_V,
        "directive_status_table": summary["directive_status_table"],
    }


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _csv_row_count(path: str | Path) -> int:
    try:
        return int(len(pd.read_csv(path, keep_default_na=False)))
    except Exception:  # noqa: BLE001 - row count is best-effort for skipped-profile reporting
        return 0


def _counts_json(frame: pd.DataFrame, column: str) -> str:
    if column not in frame.columns or frame.empty:
        return "{}"
    counts = {
        str(key): int(value)
        for key, value in frame[column].value_counts(dropna=False).sort_index().items()
    }
    return _json_inline(counts)


def _json_inline(value: Any) -> str:
    return json.dumps(_json_ready(value), sort_keys=True, separators=(",", ":"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_json_ready(value), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        value = float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, np.ndarray):
        return [_json_ready(item) for item in value.tolist()]
    if pd.isna(value) and value is not None:
        return None
    return value


def _seed_for(seed: int, label: str) -> int:
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()
    return seed + int(digest[:8], 16) % 100000


def _sha256_or_missing(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.exists():
        return "missing"
    return hashlib.sha256(candidate.read_bytes()).hexdigest()


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return number if math.isfinite(number) else float("nan")


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _abs_error(a: float, b: float) -> float:
    if not _is_finite(a) or not _is_finite(b):
        return float("nan")
    return abs(float(a) - float(b))


def _mean_or_none(values: Any) -> float | None:
    finite = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if finite.empty:
        return None
    return float(finite.mean())


def _max_or_none(values: Any) -> float | None:
    finite = pd.to_numeric(pd.Series(values), errors="coerce").dropna()
    if finite.empty:
        return None
    return float(finite.max())


def _max_or_zero(values: Any) -> float:
    value = _max_or_none(values)
    return 0.0 if value is None else value


def _fmt(value: Any, suffix: str = "") -> str:
    if not _is_finite(value):
        return "n/a"
    return f"{float(value):.3f}{suffix}"


def _fmt_percent(value: Any) -> str:
    if not _is_finite(value):
        return "n/a"
    return f"{float(value):.1%}"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

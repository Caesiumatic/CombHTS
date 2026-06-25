"""Operational calibration-role manifest validation.

This module does not define calibration coefficients. It checks that the production
Tier-1 coefficient source and the validation-profile defaults are disclosed and
internally consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from eps.validation.benchmark import load_calibration_profiles

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OPERATIONAL_MANIFEST = PROJECT_ROOT / "configs" / "calibration_operational.yaml"

SUPPORTED_SCHEMA_VERSION = 1
ALIGNED_STATE = "aligned"
INTENTIONAL_DIVERGENCE_STATES = {"intentionally_divergent_pending_evidence"}


@dataclass(frozen=True)
class OperationalCalibrationDisclosure:
    """Disclosure of production and validation calibration roles."""

    production_profile: str
    validation_default_profile: str
    relationship_state: str
    relationship_reason: str
    production_source: str
    selected_validation_profile: str
    selected_matches_production: bool
    selected_operational_role: str


def load_operational_calibration(
    *,
    project_root: str | Path = PROJECT_ROOT,
    manifest_path: str | Path | None = None,
    selected_validation_profile: str | None = None,
) -> OperationalCalibrationDisclosure:
    """Load and semantically validate the operational calibration manifest.

    Parameters
    ----------
    project_root:
        Repository root used to resolve manifest paths.
    manifest_path:
        Path to ``configs/calibration_operational.yaml`` or a test fixture equivalent.
    selected_validation_profile:
        Validation profile requested by a caller. ``None`` means the configured validation default.
    """

    root = Path(project_root)
    manifest_file = Path(manifest_path) if manifest_path is not None else root / "configs" / "calibration_operational.yaml"
    manifest = _load_yaml_mapping(manifest_file)

    schema_version = manifest.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"{manifest_file} schema_version must be {SUPPORTED_SCHEMA_VERSION}; got {schema_version!r}"
        )

    production = _required_mapping(manifest, "production", manifest_file)
    validation = _required_mapping(manifest, "validation", manifest_file)
    relationship = _required_mapping(manifest, "relationship", manifest_file)

    workflow = _required_string(production, "workflow", manifest_file)
    if workflow != "tier1":
        raise ValueError(f"{manifest_file} production.workflow must be 'tier1'; got {workflow!r}")
    production_profile = _required_string(production, "profile", manifest_file)
    coefficients_path = _required_relative_path(production, "coefficients_path", manifest_file)
    coefficients_key = _required_string(production, "coefficients_key", manifest_file)
    expected_source = _required_string(production, "expected_source", manifest_file)

    profiles_path = _required_relative_path(validation, "profiles_path", manifest_file)
    validation_default = _required_string(validation, "default_profile", manifest_file)

    relationship_state = _required_string(relationship, "state", manifest_file)
    relationship_reason = _required_string(relationship, "reason", manifest_file)
    _required_string(relationship, "production_role", manifest_file)
    _required_string(relationship, "validation_default_role", manifest_file)

    profile_config = load_calibration_profiles(root / profiles_path)
    profiles = profile_config["profiles"]
    if production_profile not in profiles:
        raise ValueError(
            f"{manifest_file} production profile {production_profile!r} is not defined in {profiles_path}"
        )
    if validation_default not in profiles:
        raise ValueError(
            f"{manifest_file} validation default {validation_default!r} is not defined in {profiles_path}"
        )
    actual_default = str(profile_config["default_screening_profile"])
    if actual_default != validation_default:
        raise ValueError(
            f"{profiles_path} default_screening_profile is {actual_default!r}, "
            f"but {manifest_file} declares {validation_default!r}"
        )

    tier1_config = _load_yaml_mapping(root / coefficients_path)
    coefficients = _mapping_at_key(tier1_config, coefficients_key, root / coefficients_path)
    if not bool(coefficients.get("enabled", False)):
        raise ValueError(f"{coefficients_path}:{coefficients_key} must contain enabled: true")
    actual_source = _required_string(coefficients, "source", root / coefficients_path)
    if actual_source != expected_source:
        raise ValueError(
            f"{coefficients_path}:{coefficients_key}.source is {actual_source!r}, "
            f"but manifest expects {expected_source!r}"
        )
    if not actual_source.startswith(f"{production_profile}_"):
        raise ValueError(
            f"{coefficients_path}:{coefficients_key}.source {actual_source!r} is not consistent "
            f"with production profile {production_profile!r}"
        )

    if production_profile == validation_default:
        if relationship_state != ALIGNED_STATE:
            raise ValueError(
                f"production/default profiles are aligned, so relationship.state must be {ALIGNED_STATE!r}"
            )
    elif relationship_state not in INTENTIONAL_DIVERGENCE_STATES:
        raise ValueError(
            "production/default profiles differ, so relationship.state must explicitly declare "
            f"intentional divergence; got {relationship_state!r}"
        )

    selected = selected_validation_profile or validation_default
    if selected not in profiles:
        known = ", ".join(sorted(profiles))
        raise ValueError(f"Unknown selected validation profile {selected!r}; known profiles: {known}")
    selected_matches_production = selected == production_profile
    selected_role = "tier1_production_profile" if selected_matches_production else "diagnostic_nonproduction"

    return OperationalCalibrationDisclosure(
        production_profile=production_profile,
        validation_default_profile=validation_default,
        relationship_state=relationship_state,
        relationship_reason=relationship_reason,
        production_source=actual_source,
        selected_validation_profile=selected,
        selected_matches_production=selected_matches_production,
        selected_operational_role=selected_role,
    )


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle)
    except Exception as exc:  # noqa: BLE001 - preserve config path context.
        raise ValueError(f"{path} is not valid YAML: {type(exc).__name__}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a mapping")
    return loaded


def _required_mapping(mapping: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must define mapping {key!r}")
    return value


def _required_string(mapping: dict[str, Any], key: str, path: Path) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must define nonempty string {key!r}")
    return value.strip()


def _required_relative_path(mapping: dict[str, Any], key: str, path: Path) -> Path:
    value = _required_string(mapping, key, path)
    relative = Path(value)
    if relative.is_absolute():
        raise ValueError(f"{path} field {key!r} must be repository-relative")
    return relative


def _mapping_at_key(mapping: dict[str, Any], dotted_key: str, path: Path) -> dict[str, Any]:
    value: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"{path} does not contain required mapping key {dotted_key!r}")
        value = value[part]
    if not isinstance(value, dict):
        raise ValueError(f"{path} key {dotted_key!r} must resolve to a mapping")
    return value

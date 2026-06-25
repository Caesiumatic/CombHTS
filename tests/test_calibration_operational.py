from __future__ import annotations

from pathlib import Path

import pytest

from eps.calibration.operational import load_operational_calibration
from eps.cli import main


def _write_project(
    root: Path,
    *,
    production_profile: str = "agagcl_peak_strict",
    validation_default: str = "agagcl_peak_relaxed",
    actual_default: str | None = None,
    source: str = "agagcl_peak_strict_2026_06_17_xtb_v3",
    relationship_state: str = "intentionally_divergent_pending_evidence",
    relationship_reason: str = "strict_vs_relaxed_peak_tiebreaker_pending_live_dft_loo_cv",
) -> Path:
    configs = root / "configs"
    configs.mkdir(parents=True)
    default = actual_default or validation_default
    (configs / "calibration_profiles.yaml").write_text(
        f"""
default_screening_profile: {default}

profiles:
  agagcl_peak_strict:
    reference_frame: agagcl
    label_types: [monomer_oxidation_peak]
    tiers: [A]
    media: [nonaqueous]
  agagcl_peak_relaxed:
    reference_frame: agagcl
    label_types: [monomer_oxidation_peak]
    tiers: [A, B]
    media: [nonaqueous]
""".lstrip(),
        encoding="utf-8",
    )
    (configs / "tier1.yaml").write_text(
        f"""
calibration:
  monomer_eox:
    enabled: true
    source: {source}
    slope: 1.0
    intercept: 0.0
""".lstrip(),
        encoding="utf-8",
    )
    manifest = configs / "calibration_operational.yaml"
    manifest.write_text(
        f"""
schema_version: 1
production:
  workflow: tier1
  profile: {production_profile}
  coefficients_path: configs/tier1.yaml
  coefficients_key: calibration.monomer_eox
  expected_source: {source}
validation:
  profiles_path: configs/calibration_profiles.yaml
  default_profile: {validation_default}
relationship:
  state: {relationship_state}
  reason: {relationship_reason}
  production_role: current_tier1_screening_truth
  validation_default_role: broader_diagnostic_validation_default
""".lstrip(),
        encoding="utf-8",
    )
    return manifest


def test_current_operational_manifest_is_valid() -> None:
    disclosure = load_operational_calibration()

    assert disclosure.production_profile == "agagcl_peak_strict"
    assert disclosure.validation_default_profile == "agagcl_peak_relaxed"
    assert disclosure.relationship_state == "intentionally_divergent_pending_evidence"
    assert disclosure.production_source == "agagcl_peak_strict_2026_06_17_xtb_v3"


def test_missing_required_manifest_key_fails(tmp_path: Path) -> None:
    manifest = _write_project(tmp_path)
    manifest.write_text(
        """
schema_version: 1
production:
  workflow: tier1
validation:
  profiles_path: configs/calibration_profiles.yaml
  default_profile: agagcl_peak_relaxed
relationship:
  state: intentionally_divergent_pending_evidence
  reason: strict_vs_relaxed_peak_tiebreaker_pending_live_dft_loo_cv
  production_role: current_tier1_screening_truth
  validation_default_role: broader_diagnostic_validation_default
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="profile"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_unknown_production_profile_fails(tmp_path: Path) -> None:
    manifest = _write_project(tmp_path, production_profile="missing_profile")

    with pytest.raises(ValueError, match="production profile"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_unknown_validation_default_fails(tmp_path: Path) -> None:
    manifest = _write_project(
        tmp_path,
        validation_default="missing_profile",
        actual_default="agagcl_peak_strict",
    )

    with pytest.raises(ValueError, match="validation default"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_actual_validation_default_differing_from_manifest_fails(tmp_path: Path) -> None:
    manifest = _write_project(tmp_path, actual_default="agagcl_peak_strict")

    with pytest.raises(ValueError, match="default_screening_profile"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_tier1_source_mismatch_fails(tmp_path: Path) -> None:
    manifest = _write_project(tmp_path)
    (tmp_path / "configs" / "tier1.yaml").write_text(
        """
calibration:
  monomer_eox:
    enabled: true
    source: agagcl_peak_relaxed_2026_06_17_xtb_v3
    slope: 1.0
    intercept: 0.0
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manifest expects"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_undeclared_production_default_divergence_fails(tmp_path: Path) -> None:
    manifest = _write_project(tmp_path, relationship_state="aligned")

    with pytest.raises(ValueError, match="intentional divergence"):
        load_operational_calibration(project_root=tmp_path, manifest_path=manifest)


def test_future_aligned_state_example_passes(tmp_path: Path) -> None:
    manifest = _write_project(
        tmp_path,
        production_profile="agagcl_peak_strict",
        validation_default="agagcl_peak_strict",
        actual_default="agagcl_peak_strict",
        relationship_state="aligned",
        relationship_reason="profiles_aligned_after_recorded_evidence",
    )

    disclosure = load_operational_calibration(project_root=tmp_path, manifest_path=manifest)

    assert disclosure.selected_matches_production
    assert disclosure.selected_operational_role == "tier1_production_profile"


def test_selected_production_profile_role() -> None:
    disclosure = load_operational_calibration(selected_validation_profile="agagcl_peak_strict")

    assert disclosure.selected_matches_production
    assert disclosure.selected_operational_role == "tier1_production_profile"


def test_selected_diagnostic_profile_role() -> None:
    disclosure = load_operational_calibration(selected_validation_profile="agagcl_peak_relaxed")

    assert not disclosure.selected_matches_production
    assert disclosure.selected_operational_role == "diagnostic_nonproduction"


def test_cli_default_profile_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "validate",
            "--engine",
            "mock",
            "--cache",
            str(tmp_path / "validation.sqlite"),
            "--report",
            str(tmp_path / "validation_report.csv"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Tier-1 production calibration profile: agagcl_peak_strict" in output
    assert "Validation calibration profile: agagcl_peak_relaxed" in output
    assert "Validation operational role: diagnostic_nonproduction" in output
    assert "WARNING: this validation profile is not the current Tier-1 production calibration" in output


def test_cli_explicit_production_profile_disclosure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "validate",
            "--engine",
            "mock",
            "--profile",
            "agagcl_peak_strict",
            "--cache",
            str(tmp_path / "validation.sqlite"),
            "--report",
            str(tmp_path / "validation_report.csv"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Validation calibration profile: agagcl_peak_strict" in output
    assert "Validation operational role: tier1_production_profile" in output
    assert "not the current Tier-1 production calibration" not in output


def test_cli_all_profile_disclosure(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "validate",
            "--engine",
            "mock",
            "--all-profiles",
            "--cache",
            str(tmp_path / "validation.sqlite"),
            "--report",
            str(tmp_path / "validation_report.csv"),
            "--profile-comparison",
            str(tmp_path / "profile_comparison.csv"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Tier-1 production calibration profile: agagcl_peak_strict" in output
    assert "Configured validation default profile: agagcl_peak_relaxed" in output
    assert "Calibration relationship: intentionally_divergent_pending_evidence" in output
    assert "compares independent fits and does not alter production" in output

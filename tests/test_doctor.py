from __future__ import annotations

from pathlib import Path

from eps.cli import main
from eps.doctor import FAIL, PASS, WARN, run_doctor


def test_doctor_runs_and_reports_valid_statuses() -> None:
    report = run_doctor()

    assert report.checks
    valid = {PASS, WARN, FAIL}
    assert all(check.status in valid for check in report.checks)

    # In a complete checkout the configs and data are present (hard requirements).
    by_name = {check.name: check for check in report.checks}
    assert by_name["python"].status == PASS
    assert by_name["config:configs/tier1.yaml"].status == PASS
    assert by_name["config:configs/calibration_operational.yaml"].status == PASS
    assert by_name["calibration:operational-truth"].status == PASS
    assert "production=agagcl_peak_strict" in by_name["calibration:operational-truth"].detail
    assert "validation_default=agagcl_peak_relaxed" in by_name["calibration:operational-truth"].detail
    assert by_name["data:data/monomers.csv"].status == PASS

    # Cluster binaries are WARN or PASS, never FAIL (they are cluster-only).
    assert by_name["binary:xtb"].status in {PASS, WARN}
    assert by_name["binary:g16"].status in {PASS, WARN}
    assert by_name["binary:orca"].status in {PASS, WARN}
    assert by_name["config:configs/orca_pilots.yaml"].status == PASS
    assert by_name["data:data/solvent_windows.csv"].status == PASS

    # Tier-2 readiness: g16 availability (cluster-only -> never FAIL) and the effective method.
    assert by_name["tier2:g16"].status in {PASS, WARN}
    tier2_config = by_name["tier2:config"]
    assert tier2_config.status == PASS  # shipped configs/tier2.yaml loads in a complete checkout
    assert "B3LYP/6-31G(d,p)" in tier2_config.detail
    assert "gas phase" in tier2_config.detail
    assert "opt only" in tier2_config.detail


def test_doctor_tier2_config_warns_when_absent(tmp_path: Path) -> None:
    from eps.doctor import run_doctor as _run

    report = _run(tmp_path)  # empty dir: no configs/tier2.yaml
    by_name = {check.name: check for check in report.checks}
    assert by_name["tier2:config"].status == WARN
    assert by_name["tier2:g16"].status in {PASS, WARN}


def test_doctor_flags_missing_configs_and_data_without_raising(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)  # empty dir: no configs, no data

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["config:configs/tier1.yaml"] == FAIL
    assert statuses["data:data/monomers.csv"] == FAIL
    assert report.has_failure


def test_doctor_flags_operational_calibration_inconsistency(tmp_path: Path) -> None:
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "tier1.yaml").write_text(
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
    (configs / "calibration_profiles.yaml").write_text(
        """
default_screening_profile: agagcl_peak_relaxed
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
    (configs / "calibration_operational.yaml").write_text(
        """
schema_version: 1
production:
  workflow: tier1
  profile: agagcl_peak_strict
  coefficients_path: configs/tier1.yaml
  coefficients_key: calibration.monomer_eox
  expected_source: agagcl_peak_strict_2026_06_17_xtb_v3
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

    report = run_doctor(tmp_path)
    check = {item.name: item for item in report.checks}["calibration:operational-truth"]

    assert check.status == FAIL
    assert "semantic inconsistency" in check.detail


def test_doctor_cli_runs_without_raising() -> None:
    # Complete checkout -> no FAIL -> exit code 0.
    assert main(["doctor"]) == 0

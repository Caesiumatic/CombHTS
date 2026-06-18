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
    assert by_name["data:data/monomers.csv"].status == PASS

    # Cluster binaries are WARN or PASS, never FAIL (they are cluster-only).
    assert by_name["binary:xtb"].status in {PASS, WARN}
    assert by_name["binary:g16"].status in {PASS, WARN}


def test_doctor_flags_missing_configs_and_data_without_raising(tmp_path: Path) -> None:
    report = run_doctor(tmp_path)  # empty dir: no configs, no data

    statuses = {check.name: check.status for check in report.checks}
    assert statuses["config:configs/tier1.yaml"] == FAIL
    assert statuses["data:data/monomers.csv"] == FAIL
    assert report.has_failure


def test_doctor_cli_runs_without_raising() -> None:
    # Complete checkout -> no FAIL -> exit code 0.
    assert main(["doctor"]) == 0

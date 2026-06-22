from __future__ import annotations

import json
from pathlib import Path

from eps.provenance import config_hashes, git_info, write_provenance


def test_write_provenance_has_expected_keys(tmp_path: Path) -> None:
    sidecar = write_provenance(
        tmp_path / "out.csv",
        engine="mock",
        method="mock-gfn2",
        extra={"command": "unit-test"},
    )

    assert sidecar.name == "out.csv.provenance.json"
    record = json.loads(sidecar.read_text(encoding="utf-8"))

    assert set(record) >= {
        "output",
        "timestamp_utc",
        "eps_version",
        "engine",
        "method",
        "git",
        "config_sha256",
        "library_sizes",
        "extra",
    }
    assert record["output"] == "out.csv"
    assert record["engine"] == "mock"
    assert record["method"] == "mock-gfn2"
    assert set(record["git"]) == {"commit", "commit_short", "dirty"}
    # The pinned config files exist in the repo, so their hashes are real 64-hex digests.
    assert "configs/tier1.yaml" in record["config_sha256"]
    assert len(record["config_sha256"]["configs/tier1.yaml"]) == 64
    # Library sizes are integers when the CSVs are present.
    assert all(isinstance(v, int) for v in record["library_sizes"].values())


def test_config_hashes_are_stable_across_calls() -> None:
    first = config_hashes()
    second = config_hashes()
    assert first == second
    assert set(first) == {
        "configs/tier1.yaml",
        "configs/scoring.yaml",
        "configs/calibration_profiles.yaml",
        "configs/validation.yaml",
        "configs/orca_pilots.yaml",
    }


def test_git_info_degrades_to_unknown_outside_a_repo(tmp_path: Path) -> None:
    info = git_info(tmp_path)  # tmp_path is not a git repository
    assert info == {"commit": "unknown", "commit_short": "unknown", "dirty": "unknown"}


def test_config_hashes_missing_file_marked_missing(tmp_path: Path) -> None:
    # An empty project root has none of the configs -> all "missing", no raise.
    hashes = config_hashes(tmp_path)
    assert set(hashes.values()) == {"missing"}

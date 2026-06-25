from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script():
    script = Path("scripts/benchmark_conformer_parallelism.py").resolve()
    spec = importlib.util.spec_from_file_location("benchmark_conformer_parallelism", script)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_conformer_benchmark_parser_smoke() -> None:
    module = _load_script()

    args = module.build_parser().parse_args(
        ["--monomer", "thiophene", "--oligomer-length", "1", "--conformers", "2"]
    )

    assert args.monomer == "thiophene"
    assert args.oligomer_length == 1
    assert args.conformers == 2


def test_conformer_benchmark_writes_local_diagnostic_json(tmp_path: Path) -> None:
    module = _load_script()
    output = tmp_path / "conformer_benchmark.json"

    exit_code = module.main(
        [
            "--monomer",
            "thiophene",
            "--oligomer-length",
            "1",
            "--conformers",
            "2",
            "--threads",
            "1",
            "--repeats",
            "1",
            "--output-json",
            str(output),
        ]
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert data["label"] == "local engineering diagnostic; not a production or scientific result"
    assert data["monomer"] == "thiophene"
    assert data["conformer_count_requested"] == 2
    assert data["runs"][0]["embedding_success"] is True
    assert data["runs"][0]["conformer_count_embedded"] == 2
    assert data["environment"]["rdkit_version"]

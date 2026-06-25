from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from eps.cli import build_parser, main
from eps.validation.benchmark import (
    DEFAULT_CACHE_PATH as DEFAULT_VALIDATION_CACHE_PATH,
)
from eps.validation.directive import DEFAULT_DIRECTIVE_CACHE, DEFAULT_DIRECTIVE_OUTDIR
from eps.workflow.tier1 import DEFAULT_CACHE_PATH, DEFAULT_OUTPUT_PATH
from eps.workflow.tier2 import (
    DEFAULT_TIER2_HARVEST_OUTPUT,
    DEFAULT_TIER2_HARVEST_REPORT,
    DEFAULT_TIER2_PLAN_OUTDIR,
    DEFAULT_TIER2_TASK_RESULTS_DIR,
    DEFAULT_TIER2_WORK_ROOT,
)


def _subcommand_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    return next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))


def test_public_subcommand_set_is_locked() -> None:
    parser = build_parser()

    assert set(_subcommand_action(parser).choices) == {
        "analyze",
        "calibrate-dft",
        "doctor",
        "memo",
        "orca-pilot-optical",
        "orca-pilot-solvation",
        "orca-pilot-solvation-grid",
        "rescore-tier1",
        "run-tier1",
        "sanity",
        "tier2",
        "tier2-harvest",
        "tier2-plan",
        "tier2-run-task",
        "tier2-screen",
        "tier3",
        "validate",
        "validate-directive",
    }


def test_run_tier1_public_defaults_are_locked() -> None:
    args = build_parser().parse_args(["run-tier1"])

    assert args.command == "run-tier1"
    assert args.engine == "mock"
    assert args.cache == DEFAULT_CACHE_PATH
    assert args.output == DEFAULT_OUTPUT_PATH
    assert args.all_output is None


def test_validate_public_defaults_are_locked() -> None:
    args = build_parser().parse_args(["validate"])

    assert args.command == "validate"
    assert args.engine == "mock"
    assert args.cache == DEFAULT_VALIDATION_CACHE_PATH
    assert args.profile is None
    assert args.all_profiles is False


def test_validate_directive_requires_harvest_and_keeps_defaults() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["validate-directive"])
    assert excinfo.value.code == 2

    args = parser.parse_args(["validate-directive", "--harvest", "outputs/tier1_all.csv"])
    assert args.command == "validate-directive"
    assert args.engine == "mock"
    assert args.harvest == Path("outputs/tier1_all.csv")
    assert args.cache == DEFAULT_DIRECTIVE_CACHE
    assert args.outdir == DEFAULT_DIRECTIVE_OUTDIR


def test_tier2_public_command_identities_and_required_args_are_locked() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["tier2-plan"])
    plan = parser.parse_args(["tier2-plan", "--selection", "selection.csv"])
    assert plan.command == "tier2-plan"
    assert plan.selection == Path("selection.csv")
    assert plan.config == Path("configs/tier2.yaml")
    assert plan.outdir == DEFAULT_TIER2_PLAN_OUTDIR

    with pytest.raises(SystemExit):
        parser.parse_args(["tier2-run-task", "--manifest", "task_manifest.csv"])
    run_task = parser.parse_args(
        ["tier2-run-task", "--manifest", "task_manifest.csv", "--task-id", "task-0001"]
    )
    assert run_task.command == "tier2-run-task"
    assert run_task.engine == "mock"
    assert run_task.result_dir == DEFAULT_TIER2_TASK_RESULTS_DIR
    assert run_task.work_root == DEFAULT_TIER2_WORK_ROOT
    assert run_task.cache is None

    with pytest.raises(SystemExit):
        parser.parse_args(["tier2-harvest"])
    harvest = parser.parse_args(["tier2-harvest", "--manifest", "task_manifest.csv"])
    assert harvest.command == "tier2-harvest"
    assert harvest.result_dir == DEFAULT_TIER2_TASK_RESULTS_DIR
    assert harvest.output == DEFAULT_TIER2_HARVEST_OUTPUT
    assert harvest.report == DEFAULT_TIER2_HARVEST_REPORT


def test_doctor_command_identity_is_locked() -> None:
    args = build_parser().parse_args(["doctor"])

    assert args.command == "doctor"


def test_invalid_command_exits_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_parser().parse_args(["not-a-command"])

    assert excinfo.value.code != 0


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["run-tier1", "--help"],
        ["validate", "--help"],
        ["validate-directive", "--help"],
        ["doctor", "--help"],
        ["tier2-plan", "--help"],
        ["tier2-run-task", "--help"],
        ["tier2-harvest", "--help"],
    ],
)
def test_help_remains_available(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(argv)

    assert excinfo.value.code == 0

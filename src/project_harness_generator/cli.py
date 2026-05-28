"""Command-line interface for Project Harness Generator."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from collections.abc import Sequence

from .inspection import InspectionError, format_inspection, inspect_repository


COMMANDS_WITH_TARGET = {
    "inspect": "Inspect a target repository without modifying it.",
    "generate": "Preview or apply a generated project harness.",
    "check": "Validate an existing generated harness.",
    "update": "Preview or apply conservative harness updates.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-harness",
        description="Generate project-specific agent harnesses from inspected project context.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="command", required=True)

    for command, help_text in COMMANDS_WITH_TARGET.items():
        command_parser = subparsers.add_parser(command, help=help_text)
        command_parser.add_argument("target")
        if command == "inspect":
            command_parser.add_argument(
                "--verify-commands",
                action="store_true",
                help="Run bounded non-invasive command verification probes.",
            )
            command_parser.add_argument(
                "--run-checks",
                action="store_true",
                help="Run detected project checks such as tests and builds.",
            )

    new_run = subparsers.add_parser("new-run", help="Create an isolated run skeleton.")
    new_run.add_argument("target")
    new_run.add_argument("slug")

    approve = subparsers.add_parser("approve", help="Record a deterministic approval marker.")
    approve.add_argument("target")
    approve.add_argument("run_id")
    approve.add_argument("gate_id")

    advance = subparsers.add_parser("advance", help="Advance a run stage after validation.")
    advance.add_argument("target")
    advance.add_argument("run_id")
    advance.add_argument("stage_id")

    skip_stage = subparsers.add_parser("skip-stage", help="Record an approved or non-applicable stage skip.")
    skip_stage.add_argument("target")
    skip_stage.add_argument("run_id")
    skip_stage.add_argument("stage_id")

    pause = subparsers.add_parser("pause", help="Pause a run with a next action.")
    pause.add_argument("target")
    pause.add_argument("run_id")

    resume = subparsers.add_parser("resume", help="Resume a paused run.")
    resume.add_argument("target")
    resume.add_argument("run_id")

    promote = subparsers.add_parser("promote", help="Promote a run artifact to a durable path.")
    promote.add_argument("target")
    promote.add_argument("run_id")
    promote.add_argument("source")
    promote.add_argument("destination")

    config = subparsers.add_parser("config", help="Manage local config; use 'config validate'.")
    config_subparsers = config.add_subparsers(
        dest="config_command",
        metavar="config_command",
        required=True,
    )
    config_validate = config_subparsers.add_parser("validate", help="Validate local config.")
    config_validate.add_argument("path", nargs="?")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect":
        return _run_inspect(
            args.target,
            verify_commands=args.verify_commands,
            run_checks=args.run_checks,
        )
    command = args.command
    if command == "config":
        command = f"{command} {args.config_command}"
    print(f"project-harness: command '{command}' is not implemented yet", file=sys.stderr)
    return 2


def _run_inspect(target: str, *, verify_commands: bool, run_checks: bool) -> int:
    try:
        result = inspect_repository(
            Path(target),
            verify_commands=verify_commands,
            run_checks=run_checks,
        )
    except InspectionError as exc:
        print(f"project-harness inspect: {exc}", file=sys.stderr)
        return 2
    print(format_inspection(result), end="")
    return 0

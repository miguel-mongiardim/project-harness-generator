"""Command-line interface for Project Harness Generator."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from collections.abc import Sequence

from .config import ConfigError, apply_config_overrides, format_config, load_config
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
        elif command == "generate":
            _add_prd_plan_workflow_options(command_parser)
        elif command == "update":
            command_parser.add_argument(
                "--update-policy",
                choices=("conservative", "manual_only", "detached"),
                help="Override the configured update policy for this command.",
            )

    new_run = subparsers.add_parser("new-run", help="Create an isolated run skeleton.")
    new_run.add_argument("target")
    new_run.add_argument("slug")
    _add_prd_plan_workflow_options(new_run)

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


def _add_prd_plan_workflow_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prd-path", help="Override the configured default PRD path.")
    parser.add_argument("--plan-path", help="Override the configured default plan path.")
    parser.add_argument(
        "--workflow-id",
        choices=("prd-plan-tdd",),
        help="Override the configured workflow id.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect":
        return _run_inspect(
            args.target,
            verify_commands=args.verify_commands,
            run_checks=args.run_checks,
        )
    if args.command == "config" and args.config_command == "validate":
        config_path = Path(args.path) if args.path is not None else None
        return _run_config_validate(config_path)
    if args.command == "generate":
        return _run_configured_command(
            command_name="generate",
            heading="Generate",
            target=args.target,
            workflow_id=args.workflow_id,
            default_prd_path=args.prd_path,
            default_plan_path=args.plan_path,
            pending_behavior="harness rendering is not implemented in this phase",
        )
    if args.command == "update":
        return _run_configured_command(
            command_name="update",
            heading="Update",
            target=args.target,
            update_policy=args.update_policy,
            pending_behavior="harness update planning is not implemented in this phase",
        )
    if args.command == "new-run":
        return _run_configured_command(
            command_name="new-run",
            heading="New Run",
            target=args.target,
            workflow_id=args.workflow_id,
            default_prd_path=args.prd_path,
            default_plan_path=args.plan_path,
            pending_behavior="run creation is not implemented in this phase",
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


def _run_config_validate(config_path: Path | None) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"project-harness config validate: {exc}", file=sys.stderr)
        return 2
    print(format_config(config), end="")
    return 0


def _run_configured_command(
    command_name: str,
    heading: str,
    target: str,
    *,
    workflow_id: str | None = None,
    default_prd_path: str | None = None,
    default_plan_path: str | None = None,
    update_policy: str | None = None,
    pending_behavior: str,
) -> int:
    try:
        config = apply_config_overrides(
            load_config(),
            workflow_id=workflow_id,
            default_prd_path=default_prd_path,
            default_plan_path=default_plan_path,
            update_policy=update_policy,
        )
    except ConfigError as exc:
        print(f"project-harness {command_name}: {exc}", file=sys.stderr)
        return 2

    print(f"Project Harness {heading}")
    print(f"Target: {Path(target).resolve()}")
    print("")
    print(format_config(config), end="")
    print("")
    print(f"No files written; {pending_behavior}.")
    return 0

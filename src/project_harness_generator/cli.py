"""Command-line interface for Project Harness Generator."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from collections.abc import Sequence

from .config import ConfigError, apply_config_overrides, format_config, load_config
from .inspection import InspectionError, format_inspection, inspect_repository
from .render_plan import (
    ApplyError,
    apply_render_plan,
    build_render_plan,
    check_harness,
    format_apply_result,
    format_check_result,
    format_render_plan,
)
from .runs import (
    RunError,
    create_run,
    format_new_run_result,
    format_run_state_result,
    pause_run,
    resume_run,
)


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
            command_parser.add_argument(
                "--apply",
                action="store_true",
                help="Write the generated harness after preview planning and safety checks.",
            )
            command_parser.add_argument(
                "--allow-non-git",
                action="store_true",
                help="Explicitly waive the Git worktree requirement for apply.",
            )
            command_parser.add_argument(
                "--update-policy",
                choices=("conservative", "manual_only", "detached"),
                help="Override the configured update policy for generated harness provenance.",
            )
        elif command == "update":
            command_parser.add_argument(
                "--update-policy",
                choices=("conservative", "manual_only", "detached"),
                help="Override the configured update policy for this command.",
            )

    new_run = subparsers.add_parser("new-run", help="Create an isolated run skeleton.")
    new_run.add_argument("target")
    new_run.add_argument("slug")
    new_run.add_argument(
        "--classification",
        choices=("trivial", "minor", "non-trivial"),
        required=True,
        help="Task classification for the run.",
    )
    new_run.add_argument("--date", help="Override the run date using YYYY-MM-DD.")
    new_run.add_argument("--source-branch", help="Record the source branch for this run.")
    new_run.add_argument(
        "--branch-waiver",
        help="Record the branch policy waiver reason for this run.",
    )
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
    pause.add_argument("--next-action", required=True, help="Next action to record.")

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
        return _run_generate(
            target=args.target,
            workflow_id=args.workflow_id,
            default_prd_path=args.prd_path,
            default_plan_path=args.plan_path,
            update_policy=args.update_policy,
            apply=args.apply,
            allow_non_git=args.allow_non_git,
        )
    if args.command == "check":
        return _run_check(args.target)
    if args.command == "update":
        return _run_configured_command(
            command_name="update",
            heading="Update",
            target=args.target,
            update_policy=args.update_policy,
            pending_behavior="harness update planning is not implemented in this phase",
        )
    if args.command == "new-run":
        return _run_new_run(
            target=args.target,
            slug=args.slug,
            classification=args.classification,
            created_date=args.date,
            source_branch=args.source_branch,
            branch_waiver=args.branch_waiver,
            workflow_id=args.workflow_id,
            default_prd_path=args.prd_path,
            default_plan_path=args.plan_path,
        )
    if args.command == "pause":
        return _run_pause(args.target, args.run_id, next_action=args.next_action)
    if args.command == "resume":
        return _run_resume(args.target, args.run_id)
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


def _run_generate(
    target: str,
    *,
    workflow_id: str | None,
    default_prd_path: str | None,
    default_plan_path: str | None,
    update_policy: str | None,
    apply: bool,
    allow_non_git: bool,
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
        print(f"project-harness generate: {exc}", file=sys.stderr)
        return 2

    try:
        inspection = inspect_repository(Path(target))
    except InspectionError as exc:
        print(f"project-harness generate: {exc}", file=sys.stderr)
        return 2

    render_plan = build_render_plan(Path(target), inspection, config)
    if apply:
        try:
            apply_result = apply_render_plan(render_plan, allow_non_git=allow_non_git)
        except ApplyError as exc:
            print(f"project-harness generate: {exc}", file=sys.stderr)
            return 2
        print("Project Harness Generate Apply")
        print(f"Target: {render_plan.target}")
        print("")
        print(format_config(config), end="")
        print("")
        print(format_apply_result(apply_result), end="")
        return 0

    print("Project Harness Generate Preview")
    print(f"Target: {render_plan.target}")
    print("")
    print(format_config(config), end="")
    print("")
    print(format_render_plan(render_plan), end="")
    print("")
    print("No files written.")
    return 0


def _run_check(target: str) -> int:
    result = check_harness(Path(target))
    print(format_check_result(result), end="")
    return 0 if result.status == "passed" else 2


def _run_new_run(
    target: str,
    slug: str,
    *,
    classification: str,
    created_date: str | None,
    source_branch: str | None,
    branch_waiver: str | None,
    workflow_id: str | None,
    default_prd_path: str | None,
    default_plan_path: str | None,
) -> int:
    try:
        config = apply_config_overrides(
            load_config(),
            workflow_id=workflow_id,
            default_prd_path=default_prd_path,
            default_plan_path=default_plan_path,
        )
    except ConfigError as exc:
        print(f"project-harness new-run: {exc}", file=sys.stderr)
        return 2

    try:
        result = create_run(
            Path(target),
            slug,
            classification=classification,
            created_date=created_date,
            source_branch=source_branch,
            branch_waiver=branch_waiver,
            config=config,
        )
    except RunError as exc:
        print(f"project-harness new-run: {exc}", file=sys.stderr)
        return 2

    print(format_new_run_result(result), end="")
    return 0


def _run_pause(target: str, run_id: str, *, next_action: str) -> int:
    try:
        result = pause_run(Path(target), run_id, next_action=next_action)
    except RunError as exc:
        print(f"project-harness pause: {exc}", file=sys.stderr)
        return 2
    print(format_run_state_result("Pause", result), end="")
    return 0


def _run_resume(target: str, run_id: str) -> int:
    try:
        result = resume_run(Path(target), run_id)
    except RunError as exc:
        print(f"project-harness resume: {exc}", file=sys.stderr)
        return 2
    print(format_run_state_result("Resume", result), end="")
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

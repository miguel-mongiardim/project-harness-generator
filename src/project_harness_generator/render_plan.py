"""Render plans, apply behavior, and validation for generated harness files."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from .config import UserConfig
from .inspection import Finding, InspectionResult
from . import __version__

import yaml


STAGE_IDS = (
    "00_project_discovery",
    "01_grill_context",
    "02_prd",
    "03_plan",
    "04_tdd_slice",
    "05_phase_review",
    "06_harness_learning",
)

REFERENCE_FILES = (
    "project.md",
    "architecture.md",
    "commands.md",
    "testing.md",
    "workflow_classification.md",
    "quality_bar.md",
    "automation_limits.md",
    "security.md",
    "dependency_policy.md",
    "check_instructions.md",
    "codex_workspace.md",
    "stack_generic.md",
    "stack_python.md",
)

TEMPLATE_FILES = (
    "current_snapshot.md",
    "context_summary.md",
    "decision_register.md",
    "phase_review.md",
    "harness_learning.md",
    "run_metadata.yaml",
    "stage.yaml",
    "module_context.md",
    "promotion_record.md",
    "next_action.md",
)

SCRIPT_FILES = (
    "check_harness.py",
    "create_run.py",
    "promote_artifact.py",
)

REQUIRED_GITIGNORE_ENTRIES = (
    ".agent-harness/runs/",
    ".agent-harness/tmp/",
)
GENERATOR_NAME = "project-harness-generator"
TEMPLATE_VERSION = "v0"
SELF_HASH_PLACEHOLDER = "SELF_HASH_PLACEHOLDER"
PROVENANCE_NOTICE = (
    "Human edits are allowed; preview-first updates must protect them."
)
STAGE_TITLES = {
    "00_project_discovery": "Project Discovery",
    "01_grill_context": "Grill Context",
    "02_prd": "PRD",
    "03_plan": "Plan",
    "04_tdd_slice": "TDD Slice",
    "05_phase_review": "Phase Review",
    "06_harness_learning": "Harness Learning",
}
REQUIRED_STAGE_MANIFEST_FIELDS = {
    "stage_id",
    "title",
    "required_inputs",
    "required_outputs",
    "required_gates",
    "required_skills",
    "fallback_procedure",
    "verification",
    "next_stage",
    "completion_criteria",
}
REQUIRED_STAGE_MARKDOWN_HEADINGS = (
    "## Purpose",
    "## Inputs",
    "## Process",
    "## Outputs",
    "## Approval Gates",
    "## Verification",
    "## Required Skills",
    "## Fallback",
    "## Completion Criteria",
)
RUN_STATUS_VALUES = {"active", "paused", "completed", "abandoned"}
STAGE_STATUS_VALUES = {"pending", "active", "complete", "skipped"}


@dataclass(frozen=True)
class PlannedFile:
    path: str
    category: str
    status: str
    provenance_status: str
    content: str


@dataclass(frozen=True)
class GitignoreEntryPlan:
    entry: str
    path: str
    status: str
    reason: str


@dataclass(frozen=True)
class RenderPlan:
    target: Path
    files: tuple[PlannedFile, ...]
    gitignore_entries: tuple[GitignoreEntryPlan, ...]


@dataclass(frozen=True)
class ApplyResult:
    target: Path
    files_written: tuple[str, ...]
    gitignore_entries_written: tuple[str, ...]
    git_worktree_waiver: bool


@dataclass(frozen=True)
class CheckIssue:
    path: str
    message: str


@dataclass(frozen=True)
class CheckResult:
    target: Path
    status: str
    issues: tuple[CheckIssue, ...]


class ApplyError(Exception):
    """Raised when a render plan cannot be safely applied."""


def build_render_plan(
    target: Path,
    inspection: InspectionResult,
    config: UserConfig,
) -> RenderPlan:
    target = target.resolve()
    planned_files: list[PlannedFile] = []
    gitignore_entries = _required_gitignore_entries(target)
    generated_content = _render_generated_content(inspection, config)
    for relative_path, category in _planned_file_specs():
        content = generated_content[relative_path]
        status = _planned_file_status(target, relative_path, content)
        planned_files.append(
            PlannedFile(
                path=relative_path,
                category=category,
                status=status,
                provenance_status=_provenance_status(status),
                content=content,
            )
        )
    gitignore_status = (
        "unchanged"
        if all(entry.status == "unchanged" for entry in gitignore_entries)
        else "ignored-state-related"
    )
    planned_files.append(
        PlannedFile(
            path=".gitignore",
            category="ignore-policy",
            status=gitignore_status,
            provenance_status=_provenance_status(gitignore_status),
            content=_preview_gitignore_content(gitignore_entries),
        )
    )

    return RenderPlan(
        target=target,
        files=tuple(planned_files),
        gitignore_entries=gitignore_entries,
    )


def apply_render_plan(plan: RenderPlan, *, allow_non_git: bool = False) -> ApplyResult:
    if not allow_non_git and not _looks_like_git_worktree(plan.target):
        raise ApplyError(
            "apply requires a Git worktree; initialize Git or pass an explicit waiver"
        )

    conflicts = [planned_file.path for planned_file in plan.files if planned_file.status == "conflicted"]
    if conflicts:
        first_conflict = conflicts[0]
        raise ApplyError(
            f"cannot apply because existing harness path is conflicted: {first_conflict}"
        )

    files_written: list[str] = []
    for planned_file in plan.files:
        if planned_file.path == ".gitignore":
            continue
        if planned_file.status != "addable":
            continue
        output_path = plan.target / planned_file.path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(planned_file.content, encoding="utf-8")
        files_written.append(planned_file.path)

    gitignore_entries_written = _apply_gitignore_entries(
        plan.target / ".gitignore",
        plan.gitignore_entries,
    )
    if gitignore_entries_written:
        files_written.append(".gitignore")

    return ApplyResult(
        target=plan.target,
        files_written=tuple(files_written),
        gitignore_entries_written=tuple(gitignore_entries_written),
        git_worktree_waiver=allow_non_git and not _looks_like_git_worktree(plan.target),
    )


def format_apply_result(result: ApplyResult) -> str:
    lines = [
        f"git_worktree_waiver: {_format_bool(result.git_worktree_waiver)}",
        "files_written:",
    ]
    if not result.files_written:
        lines.append("- none")
    for path in result.files_written:
        lines.append(f"- path: {path}")
    lines.append("gitignore_entries_written:")
    if not result.gitignore_entries_written:
        lines.append("- none")
    for entry in result.gitignore_entries_written:
        lines.append(f"- entry: {entry}")
    return "\n".join(lines).rstrip() + "\n"


def check_harness(target: Path) -> CheckResult:
    target = target.expanduser().resolve()
    issues: list[CheckIssue] = []
    if not target.exists():
        return CheckResult(
            target=target,
            status="failed",
            issues=(CheckIssue(".", f"target path does not exist: {target}"),),
        )
    if not target.is_dir():
        return CheckResult(
            target=target,
            status="failed",
            issues=(CheckIssue(".", f"target path is not a directory: {target}"),),
        )

    required_paths = [path for path, _category in _planned_file_specs()]
    for relative_path in required_paths:
        if not (target / relative_path).exists():
            issues.append(CheckIssue(relative_path, "required harness file is missing"))

    _check_gitignore_policy(target, issues)
    manifest = _load_manifest(target, issues)
    registry_paths: set[str] = set()
    if isinstance(manifest, dict):
        registry_paths = _check_manifest_schema(manifest, issues)
        _check_registry_consistency(target, manifest, issues)

    expected_registry_paths = {
        path
        for path, _category in _planned_file_specs()
    }
    missing_registry_paths = sorted(expected_registry_paths - registry_paths)
    for path in missing_registry_paths:
        issues.append(CheckIssue(".agent-harness/harness.yaml", f"missing generated-file registry entry for {path}"))

    _check_manifest_provenance(target, issues)
    _check_stage_contracts(target, issues)
    _check_runs(target, issues)

    return CheckResult(
        target=target,
        status="failed" if issues else "passed",
        issues=tuple(issues),
    )


def format_check_result(result: CheckResult) -> str:
    lines = [
        "Project Harness Check",
        f"Target: {result.target}",
        f"status: {result.status}",
        "Issues:",
    ]
    if not result.issues:
        lines.append("- none")
    for issue in result.issues:
        lines.append(f"- path: {issue.path}")
        lines.append(f"  message: {issue.message}")
    return "\n".join(lines).rstrip() + "\n"


def format_render_plan(plan: RenderPlan) -> str:
    lines = [
        "Render Plan:",
    ]
    for planned_file in plan.files:
        lines.extend(
            [
                f"- path: {planned_file.path}",
                f"  category: {planned_file.category}",
                f"  status: {planned_file.status}",
                f"  provenance_status: {planned_file.provenance_status}",
            ]
        )
    lines.append("")
    lines.append("Required .gitignore Entries:")
    for entry in plan.gitignore_entries:
        lines.extend(
            [
                f"- entry: {entry.entry}",
                f"  path: {entry.path}",
                f"  status: {entry.status}",
                f"  reason: {entry.reason}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _planned_file_specs() -> tuple[tuple[str, str], ...]:
    specs: list[tuple[str, str]] = [
        ("AGENTS.md", "root-router"),
        (".agent-harness/CONTEXT.md", "harness-context"),
        (".agent-harness/harness.yaml", "harness-manifest"),
        (".agent-harness/CHANGELOG.md", "harness-changelog"),
    ]
    specs.extend(
        (f".agent-harness/references/{path}", "reference")
        for path in REFERENCE_FILES
    )
    for stage_id in STAGE_IDS:
        specs.append((f".agent-harness/stages/{stage_id}/CONTEXT.md", "stage-contract"))
        specs.append((f".agent-harness/stages/{stage_id}/stage.yaml", "stage-manifest"))
    specs.extend(
        (f".agent-harness/templates/{path}", "template")
        for path in TEMPLATE_FILES
    )
    specs.extend(
        (f".agent-harness/scripts/{path}", "script")
        for path in SCRIPT_FILES
    )
    specs.append((".agent-harness/modules/module_map.yaml", "module-map"))
    return tuple(specs)


def _render_generated_content(
    inspection: InspectionResult,
    config: UserConfig,
) -> dict[str, str]:
    body_by_path: dict[str, str] = {}
    category_by_path = dict(_planned_file_specs())
    for relative_path, category in _planned_file_specs():
        if relative_path == ".agent-harness/harness.yaml":
            continue
        body_by_path[relative_path] = _render_body(relative_path, category, inspection, config)

    registry = [
        _generated_file_record(path, category_by_path[path], body, config)
        for path, body in body_by_path.items()
    ]
    manifest_record = _generated_file_record(
        ".agent-harness/harness.yaml",
        category_by_path[".agent-harness/harness.yaml"],
        "",
        config,
        body_hash=SELF_HASH_PLACEHOLDER,
    )
    manifest_body_with_placeholder = _render_manifest_body(
        [*registry, manifest_record],
        config,
    )
    manifest_hash = _sha256(manifest_body_with_placeholder)
    manifest_record = _generated_file_record(
        ".agent-harness/harness.yaml",
        category_by_path[".agent-harness/harness.yaml"],
        "",
        config,
        body_hash=manifest_hash,
    )
    body_by_path[".agent-harness/harness.yaml"] = _render_manifest_body(
        [*registry, manifest_record],
        config,
    )

    return {
        path: _with_provenance(
            path=path,
            category=category_by_path[path],
            body=body,
            config=config,
            body_hash=manifest_hash if path == ".agent-harness/harness.yaml" else None,
        )
        for path, body in body_by_path.items()
    }


def _render_body(
    relative_path: str,
    category: str,
    inspection: InspectionResult,
    config: UserConfig,
) -> str:
    project_name = _finding_value(inspection.package_metadata, "name", "unknown")
    language = _finding_value(inspection.stack, "language", "generic")
    if relative_path == "AGENTS.md":
        return _render_root_router_body(config)
    if relative_path == ".agent-harness/CONTEXT.md":
        return _render_harness_context_body(project_name, language, config)
    if relative_path == ".agent-harness/CHANGELOG.md":
        return "# Harness Changelog\n\n- Generated initial V0 harness source.\n"
    if relative_path.startswith(".agent-harness/stages/") and relative_path.endswith("/CONTEXT.md"):
        stage_id = relative_path.split("/")[2]
        return _render_stage_context_body(stage_id)
    if relative_path.startswith(".agent-harness/stages/") and relative_path.endswith("/stage.yaml"):
        stage_id = relative_path.split("/")[2]
        return _render_stage_manifest_body(stage_id)
    if relative_path.startswith(".agent-harness/references/"):
        return _render_reference_body(relative_path, inspection, config, project_name, language)
    if relative_path.startswith(".agent-harness/templates/"):
        return _render_template_body(relative_path)
    if relative_path.startswith(".agent-harness/scripts/"):
        return _render_script_body(relative_path)
    if relative_path == ".agent-harness/modules/module_map.yaml":
        return yaml.safe_dump(
            {
                "modules": [
                    {
                        "id": "default",
                        "paths": ["src/**", "tests/**"],
                        "context": ".agent-harness/templates/module_context.md",
                    }
                ]
            },
            sort_keys=False,
        )
    return "\n".join(
        [
            "# Project Harness Generated Preview",
            "",
            f"path: {relative_path}",
            f"category: {category}",
            f"target: {inspection.target}",
            f"project_name: {project_name}",
            f"language: {language}",
            f"workflow_id: {config.workflow_id}",
            f"default_prd_path: {config.default_prd_path}",
            f"default_plan_path: {config.default_plan_path}",
            f"update_policy: {config.update_policy}",
            "",
        ]
    )


def _render_root_router_body(config: UserConfig) -> str:
    return "\n".join(
        [
            "# AGENTS.md",
            "",
            "This repository uses a generated project harness.",
            "",
            "Start at `.agent-harness/CONTEXT.md` for project rules, workflow stages,",
            "and generated references. The root file is a router and intentionally",
            "does not duplicate full stage contracts.",
            "",
            "Non-trivial work follows the generated stage contracts under",
            "`.agent-harness/stages/`.",
            "",
            f"Default workflow: `{config.workflow_id}`.",
            "",
        ]
    )


def _render_harness_context_body(
    project_name: str,
    language: str,
    config: UserConfig,
) -> str:
    return "\n".join(
        [
            "# Project Harness Context",
            "",
            f"Project: {project_name}",
            f"Detected language: {language}",
            f"Workflow: {config.workflow_id}",
            "",
            "## Rule Source",
            "",
            "Durable workflow and project rules live in `.agent-harness/references/`.",
            "Stage contracts under `.agent-harness/stages/` define required inputs,",
            "outputs, gates, verification, skills, fallback, and completion criteria.",
            "",
            "## Volatile State",
            "",
            "Run artifacts live in `.agent-harness/runs/` and temporary state lives in",
            "`.agent-harness/tmp/`; both should remain ignored by Git.",
            "",
        ]
    )


def _render_stage_context_body(stage_id: str) -> str:
    title = STAGE_TITLES[stage_id]
    gates = _stage_required_gates(stage_id)
    outputs = _stage_required_outputs(stage_id)
    process = _stage_process_lines(stage_id)
    skills = _stage_required_skills(stage_id)
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Stage ID: {stage_id}",
            "",
            "## Purpose",
            "",
            f"Run the `{stage_id}` stage for the generated project workflow.",
            "",
            "## Inputs",
            "",
            "- Current task request.",
            "- Project harness context.",
            "",
            "## Process",
            "",
            *[f"- {line}" for line in process],
            "",
            "## Outputs",
            "",
            *[f"- `{output}`" for output in outputs],
            "",
            "## Approval Gates",
            "",
            *( [f"- `{gate}`" for gate in gates] if gates else ["- none"] ),
            "",
            "## Verification",
            "",
            "- Required artifacts exist and match this contract.",
            "- Harness self-check remains green after durable harness changes.",
            "",
            "## Required Skills",
            "",
            *[f"- `{item['skill']}` for {item['role']}" for item in skills],
            "",
            "## Fallback",
            "",
            "- compact fallback: if a named skill is unavailable, use the process in this contract.",
            "",
            "## Completion Criteria",
            "",
            "- Required outputs are present.",
            "- Required approval gates are satisfied or explicitly not applicable.",
            "",
        ]
    )


def _render_stage_manifest_body(stage_id: str) -> str:
    title = STAGE_TITLES[stage_id]
    next_stage = _next_stage(stage_id)
    data = {
        "stage_id": stage_id,
        "title": title,
        "required_inputs": ["current task request", ".agent-harness/CONTEXT.md"],
        "required_outputs": _stage_required_outputs(stage_id),
        "required_gates": _stage_required_gates(stage_id),
        "required_skills": _stage_required_skills(stage_id),
        "fallback_procedure": [
            "Use the compact procedure in the stage Markdown contract when a named skill is unavailable."
        ],
        "verification": [
            "Required outputs exist.",
            "Stage Markdown contract contains the required structural sections.",
        ],
        "next_stage": next_stage,
        "completion_criteria": [
            "Required outputs are present.",
            "Required gates are satisfied or explicitly not applicable.",
        ],
    }
    return yaml.safe_dump(data, sort_keys=False)


def _render_reference_body(
    relative_path: str,
    inspection: InspectionResult,
    config: UserConfig,
    project_name: str,
    language: str,
) -> str:
    title = Path(relative_path).stem.replace("_", " ").title()
    if relative_path.endswith("/commands.md"):
        return "\n".join(
            [
                "# Commands",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Command Candidates",
                "",
                *_format_command_reference_lines(inspection),
                "",
            ]
        )
    if relative_path.endswith("/architecture.md"):
        return "\n".join(
            [
                "# Architecture",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Inferred Architecture Signals",
                "",
                *_format_finding_reference_lines(inspection.architecture_signals),
                "",
            ]
        )
    if relative_path.endswith("/testing.md"):
        return "\n".join(
            [
                "# Testing",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Inferred Testing Strategy",
                "",
                *_format_finding_reference_lines(inspection.test_configuration),
                "",
            ]
        )
    if relative_path.endswith("/workflow_classification.md"):
        return "\n".join(
            [
                "# Workflow Classification",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Escalation Checklist",
                "",
                "- trivial: local, mechanical, low-risk work with no meaningful public behavior change.",
                "- minor: bounded behavior or documentation work with clear acceptance criteria.",
                "- non-trivial: work that affects public behavior, architecture impact, risk, uncertainty, or an explicit user request for the full workflow.",
                "",
                "Escalate when any of these factors are material: public behavior,",
                "architecture impact, risk, uncertainty, or explicit user request.",
                "",
            ]
        )
    if relative_path.endswith("/quality_bar.md"):
        return "\n".join(
            [
                "# Quality Bar",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Done Definitions",
                "",
                "- slice done: the observable behavior is implemented, tested through the public interface, reviewed against acceptance criteria, and ready for phase review.",
                "- feature done: all planned slices are complete, cross-phase invariants still hold, and docs describe only implemented behavior.",
                "- run done: required stages are complete or explicitly skipped, durable artifacts are promoted, and final validation passes.",
                "",
                "## Testing Rule",
                "",
                "- Use integration-style public-interface tests by default unless project evidence contradicts that testing strategy.",
                "",
            ]
        )
    if relative_path.endswith("/stack_generic.md"):
        return "\n".join(
            [
                "# Generic Stack Add-On",
                "",
                f"Project: {project_name}",
                "",
                "This language-agnostic stack add-on applies to every generated harness",
                "and does not replace the core workflow contracts.",
                "",
                "## Guidance",
                "",
                "- Prefer repository-discovered commands over invented commands.",
                "- Keep generated workflow rules separate from stack-specific conventions.",
                "",
            ]
        )
    if relative_path.endswith("/stack_python.md"):
        return "\n".join(
            [
                "# Python Stack Add-On",
                "",
                f"Project: {project_name}",
                "",
                "This Python stack add-on layers detected Python conventions onto the",
                "generic harness and does not replace the core workflow contracts.",
                "",
                "## Evidence",
                "",
                "- pyproject.toml is the primary Python project metadata source when present.",
                "- pytest is the preferred generated check when pytest configuration or a tests directory is detected.",
                "",
                "## Guidance",
                "",
                "- Keep Python-specific commands in references/commands.md.",
                "- Keep public-interface tests as the default quality rule unless project evidence contradicts it.",
                "",
            ]
        )
    if relative_path.endswith("/security.md"):
        return "\n".join(
            [
                "# Security",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Baseline",
                "",
                "- secrets: never print, commit, or move secrets into run artifacts.",
                "- risky commands: get approval before destructive filesystem, shell, or Git operations.",
                "- external mutation: get approval before mutating external services or user systems.",
                "- dependency changes: get approval before adding, upgrading, or removing dependencies.",
                "- untrusted input: validate paths and generated content before writing project files.",
                "",
            ]
        )
    if relative_path.endswith("/automation_limits.md"):
        return "\n".join(
            [
                "# Automation Limits",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Limits",
                "",
                "- The generated helper surface does not execute AI stages.",
                "- Require approval before risky commands, destructive writes, external mutation, or dependency changes.",
                "- Prefer preview-first behavior for generated harness updates.",
                "",
            ]
        )
    if relative_path.endswith("/dependency_policy.md"):
        return "\n".join(
            [
                "# Dependency Policy",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Dependency Changes",
                "",
                "- Get approval before adding, upgrading, or removing dependencies.",
                "- record the rationale, affected commands, and validation evidence for each dependency change.",
                "- Keep dependency changes separate from unrelated cleanup.",
                "",
            ]
        )
    if relative_path.endswith("/check_instructions.md"):
        return "\n".join(
            [
                "# Check Instructions",
                "",
                f"Project: {project_name}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Local Self-Check",
                "",
                "- Run `project-harness check <target>` after harness-source changes.",
                "",
                "## CI",
                "",
                "- optional CI snippet: run `project-harness check .` after installing the generator.",
                "- The generator describes checks only and does not modify CI files.",
                "",
            ]
        )
    if relative_path.endswith("/codex_workspace.md"):
        state = "enabled" if config.codex_workspace.enabled else "disabled"
        return "\n".join(
            [
                "# Codex Workspace",
                "",
                f"Project: {project_name}",
                f"Codex Workspace integration: {state}",
                "",
                "This generated reference is an editable default. Durable rule changes",
                "should be made here before they are summarized by routers or stage contracts.",
                "",
                "## Separation",
                "",
                "- project-local run artifacts stay in `.agent-harness/runs/`.",
                "- cross-session operational notes stay outside the repository.",
                "- Link active run ids from session notes instead of moving run artifacts into Codex Workspace.",
                "",
            ]
        )
    return "\n".join(
        [
            f"# {title}",
            "",
            f"Project: {project_name}",
            f"Detected language: {language}",
            "",
            "This generated reference is an editable default. Durable rule changes",
            "should be made here before they are summarized by routers or stage contracts.",
            "",
        ]
    )


def _format_command_reference_lines(inspection: InspectionResult) -> list[str]:
    if not inspection.command_candidates:
        return ["- none detected"]
    lines: list[str] = []
    for candidate in inspection.command_candidates:
        lines.extend(
            [
                f"- command: {candidate.command}",
                f"  source: {candidate.source}",
                f"  verification_state: {candidate.verification_state}",
                f"  confidence: {candidate.confidence}",
                f"  notes: {candidate.notes}",
            ]
        )
    return lines


def _format_finding_reference_lines(findings: list[Finding]) -> list[str]:
    if not findings:
        return ["- none detected"]
    lines: list[str] = []
    for finding in findings:
        lines.extend(
            [
                f"- {finding.name}: {finding.value}",
                f"  evidence: {finding.evidence}",
                f"  confidence: {finding.confidence}",
                "  confirmation_status: unconfirmed",
            ]
        )
    return lines


def _render_template_body(relative_path: str) -> str:
    name = Path(relative_path).name
    if name.endswith(".yaml"):
        return yaml.safe_dump({"template": name, "status": "generated"}, sort_keys=False)
    return "\n".join(
        [
            f"# {Path(name).stem.replace('_', ' ').title()}",
            "",
            "Generated local template for run-local harness artifacts.",
            "",
        ]
    )


def _render_script_body(relative_path: str) -> str:
    script_name = Path(relative_path).name
    return "\n".join(
        [
            '"""Deterministic helper placeholder generated by project-harness-generator."""',
            "",
            "from __future__ import annotations",
            "",
            "",
            "def main() -> int:",
            f'    print("{script_name} is a generated deterministic helper placeholder.")',
            "    return 0",
            "",
            "",
            'if __name__ == "__main__":',
            "    raise SystemExit(main())",
            "",
        ]
    )


def _render_manifest_body(
    registry: list[dict[str, str]],
    config: UserConfig,
) -> str:
    data = {
        "generator": {
            "name": GENERATOR_NAME,
            "version": __version__,
        },
        "workflow_id": config.workflow_id,
        "update_policy": config.update_policy,
        "template_version": TEMPLATE_VERSION,
        "generated_files": registry,
        "stages": [
            {
                "stage_id": stage_id,
                "title": STAGE_TITLES[stage_id],
                "contract_path": f".agent-harness/stages/{stage_id}/CONTEXT.md",
                "manifest_path": f".agent-harness/stages/{stage_id}/stage.yaml",
            }
            for stage_id in STAGE_IDS
        ],
    }
    return yaml.safe_dump(data, sort_keys=False)


def _generated_file_record(
    path: str,
    category: str,
    body: str,
    config: UserConfig,
    *,
    body_hash: str | None = None,
) -> dict[str, str]:
    return {
        "file_id": _file_id(path),
        "path": path,
        "category": category,
        "generator_version": __version__,
        "template_version": TEMPLATE_VERSION,
        "update_policy": config.update_policy,
        "last_generated_sha256": body_hash or _sha256(body),
    }


def _with_provenance(
    *,
    path: str,
    category: str,
    body: str,
    config: UserConfig,
    body_hash: str | None = None,
) -> str:
    header = _provenance_header(
        path=path,
        category=category,
        file_id=_file_id(path),
        update_policy=config.update_policy,
        body_hash=body_hash or _sha256(body),
    )
    return f"{header}{body}"


def _provenance_header(
    *,
    path: str,
    category: str,
    file_id: str,
    update_policy: str,
    body_hash: str,
) -> str:
    fields = [
        "project-harness provenance",
        f"generator_name: {GENERATOR_NAME}",
        f"generator_version: {__version__}",
        "managed: true",
        f"update_policy: {update_policy}",
        f"file_id: {file_id}",
        f"path: {path}",
        f"category: {category}",
        f"template_version: {TEMPLATE_VERSION}",
        f"last_generated_sha256: {body_hash}",
        PROVENANCE_NOTICE,
    ]
    if path.endswith(".md"):
        return "<!--\n" + "\n".join(fields) + "\n-->\n"
    return "".join(f"# {field}\n" for field in fields) + "# end project-harness provenance\n"


def _extract_provenance_header(content: str) -> tuple[dict[str, str], str, bool]:
    if content.startswith("<!--\nproject-harness provenance\n"):
        header_text, separator, body = content.partition("-->\n")
        if not separator:
            return {}, content, False
        fields = _parse_header_lines(header_text.removeprefix("<!--\n").splitlines())
        return fields, body, PROVENANCE_NOTICE in header_text
    if content.startswith("# project-harness provenance\n"):
        header_lines: list[str] = []
        body_lines: list[str] = []
        in_header = True
        for line in content.splitlines(keepends=True):
            if in_header:
                header_lines.append(line)
                if line.strip() == "# end project-harness provenance":
                    in_header = False
                continue
            body_lines.append(line)
        if in_header:
            return {}, content, False
        fields = _parse_header_lines(
            line.removeprefix("# ").rstrip("\n")
            for line in header_lines
            if line.startswith("# ") and line.strip() != "# end project-harness provenance"
        )
        return fields, "".join(body_lines), PROVENANCE_NOTICE in "".join(header_lines)
    return {}, content, False


def _parse_header_lines(lines: object) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        if not isinstance(line, str):
            continue
        key, separator, value = line.partition(": ")
        if separator:
            fields[key] = value
    return fields


def _stage_required_gates(stage_id: str) -> list[str]:
    if stage_id == "01_grill_context":
        return ["context_summary_gate"]
    if stage_id == "02_prd":
        return ["context_summary_gate"]
    if stage_id == "03_plan":
        return ["prd_gate"]
    return []


def _stage_required_outputs(stage_id: str) -> list[str]:
    if stage_id == "01_grill_context":
        return ["interview_log.md", "context_summary.md", "decision_register.md"]
    if stage_id == "02_prd":
        return ["prd.md"]
    if stage_id == "03_plan":
        return ["plan.md", "per-slice execution summaries", "cross-phase invariants"]
    if stage_id == "04_tdd_slice":
        return ["run-local progress"]
    if stage_id == "05_phase_review":
        return ["phase_review.md"]
    if stage_id == "06_harness_learning":
        return ["harness_learning.md"]
    return ["run-local stage artifacts"]


def _stage_process_lines(stage_id: str) -> list[str]:
    if stage_id == "01_grill_context":
        return [
            "Run one controlling interview for the task.",
            "Use focused sub-interviews only for complex independent branches.",
            "For each decision point, offer a recommended answer with rationale.",
            "Proceed one decision branch at a time by default.",
            "batch only independent low-risk facts.",
            "Record evidence-backed premise challenges as explicit decisions.",
            "testing-strategy candidates must be confirmed, revised, or rejected.",
        ]
    if stage_id == "02_prd":
        return [
            "Consume `context_summary.md` by default.",
            "Use `interview_log.md` and `decision_register.md` as source evidence when needed.",
            "workflow skills supply PRD, plan, slice, and TDD artifact formats.",
            "Classify every open question as blocking or non-blocking.",
            "blocking open questions prevent PRD approval.",
        ]
    if stage_id == "03_plan":
        return [
            "Require an exact approved `prd_gate` marker for the PRD being planned.",
            "Produce durable tracer-bullet plans.",
            "Include per-slice execution summaries.",
            "Track cross-phase invariants separately from acceptance criteria.",
        ]
    if stage_id == "04_tdd_slice":
        return [
            "Execute one observable behavior at a time.",
            "Record run-local progress for the active slice.",
            "The TDD slice does not update durable plan state directly.",
        ]
    if stage_id == "05_phase_review":
        return [
            "Phase review can fail a slice even when tests pass.",
            "Check acceptance criteria and project rules.",
            "Check cross-phase invariants.",
            "Require structured self-review.",
            "Require high-risk independent review when risk is high.",
            "Require pre-commit review when committing is in scope.",
            "Check review gates before durable plan state changes.",
        ]
    if stage_id == "06_harness_learning":
        return [
            "Separate local observations from generator backlog candidates.",
            "Track proposed durable harness-source patches separately.",
            "Patch proposals must cite evidence.",
            "Patch proposals must explain justification.",
            "Patch proposals must name a target harness-source file.",
            "Patch proposals remain unapplied until user acceptance.",
        ]
    return [
        "Follow the project-local harness references before changing durable artifacts.",
        "Keep outputs scoped to this stage.",
    ]


def _stage_required_skills(stage_id: str) -> list[dict[str, str]]:
    skill_by_stage = {
        "01_grill_context": "grill-me",
        "02_prd": "write-a-prd",
        "03_plan": "prd-to-plan",
        "04_tdd_slice": "tdd",
        "05_phase_review": "precommit-review",
    }
    skill = skill_by_stage.get(stage_id, "prd-plan-tdd-workflow")
    return [{"role": stage_id, "skill": skill}]


def _next_stage(stage_id: str) -> str | None:
    index = STAGE_IDS.index(stage_id)
    if index + 1 >= len(STAGE_IDS):
        return None
    return STAGE_IDS[index + 1]


def _planned_file_status(target: Path, relative_path: str, content: str) -> str:
    path = target / relative_path
    harness_root = target / ".agent-harness"
    if relative_path == "AGENTS.md" and path.exists():
        return "conflicted"
    if relative_path.startswith(".agent-harness/") and harness_root.exists():
        return "conflicted"
    if not path.exists():
        return "addable"
    try:
        existing = path.read_text(encoding="utf-8")
    except OSError:
        return "conflicted"
    return "unchanged" if existing == content else "conflicted"


def _provenance_status(status: str) -> str:
    if status == "addable":
        return "missing"
    if status == "unchanged":
        return "matches planned generated content"
    if status == "ignored-state-related":
        return "requires minimal volatile-state ignore entries"
    return "existing path blocks generate; use update for existing harness files"


def _preview_gitignore_content(entries: tuple[GitignoreEntryPlan, ...]) -> str:
    missing_entries = [entry.entry for entry in entries if entry.status != "unchanged"]
    return "\n".join(missing_entries) + ("\n" if missing_entries else "")


def _apply_gitignore_entries(
    path: Path,
    entries: tuple[GitignoreEntryPlan, ...],
) -> tuple[str, ...]:
    missing_entries = [entry.entry for entry in entries if entry.status != "unchanged"]
    if not missing_entries:
        return ()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    path.write_text(prefix + "".join(f"{entry}\n" for entry in missing_entries), encoding="utf-8")
    return tuple(missing_entries)


def _required_gitignore_entries(target: Path) -> tuple[GitignoreEntryPlan, ...]:
    present_entries = _existing_gitignore_entries(target / ".gitignore")
    plans: list[GitignoreEntryPlan] = []
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        status = "unchanged" if entry in present_entries else "ignored-state-related"
        reason = (
            "already ignores volatile harness state"
            if status == "unchanged"
            else "required to keep volatile harness state out of committed source"
        )
        plans.append(
            GitignoreEntryPlan(
                entry=entry,
                path=".gitignore",
                status=status,
                reason=reason,
            )
        )
    return tuple(plans)


def _existing_gitignore_entries(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        return {
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except OSError:
        return set()


def _finding_value(findings: list[Finding], name: str, default: str) -> str:
    for finding in findings:
        if finding.name == name:
            return finding.value
    return default


def _load_manifest(target: Path, issues: list[CheckIssue]) -> object:
    manifest_path = target / ".agent-harness/harness.yaml"
    if not manifest_path.exists():
        return None
    try:
        return yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        issues.append(CheckIssue(".agent-harness/harness.yaml", f"could not read manifest: {exc}"))
        return None


def _check_manifest_schema(manifest: dict[object, object], issues: list[CheckIssue]) -> set[str]:
    for field in ("generator", "workflow_id", "update_policy", "template_version", "generated_files", "stages"):
        if field not in manifest:
            issues.append(CheckIssue(".agent-harness/harness.yaml", f"manifest missing required field: {field}"))

    generated_files = manifest.get("generated_files")
    if not isinstance(generated_files, list):
        issues.append(CheckIssue(".agent-harness/harness.yaml", "generated_files must be a list"))
        return set()

    registry_paths: set[str] = set()
    required_record_fields = {
        "file_id",
        "path",
        "generator_version",
        "template_version",
        "update_policy",
        "last_generated_sha256",
    }
    for index, record in enumerate(generated_files):
        if not isinstance(record, dict):
            issues.append(CheckIssue(".agent-harness/harness.yaml", f"generated_files[{index}] must be a mapping"))
            continue
        missing_fields = sorted(required_record_fields - set(record))
        for field in missing_fields:
            issues.append(CheckIssue(".agent-harness/harness.yaml", f"generated_files[{index}] missing required field: {field}"))
        path = record.get("path")
        if isinstance(path, str):
            registry_paths.add(path)
    return registry_paths


def _check_registry_consistency(
    target: Path,
    manifest: dict[object, object],
    issues: list[CheckIssue],
) -> None:
    generated_files = manifest.get("generated_files")
    if not isinstance(generated_files, list):
        return
    for index, record in enumerate(generated_files):
        if not isinstance(record, dict):
            continue
        path_value = record.get("path")
        hash_value = record.get("last_generated_sha256")
        file_id = record.get("file_id")
        if not isinstance(path_value, str) or not isinstance(hash_value, str):
            continue
        generated_path = target / path_value
        if not generated_path.exists():
            issues.append(CheckIssue(path_value, f"registry entry points to missing file at generated_files[{index}]"))
            continue
        try:
            fields, body, has_notice = _extract_provenance_header(
                generated_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError) as exc:
            issues.append(CheckIssue(path_value, f"could not read generated file: {exc}"))
            continue
        if not fields:
            issues.append(CheckIssue(path_value, "generated file is missing provenance header"))
            continue
        if not has_notice:
            issues.append(CheckIssue(path_value, "provenance header is missing human-edit protection wording"))
        if fields.get("path") != path_value:
            issues.append(CheckIssue(path_value, "provenance header path does not match registry path"))
        if isinstance(file_id, str) and fields.get("file_id") != file_id:
            issues.append(CheckIssue(path_value, "provenance header file_id does not match registry file_id"))
        if fields.get("last_generated_sha256") != hash_value:
            issues.append(CheckIssue(path_value, "provenance header hash drift; registry data is authoritative"))
        if _registry_body_hash(path_value, body, hash_value) != hash_value:
            issues.append(CheckIssue(path_value, "file content hash does not match generated-file registry"))


def _check_manifest_provenance(target: Path, issues: list[CheckIssue]) -> None:
    path = target / ".agent-harness/harness.yaml"
    if not path.exists():
        return
    try:
        fields, body, has_notice = _extract_provenance_header(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        issues.append(CheckIssue(".agent-harness/harness.yaml", f"could not read manifest provenance: {exc}"))
        return
    if not fields:
        issues.append(CheckIssue(".agent-harness/harness.yaml", "manifest is missing provenance header"))
        return
    expected = {
        "generator_name": GENERATOR_NAME,
        "generator_version": __version__,
        "managed": "true",
        "path": ".agent-harness/harness.yaml",
        "template_version": TEMPLATE_VERSION,
    }
    for key, value in expected.items():
        if fields.get(key) != value:
            issues.append(CheckIssue(".agent-harness/harness.yaml", f"manifest provenance {key} is invalid"))
    if not has_notice:
        issues.append(CheckIssue(".agent-harness/harness.yaml", "manifest provenance is missing human-edit protection wording"))
    manifest_hash = fields.get("last_generated_sha256")
    if manifest_hash is None:
        issues.append(CheckIssue(".agent-harness/harness.yaml", "manifest provenance hash is missing"))
    elif _registry_body_hash(".agent-harness/harness.yaml", body, manifest_hash) != manifest_hash:
        issues.append(CheckIssue(".agent-harness/harness.yaml", "manifest provenance hash does not match content"))


def _check_stage_contracts(target: Path, issues: list[CheckIssue]) -> None:
    for stage_id in STAGE_IDS:
        manifest_path = f".agent-harness/stages/{stage_id}/stage.yaml"
        context_path = f".agent-harness/stages/{stage_id}/CONTEXT.md"
        manifest_file = target / manifest_path
        context_file = target / context_path
        if manifest_file.exists():
            _check_stage_manifest(stage_id, manifest_file, manifest_path, issues)
        if context_file.exists():
            _check_stage_markdown(stage_id, context_file, context_path, issues)


def _check_stage_manifest(
    expected_stage_id: str,
    path: Path,
    relative_path: str,
    issues: list[CheckIssue],
) -> None:
    try:
        raw_manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        issues.append(CheckIssue(relative_path, f"could not read stage manifest: {exc}"))
        return
    if not isinstance(raw_manifest, dict):
        issues.append(CheckIssue(relative_path, "stage manifest must be a mapping"))
        return
    missing_fields = sorted(REQUIRED_STAGE_MANIFEST_FIELDS - set(raw_manifest))
    for field in missing_fields:
        issues.append(CheckIssue(relative_path, f"stage manifest missing required field: {field}"))
    if raw_manifest.get("stage_id") != expected_stage_id:
        issues.append(CheckIssue(relative_path, "stage manifest id does not match path"))


def _check_stage_markdown(
    expected_stage_id: str,
    path: Path,
    relative_path: str,
    issues: list[CheckIssue],
) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        issues.append(CheckIssue(relative_path, f"could not read stage contract: {exc}"))
        return
    _fields, body, _has_notice = _extract_provenance_header(content)
    if f"Stage ID: {expected_stage_id}" not in body:
        issues.append(CheckIssue(relative_path, "stage Markdown contract id does not match path"))
    for heading in REQUIRED_STAGE_MARKDOWN_HEADINGS:
        if heading not in body:
            issues.append(CheckIssue(relative_path, f"stage Markdown contract missing heading: {heading}"))


def _check_gitignore_policy(target: Path, issues: list[CheckIssue]) -> None:
    present_entries = _existing_gitignore_entries(target / ".gitignore")
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        if entry not in present_entries:
            issues.append(CheckIssue(".gitignore", f"missing required volatile-state ignore entry: {entry}"))


def _check_runs(target: Path, issues: list[CheckIssue]) -> None:
    runs_root = target / ".agent-harness" / "runs"
    if not runs_root.exists():
        return
    for metadata_file in runs_root.glob("*/run_metadata.yaml"):
        relative_path = metadata_file.relative_to(target).as_posix()
        try:
            metadata = yaml.safe_load(metadata_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            issues.append(CheckIssue(relative_path, f"could not read run metadata: {exc}"))
            continue
        if not isinstance(metadata, dict):
            issues.append(CheckIssue(relative_path, "run metadata must be a mapping"))
            continue

        if metadata.get("task_classification") == "non-trivial":
            if not metadata.get("source_branch") and not metadata.get("branch_waiver"):
                issues.append(
                    CheckIssue(
                        relative_path,
                        "non-trivial run requires source_branch or branch_waiver",
                    )
                )
        status = metadata.get("status")
        if status not in RUN_STATUS_VALUES:
            issues.append(CheckIssue(relative_path, "run status is not a supported value"))
        current_stage = metadata.get("current_stage")
        if current_stage not in STAGE_IDS:
            issues.append(CheckIssue(relative_path, "current_stage is not a generated stage id"))
        stages = metadata.get("stages")
        if not isinstance(stages, dict):
            issues.append(CheckIssue(relative_path, "stages must be a mapping"))
            continue
        for stage_id in STAGE_IDS:
            stage = stages.get(stage_id)
            if not isinstance(stage, dict):
                issues.append(CheckIssue(relative_path, f"missing run stage metadata: {stage_id}"))
                continue
            if stage.get("status") not in STAGE_STATUS_VALUES:
                issues.append(CheckIssue(relative_path, f"unsupported stage status for {stage_id}"))


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _registry_body_hash(path: str, body: str, recorded_hash: str) -> str:
    if path != ".agent-harness/harness.yaml":
        return _sha256(body)
    return _sha256(_canonical_manifest_body_for_self_hash(body, recorded_hash))


def _canonical_manifest_body_for_self_hash(body: str, recorded_hash: str) -> str:
    lines = body.splitlines()
    self_record_started = False
    for index, line in enumerate(lines):
        if line == f"- file_id: {_file_id('.agent-harness/harness.yaml')}":
            self_record_started = True
            continue
        if self_record_started and line.startswith("- file_id: "):
            break
        if self_record_started and line == f"  last_generated_sha256: {recorded_hash}":
            lines[index] = f"  last_generated_sha256: {SELF_HASH_PLACEHOLDER}"
            break
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(lines) + suffix


def _file_id(path: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", path.lower()).strip("_")


def _format_bool(value: bool) -> str:
    return "true" if value else "false"


def _looks_like_git_worktree(target: Path) -> bool:
    return (target / ".git").exists()

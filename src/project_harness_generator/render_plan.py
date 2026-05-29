"""Preview render plans for generated project harness files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import UserConfig
from .inspection import Finding, InspectionResult


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


def build_render_plan(
    target: Path,
    inspection: InspectionResult,
    config: UserConfig,
) -> RenderPlan:
    target = target.resolve()
    planned_files: list[PlannedFile] = []
    gitignore_entries = _required_gitignore_entries(target)
    for relative_path, category in _planned_file_specs():
        content = _preview_content(relative_path, category, inspection, config)
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


def _preview_content(
    relative_path: str,
    category: str,
    inspection: InspectionResult,
    config: UserConfig,
) -> str:
    project_name = _finding_value(inspection.package_metadata, "name", "unknown")
    language = _finding_value(inspection.stack, "language", "generic")
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

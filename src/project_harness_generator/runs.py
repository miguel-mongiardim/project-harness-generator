"""Run skeleton creation and run state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import subprocess

import yaml

from .config import UserConfig
from .render_plan import STAGE_IDS


RUN_STATUS_VALUES = ["active", "paused", "completed", "abandoned"]
STAGE_STATUS_VALUES = ["pending", "active", "complete", "skipped"]
TASK_CLASSIFICATIONS = {"trivial", "minor", "non-trivial"}


@dataclass(frozen=True)
class NewRunResult:
    target: Path
    run_id: str
    run_root: Path
    files_written: tuple[str, ...]


@dataclass(frozen=True)
class RunStateResult:
    target: Path
    run_id: str
    status: str
    current_stage: str


class RunError(Exception):
    """Raised when run metadata cannot be created or updated."""


def create_run(
    target: Path,
    slug: str,
    *,
    classification: str,
    created_date: str | None,
    source_branch: str | None,
    branch_waiver: str | None,
    config: UserConfig,
) -> NewRunResult:
    target = target.expanduser().resolve()
    if classification not in TASK_CLASSIFICATIONS:
        raise RunError("classification must be one of: trivial, minor, non-trivial")
    if not (target / ".agent-harness" / "harness.yaml").exists():
        raise RunError("new-run requires an existing generated harness")

    run_date = _validated_date(created_date)
    normalized_slug = _normalize_slug(slug)
    run_id = f"{run_date}-{normalized_slug}"
    run_root = target / ".agent-harness" / "runs" / run_id
    if run_root.exists():
        raise RunError(f"run id already exists: {run_id}")

    resolved_source_branch = source_branch or _detect_git_branch(target)
    if classification == "non-trivial" and not resolved_source_branch and not branch_waiver:
        raise RunError(
            "non-trivial Git worktree runs require --source-branch or --branch-waiver"
        )

    stage_statuses = {
        stage_id: {"status": "active" if index == 0 else "pending"}
        for index, stage_id in enumerate(STAGE_IDS)
    }
    metadata = {
        "run_id": run_id,
        "created_date": run_date,
        "task_classification": classification,
        "workflow_id": config.workflow_id,
        "default_prd_path": config.default_prd_path,
        "default_plan_path": config.default_plan_path,
        "status": "active",
        "status_values": RUN_STATUS_VALUES,
        "stage_status_values": STAGE_STATUS_VALUES,
        "current_stage": STAGE_IDS[0],
        "source_branch": resolved_source_branch,
        "branch_waiver": branch_waiver,
        "stages": stage_statuses,
    }

    files_written: list[str] = []
    stage_root = run_root / "stages"
    for stage_id in STAGE_IDS:
        (stage_root / stage_id).mkdir(parents=True, exist_ok=True)
    metadata_path = run_root / "run_metadata.yaml"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    files_written.append(_relative_to_target(metadata_path, target))
    next_action_path = run_root / "next_action.md"
    next_action_path.write_text(
        "\n".join(
            [
                "# Next Action",
                "",
                f"- Start stage `{STAGE_IDS[0]}` for run `{run_id}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    files_written.append(_relative_to_target(next_action_path, target))

    return NewRunResult(
        target=target,
        run_id=run_id,
        run_root=run_root,
        files_written=tuple(files_written),
    )


def format_new_run_result(result: NewRunResult) -> str:
    lines = [
        "Project Harness New Run",
        f"Target: {result.target}",
        f"run_id: {result.run_id}",
        f"run_root: {result.run_root}",
        "files_written:",
    ]
    for path in result.files_written:
        lines.append(f"- path: {path}")
    return "\n".join(lines).rstrip() + "\n"


def pause_run(target: Path, run_id: str, *, next_action: str) -> RunStateResult:
    target = target.expanduser().resolve()
    run_root, metadata_path = _run_paths(target, run_id)
    metadata = _load_run_metadata(metadata_path)
    metadata["status"] = "paused"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    (run_root / "next_action.md").write_text(
        "\n".join(
            [
                "# Next Action",
                "",
                next_action,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return RunStateResult(
        target=target,
        run_id=run_id,
        status="paused",
        current_stage=str(metadata.get("current_stage", "")),
    )


def resume_run(target: Path, run_id: str) -> RunStateResult:
    target = target.expanduser().resolve()
    _run_root, metadata_path = _run_paths(target, run_id)
    metadata = _load_run_metadata(metadata_path)
    metadata["status"] = "active"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    return RunStateResult(
        target=target,
        run_id=run_id,
        status="active",
        current_stage=str(metadata.get("current_stage", "")),
    )


def format_run_state_result(heading: str, result: RunStateResult) -> str:
    return "\n".join(
        [
            f"Project Harness {heading}",
            f"Target: {result.target}",
            f"run_id: {result.run_id}",
            f"status: {result.status}",
            f"current_stage: {result.current_stage}",
            "",
        ]
    )


def _validated_date(value: str | None) -> str:
    if value is None:
        return date.today().isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise RunError("date must use YYYY-MM-DD format") from exc


def _normalize_slug(value: str) -> str:
    lowered = value.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized:
        raise RunError("slug must contain ASCII letters or digits")
    return normalized


def _detect_git_branch(target: Path) -> str | None:
    if not (target / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=target,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    branch = completed.stdout.strip()
    return branch or None


def _relative_to_target(path: Path, target: Path) -> str:
    return path.relative_to(target).as_posix()


def _run_paths(target: Path, run_id: str) -> tuple[Path, Path]:
    run_root = target / ".agent-harness" / "runs" / run_id
    metadata_path = run_root / "run_metadata.yaml"
    if not metadata_path.exists():
        raise RunError(f"run metadata does not exist for run id: {run_id}")
    return run_root, metadata_path


def _load_run_metadata(path: Path) -> dict[str, object]:
    try:
        metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RunError(f"could not read run metadata: {exc}") from exc
    if not isinstance(metadata, dict):
        raise RunError("run metadata must be a mapping")
    return metadata

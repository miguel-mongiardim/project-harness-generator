"""Run skeleton creation and run state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import subprocess

import yaml

from .config import UserConfig
from .workflow import STAGE_IDS, STAGE_STATUS_VALUES, RUN_STATUS_VALUES


TASK_CLASSIFICATIONS = {"trivial", "minor", "non-trivial"}
RUN_ID_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\Z")


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

    stage_root = run_root / "stages"
    stage_dirs = [stage_root / stage_id for stage_id in STAGE_IDS]
    metadata_path = run_root / "run_metadata.yaml"
    next_action_path = run_root / "next_action.md"
    _preflight_write_paths(target, [run_root, *stage_dirs, metadata_path, next_action_path])

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
        "status_values": list(RUN_STATUS_VALUES),
        "stage_status_values": list(STAGE_STATUS_VALUES),
        "current_stage": STAGE_IDS[0],
        "source_branch": resolved_source_branch,
        "branch_waiver": branch_waiver,
        "stages": stage_statuses,
    }

    files_written: list[str] = []
    for stage_dir in stage_dirs:
        stage_dir.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    files_written.append(_relative_to_target(metadata_path, target))
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
    next_action_path = run_root / "next_action.md"
    _preflight_write_paths(target, [metadata_path, next_action_path])
    metadata = _load_run_metadata(metadata_path)
    metadata["status"] = "paused"
    metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    next_action_path.write_text(
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
    _preflight_write_paths(target, [metadata_path])
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
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise RunError("run id must match generated run id format: <YYYY-MM-DD>-<slug>")
    run_root = target / ".agent-harness" / "runs" / run_id
    metadata_path = run_root / "run_metadata.yaml"
    if not metadata_path.exists():
        raise RunError(f"run metadata does not exist for run id: {run_id}")
    return run_root, metadata_path


def _preflight_write_paths(target: Path, paths: list[Path]) -> None:
    for path in paths:
        _preflight_write_path(target, path)


def _preflight_write_path(target: Path, path: Path) -> None:
    target_root = target.resolve()
    symlink_path = _first_symlink_path(target_root, path)
    if symlink_path is not None:
        raise RunError(
            f"refusing to write through symlinked path: {_display_path(target_root, symlink_path)}"
        )
    resolved_path = path.resolve(strict=False)
    if resolved_path != target_root and not resolved_path.is_relative_to(target_root):
        raise RunError(f"refusing to write outside target: {_display_path(target_root, path)}")


def _first_symlink_path(target: Path, path: Path) -> Path | None:
    current = path
    while current != target:
        if current.is_symlink():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _display_path(target: Path, path: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return str(path)


def _load_run_metadata(path: Path) -> dict[str, object]:
    try:
        metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise RunError(f"could not read run metadata: {exc}") from exc
    if not isinstance(metadata, dict):
        raise RunError("run metadata must be a mapping")
    return metadata

"""Local user config loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

import yaml


DEFAULT_WORKFLOW_ID = "prd-plan-tdd"
DEFAULT_PRD_PATH = "docs/prd.md"
DEFAULT_PLAN_PATH = "plans/plan.md"
DEFAULT_UPDATE_POLICY = "conservative"
SUPPORTED_WORKFLOW_IDS = {DEFAULT_WORKFLOW_ID}
SUPPORTED_UPDATE_POLICIES = {"conservative", "manual_only", "detached"}
TOP_LEVEL_FIELDS = {
    "workflow_id",
    "default_prd_path",
    "default_plan_path",
    "update_policy",
    "codex_workspace",
}
CODEX_WORKSPACE_FIELDS = {"enabled"}


@dataclass(frozen=True)
class CodexWorkspaceConfig:
    enabled: bool = False


@dataclass(frozen=True)
class UserConfig:
    workflow_id: str = DEFAULT_WORKFLOW_ID
    default_prd_path: str = DEFAULT_PRD_PATH
    default_plan_path: str = DEFAULT_PLAN_PATH
    update_policy: str = DEFAULT_UPDATE_POLICY
    codex_workspace: CodexWorkspaceConfig = CodexWorkspaceConfig()
    source: str = "defaults"


class ConfigError(Exception):
    """Raised when local user config is invalid."""


def default_config_path() -> Path:
    return Path.home() / ".agent-harness" / "config.yaml"


def load_config(path: Path | None = None) -> UserConfig:
    use_defaults_when_missing = path is None
    config_path = path or default_config_path()
    if not config_path.exists():
        if not use_defaults_when_missing:
            raise ConfigError(f"config file does not exist: {config_path}")
        return UserConfig(source="defaults")

    try:
        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"could not read config: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"could not decode config as UTF-8: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse config: {exc}") from exc
    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        raise ConfigError("config root must be a mapping")

    return _build_config(raw_config, source=str(config_path))


def apply_config_overrides(
    config: UserConfig,
    *,
    workflow_id: str | None = None,
    default_prd_path: str | None = None,
    default_plan_path: str | None = None,
    update_policy: str | None = None,
) -> UserConfig:
    raw_config: dict[str, object] = {
        "workflow_id": workflow_id if workflow_id is not None else config.workflow_id,
        "default_prd_path": (
            default_prd_path if default_prd_path is not None else config.default_prd_path
        ),
        "default_plan_path": (
            default_plan_path if default_plan_path is not None else config.default_plan_path
        ),
        "update_policy": update_policy if update_policy is not None else config.update_policy,
        "codex_workspace": {"enabled": config.codex_workspace.enabled},
    }
    return _build_config(raw_config, source=config.source)


def _build_config(raw_config: dict[object, object], *, source: str) -> UserConfig:
    unknown_fields = sorted(str(field) for field in set(raw_config) - TOP_LEVEL_FIELDS)
    if unknown_fields:
        raise ConfigError(f"unknown config field: {unknown_fields[0]}")

    workflow_id = _optional_string(raw_config, "workflow_id", DEFAULT_WORKFLOW_ID)
    if workflow_id not in SUPPORTED_WORKFLOW_IDS:
        raise ConfigError("workflow_id must be prd-plan-tdd")

    default_prd_path = _project_relative_path(
        raw_config,
        "default_prd_path",
        DEFAULT_PRD_PATH,
    )
    default_plan_path = _project_relative_path(
        raw_config,
        "default_plan_path",
        DEFAULT_PLAN_PATH,
    )

    update_policy = _optional_string(raw_config, "update_policy", DEFAULT_UPDATE_POLICY)
    if update_policy not in SUPPORTED_UPDATE_POLICIES:
        supported = ", ".join(sorted(SUPPORTED_UPDATE_POLICIES))
        raise ConfigError(f"update_policy must be one of: {supported}")

    codex_workspace = _codex_workspace_config(raw_config.get("codex_workspace", {}))
    return UserConfig(
        workflow_id=workflow_id,
        default_prd_path=default_prd_path,
        default_plan_path=default_plan_path,
        update_policy=update_policy,
        codex_workspace=codex_workspace,
        source=source,
    )


def _optional_string(config: dict[object, object], field: str, default: str) -> str:
    value = config.get(field, default)
    if not isinstance(value, str):
        raise ConfigError(f"{field} must be a string")
    return value


def _project_relative_path(config: dict[object, object], field: str, default: str) -> str:
    value = _optional_string(config, field, default)
    if not _is_project_relative_path(value):
        raise ConfigError(f"{field} must be a project-relative path")
    return value


def _is_project_relative_path(value: str) -> bool:
    if value == "":
        return False
    posix_path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if Path(value).is_absolute() or posix_path.is_absolute() or windows_path.is_absolute():
        return False
    if windows_path.drive or windows_path.root:
        return False
    return ".." not in posix_path.parts and ".." not in windows_path.parts


def _codex_workspace_config(value: object) -> CodexWorkspaceConfig:
    if not isinstance(value, dict):
        raise ConfigError("codex_workspace must be a mapping")
    unknown_fields = sorted(str(field) for field in set(value) - CODEX_WORKSPACE_FIELDS)
    if unknown_fields:
        raise ConfigError(f"unknown codex_workspace field: {unknown_fields[0]}")
    enabled = value.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ConfigError("codex_workspace.enabled must be a boolean")
    return CodexWorkspaceConfig(enabled=enabled)


def format_config(config: UserConfig) -> str:
    codex_enabled = "true" if config.codex_workspace.enabled else "false"
    lines = [
        "Project Harness Config",
        f"source: {config.source}",
        f"workflow_id: {config.workflow_id}",
        f"default_prd_path: {config.default_prd_path}",
        f"default_plan_path: {config.default_plan_path}",
        f"update_policy: {config.update_policy}",
        f"codex_workspace.enabled: {codex_enabled}",
    ]
    return "\n".join(lines) + "\n"

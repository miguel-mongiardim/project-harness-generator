import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def run_project_harness(
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "project_harness_generator", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_missing_config_uses_stable_defaults() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        home = Path(temp_dir)

        result = run_project_harness(
            "config",
            "validate",
            extra_env={"HOME": str(home), "USERPROFILE": str(home)},
        )

        assert result.returncode == 0, result.stderr
        assert "Project Harness Config" in result.stdout
        assert "source: defaults" in result.stdout
        assert "workflow_id: prd-plan-tdd" in result.stdout
        assert "default_prd_path: docs/prd.md" in result.stdout
        assert "default_plan_path: plans/plan.md" in result.stdout
        assert "update_policy: conservative" in result.stdout
        assert "codex_workspace.enabled: false" in result.stdout


def test_explicit_missing_config_path_fails_actionably() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        missing_config = Path(temp_dir) / "missing.yaml"

        result = run_project_harness("config", "validate", str(missing_config))

        assert result.returncode != 0
        assert f"config file does not exist: {missing_config}" in result.stderr
        assert "Project Harness Config" not in result.stdout
        assert "traceback" not in result.stderr.lower()


def test_explicit_empty_config_path_fails_actionably() -> None:
    result = run_project_harness("config", "validate", "")

    assert result.returncode != 0
    assert "could not read config" in result.stderr
    assert "Project Harness Config" not in result.stdout
    assert "traceback" not in result.stderr.lower()


def test_valid_config_can_be_validated_through_public_cli() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "workflow_id: prd-plan-tdd",
                    "default_prd_path: docs/product-prd.md",
                    "default_plan_path: plans/product-plan.md",
                    "update_policy: manual_only",
                    "codex_workspace:",
                    "  enabled: true",
                ]
            )
        )

        result = run_project_harness("config", "validate", str(config_path))

        assert result.returncode == 0, result.stderr
        assert f"source: {config_path}" in result.stdout
        assert "workflow_id: prd-plan-tdd" in result.stdout
        assert "default_prd_path: docs/product-prd.md" in result.stdout
        assert "default_plan_path: plans/product-plan.md" in result.stdout
        assert "update_policy: manual_only" in result.stdout
        assert "codex_workspace.enabled: true" in result.stdout


@pytest.mark.parametrize(
    ("content", "diagnostic"),
    [
        ("unknown_field: true\n", "unknown config field: unknown_field"),
        ("workflow_id: other-workflow\n", "workflow_id must be prd-plan-tdd"),
        ("default_prd_path: \"\"\n", "default_prd_path must be a project-relative path"),
        ("default_prd_path: C:/absolute/prd.md\n", "default_prd_path must be a project-relative path"),
        ("default_prd_path: C:drive-relative.md\n", "default_prd_path must be a project-relative path"),
        ("default_prd_path: ../outside.md\n", "default_prd_path must be a project-relative path"),
        ("default_prd_path: docs/../prd.md\n", "default_prd_path must be a project-relative path"),
        ("default_prd_path: \\rooted.md\n", "default_prd_path must be a project-relative path"),
        ("default_plan_path: \"\"\n", "default_plan_path must be a project-relative path"),
        ("default_plan_path:\n  - plans/plan.md\n", "default_plan_path must be a string"),
        ("update_policy: overwrite\n", "update_policy must be one of: conservative, detached, manual_only"),
        ("codex_workspace:\n  enabled: \"yes\"\n", "codex_workspace.enabled must be a boolean"),
        (
            "codex_workspace:\n  enabled: true\n  1: false\n  other: false\n",
            "unknown codex_workspace field: 1",
        ),
    ],
)
def test_invalid_config_fails_with_actionable_diagnostic(
    content: str,
    diagnostic: str,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.write_text(content)

        result = run_project_harness("config", "validate", str(config_path))

        assert result.returncode != 0
        assert diagnostic in result.stderr
        assert "traceback" not in result.stderr.lower()


def test_command_cli_flags_override_user_config_values() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        home = root / "home"
        target = root / "target"
        config_dir = home / ".agent-harness"
        home.mkdir()
        target.mkdir()
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(
            "\n".join(
                [
                    "workflow_id: prd-plan-tdd",
                    "default_prd_path: docs/config-prd.md",
                    "default_plan_path: plans/config-plan.md",
                    "update_policy: manual_only",
                    "codex_workspace:",
                    "  enabled: true",
                ]
            )
        )
        env = {"HOME": str(home), "USERPROFILE": str(home)}
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        generate = run_project_harness(
            "generate",
            str(target),
            "--prd-path",
            "docs/cli-prd.md",
            "--plan-path",
            "plans/cli-plan.md",
            "--workflow-id",
            "prd-plan-tdd",
            extra_env=env,
        )
        update = run_project_harness(
            "update",
            str(target),
            "--update-policy",
            "detached",
            extra_env=env,
        )
        apply_harness = run_project_harness(
            "generate",
            str(target),
            "--apply",
            extra_env=env,
        )
        new_run = run_project_harness(
            "new-run",
            str(target),
            "config-slice",
            "--classification",
            "minor",
            "--date",
            "2026-05-29",
            "--prd-path",
            "docs/run-prd.md",
            "--plan-path",
            "plans/run-plan.md",
            "--workflow-id",
            "prd-plan-tdd",
            extra_env=env,
        )

        assert generate.returncode == 0, generate.stderr
        assert "Project Harness Generate" in generate.stdout
        assert "default_prd_path: docs/cli-prd.md" in generate.stdout
        assert "default_plan_path: plans/cli-plan.md" in generate.stdout
        assert "update_policy: manual_only" in generate.stdout
        assert "codex_workspace.enabled: true" in generate.stdout

        assert update.returncode == 0, update.stderr
        assert "Project Harness Update" in update.stdout
        assert "default_prd_path: docs/config-prd.md" in update.stdout
        assert "update_policy: detached" in update.stdout

        assert apply_harness.returncode == 0, apply_harness.stderr
        assert new_run.returncode == 0, new_run.stderr
        assert "Project Harness New Run" in new_run.stdout
        metadata = yaml.safe_load(
            (
                target
                / ".agent-harness"
                / "runs"
                / "2026-05-29-config-slice"
                / "run_metadata.yaml"
            ).read_text()
        )
        assert metadata["default_prd_path"] == "docs/run-prd.md"
        assert metadata["default_plan_path"] == "plans/run-plan.md"
        assert metadata["workflow_id"] == "prd-plan-tdd"


def test_cli_path_overrides_must_stay_project_relative() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "target"
        target.mkdir()

        generate = run_project_harness(
            "generate",
            str(target),
            "--prd-path",
            "../outside.md",
        )
        new_run = run_project_harness(
            "new-run",
            str(target),
            "config-slice",
            "--classification",
            "minor",
            "--prd-path",
            "../outside.md",
        )
        empty_generate = run_project_harness(
            "generate",
            str(target),
            "--plan-path",
            "",
        )

        assert generate.returncode != 0
        assert "project-harness generate: default_prd_path must be a project-relative path" in generate.stderr
        assert "Project Harness Generate" not in generate.stdout

        assert new_run.returncode != 0
        assert "project-harness new-run: default_prd_path must be a project-relative path" in new_run.stderr
        assert "Project Harness New Run" not in new_run.stdout

        assert empty_generate.returncode != 0
        assert "project-harness generate: default_plan_path must be a project-relative path" in empty_generate.stderr
        assert "Project Harness Generate" not in empty_generate.stdout


def test_generate_and_update_reject_invalid_config_before_command_work() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        home = root / "home"
        target = root / "target"
        config_dir = home / ".agent-harness"
        home.mkdir()
        target.mkdir()
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text("unknown_field: true\n")
        env = {"HOME": str(home), "USERPROFILE": str(home)}

        generate = run_project_harness("generate", str(target), extra_env=env)
        update = run_project_harness("update", str(target), extra_env=env)

        assert generate.returncode != 0
        assert "unknown config field: unknown_field" in generate.stderr
        assert "Project Harness Generate" not in generate.stdout

        assert update.returncode != 0
        assert "unknown config field: unknown_field" in update.stderr
        assert "Project Harness Update" not in update.stdout


def test_config_read_failure_reports_actionable_diagnostic() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.yaml"
        config_path.mkdir()

        result = run_project_harness("config", "validate", str(config_path))

        assert result.returncode != 0
        assert "could not read config" in result.stderr
        assert "traceback" not in result.stderr.lower()

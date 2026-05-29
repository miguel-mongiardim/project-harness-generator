import os
import subprocess
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def run_project_harness(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    return subprocess.run(
        [sys.executable, "-m", "project_harness_generator", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_help_lists_public_commands() -> None:
    result = run_project_harness("--help")

    assert result.returncode == 0
    help_text = result.stdout
    for command in [
        "inspect",
        "generate",
        "check",
        "update",
        "new-run",
        "approve",
        "advance",
        "skip-stage",
        "pause",
        "resume",
        "promote",
        "config",
        "validate",
    ]:
        assert command in help_text


def test_missing_command_fails_with_usage() -> None:
    result = run_project_harness()

    assert result.returncode != 0
    assert "usage:" in result.stderr
    assert "traceback" not in result.stderr.lower()


def test_unknown_command_fails_without_traceback() -> None:
    result = run_project_harness("unknown-command")

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
    assert "traceback" not in result.stderr.lower()


def test_missing_command_argument_fails_with_command_usage() -> None:
    result = run_project_harness("inspect")

    assert result.returncode != 0
    assert "usage: project-harness inspect" in result.stderr
    assert "target" in result.stderr
    assert "traceback" not in result.stderr.lower()


def test_unimplemented_command_fails_actionably() -> None:
    result = run_project_harness("check", ".")

    assert result.returncode != 0
    assert "not implemented" in result.stderr
    assert "check" in result.stderr
    assert "traceback" not in result.stderr.lower()


def test_project_metadata_exposes_console_script() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())

    assert pyproject["project"]["scripts"]["project-harness"] == (
        "project_harness_generator.cli:main"
    )

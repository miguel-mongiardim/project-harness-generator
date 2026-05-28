import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


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


def test_inspect_reports_python_repo_evidence_without_running_commands() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [build-system]
                requires = ["setuptools>=69", "wheel"]
                build-backend = "setuptools.build_meta"

                [project]
                name = "sample-project"
                version = "1.2.3"
                requires-python = ">=3.11"
                dependencies = ["requests>=2"]

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ).strip()
        )
        (target / "README.md").write_text("# Sample Project\n")
        (target / "AGENTS.md").write_text("# Agent Instructions\n")
        (target / "docs").mkdir()
        (target / "docs" / "architecture.md").write_text("# Architecture\n")
        (target / "src").mkdir()
        (target / "src" / "sample_project").mkdir()
        (target / "src" / "sample_project" / "__init__.py").write_text("")
        (target / "src" / "sample_project.egg-info").mkdir()
        (target / "tests").mkdir()
        (target / "tests" / "test_sample.py").write_text("def test_sample():\n    assert True\n")

        command_sentinel = target / "command-ran.txt"

        result = run_project_harness("inspect", str(target))

        assert result.returncode == 0, result.stderr
        output = result.stdout
        assert "Stack" in output
        assert "git worktree: no" in output
        assert "Python" in output
        assert "evidence: pyproject.toml" in output
        assert "confidence: high" in output
        assert "name: sample-project" in output
        assert "requires-python: >=3.11" in output
        assert "dependencies: requests>=2" in output
        assert "testpaths: tests" in output
        assert "AGENTS.md" in output
        assert "docs/" in output
        assert "src layout" in output
        assert "sample_project.egg-info" not in output
        assert "command: python -m pytest -q" in output
        assert "verification_state: not_run" in output
        assert "passive inspection did not execute target commands" in output
        assert not command_sentinel.exists()


def test_inspect_missing_target_fails_with_clear_diagnostic() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        missing = Path(temp_dir) / "missing"

        result = run_project_harness("inspect", str(missing))

        assert result.returncode != 0
        assert "target path does not exist" in result.stderr
        assert str(missing) in result.stderr
        assert "traceback" not in result.stderr.lower()

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

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


def test_generated_references_include_quality_bar_and_security_baseline() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        harness_context = (target / ".agent-harness" / "CONTEXT.md").read_text()
        quality_bar = (
            target / ".agent-harness" / "references" / "quality_bar.md"
        ).read_text()
        security = (target / ".agent-harness" / "references" / "security.md").read_text()
        assert ".agent-harness/references/" in harness_context
        assert "slice done" in quality_bar
        assert "feature done" in quality_bar
        assert "run done" in quality_bar
        assert "integration-style public-interface tests" in quality_bar
        for phrase in [
            "secrets",
            "risky commands",
            "external mutation",
            "dependency changes",
            "untrusted input",
        ]:
            assert phrase in security


def test_generated_references_preserve_inspection_evidence_and_command_metadata() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ).strip()
        )
        (target / "src" / "sample_project").mkdir(parents=True)
        (target / "src" / "sample_project" / "__init__.py").write_text("")
        (target / "tests").mkdir()

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        commands = (target / ".agent-harness" / "references" / "commands.md").read_text()
        architecture = (
            target / ".agent-harness" / "references" / "architecture.md"
        ).read_text()
        testing = (target / ".agent-harness" / "references" / "testing.md").read_text()
        for phrase in [
            "command: python --version",
            "source: pyproject.toml",
            "verification_state: not_run",
            "confidence: high",
            "notes: passive inspection did not execute target commands",
            "command: python -m pytest -q",
            "source: pyproject.toml [tool.pytest.ini_options.testpaths]",
        ]:
            assert phrase in commands
        assert "layout: src layout" in architecture
        assert "evidence: src/" in architecture
        assert "confidence: high" in architecture
        assert "confirmation_status: unconfirmed" in architecture
        assert "testpaths: tests" in testing
        assert "evidence: pyproject.toml [tool.pytest.ini_options.testpaths]" in testing
        assert "confidence: high" in testing
        assert "confirmation_status: unconfirmed" in testing


def test_generated_references_separate_core_workflow_from_stack_addons() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ).strip()
        )
        (target / "tests").mkdir()

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        workflow = (
            target / ".agent-harness" / "references" / "workflow_classification.md"
        ).read_text()
        stack_generic = (
            target / ".agent-harness" / "references" / "stack_generic.md"
        ).read_text()
        stack_python = (
            target / ".agent-harness" / "references" / "stack_python.md"
        ).read_text()
        module_map_text = (
            target / ".agent-harness" / "modules" / "module_map.yaml"
        ).read_text()
        module_map = yaml.safe_load(module_map_text)
        for phrase in [
            "trivial",
            "minor",
            "non-trivial",
            "public behavior",
            "architecture impact",
            "risk",
            "uncertainty",
            "explicit user request",
        ]:
            assert phrase in workflow
        assert "Python" not in workflow
        assert "language-agnostic stack add-on" in stack_generic
        assert "Python stack add-on" in stack_python
        assert "pyproject.toml" in stack_python
        assert "pytest" in stack_python
        assert "does not replace the core workflow contracts" in stack_python
        assert module_map["modules"][0]["paths"] == ["src/**", "tests/**"]
        assert ".agent-harness/templates/module_context.md" in module_map_text


def test_generated_references_include_operational_boundaries() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        home = root / "home"
        target = root / "sample_project"
        config_dir = home / ".agent-harness"
        home.mkdir()
        target.mkdir()
        config_dir.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )
        (config_dir / "config.yaml").write_text(
            "\n".join(
                [
                    "workflow_id: prd-plan-tdd",
                    "default_prd_path: docs/prd.md",
                    "default_plan_path: plans/plan.md",
                    "update_policy: conservative",
                    "codex_workspace:",
                    "  enabled: true",
                ]
            )
        )

        result = run_project_harness(
            "generate",
            str(target),
            "--apply",
            extra_env={"HOME": str(home), "USERPROFILE": str(home)},
        )

        assert result.returncode == 0, result.stderr
        codex_workspace = (
            target / ".agent-harness" / "references" / "codex_workspace.md"
        ).read_text()
        check_instructions = (
            target / ".agent-harness" / "references" / "check_instructions.md"
        ).read_text()
        automation_limits = (
            target / ".agent-harness" / "references" / "automation_limits.md"
        ).read_text()
        dependency_policy = (
            target / ".agent-harness" / "references" / "dependency_policy.md"
        ).read_text()
        assert "Codex Workspace integration: enabled" in codex_workspace
        assert "project-local run artifacts stay in `.agent-harness/runs/`" in codex_workspace
        assert "cross-session operational notes stay outside the repository" in codex_workspace
        assert "project-harness check <target>" in check_instructions
        assert "optional CI snippet" in check_instructions
        assert "does not modify CI files" in check_instructions
        assert not (target / ".github").exists()
        assert "does not execute AI stages" in automation_limits
        assert "approval before risky commands" in automation_limits
        assert "approval before adding, upgrading, or removing dependencies" in dependency_policy
        assert "record the rationale" in dependency_policy

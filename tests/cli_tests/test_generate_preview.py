import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


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


def test_generate_preview_reports_files_without_writing() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )
        (target / "README.md").write_text("# Sample Project\n")
        before_paths = _path_inventory(target)

        result = run_project_harness("generate", str(target))

        assert result.returncode == 0, result.stderr
        output = result.stdout
        assert "Project Harness Generate Preview" in output
        assert "No files written." in output
        assert "Target:" in output
        assert "Render Plan:" in output
        assert "path: AGENTS.md" in output
        assert "category: root-router" in output
        assert "status: addable" in output
        assert "path: .agent-harness/CONTEXT.md" in output
        assert "path: .agent-harness/harness.yaml" in output
        assert "path: .agent-harness/stages/00_project_discovery/CONTEXT.md" in output
        assert "Required .gitignore Entries:" in output
        assert "entry: .agent-harness/runs/" in output
        assert "entry: .agent-harness/tmp/" in output
        assert "status: ignored-state-related" in output
        assert not (target / "AGENTS.md").exists()
        assert not (target / ".agent-harness").exists()
        assert _path_inventory(target) == before_paths


def test_generate_preview_consumes_config_and_cli_overrides() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        home = root / "home"
        target = root / "sample_project"
        config_dir = home / ".agent-harness"
        home.mkdir()
        target.mkdir()
        config_dir.mkdir()
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
                    "default_prd_path: docs/config-prd.md",
                    "default_plan_path: plans/config-plan.md",
                    "update_policy: manual_only",
                    "codex_workspace:",
                    "  enabled: true",
                ]
            )
        )

        result = run_project_harness(
            "generate",
            str(target),
            "--prd-path",
            "docs/cli-prd.md",
            "--plan-path",
            "plans/cli-plan.md",
            "--workflow-id",
            "prd-plan-tdd",
            "--update-policy",
            "detached",
            extra_env={"HOME": str(home), "USERPROFILE": str(home)},
        )

        assert result.returncode == 0, result.stderr
        assert "Project Harness Generate Preview" in result.stdout
        assert f"source: {config_dir / 'config.yaml'}" in result.stdout
        assert "workflow_id: prd-plan-tdd" in result.stdout
        assert "default_prd_path: docs/cli-prd.md" in result.stdout
        assert "default_plan_path: plans/cli-plan.md" in result.stdout
        assert "update_policy: detached" in result.stdout
        assert "codex_workspace.enabled: true" in result.stdout


def test_generate_preview_reports_gitignore_as_required_write_path() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()

        result = run_project_harness("generate", str(target))

        assert result.returncode == 0, result.stderr
        assert "Render Plan:" in result.stdout
        assert "path: .gitignore" in result.stdout
        assert "category: ignore-policy" in result.stdout
        assert "status: ignored-state-related" in result.stdout
        assert "Required .gitignore Entries:" in result.stdout
        assert "entry: .agent-harness/runs/" in result.stdout
        assert "entry: .agent-harness/tmp/" in result.stdout
        assert not (target / ".gitignore").exists()


def test_generate_preview_reports_existing_harness_files_as_conflicts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "AGENTS.md").write_text("# Existing agent router\n")
        harness_root = target / ".agent-harness"
        harness_root.mkdir()
        (harness_root / "CONTEXT.md").write_text("# Existing harness\n")

        result = run_project_harness("generate", str(target))

        assert result.returncode == 0, result.stderr
        blocks = _render_plan_blocks(result.stdout)
        assert blocks["AGENTS.md"]["status"] == "conflicted"
        assert blocks["AGENTS.md"]["provenance_status"] == (
            "existing path blocks generate; use update for existing harness files"
        )
        assert blocks[".agent-harness/CONTEXT.md"]["status"] == "conflicted"
        assert blocks[".agent-harness/harness.yaml"]["status"] == "conflicted"
        assert (target / "AGENTS.md").read_text() == "# Existing agent router\n"
        assert (harness_root / "CONTEXT.md").read_text() == "# Existing harness\n"


def test_generate_preview_reports_only_missing_gitignore_entries() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / ".gitignore").write_text(".agent-harness/runs/\n")

        result = run_project_harness("generate", str(target))

        assert result.returncode == 0, result.stderr
        blocks = _render_plan_blocks(result.stdout)
        entries = _gitignore_entry_blocks(result.stdout)
        assert blocks[".gitignore"]["status"] == "ignored-state-related"
        assert entries[".agent-harness/runs/"]["status"] == "unchanged"
        assert entries[".agent-harness/tmp/"]["status"] == "ignored-state-related"
        assert (target / ".gitignore").read_text() == ".agent-harness/runs/\n"


def test_generate_preview_includes_phase_4_harness_path_set() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()

        result = run_project_harness("generate", str(target))

        assert result.returncode == 0, result.stderr
        planned_paths = set(_render_plan_blocks(result.stdout))
        expected_paths = {
            "AGENTS.md",
            ".agent-harness/CONTEXT.md",
            ".agent-harness/harness.yaml",
            ".agent-harness/CHANGELOG.md",
            ".agent-harness/references/project.md",
            ".agent-harness/references/commands.md",
            ".agent-harness/references/testing.md",
            ".agent-harness/references/quality_bar.md",
            ".agent-harness/references/security.md",
            ".agent-harness/stages/00_project_discovery/CONTEXT.md",
            ".agent-harness/stages/00_project_discovery/stage.yaml",
            ".agent-harness/stages/01_grill_context/CONTEXT.md",
            ".agent-harness/stages/02_prd/CONTEXT.md",
            ".agent-harness/stages/03_plan/CONTEXT.md",
            ".agent-harness/stages/04_tdd_slice/CONTEXT.md",
            ".agent-harness/stages/05_phase_review/CONTEXT.md",
            ".agent-harness/stages/06_harness_learning/CONTEXT.md",
            ".agent-harness/templates/current_snapshot.md",
            ".agent-harness/templates/context_summary.md",
            ".agent-harness/templates/decision_register.md",
            ".agent-harness/templates/run_metadata.yaml",
            ".agent-harness/templates/next_action.md",
            ".agent-harness/scripts/check_harness.py",
            ".agent-harness/scripts/create_run.py",
            ".agent-harness/scripts/promote_artifact.py",
            ".agent-harness/modules/module_map.yaml",
            ".gitignore",
        }
        assert expected_paths <= planned_paths


def _render_plan_blocks(output: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current_path: str | None = None
    for line in output.splitlines():
        if line.startswith("- path: "):
            current_path = line.removeprefix("- path: ")
            blocks[current_path] = {}
        elif current_path is not None and line.startswith("  "):
            key, separator, value = line.strip().partition(": ")
            if separator:
                blocks[current_path][key] = value
    return blocks


def _gitignore_entry_blocks(output: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current_entry: str | None = None
    for line in output.splitlines():
        if line.startswith("- entry: "):
            current_entry = line.removeprefix("- entry: ")
            blocks[current_entry] = {}
        elif current_entry is not None and line.startswith("  "):
            key, separator, value = line.strip().partition(": ")
            if separator:
                blocks[current_entry][key] = value
    return blocks


def _path_inventory(root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(root)).replace(os.sep, "/")
        for path in root.rglob("*")
    )

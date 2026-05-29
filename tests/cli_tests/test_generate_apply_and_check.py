import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import yaml


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


def test_apply_creates_harness_that_check_accepts() -> None:
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
        (target / "README.md").write_text("# Sample Project\n")

        apply_result = run_project_harness("generate", str(target), "--apply")

        assert apply_result.returncode == 0, apply_result.stderr
        assert "Project Harness Generate Apply" in apply_result.stdout
        assert "files_written:" in apply_result.stdout
        assert "path: AGENTS.md" in apply_result.stdout
        assert "path: .agent-harness/harness.yaml" in apply_result.stdout
        assert (target / "AGENTS.md").exists()
        assert (target / ".agent-harness" / "CONTEXT.md").exists()
        assert (target / ".agent-harness" / "stages" / "00_project_discovery" / "CONTEXT.md").exists()
        assert (target / ".agent-harness" / "stages" / "00_project_discovery" / "stage.yaml").exists()
        assert ".agent-harness/runs/" in (target / ".gitignore").read_text()
        assert ".agent-harness/tmp/" in (target / ".gitignore").read_text()

        manifest = yaml.safe_load((target / ".agent-harness" / "harness.yaml").read_text())
        assert manifest["workflow_id"] == "prd-plan-tdd"
        assert manifest["update_policy"] == "conservative"
        assert any(
            generated_file["path"] == "AGENTS.md"
            for generated_file in manifest["generated_files"]
        )

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode == 0, check_result.stderr
        assert "Project Harness Check" in check_result.stdout
        assert "status: passed" in check_result.stdout


def test_apply_requires_git_worktree_unless_explicitly_waived() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()

        blocked = run_project_harness("generate", str(target), "--apply")

        assert blocked.returncode != 0
        assert "apply requires a Git worktree" in blocked.stderr
        assert not (target / "AGENTS.md").exists()
        assert not (target / ".agent-harness").exists()

        waived = run_project_harness(
            "generate",
            str(target),
            "--apply",
            "--allow-non-git",
        )

        assert waived.returncode == 0, waived.stderr
        assert "Project Harness Generate Apply" in waived.stdout
        assert "git_worktree_waiver: true" in waived.stdout
        assert (target / "AGENTS.md").exists()


def test_apply_refuses_existing_harness_paths_without_overwriting() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        existing_router = "# Existing router\n"
        (target / "AGENTS.md").write_text(existing_router)
        harness_root = target / ".agent-harness"
        harness_root.mkdir()
        existing_context = "# Existing harness context\n"
        (harness_root / "CONTEXT.md").write_text(existing_context)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode != 0
        assert "cannot apply because existing harness path is conflicted" in result.stderr
        assert (target / "AGENTS.md").read_text() == existing_router
        assert (harness_root / "CONTEXT.md").read_text() == existing_context
        assert not (harness_root / "harness.yaml").exists()


def test_check_reports_missing_required_harness_file() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        apply_result = run_project_harness("generate", str(target), "--apply")
        assert apply_result.returncode == 0, apply_result.stderr
        missing_path = target / ".agent-harness" / "stages" / "00_project_discovery" / "stage.yaml"
        missing_path.unlink()

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode != 0
        assert "Project Harness Check" in check_result.stdout
        assert "status: failed" in check_result.stdout
        assert "path: .agent-harness/stages/00_project_discovery/stage.yaml" in check_result.stdout
        assert "required harness file is missing" in check_result.stdout


def test_check_reports_incomplete_stage_manifest_and_markdown_contract() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        apply_result = run_project_harness("generate", str(target), "--apply")
        assert apply_result.returncode == 0, apply_result.stderr
        stage_yaml = target / ".agent-harness" / "stages" / "00_project_discovery" / "stage.yaml"
        stage_data = yaml.safe_load(stage_yaml.read_text())
        del stage_data["required_outputs"]
        stage_yaml.write_text(yaml.safe_dump(stage_data, sort_keys=False))
        stage_contract = target / ".agent-harness" / "stages" / "00_project_discovery" / "CONTEXT.md"
        stage_contract.write_text(stage_contract.read_text().replace("## Verification", "## Checks"))

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode != 0
        assert "stage manifest missing required field: required_outputs" in check_result.stdout
        assert "stage Markdown contract missing heading: ## Verification" in check_result.stdout


def test_check_reports_header_drift_with_registry_authoritative() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        apply_result = run_project_harness("generate", str(target), "--apply")
        assert apply_result.returncode == 0, apply_result.stderr
        manifest = yaml.safe_load((target / ".agent-harness" / "harness.yaml").read_text())
        router_record = next(
            record
            for record in manifest["generated_files"]
            if record["path"] == "AGENTS.md"
        )
        router = target / "AGENTS.md"
        router.write_text(
            router.read_text().replace(
                f"last_generated_sha256: {router_record['last_generated_sha256']}",
                "last_generated_sha256: 0000000000000000000000000000000000000000000000000000000000000000",
            )
        )

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode != 0
        assert "path: AGENTS.md" in check_result.stdout
        assert "provenance header hash drift; registry data is authoritative" in check_result.stdout


def test_check_reports_missing_volatile_state_ignore_policy() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)
        apply_result = run_project_harness("generate", str(target), "--apply")
        assert apply_result.returncode == 0, apply_result.stderr
        (target / ".gitignore").write_text(".agent-harness/runs/\n")

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode != 0
        assert "path: .gitignore" in check_result.stdout
        assert "missing required volatile-state ignore entry: .agent-harness/tmp/" in check_result.stdout


def test_apply_writes_provenance_headers_and_registry_metadata() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        apply_result = run_project_harness("generate", str(target), "--apply")

        assert apply_result.returncode == 0, apply_result.stderr
        router = (target / "AGENTS.md").read_text()
        assert "generator_name: project-harness-generator" in router
        assert "generator_version: 0.0.0" in router
        assert "managed: true" in router
        assert "file_id: agents_md" in router
        assert "template_version: v0" in router
        assert "last_generated_sha256:" in router
        assert "Human edits are allowed; preview-first updates must protect them." in router

        manifest = yaml.safe_load((target / ".agent-harness" / "harness.yaml").read_text())
        router_record = next(
            record
            for record in manifest["generated_files"]
            if record["path"] == "AGENTS.md"
        )
        manifest_record = next(
            record
            for record in manifest["generated_files"]
            if record["path"] == ".agent-harness/harness.yaml"
        )
        assert router_record["generator_version"] == "0.0.0"
        assert router_record["template_version"] == "v0"
        assert router_record["update_policy"] == "conservative"
        assert len(router_record["last_generated_sha256"]) == 64
        assert manifest_record["file_id"] == "agent_harness_harness_yaml"
        assert len(manifest_record["last_generated_sha256"]) == 64


def test_apply_outputs_selective_representative_contract_content() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        apply_result = run_project_harness("generate", str(target), "--apply")

        assert apply_result.returncode == 0, apply_result.stderr
        router = (target / "AGENTS.md").read_text()
        harness_context = (target / ".agent-harness" / "CONTEXT.md").read_text()
        stage_contract = (
            target
            / ".agent-harness"
            / "stages"
            / "00_project_discovery"
            / "CONTEXT.md"
        ).read_text()
        harness_manifest = (target / ".agent-harness" / "harness.yaml").read_text()
        stage_manifest = (
            target
            / ".agent-harness"
            / "stages"
            / "00_project_discovery"
            / "stage.yaml"
        ).read_text()

        assert "Start at `.agent-harness/CONTEXT.md`" in router
        assert "does not duplicate full stage contracts" in router
        assert "Durable workflow and project rules live in `.agent-harness/references/`." in harness_context
        assert "Run artifacts live in `.agent-harness/runs/`" in harness_context
        assert "# Project Discovery" in stage_contract
        assert "Stage ID: 00_project_discovery" in stage_contract
        assert "## Approval Gates" in stage_contract
        assert "generated_files:" in harness_manifest
        assert "stages:" in harness_manifest
        assert "stage_id: 00_project_discovery" in stage_manifest
        assert "completion_criteria:" in stage_manifest

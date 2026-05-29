import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
STAGE_IDS = [
    "00_project_discovery",
    "01_grill_context",
    "02_prd",
    "03_plan",
    "04_tdd_slice",
    "05_phase_review",
    "06_harness_learning",
]


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


def test_new_run_creates_deterministic_stage_skeleton() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = _generated_harness_target(Path(temp_dir))

        result = run_project_harness(
            "new-run",
            str(target),
            "Feature Slice!",
            "--classification",
            "minor",
            "--date",
            "2026-05-29",
        )

        assert result.returncode == 0, result.stderr
        assert "Project Harness New Run" in result.stdout
        assert "run_id: 2026-05-29-feature-slice" in result.stdout
        run_root = target / ".agent-harness" / "runs" / "2026-05-29-feature-slice"
        metadata = yaml.safe_load((run_root / "run_metadata.yaml").read_text())
        assert metadata["run_id"] == "2026-05-29-feature-slice"
        assert metadata["created_date"] == "2026-05-29"
        assert metadata["task_classification"] == "minor"
        assert metadata["status"] == "active"
        assert metadata["status_values"] == [
            "active",
            "paused",
            "completed",
            "abandoned",
        ]
        assert metadata["stage_status_values"] == [
            "pending",
            "active",
            "complete",
            "skipped",
        ]
        assert metadata["current_stage"] == "00_project_discovery"
        assert metadata["stages"]["00_project_discovery"]["status"] == "active"
        assert metadata["stages"]["01_grill_context"]["status"] == "pending"
        assert (run_root / "next_action.md").read_text().startswith("# Next Action")
        for stage_id in STAGE_IDS:
            assert (run_root / "stages" / stage_id).is_dir()


def test_pause_and_resume_preserve_stage_status() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = _generated_harness_target(Path(temp_dir))
        create_result = run_project_harness(
            "new-run",
            str(target),
            "Pause Me",
            "--classification",
            "minor",
            "--date",
            "2026-05-29",
        )
        assert create_result.returncode == 0, create_result.stderr
        run_id = "2026-05-29-pause-me"
        metadata_path = target / ".agent-harness" / "runs" / run_id / "run_metadata.yaml"
        before_pause = yaml.safe_load(metadata_path.read_text())

        pause_result = run_project_harness(
            "pause",
            str(target),
            run_id,
            "--next-action",
            "Continue with the PRD stage.",
        )

        assert pause_result.returncode == 0, pause_result.stderr
        paused = yaml.safe_load(metadata_path.read_text())
        assert paused["status"] == "paused"
        assert paused["current_stage"] == before_pause["current_stage"]
        assert paused["stages"] == before_pause["stages"]
        assert "Continue with the PRD stage." in (
            target / ".agent-harness" / "runs" / run_id / "next_action.md"
        ).read_text()

        resume_result = run_project_harness("resume", str(target), run_id)

        assert resume_result.returncode == 0, resume_result.stderr
        resumed = yaml.safe_load(metadata_path.read_text())
        assert resumed["status"] == "active"
        assert resumed["current_stage"] == before_pause["current_stage"]
        assert resumed["stages"] == before_pause["stages"]


def test_pause_rejects_run_id_path_traversal_without_touching_external_files() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = _generated_harness_target(root)
        outside = root / "outside"
        outside.mkdir()
        metadata_path = outside / "run_metadata.yaml"
        original_metadata = yaml.safe_dump(
            {
                "status": "active",
                "current_stage": "00_project_discovery",
                "stages": {},
            },
            sort_keys=False,
        )
        metadata_path.write_text(original_metadata)

        result = run_project_harness(
            "pause",
            str(target),
            "../../../outside",
            "--next-action",
            "Do not write this outside the target.",
        )

        assert result.returncode != 0
        assert "run id must match generated run id format" in result.stderr
        assert metadata_path.read_text() == original_metadata
        assert not (outside / "next_action.md").exists()


def test_pause_preflights_next_action_symlink_before_metadata_update() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = _generated_harness_target(root)
        create_result = run_project_harness(
            "new-run",
            str(target),
            "Symlink Pause",
            "--classification",
            "minor",
            "--date",
            "2026-05-29",
        )
        assert create_result.returncode == 0, create_result.stderr
        run_id = "2026-05-29-symlink-pause"
        run_root = target / ".agent-harness" / "runs" / run_id
        metadata_path = run_root / "run_metadata.yaml"
        original_metadata = metadata_path.read_text()
        outside_next_action = root / "outside-next-action.md"
        outside_next_action.write_text("# Outside\n")
        (run_root / "next_action.md").unlink()
        _symlink_or_skip(outside_next_action, run_root / "next_action.md")

        result = run_project_harness(
            "pause",
            str(target),
            run_id,
            "--next-action",
            "Do not write through a symlink.",
        )

        assert result.returncode != 0
        assert "refusing to write through symlinked path" in result.stderr
        assert metadata_path.read_text() == original_metadata
        assert outside_next_action.read_text() == "# Outside\n"


def test_new_run_rejects_symlinked_runs_directory_without_writing_outside_target() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = _generated_harness_target(root)
        outside_runs = root / "outside-runs"
        outside_runs.mkdir()
        _symlink_or_skip(outside_runs, target / ".agent-harness" / "runs")

        result = run_project_harness(
            "new-run",
            str(target),
            "External Run",
            "--classification",
            "minor",
            "--date",
            "2026-05-29",
        )

        assert result.returncode != 0
        assert "refusing to write through symlinked path: .agent-harness/runs" in result.stderr
        assert not (outside_runs / "2026-05-29-external-run").exists()


def test_check_fails_non_trivial_run_without_source_branch_or_waiver() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = _generated_harness_target(Path(temp_dir))
        create_result = run_project_harness(
            "new-run",
            str(target),
            "Risky Work",
            "--classification",
            "non-trivial",
            "--date",
            "2026-05-29",
            "--branch-waiver",
            "Solo local test run.",
        )
        assert create_result.returncode == 0, create_result.stderr
        metadata_path = (
            target
            / ".agent-harness"
            / "runs"
            / "2026-05-29-risky-work"
            / "run_metadata.yaml"
        )
        metadata = yaml.safe_load(metadata_path.read_text())
        metadata["source_branch"] = None
        metadata["branch_waiver"] = None
        metadata_path.write_text(yaml.safe_dump(metadata, sort_keys=False))

        check_result = run_project_harness("check", str(target))

        assert check_result.returncode != 0
        assert "path: .agent-harness/runs/2026-05-29-risky-work/run_metadata.yaml" in check_result.stdout
        assert "non-trivial run requires source_branch or branch_waiver" in check_result.stdout


def test_new_run_validates_collision_classification_and_branch_policy() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = _generated_harness_target(root)
        first = run_project_harness(
            "new-run",
            str(target),
            "Repeat",
            "--classification",
            "trivial",
            "--date",
            "2026-05-29",
        )
        assert first.returncode == 0, first.stderr

        collision = run_project_harness(
            "new-run",
            str(target),
            "Repeat",
            "--classification",
            "trivial",
            "--date",
            "2026-05-29",
        )
        missing_classification = run_project_harness(
            "new-run",
            str(target),
            "No Class",
            "--date",
            "2026-05-30",
        )
        explicit_branch = run_project_harness(
            "new-run",
            str(target),
            "Branched",
            "--classification",
            "non-trivial",
            "--date",
            "2026-05-31",
            "--source-branch",
            "feature/harness-run",
        )

        assert collision.returncode != 0
        assert "run id already exists: 2026-05-29-repeat" in collision.stderr
        assert missing_classification.returncode != 0
        assert "--classification" in missing_classification.stderr
        assert explicit_branch.returncode == 0, explicit_branch.stderr
        branch_metadata = yaml.safe_load(
            (
                target
                / ".agent-harness"
                / "runs"
                / "2026-05-31-branched"
                / "run_metadata.yaml"
            ).read_text()
        )
        assert branch_metadata["source_branch"] == "feature/harness-run"

        non_git = root / "non_git_project"
        non_git.mkdir()
        (non_git / "pyproject.toml").write_text("[project]\nname = \"non-git\"\n")
        apply_result = run_project_harness(
            "generate",
            str(non_git),
            "--apply",
            "--allow-non-git",
        )
        assert apply_result.returncode == 0, apply_result.stderr
        blocked_non_trivial = run_project_harness(
            "new-run",
            str(non_git),
            "Needs Branch",
            "--classification",
            "non-trivial",
            "--date",
            "2026-05-29",
        )
        waived_non_trivial = run_project_harness(
            "new-run",
            str(non_git),
            "Waived",
            "--classification",
            "non-trivial",
            "--date",
            "2026-05-30",
            "--branch-waiver",
            "No Git branch for throwaway target.",
        )

        assert blocked_non_trivial.returncode != 0
        assert "require --source-branch or --branch-waiver" in blocked_non_trivial.stderr
        assert waived_non_trivial.returncode == 0, waived_non_trivial.stderr
        waiver_metadata = yaml.safe_load(
            (
                non_git
                / ".agent-harness"
                / "runs"
                / "2026-05-30-waived"
                / "run_metadata.yaml"
            ).read_text()
        )
        assert waiver_metadata["branch_waiver"] == "No Git branch for throwaway target."


def _generated_harness_target(root: Path) -> Path:
    target = root / "sample_project"
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
    apply_result = run_project_harness("generate", str(target), "--apply")
    assert apply_result.returncode == 0, apply_result.stderr
    return target


def _symlink_or_skip(source: Path, link: Path) -> None:
    try:
        os.symlink(source, link, target_is_directory=source.is_dir())
    except OSError as exc:
        pytest.skip(f"symlink unavailable in this environment: {exc}")

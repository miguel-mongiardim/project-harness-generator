import os
import subprocess
import sys
import tempfile
from pathlib import Path

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


def test_generated_grill_contract_names_required_outputs_and_gate() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        contract = (
            target
            / ".agent-harness"
            / "stages"
            / "01_grill_context"
            / "CONTEXT.md"
        ).read_text()
        manifest = yaml.safe_load(
            (
                target
                / ".agent-harness"
                / "stages"
                / "01_grill_context"
                / "stage.yaml"
            ).read_text()
        )
        for artifact in ["interview_log.md", "context_summary.md", "decision_register.md"]:
            assert artifact in contract
            assert artifact in manifest["required_outputs"]
        assert "context_summary_gate" in contract
        assert "context_summary_gate" in manifest["required_gates"]


def test_generated_grill_contract_encodes_interview_mechanics() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        contract = (
            target
            / ".agent-harness"
            / "stages"
            / "01_grill_context"
            / "CONTEXT.md"
        ).read_text()
        expected_phrases = [
            "one controlling interview",
            "focused sub-interviews",
            "recommended answer with rationale",
            "one decision branch at a time",
            "batch only independent low-risk facts",
            "evidence-backed premise challenges",
            "testing-strategy candidates",
            "confirmed, revised, or rejected",
        ]
        for phrase in expected_phrases:
            assert phrase in contract


def test_prd_plan_tdd_and_review_contracts_define_handoffs_and_gates() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        contracts = {
            stage_id: (
                target / ".agent-harness" / "stages" / stage_id / "CONTEXT.md"
            ).read_text()
            for stage_id in [
                "02_prd",
                "03_plan",
                "04_tdd_slice",
                "05_phase_review",
            ]
        }
        assert "context_summary.md" in contracts["02_prd"]
        assert "blocking open questions prevent PRD approval" in contracts["02_prd"]
        assert "exact approved `prd_gate` marker" in contracts["03_plan"]
        assert "durable tracer-bullet plans" in contracts["03_plan"]
        assert "per-slice execution summaries" in contracts["03_plan"]
        assert "cross-phase invariants" in contracts["03_plan"]
        assert "run-local progress" in contracts["04_tdd_slice"]
        assert "does not update durable plan state directly" in contracts["04_tdd_slice"]
        assert "can fail a slice even when tests pass" in contracts["05_phase_review"]
        assert "acceptance criteria" in contracts["05_phase_review"]
        assert "structured self-review" in contracts["05_phase_review"]
        assert "high-risk independent review" in contracts["05_phase_review"]
        assert "pre-commit review when committing is in scope" in contracts["05_phase_review"]
        assert "review gates" in contracts["05_phase_review"]


def test_harness_learning_contract_separates_observations_backlog_and_patches() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        contract = (
            target
            / ".agent-harness"
            / "stages"
            / "06_harness_learning"
            / "CONTEXT.md"
        ).read_text()
        expected_phrases = [
            "local observations",
            "generator backlog",
            "proposed durable harness-source patches",
            "cite evidence",
            "explain justification",
            "target harness-source file",
            "remain unapplied until user acceptance",
        ]
        for phrase in expected_phrases:
            assert phrase in contract


def test_stage_contracts_reference_required_skills_with_compact_fallbacks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        contract_text = "\n".join(
            (
                target / ".agent-harness" / "stages" / stage_id / "CONTEXT.md"
            ).read_text()
            for stage_id in [
                "00_project_discovery",
                "01_grill_context",
                "02_prd",
                "03_plan",
                "04_tdd_slice",
                "05_phase_review",
                "06_harness_learning",
            ]
        )
        manifest_skills = set()
        for stage_id in [
            "00_project_discovery",
            "01_grill_context",
            "02_prd",
            "03_plan",
            "04_tdd_slice",
            "05_phase_review",
            "06_harness_learning",
        ]:
            manifest = yaml.safe_load(
                (
                    target / ".agent-harness" / "stages" / stage_id / "stage.yaml"
                ).read_text()
            )
            manifest_skills.update(
                item["skill"] for item in manifest["required_skills"]
            )
        for skill in [
            "grill-me",
            "write-a-prd",
            "prd-to-plan",
            "tdd",
            "prd-plan-tdd-workflow",
            "precommit-review",
        ]:
            assert skill in contract_text
            assert skill in manifest_skills
        assert "compact fallback" in contract_text


def test_generated_local_templates_include_only_harness_owned_artifacts() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True)

        result = run_project_harness("generate", str(target), "--apply")

        assert result.returncode == 0, result.stderr
        template_names = {
            path.name
            for path in (target / ".agent-harness" / "templates").iterdir()
        }
        assert {
            "current_snapshot.md",
            "context_summary.md",
            "decision_register.md",
            "phase_review.md",
            "harness_learning.md",
            "run_metadata.yaml",
            "stage.yaml",
            "module_context.md",
            "promotion_record.md",
            "next_action.md",
        } <= template_names
        assert not {
            "prd.md",
            "plan.md",
            "slice.md",
            "tdd.md",
        } & template_names
        contract_text = "\n".join(
            (
                target / ".agent-harness" / "stages" / stage_id / "CONTEXT.md"
            ).read_text()
            for stage_id in ["02_prd", "03_plan", "04_tdd_slice"]
        )
        assert "workflow skills supply PRD, plan, slice, and TDD artifact formats" in contract_text

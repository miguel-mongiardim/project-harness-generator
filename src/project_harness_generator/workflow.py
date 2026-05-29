"""Shared generated workflow constants."""

from __future__ import annotations


STAGE_IDS = (
    "00_project_discovery",
    "01_grill_context",
    "02_prd",
    "03_plan",
    "04_tdd_slice",
    "05_phase_review",
    "06_harness_learning",
)

STAGE_TITLES = {
    "00_project_discovery": "Project Discovery",
    "01_grill_context": "Grill Context",
    "02_prd": "PRD",
    "03_plan": "Plan",
    "04_tdd_slice": "TDD Slice",
    "05_phase_review": "Phase Review",
    "06_harness_learning": "Harness Learning",
}

RUN_STATUS_VALUES = ("active", "paused", "completed", "abandoned")
STAGE_STATUS_VALUES = ("pending", "active", "complete", "skipped")

# Project Harness Generator Interview Log

This file records the full numbered grill interview that defined the initial
project direction. It is intentionally an interview log only: it is not a PRD,
not an implementation plan, and not an acceptance checklist.

## 1. Hybrid Harness Model

Question: Should the generated harness live outside the project, inside the
project, or both?

Recommended answer: Both. Use an external generator and a project-local
generated harness with different responsibilities.

User decision: Accepted.

## 2. Runtime Boundary

Question: What is the generated harness supposed to be at runtime?

Recommended answer: A context-and-contract harness, not a new orchestration
framework.

User decision: Accepted.

## 3. Primary Target

Question: Should the harness optimize first for new projects, existing repos,
or both?

Recommended answer: Existing repos first, greenfield second.

User decision: Accepted.

## 4. Initial Pipeline Proposal

Question: What is the minimum software-project harness pipeline?

Recommended answer: Discovery, requirements, plan, implement, verify, review.

User decision: Partially rejected. User prefers the existing
`prd-plan-tdd-workflow`.

## 5. Pre-PRD Grill Stage

Question: Should the harness have a formal pre-PRD grill stage?

Recommended answer: Yes. Treat `grill-me` as an artifact-producing
context-building compiler pass before PRD writing.

User decision: Accepted.

## 6. Context Summary Artifact

Question: What exactly should `01_grill_context` produce?

Recommended answer: A structured `context_summary.md`, not loose notes.

User decision: Accepted.

## 7. Grill Output Set

Question: Should `01_grill_context` keep the raw interview transcript, or only
the distilled context summary?

Recommended answer: Keep `interview_log.md`, `context_summary.md`, and
`decision_register.md`; only promote the summary downstream by default.

User decision: Accepted.

## 8. Discovery Frequency

Question: Should project discovery run before every grill session or only at
attachment time?

Recommended answer: Split discovery into bootstrap discovery and current-task
discovery.

User decision: Accepted.

## 9. Project-Local Harness Directory

Question: Where should the generated project-local harness live?

Recommended answer: `.icm/`.

User decision: Rejected. User prefers `.agent-harness/`.

## 10. Run Artifact Versioning

Question: Should `.agent-harness/runs/` be committed or ignored?

Recommended answer: Ignore run artifacts by default and promote durable outputs
elsewhere.

User decision: Accepted.

## 11. Root Agent Router

Question: Should the generator modify or create root `AGENTS.md`?

Recommended answer: Create or update a minimal router that points to
`.agent-harness/CONTEXT.md`.

User decision: Accepted.

## 12. Stage-Skip Strictness

Question: How strict should the harness be when an agent tries to skip stages?

Recommended answer: Strict for non-trivial work, permissive for small work.

User decision: Provisionally accepted.

## 13. Task Escalation Checklist

Question: How should the harness decide whether work is trivial, minor, or
non-trivial?

Recommended answer: Use a short escalation checklist based on public behavior,
architecture impact, risk, uncertainty, and explicit user requests.

User decision: Accepted.

## 14. Inspect-First Generator

Question: Should the generator be interactive only, or inspect the repo and
propose answers automatically?

Recommended answer: Inspect first, ask only what inspection cannot answer.

User decision: Accepted.

## 15. Durable Rule Source

Question: What should count as the source of truth for project rules?

Recommended answer: `.agent-harness/references/` owns durable agent/project
workflow rules.

User decision: Accepted.

## 16. Project-Specific Stage Contracts

Question: Should generated stage contracts be generic or customized per project?

Recommended answer: Customized per project, with editable generated defaults.

User decision: Accepted.

## 17. Skill Handling

Question: How should the harness handle skills like `write-a-prd`,
`prd-to-plan`, `tdd`, and `grill-me`?

Recommended answer: Stage contracts reference required skills by name and role,
without copying full skill bodies.

User decision: Provisionally accepted.

## 18. Missing Skill Fallbacks

Question: What should happen if a required global skill is missing?

Recommended answer: Include compact fallback procedures in stage contracts.

User decision: Accepted.

## 19. Helper Scripts

Question: Should the generator create executable helper scripts or only
Markdown files?

Recommended answer: Create deterministic helper scripts when they remove
repeated mechanical work.

User decision: Accepted, with correction that scripts do not need to be small.

## 20. Script Ownership Split

Question: Should scripts be generator-level or project-local?

Recommended answer: Use both. Generic mechanics stay in the generator;
project-specific automation lives under `.agent-harness/scripts/`.

User decision: Accepted.

## 21. Architecture Boundary Inference

Question: Should the generator infer architecture boundaries automatically?

Recommended answer: Infer candidates with evidence and confidence, but require
confirmation before treating them as durable rules.

User decision: Accepted.

## 22. Focused Grill Summaries

Question: Should `01_grill_context` be one interview or allow focused
sub-interviews?

Recommended answer: Use one controlling interview with optional focused
sub-summaries for complex branches.

User decision: Accepted.

## 23. Context Summary Approval Gate

Question: Should the harness require explicit approval after `context_summary.md`
before writing the PRD?

Recommended answer: Yes for non-trivial work.

User decision: Accepted.

## 24. PRD Approval Gate

Question: Should the PRD stage require approval before planning starts?

Recommended answer: Yes, but lighter than the context-summary gate.

User decision: Accepted.

## 25. Plan Outputs

Question: Should the plan stage produce one big plan or executable TDD slice
summaries?

Recommended answer: Produce both a durable plan and per-slice execution summaries.

User decision: Accepted.

## 26. Durable Plan Updates

Question: During TDD, should `04_tdd_slice` update durable `plan.md` directly?

Recommended answer: Record run-local progress during TDD and update durable
plan state during phase review.

User decision: Accepted.

## 27. Review Authority

Question: Should `05_phase_review` be allowed to fail a slice even if tests
pass?

Recommended answer: Yes. Green tests are necessary but not sufficient.

User decision: Accepted.

## 28. Harness Learning Cadence

Question: Should `06_harness_learning` run automatically after every phase?

Recommended answer: Run a lightweight check every phase, but update durable
rules only when evidence justifies it.

User decision: Accepted.

## 29. Automation Limits

Question: Should generated harnesses include explicit automation limits?

Recommended answer: Yes, mandatory.

User decision: Accepted.

## 30. Harness Self-Check

Question: Should every generated harness include a validation command?

Recommended answer: Yes. Include a self-check script such as
`.agent-harness/scripts/check_harness.py`.

User decision: Accepted.

## 31. Stage Manifests

Question: Should generated stage contracts be Markdown-only or include a
machine-readable manifest?

Recommended answer: Use both `CONTEXT.md` and `stage.yaml`.

User decision: Accepted.

## 32. Manifest Drift

Question: If `CONTEXT.md` and `stage.yaml` disagree, which wins?

Recommended answer: Neither silently wins; validation fails.

User decision: Accepted.

## 33. Module-Specific Context

Question: Should generated harnesses support nested or module-specific rules?

Recommended answer: Support one explicit module-context layer initially.

User decision: Accepted.

## 34. Module Context Selection

Question: How should the harness decide which module contexts to load?

Recommended answer: Use an editable path-based `module_map.yaml`.

User decision: Accepted.

## 35. Multiple Active Runs

Question: Should the harness support multiple active projects/features at once?

Recommended answer: Yes, through isolated run folders.

User decision: Accepted.

## 36. Run IDs

Question: What should a run ID contain?

Recommended answer: Date plus short human-readable slug; no hidden UUID by
default.

User decision: Accepted.

## 37. Branch Per Run

Question: Should the harness require one Git branch per non-trivial run?

Recommended answer: Yes by default, with an explicit exception path.

User decision: Accepted.

## 38. Completion Levels

Question: Should the harness define done at slice, feature, and run levels?

Recommended answer: Yes.

User decision: Accepted.

## 39. Codex Workspace Integration

Question: Should harnesses integrate with Codex Workspace session notes?

Recommended answer: Yes, with clear separation between project-local run
artifacts and cross-session operational notes.

User decision: Accepted.

## 40. Project Templates

Question: Should the generator create project-specific PRD and plan templates?

Recommended answer: Create thin templates.

User decision: Revised. Use workflow skill templates for PRD, plan, slice, and
TDD; only create local templates for documents not covered by skills.

## 41. Local Template Boundary

Question: Which documents should the harness template locally?

Recommended answer: Only ICM-specific and project-local artifacts such as
current snapshots, context summaries, decision registers, phase review records,
harness learning, run metadata, stage manifests, module context, and promotion
records.

User decision: Accepted.

## 42. Context Summary Template

Question: Should `context_summary.md` be a local template-owned document?

Recommended answer: Yes. It is the most important new template.

User decision: Accepted.

## 43. Open Questions

Question: Should `02_prd` proceed if `context_summary.md` still has open
questions?

Recommended answer: Yes, only if every open question is classified as blocking
or non-blocking.

User decision: Accepted.

## 44. Recommended Answers in Grill

Question: Should `01_grill_context` recommend answers to its own questions?

Recommended answer: Always recommend an answer with rationale.

User decision: Accepted.

## 45. Grill Pacing

Question: Should `01_grill_context` stop after one question at a time or batch
questions?

Recommended answer: One decision branch at a time by default; batch only
independent low-risk facts.

User decision: Accepted.

## 46. Premise Challenges

Question: Should `01_grill_context` be allowed to challenge the user's premise?

Recommended answer: Yes, explicitly, with evidence and a concrete decision.

User decision: Accepted.

## 47. Workflow Profiles

Question: Should the generator support multiple workflow profiles?

Recommended answer: One default profile now; profile support later.

User decision: Accepted.

## 48. Dogfooding Direction

Question: Should the generator itself be built using the same harness workflow?

Recommended answer: Yes, but bootstrap pragmatically.

User decision: Accepted in principle.

## 49. Dogfooding Timing

Question: Should dogfooding be a V0 acceptance criterion or V1 milestone?

Recommended answer: Narrow V0 acceptance criterion.

User decision: Accepted.

## 50. Primary Interface

Question: What should the generator's primary interface be?

Recommended answer: CLI first, library/API later.

User decision: Accepted.

## 51. Preview Before Apply

Question: Should the CLI generate files directly or first produce a preview?

Recommended answer: Preview by default, write with explicit apply.

User decision: Accepted.

## 52. Existing Harness Overwrites

Question: Should the generator overwrite existing `.agent-harness/` files?

Recommended answer: Never silently.

User decision: Accepted.

## 53. Provenance Headers

Question: Should generated harness files include provenance headers?

Recommended answer: Yes, with an explicit "edits expected" policy.

User decision: Accepted.

## 54. Git Requirement

Question: Should the generator require Git to operate?

Recommended answer: Optional for inspect/preview, required or explicitly waived
for apply.

User decision: Accepted.

## 55. Implementation Language

Question: What should be the generator's V0 implementation language?

Recommended answer: Python.

User decision: Accepted.

## 56. Template Rendering

Question: Should V0 use a template engine or plain Python render functions?

Recommended answer: Plain Python render functions.

User decision: Accepted.

## 57. Schema Approach

Question: Should V0 use Pydantic or standard-library dataclasses?

Recommended answer: Dataclasses plus explicit validation for V0.

User decision: Accepted.

## 58. Manifest Format

Question: Should V0 use YAML or JSON for editable manifests?

Recommended answer: YAML for human-authored/editable manifests; JSON only for
machine logs if needed.

User decision: Accepted.

## 59. YAML Dependency

Question: Should the generator add a YAML dependency or write minimal YAML
itself?

Recommended answer: Use PyYAML through an isolated adapter.

User decision: Accepted.

## 60. Inspect Command Execution

Question: Should `agent-harness inspect` run project commands or only inspect
files?

Recommended answer: File inspection by default; command execution only with
explicit opt-in.

User decision: Accepted.

## 61. Command Verification Levels

Question: Should `--verify-commands` run tests/builds or only check commands?

Recommended answer: Separate non-invasive `--verify-commands` from
`--run-checks`.

User decision: Accepted.

## 62. Command Confidence

Question: Should the generated harness include command confidence levels?

Recommended answer: Yes. Record source, verification state, confidence, and
notes.

User decision: Accepted.

## 63. Testing Strategy Inference

Question: Should the generator infer testing strategy or require the user to
define it?

Recommended answer: Infer candidates, then confirm during grill.

User decision: Accepted.

## 64. Testing Philosophy

Question: Should the harness encode integration-style tests through public
interfaces as a default quality rule?

Recommended answer: Yes, unless project evidence contradicts it.

User decision: Accepted.

## 65. No Dead Architecture

Question: Should the harness include an explicit no-dead-architecture rule?

Recommended answer: Yes, as a cross-phase invariant.

User decision: Accepted.

## 66. Walking Skeleton

Question: Should `03_plan` be allowed to include a walking skeleton phase?

Recommended answer: Yes, only under the tracer-bullet rule.

User decision: Accepted.

## 67. Cross-Phase Invariants

Question: Should cross-phase invariants be tracked separately from acceptance
criteria?

Recommended answer: Yes, and include them in every plan.

User decision: Accepted.

## 68. Independent Review

Question: Should `05_phase_review` include an independent review pass?

Recommended answer: Structured self-review by default; independent review when
risk is high.

User decision: Accepted.

## 69. Pre-Commit Review

Question: Should the harness have a built-in pre-commit review gate?

Recommended answer: Yes, but only when committing is in scope.

User decision: Accepted.

## 70. CI Integration

Question: Should the generator create CI integration for `check_harness.py`?

Recommended answer: Not by default in V0; generate instructions and optional
snippet.

User decision: Accepted.

## 71. Gitignore Entries

Question: Should the generator create `.gitignore` entries automatically?

Recommended answer: Yes, preview-first and minimal.

User decision: Accepted.

## 72. Harness Changelog

Question: Should the harness include a lightweight changelog for harness-source
changes?

Recommended answer: Yes.

User decision: Accepted.

## 73. Root Harness Manifest

Question: Should generated harnesses have a version file?

Recommended answer: Yes. Use `.agent-harness/harness.yaml`.

User decision: Accepted.

## 74. Conservative Update

Question: Should V0 support updating an existing harness when the generator
improves?

Recommended answer: Yes, but only conservative update mode.

User decision: Accepted.

## 75. Update Policy

Question: Should the generator support detaching a harness from generator
updates?

Recommended answer: Yes. Use `update_policy` modes: conservative, manual_only,
detached.

User decision: Accepted.

## 76. Codex Workspace Scope

Question: Should Codex Workspace support be core or optional?

Recommended answer: Optional user-profile integration, not core generator
behavior.

User decision: Accepted.

## 77. User Config

Question: Should the generator support user profiles for personal defaults?

Recommended answer: Use a simple local user config file, not a profile system.

User decision: Accepted.

## 78. Inspection Caches

Question: Should the generator store project inspection caches?

Recommended answer: No persistent cache in V0; optional ignored temporary cache
only.

User decision: Accepted.

## 79. Run Skeletons

Question: Should `new-run` create all stage output folders upfront?

Recommended answer: Yes.

User decision: Accepted.

## 80. AI Stage Execution

Question: Should stage execution be automated by the CLI?

Recommended answer: No AI stage execution in V0.

User decision: Accepted.

## 81. Run Metadata

Question: Should `run_metadata.yaml` track stage status?

Recommended answer: Yes.

User decision: Accepted.

## 82. Skipped Stages

Question: Should agents be allowed to mark stages skipped?

Recommended answer: Yes, with recorded reason and user approval for mandatory
stage skips.

User decision: Accepted.

## 83. Pause and Resume

Question: Should the harness support pausing and resuming runs?

Recommended answer: Yes, through run metadata and `next_action.md`.

User decision: Accepted.

## 84. Promotion Record

Question: Should the harness include a standard promotion record?

Recommended answer: Yes.

User decision: Accepted.

## 85. Promotion Backlinks

Question: Should promoted PRDs and plans link back to their source run?

Recommended answer: Yes.

User decision: Accepted.

## 86. Edit-Source Opportunities

Question: Should harness learning track edit-source opportunities separately?

Recommended answer: Yes.

User decision: Accepted.

## 87. Harness Learning Apply Policy

Question: Should harness learning update project source rules automatically?

Recommended answer: No automatic apply; propose patches only.

User decision: Accepted.

## 88. Security Defaults

Question: Should the generator include security-specific defaults even for
non-security projects?

Recommended answer: Yes, minimal baseline only.

User decision: Accepted.

## 89. Dependency Change Policy

Question: Should the generator include dependency-change policy?

Recommended answer: Yes.

User decision: Accepted.

## 90. Dependency Health Scope

Question: Should bootstrap discovery inspect dependency health?

Recommended answer: Lightweight inventory only in V0.

User decision: Accepted.

## 91. Stack Model

Question: Should generated harnesses be language/framework-specific or
language-agnostic with detected add-ons?

Recommended answer: Language-agnostic core with detected stack add-ons.

User decision: Accepted.

## 92. V0 Stack Detectors

Question: Which stack detector should V0 implement first?

Recommended answer: Generic plus Python detectors only.

User decision: Accepted.

## 93. Python Runtime Baseline

Question: Should the Python detector parse `pyproject.toml` with `tomllib`?

Recommended answer: Yes. Use Python 3.11+.

User decision: Accepted.

## 94. Packaging

Question: Should the generator be an installable Python CLI or just a script?

Recommended answer: Minimal installable Python package from the start.

User decision: Accepted.

## 95. CLI Parser

Question: Should the CLI use `argparse` or Typer/Click?

Recommended answer: `argparse` for V0.

User decision: Accepted.

## 96. Generator Tests

Question: Should V0 include tests for the generator itself from the start?

Recommended answer: Yes, TDD-aligned public CLI behavior tests.

User decision: Accepted.

## 97. Golden File Tests

Question: Should V0 use golden-file tests for generated Markdown/YAML?

Recommended answer: Selectively.

User decision: Accepted.

## 98. First PRD Target

Question: Should the generator's first PRD be for the generator itself?

Recommended answer: Yes.

User decision: Accepted at the time, later superseded by the decision to create
the repo first and defer PRD/plan until explicitly requested.

## 99. V0 Out Of Scope

Question: What should be explicitly out of scope for Generator V0?

Recommended answer: No AI stage execution by CLI, web UI, daemon/server,
multi-profile framework, complex semantic merge, non-Python stack detectors
beyond generic fallback, automatic CI modification, vulnerability/license
scanning, persistent inspection cache, automatic harness-learning rule
application, autonomous source edits by scripts, cloud sync/hosted service, or
framework/runtime orchestration layer.

User decision: Accepted.

## 100. V0 Success Demo

Question: What should be the V0 success demo?

Recommended answer: Attach the generator to a small Python repo and complete one
narrow dogfood loop.

User decision: Accepted.

## 101. Existing `agent_harness` Inspection

Question: Should the existing `agent_harness` repo be inspected before drafting
the PRD?

Recommended answer: Yes.

User decision: Accepted.

## 102. Existing Repo Integration

Question: Should Generator V0 be a feature track inside the existing
`agent_harness` package?

Recommended answer: Initially yes, under a separate command family.

User decision: Rejected. User clarified this is not the same project.

## 103. New Project Name

Question: What should the new project/package be called?

Recommended answer: Distribution `project-harness-generator`, Python package
`project_harness_generator`.

User decision: Accepted.

## 104. New Project Location

Question: Where should the new project live?

Recommended answer:
`C:\Users\mmarque9\ai_projects\projects\project-harness-generator`.

User decision: Accepted.

## 105. Repo Before PRD

Question: Should the repo be created before writing the PRD, or should the PRD
come first?

Recommended answer: PRD first.

User decision: Rejected. User wants repo/project first. PRD and plan will be
requested later. Inside the repo, this interview log should be the only planning
artifact for now.

## 106. Minimal Initial Project

Question: When creating the repo before PRD, how minimal should the initial
project be?

Recommended answer: Minimal Git/Python skeleton plus interview log only:
`README.md`, `pyproject.toml`, `src/project_harness_generator/__init__.py`,
`tests/`, and `docs/interview-log.md`.

User decision: Accepted.

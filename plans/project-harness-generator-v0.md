# Plan: Project Harness Generator V0

> Source PRD: `docs/prd-project-harness-generator-v0.md`
> Source context: `docs/interview-log.md`
> Workflow: `prd-plan-tdd-workflow` with `prd-to-plan`

## Bootstrap Note

This repository does not yet contain the generated harness that will later
enforce `context_summary_gate` and `prd_gate` mechanically. This plan is created
under the user's explicit instruction to run `prd-to-plan` after the PRD was
drafted and reviewed. Future generated harnesses must enforce the PRD approval
gate before planning.

## Architectural Decisions

Durable decisions that apply across all phases:

- **Public interface**: CLI-first package with the command name
  `project-harness`.
- **Supported commands**: `inspect`, `generate`, `check`, `update`, `new-run`,
  `approve`, `advance`, `skip-stage`, `pause`, `resume`, `promote`, and
  `config validate`.
- **Implementation language**: Python 3.11+.
- **CLI parser**: standard-library `argparse`.
- **Core models**: standard-library dataclasses with explicit validation for
  inspection evidence, command candidates, render plans, generated-file records,
  stage definitions, local config, run metadata, approval markers, promotion
  records, and update decisions.
- **Project metadata parser**: standard-library `tomllib` for `pyproject.toml`.
- **Template approach**: plain Python render functions, not a template engine.
- **YAML boundary**: editable manifests and run metadata are YAML through an
  isolated adapter. Introduce PyYAML only when the first YAML-backed public
  behavior needs it.
- **Storage**: generated harness source lives in `.agent-harness/`; volatile
  runs and temporary state live in ignored `.agent-harness/runs/` and
  `.agent-harness/tmp/`.
- **Generated source of truth**: `.agent-harness/references/` owns durable
  project and workflow rules. Root `AGENTS.md` and stage contracts route to or
  summarize those references.
- **Runtime boundary**: the CLI performs deterministic file and metadata
  operations only. It does not execute AI stages.
- **Inspection boundary**: default inspection reads files only. Command
  verification and project check execution are separate explicit opt-ins.
- **Write boundary**: preview is the default for generation and update. Writes
  require explicit apply actions and are conflict-aware.
- **Git policy**: inspect and preview can run without Git; write operations
  require a Git worktree unless explicitly waived.
- **Approval model**: approvals are run-local YAML markers bound to gate ids and,
  for artifact approvals, exact artifact hashes.
- **Audit model**: run metadata, promotion records, generated-file registry
  entries, provenance headers, and check diagnostics provide the mechanical
  audit trail.
- **Update model**: `.agent-harness/harness.yaml` owns the generated-file
  registry. Registry data is authoritative if it disagrees with provenance
  headers.
- **External service boundary**: V0 does not modify CI or call hosted services.
  It may generate optional CI snippets as inert documentation.
- **Testing stance**: tests exercise public CLI behavior and filesystem
  artifacts through temporary target repositories. Private helper tests are
  secondary and used only where they clarify deterministic edge cases.

## TDD Execution Rules

- Execute one observable behavior at a time.
- Start each phase with the listed RED test, then add narrower tests as needed.
- Keep implementation limited to what the current behavior exercises.
- Refactor only when relevant tests are green.
- A phase is complete only when its acceptance criteria are satisfied, tests are
  green, public docs match behavior, and cross-phase invariants still hold.
- Update this plan's checklist only after phase review, not during in-progress
  TDD work.

---

## Phase 0: CLI Walking Skeleton

**User stories covered**

- Story 14: dogfood the workflow on a small Python repository.

**PRD requirements covered**

- Behavioral: 1
- Implementation decisions: 1-5
- Testing decisions: 1-3

**Observable behaviors**

- `project-harness --help` prints command help.
- Invalid commands and invalid arguments return non-zero status with actionable
  usage diagnostics.
- The package exposes the installed console script through the Python project
  metadata.

**First RED test**

- `tests/cli_tests/test_cli_skeleton.py::test_help_lists_public_commands`

### What to build

Create the smallest CLI entry point that can parse top-level commands, return
stable exit codes, and expose placeholders for the V0 command surface. This is
the walking skeleton through packaging, CLI invocation, and test execution. It
does not implement command internals beyond help and diagnostics.

### Acceptance criteria

- [x] `project-harness --help` lists every V0 command from the PRD.
- [x] Unknown commands fail without a traceback.
- [x] Missing required arguments fail with command-specific usage text.
- [x] Tests invoke the CLI through the public entry point or module entry point,
      not private parser helpers.
- [x] The pytest-based TDD command is reproducible through declared project
      metadata or documented environment setup without adding pytest as a
      runtime dependency.
- [x] README usage reflects only implemented skeleton behavior.

### Out of scope

- Repository inspection.
- File rendering or writes.
- YAML manifests.
- Target repository mutation.

---

## Phase 1: Passive Repository Inspection

**User stories covered**

- Story 1: inspect an existing repository before generating anything.

**PRD requirements covered**

- Behavioral: 2-5
- Implementation decisions: 6-8, 11, 35-36, 41
- Testing decisions: 4-7

**Observable behaviors**

- `project-harness inspect <target>` reads a target repository and emits an
  evidence-labeled summary.
- A minimal Python fixture repository reports detected stack, package metadata,
  test configuration, docs conventions, existing agent/context files, command
  candidates, lightweight dependency inventory, and architecture signals.
- Default inspection does not execute target tests, builds, scripts, installs,
  or package-manager mutation commands.

**First RED test**

- `tests/cli_tests/test_inspect.py::test_inspect_reports_python_repo_evidence_without_running_commands`

### What to build

Implement read-only target resolution, file inventory, Python metadata
detection, pytest/testpath detection, agent/context file detection, docs
convention detection, dependency inventory, command-candidate discovery, and
evidence/confidence reporting. Model inspection results as structured data
before formatting them for CLI output.

### Acceptance criteria

- [x] Missing target paths fail with clear diagnostics.
- [x] Non-repository directories can be inspected in read-only mode.
- [x] Python projects are detected from `pyproject.toml` using `tomllib`.
- [x] Command candidates include command text, source, verification state,
      confidence, and notes.
- [x] Default inspection records candidate commands but does not run them.
- [x] Inferred facts are labeled with evidence and confidence rather than
      re-asked as prompts.

### Out of scope

- Command verification probes.
- Project test/build execution.
- Harness preview or apply.

---

## Phase 2: Command Verification Opt-Ins

**User stories covered**

- Story 1: inspect safely.
- Story 11: avoid risky commands and external mutation without approval.

**PRD requirements covered**

- Behavioral: 6-9
- Testing decisions: 5, 13, 29

**Observable behaviors**

- `project-harness inspect <target> --verify-commands` performs only bounded,
  non-invasive command checks.
- Unsafe command candidates are reported as skipped rather than treated as
  verified.
- `--run-checks` is required before target repository tests or builds execute,
  and those check results are reported separately from passive inspection and
  verification evidence.

**First RED test**

- `tests/cli_tests/test_command_verification.py::test_verify_commands_skips_project_tests_without_run_checks`

### What to build

Add a command safety classifier, executable/help/version probe runner with
timeouts, explicit skipped-probe diagnostics, and a separate project-check
runner gated by `--run-checks`. Keep command verification unable to upgrade
unsafe or skipped target checks into verified confidence.

### Acceptance criteria

- [x] Default inspect runs no external target commands.
- [x] `--verify-commands` may resolve executables and run bounded help/version
      probes only for allowed tools.
- [x] Test, build, install, package-manager mutation, and side-effect commands
      are skipped without `--run-checks`.
- [x] Probe timeouts and errors are reported without crashing.
- [x] `--run-checks` results are reported in a distinct section from passive
      evidence and command verification.

### Out of scope

- Persistent inspection cache.
- Dependency health scanning.
- Vulnerability or license checks.

---

## Phase 3: Local User Config

**User stories covered**

- Story 13: use personal defaults without re-entering them for every project.

**PRD requirements covered**

- Behavioral: 11-16
- Implementation decisions: 38-40
- Testing decisions: 32

**Observable behaviors**

- `project-harness config validate [path]` accepts a valid V0 config and rejects
  unknown fields, invalid types, invalid enum values, unsupported workflow ids,
  and absolute project-relative paths.
- Missing config produces stable defaults.
- CLI arguments override config values where a command consumes the relevant
  behavior.

**First RED test**

- `tests/cli_tests/test_config.py::test_missing_config_uses_stable_defaults`

### What to build

Implement config discovery, parsing, validation, defaulting, CLI override
resolution, and command-specific consumption. Keep config small:
`workflow_id`, `default_prd_path`, `default_plan_path`, `update_policy`, and
`codex_workspace.enabled`.

### Acceptance criteria

- [x] Missing config returns the PRD-defined defaults.
- [x] Valid config can be validated through the public CLI.
- [x] Unknown fields and invalid types fail before generate or update proceeds.
- [x] `update_policy` only accepts `conservative`, `manual_only`, or `detached`.
- [x] `workflow_id` only accepts `prd-plan-tdd`.
- [x] Project-relative path fields reject absolute paths.
- [x] CLI flags override config values for generate, update, and new-run.

### Out of scope

- Multi-profile config.
- Project-local config discovery beyond the V0 user config.
- Core dependency on Codex Workspace.

---

## Phase 4: Preview-First Harness Render Plan

**User stories covered**

- Story 2: preview proposed files before writing.
- Story 3: avoid silent overwrites.

**PRD requirements covered**

- Behavioral: 10, 17, 20, 64
- Implementation decisions: 11, 29, 43
- Testing decisions: 2-3, 8, 35

**Observable behaviors**

- `project-harness generate <target>` produces a preview of proposed writes
  without modifying the target repository.
- Preview reports intended paths, file categories, overwrite/conflict status,
  provenance status, and required `.gitignore` entries.
- Existing harness files are reported as conflicts for generation apply rather
  than being silently treated as an update.

**First RED test**

- `tests/cli_tests/test_generate_preview.py::test_generate_preview_reports_files_without_writing`

### What to build

Build a render-plan model from inspection evidence and config defaults. Generate
file plans for root `AGENTS.md`, `.agent-harness/` source, references, stages,
templates, scripts, module map, manifest, changelog, and ignore entries, but
emit only preview output in this phase.

### Acceptance criteria

- [x] Preview creates no files or directories in the target repository.
- [x] Preview includes every intended write path and whether it is addable,
      unchanged, conflicted, or ignored-state-related.
- [x] Preview reports minimal required `.gitignore` changes for
      `.agent-harness/runs/` and `.agent-harness/tmp/`.
- [x] Existing `AGENTS.md` or `.agent-harness/` files are reported as conflicts
      unless the future update command is used.
- [x] Preview consumes config defaults and CLI overrides for PRD path, plan
      path, workflow id, and update policy.

### Out of scope

- Writing harness files.
- Harness self-check.
- Conservative update application.

---

## Phase 5: Apply a Valid Harness and Check It

**User stories covered**

- Story 4: root router and project-local harness context.
- Story 8: harness self-check.

**PRD requirements covered**

- Behavioral: 18-24, 50-53, 65-66
- Implementation decisions: 9-15, 29-32, 34
- Testing decisions: 3, 9-11, 37-39

**Observable behaviors**

- `project-harness generate <target> --apply` writes a new valid harness only
  after explicit apply.
- `project-harness check <target>` passes for a freshly generated harness.
- `check` fails with actionable diagnostics when required files are missing,
  manifests are incomplete, stage contracts omit required structural items, or
  manifests and Markdown contracts drift.

**First RED test**

- `tests/cli_tests/test_generate_apply_and_check.py::test_apply_creates_harness_that_check_accepts`

### What to build

Introduce the YAML adapter, generated-file registry, provenance headers, root
router rendering, minimal generated harness source, stage manifests, stage
Markdown contract structure, helper script placeholders for deterministic
mechanics, and self-check validation. Write only through an apply path that
enforces Git worktree policy or explicit waiver.

### Acceptance criteria

- [ ] Apply requires a Git worktree unless explicitly waived.
- [ ] Apply writes root `AGENTS.md` as a router rather than duplicating full
      contracts.
- [ ] Apply writes `.agent-harness/CONTEXT.md`, `harness.yaml`,
      `CHANGELOG.md`, `references/`, `stages/`, `templates/`, `scripts/`, and
      `modules/module_map.yaml`.
- [ ] Generated source files include provenance headers with generator name,
      version, managed/update status, file or template id, last generated hash
      when applicable, and human-edit protection wording.
- [ ] `.agent-harness/harness.yaml` records generated-file ids, paths, generator
      versions, template versions, update policy, and last generated SHA-256.
- [ ] `.gitignore` keeps volatile run and temporary state ignored while harness
      source remains commit-eligible.
- [ ] `check` validates required files, manifest schema, Markdown structural
      headings, generated-file registry consistency, and ignore policy.
- [ ] `check` treats registry data as authoritative when headers disagree and
      reports header drift.
- [ ] Golden-file coverage stays selective: root router,
      `.agent-harness/CONTEXT.md`, one representative stage contract,
      `harness.yaml`, and one `stage.yaml`; broad snapshots for every generated
      file are avoided unless later evidence justifies them.

### Out of scope

- Full stage prose quality beyond required structural contracts.
- Run creation.
- Update semantics.

---

## Phase 6: Stage Contracts and Local Templates

**User stories covered**

- Story 5: explicit stage contracts for non-trivial work.
- Story 6: required skills by name with compact fallbacks.
- Story 12: required artifacts and approval gates are not optional guidance.

**PRD requirements covered**

- Behavioral: 22-49, 85
- Implementation decisions: 14, 16-24, 31-34
- Testing decisions: 16-20, 22-23, 30

**Observable behaviors**

- A generated harness contains project-customized stage contracts for
  `00_project_discovery`, `01_grill_context`, `02_prd`, `03_plan`,
  `04_tdd_slice`, `05_phase_review`, and `06_harness_learning`.
- Stage contracts name required inputs, outputs, approvals, verification,
  required skills, fallbacks, and completion criteria.
- Generated local templates exist only for artifacts not owned by the workflow
  skills.

**First RED test**

- `tests/cli_tests/test_stage_contracts.py::test_generated_grill_contract_names_required_outputs_and_gate`

### What to build

Render complete stage contracts and local templates. Encode the accepted grill
mechanics, context summary approval, PRD approval, vertical plan handoff,
run-local TDD progress, phase review authority, pre-commit review when
committing is in scope, harness-learning proposal behavior, and no-dead-
architecture rule. Reference workflow skills by role/name and include compact
fallback procedures without vendoring skill bodies.

### Acceptance criteria

- [ ] Grill context contract requires `interview_log.md`,
      `context_summary.md`, and `decision_register.md`.
- [ ] Downstream PRD work consumes `context_summary.md` by default.
- [ ] Grill mechanics require one controlling interview, optional focused
      sub-interviews, recommended answers with rationale, one branch at a time
      by default, limited batching for independent low-risk facts, and explicit
      evidence-backed premise challenges.
- [ ] Grill contract requires testing-strategy candidates to be confirmed,
      revised, or rejected.
- [ ] PRD contract blocks approval while blocking open questions remain.
- [ ] Plan contract requires an exact approved `prd_gate` marker for the PRD
      being planned.
- [ ] Plan contract produces durable tracer-bullet plans, per-slice execution
      summaries, and cross-phase invariants.
- [ ] TDD slice contract records run-local progress without updating durable
      plan state directly.
- [ ] Phase review can fail a slice even when tests pass.
- [ ] Phase review checks acceptance criteria, project rules, cross-phase
      invariants, structured self-review, high-risk independent review,
      pre-commit review when committing is in scope, and review gates.
- [ ] Harness learning separates local observations, generator backlog, and
      proposed durable harness-source patches.
- [ ] Harness-learning proposals cite evidence, explain justification, name a
      target harness-source file, and remain unapplied until user acceptance.
- [ ] Generated local templates include current snapshot, context summary,
      decision register, phase review, harness learning, run metadata, stage
      manifest, module context, promotion record, and next action templates.
- [ ] PRD, plan, slice, and TDD artifact formats are referenced from workflow
      skills rather than generated as local templates.
- [ ] Required-skill references include `grill-me`, `write-a-prd`,
      `prd-to-plan`, `tdd`, `prd-plan-tdd-workflow`, and `precommit-review`
      by role/name with compact missing-skill fallbacks.

### Out of scope

- CLI enforcement of approval markers.
- Run metadata mutation.
- Applying harness-learning patches.

---

## Phase 7: Durable References and Project Customization

**User stories covered**

- Story 4: agents can find project rules without chat history.
- Story 6: portable skill-aware contracts.
- Story 11: security and automation limits.

**PRD requirements covered**

- Behavioral: 24, 53-64, 85
- Implementation decisions: 25-28, 33, 36-37, 41-42
- Testing decisions: 21, 24-26, 28-30

**Observable behaviors**

- Generated references contain the durable workflow and project rules needed by
  future agents.
- References preserve inspection evidence, command confidence, stack add-ons,
  security baseline, dependency-change policy, optional Codex Workspace
  integration, and generated check instructions.
- Stage contracts and references reflect target project evidence while
  remaining editable generated defaults.

**First RED test**

- `tests/cli_tests/test_generated_references.py::test_generated_references_include_quality_bar_and_security_baseline`

### What to build

Render and validate durable reference files for project purpose, architecture
candidates, command candidates, testing, workflow classification, quality bar,
automation limits, security baseline, dependency-change policy, check
instructions, optional CI snippets, optional Codex Workspace integration, and
generic/Python stack add-ons. Keep language-agnostic workflow rules separate
from detected stack add-ons.

### Acceptance criteria

- [ ] `.agent-harness/references/` is named as the durable rule source of truth.
- [ ] Command references preserve source, verification state, confidence, and
      notes.
- [ ] Workflow classification reference includes a concrete
      trivial/minor/non-trivial escalation checklist based on public behavior,
      architecture impact, risk, uncertainty, and explicit user requests.
- [ ] Quality-bar reference defines slice, feature, and run done.
- [ ] Quality-bar reference encodes integration-style public-interface tests as
      the default unless project evidence contradicts it.
- [ ] Module context is selected through an editable path-based
      `modules/module_map.yaml`.
- [ ] Core workflow references are language-agnostic.
- [ ] Generic and Python stack add-ons are layered separately and do not replace
      core workflow contracts.
- [ ] Optional Codex Workspace integration keeps project-local run artifacts
      separate from cross-session operational notes.
- [ ] Security baseline covers secrets, risky commands, external mutation,
      dependency changes, and untrusted inputs.
- [ ] Generated check instructions describe local self-check and optional CI
      snippets without modifying CI files.
- [ ] Architecture and testing inferences are labeled with evidence,
      confidence, and confirmation status before becoming durable rules.

### Out of scope

- Non-Python stack detectors beyond generic fallback.
- Automatic CI modification.
- Dependency health, vulnerability, or license scanning.

---

## Phase 8: Run Skeletons, Branch Policy, and Pause/Resume

**User stories covered**

- Story 7: isolated run folders and metadata.
- Story 12: stage status and approvals are explicit.

**PRD requirements covered**

- Behavioral: 39, 67-74
- Implementation decisions: 19-20
- Testing decisions: 12, 27, 31, 36

**Observable behaviors**

- `project-harness new-run <target> <slug> --classification <...>` creates a
  deterministic isolated run skeleton.
- Non-trivial runs in Git worktrees require a source branch or explicit branch
  waiver.
- `pause` records the next action and marks the run paused; `resume` reads the
  next action and restores active state without losing stage status.

**First RED test**

- `tests/cli_tests/test_runs.py::test_new_run_creates_deterministic_stage_skeleton`

### What to build

Implement run-id normalization, collision checks, run metadata writing, stage
directory creation, `next_action.md`, source branch detection or CLI override,
branch waiver storage, pause/resume commands, and self-check validation for
branch metadata.

### Acceptance criteria

- [ ] Run ids use `<YYYY-MM-DD>-<slug>` with local date by default and
      `--date` override for deterministic tests.
- [ ] Slugs normalize to lowercase kebab case with ASCII letters, digits, and
      hyphens only.
- [ ] Run id collisions fail with actionable diagnostics.
- [ ] New runs require explicit task classification:
      `trivial`, `minor`, or `non-trivial`.
- [ ] New runs receive metadata, stage output directories, and `next_action.md`.
- [ ] Run metadata records run status, current stage, per-stage status, source
      branch, branch waiver when used, created date, and task classification.
- [ ] Run status values are `active`, `paused`, `completed`, and `abandoned`.
- [ ] Stage status values are `pending`, `active`, `complete`, and `skipped`.
- [ ] Non-trivial Git worktree runs require a source branch or branch waiver.
- [ ] `check` fails when a non-trivial run lacks both source branch and waiver.
- [ ] `pause` and `resume` preserve per-stage status.

### Out of scope

- Approval marker validation.
- Artifact promotion.
- Completing runs.

---

## Phase 9: Approval Gates, Advancement, and Stage Skips

**User stories covered**

- Story 5: agents know required gates and completion criteria.
- Story 12: approval gates are enforceable.

**PRD requirements covered**

- Behavioral: 30-41
- Implementation decisions: 18-20
- Testing decisions: 14-15

**Observable behaviors**

- `approve` creates deterministic approval markers without executing AI stages.
- `advance` validates the supplied stage's required artifacts, approvals, and
  branch policy before marking that stage complete and activating the next one.
- `skip-stage` records reasons and requires exact-stage approval for mandatory
  non-trivial stage skips.

**First RED test**

- `tests/cli_tests/test_approvals_and_advancement.py::test_prd_stage_cannot_advance_without_exact_prd_gate`

### What to build

Implement approval marker schema validation, artifact hash binding, context
summary readiness derivation, lighter PRD gate behavior, rejected-marker
handling, advance validation, stage skip rules, and run metadata transitions.

### Acceptance criteria

- [ ] Approval markers live under
      `.agent-harness/runs/<run-id>/approvals/<gate-id>.yaml`.
- [ ] Markers include gate id, approval type, optional stage id, optional
      artifact path and hash, decision, approver, timestamp, and optional note.
- [ ] Artifact gates require `decision: approved` and a current matching
      artifact hash.
- [ ] Rejected approval markers are audit evidence but never satisfy gates.
- [ ] `context_summary_gate` readiness is derived from required sections and
      open-question classifications in `context_summary.md`.
- [ ] `context_summary_gate` marker records derived readiness rather than a raw
      unchecked user assertion.
- [ ] `prd_gate` binds to the exact PRD artifact hash and does not reopen grill
      decisions unless the PRD introduces new blocking questions.
- [ ] Non-trivial runs cannot advance from context summary to PRD or PRD to plan
      without required exact approval markers.
- [ ] `advance` treats the supplied stage id as the stage being completed.
- [ ] Mandatory non-trivial stage skips require a reason and an approved
      `stage_skip` marker bound to the exact skipped stage.
- [ ] Trivial and minor runs may record non-applicable stage skips without
      approval unless the stage is security-sensitive or destructive.

### Out of scope

- Human approval UI.
- AI stage execution.
- Semantic review of PRD or plan prose.

---

## Phase 10: Promotion Records and Durable Artifact Copy

**User stories covered**

- Story 9: promoted outputs link back to their source run.

**PRD requirements covered**

- Behavioral: 75-78
- Implementation decisions: 19-20
- Testing decisions: 33

**Observable behaviors**

- `project-harness promote <target> <run-id> <source> <destination> --reason
  <reason> --review-status <status>` copies an allowed run artifact to a durable
  repository path.
- Promotion writes a run-local promotion record and backlinks or sidecar
  metadata for the destination artifact.
- Unsafe source and destination paths are rejected.

**First RED test**

- `tests/cli_tests/test_promotion.py::test_promote_markdown_artifact_copies_file_and_writes_backlinks`

### What to build

Implement promotion path normalization, source/destination boundary checks,
existing-destination refusal, copy operation, run-local promotion record
writing, Markdown backlink update, non-Markdown sidecar metadata, review status
validation, and diagnostics.

### Acceptance criteria

- [ ] Promotion requires source artifact, destination path, reason, review
      status, date, and run id.
- [ ] Promotion copies only from inside `.agent-harness/runs/<run-id>/`.
- [ ] Destination must be inside the target repository and outside ignored
      volatile harness paths.
- [ ] Existing destinations are refused unless a later explicit overwrite
      option is added.
- [ ] Run-local promotion record is written for every successful promotion.
- [ ] Markdown destinations receive a backlink to the source run and promotion
      record.
- [ ] Non-Markdown destinations receive sidecar promotion metadata.

### Out of scope

- Overwrite option.
- Publishing promoted artifacts outside the repository.
- Review workflow beyond the recorded review status.

---

## Phase 11: Conservative Update Workflow

**User stories covered**

- Story 3: updates do not destroy local edits.
- Story 10: future generator improvements can be previewed and safely applied.

**PRD requirements covered**

- Behavioral: 79-84
- Implementation decisions: 29-30, 43
- Testing decisions: 34-35, 37

**Observable behaviors**

- `project-harness update <target>` previews update decisions for an existing
  harness.
- `project-harness update <target> --apply` writes only safe updates allowed by
  the current update policy and generated-file registry.
- `generate --apply` reports an existing harness conflict rather than acting as
  update.

**First RED test**

- `tests/cli_tests/test_update.py::test_update_preview_protects_file_with_human_edits`

### What to build

Implement update decision planning, generated-file hash comparison, provenance
header diagnostics, policy handling for `conservative`, `manual_only`, and
`detached`, add-only safe updates, unchanged-file detection, conflict
reporting, and explicit apply behavior.

### Acceptance criteria

- [ ] Update preview classifies files as unchanged, safely addable, updateable,
      conflicted, or protected by policy.
- [ ] `conservative` permits safe additions and generated-file replacements
      only when no protected human edits are detected.
- [ ] `manual_only` previews changes but refuses automatic update writes.
- [ ] `detached` records that the harness is disconnected from generator
      updates.
- [ ] Hash mismatches from the registry mark files as protected unless a later
      manual update path is explicitly used.
- [ ] Header/registry disagreement is diagnosed, with registry data treated as
      authoritative.
- [ ] Update apply does not attempt complex semantic merges of heavily edited
      files.
- [ ] Existing harness conflicts remain on `generate --apply`; update is the
      explicit public surface for existing harness updates.

### Out of scope

- Semantic merge tools.
- Interactive conflict resolution.
- Remote template registry or package publishing.

---

## Phase 12: Dogfood Core Loop and V0 Completion Review

**User stories covered**

- Story 14: prove the concept end to end on a small Python repository.

**PRD requirements covered**

- Behavioral: 86
- Testing decisions: 40
- Global project completion criteria from `prd-plan-tdd-workflow`

**Observable behaviors**

- A dogfood integration test or documented demo attaches the generator to a
  small Python repository and completes the V0 core loop: inspect, preview,
  apply, check, create a run, promote a PRD or plan artifact record, and
  validate the resulting harness.
- The completion review maps every PRD user story and behavioral requirement to
  implemented behavior, deferred scope, or explicit out-of-scope decision.

**First RED test**

- `tests/integration_tests/test_dogfood_loop.py::test_generator_attaches_to_small_python_repo_and_promotes_plan_record`

### What to build

Create a dogfood fixture or demo harness repository, run the public CLI through
the core loop, capture meaningful diagnostics, update public docs to reflect
actual V0 behavior, and complete a requirements trace before marking V0 done.

### Acceptance criteria

- [ ] Dogfood loop uses public CLI commands only.
- [ ] Dogfood target is a small Python repository.
- [ ] Dogfood proves inspect, preview, apply, check, new-run, promote, and final
      check.
- [ ] Public docs describe implemented behavior only.
- [ ] Every PRD user story is implemented or explicitly deferred.
- [ ] Every plan phase is complete or explicitly deferred.
- [ ] Behavioral tests exist for critical paths.
- [ ] Full relevant test suite passes.
- [ ] No documentation claims unsupported behavior.
- [ ] Roadmap items are clearly separated from implemented capabilities.

### Out of scope

- Package publishing.
- Installer UX.
- Hosted or remote demos.

---

## Requirement Coverage Map

- **CLI and packaging**: Phase 0 covers command skeleton and usage diagnostics.
- **Inspection and command safety**: Phases 1-2 cover passive inspection,
  evidence labeling, command candidates, verification probes, and `--run-checks`.
- **User config**: Phase 3 covers defaults, validation, and CLI override
  precedence.
- **Preview/apply/check**: Phases 4-5 cover preview-first generation, explicit
  apply, root router, harness source, provenance, registry, ignore boundaries,
  Git policy, and self-check.
- **Workflow contracts and templates**: Phase 6 covers generated stages,
  approval gate descriptions, required skills, fallbacks, workflow-skill
  template boundaries, phase review, TDD handoff, and harness learning.
- **Durable references and customization**: Phase 7 covers `.agent-harness`
  reference ownership, command confidence, classification, quality bar, module
  context, stack layering, Codex Workspace separation, security, dependency
  policy, and CI snippets.
- **Run management**: Phase 8 covers deterministic run ids, stage skeletons,
  metadata, branch policy, pause, and resume.
- **Approvals and advancement**: Phase 9 covers approval markers, artifact hash
  binding, context summary and PRD gates, stage advancement, and skip policy.
- **Promotion**: Phase 10 covers durable artifact copy, path boundaries,
  backlinks, sidecars, and promotion records.
- **Update**: Phase 11 covers conservative update preview/apply, update policy,
  registry-hash protection, provenance drift, and generation/update separation.
- **V0 acceptance**: Phase 12 covers the dogfood loop and final requirements
  trace.

## Cross-Phase Invariants

- Tests verify behavior through public CLI interfaces and observable filesystem
  artifacts unless a narrow helper-level test is clearly justified.
- No phase runs target repository tests, builds, installs, task scripts, or
  package-manager mutation commands without explicit opt-in.
- Preview is the default for generation and update.
- Apply and update never silently overwrite existing files or protected human
  edits.
- The CLI never executes AI stages.
- Generated helper scripts are deterministic support tools only.
- `.agent-harness/references/` remains the durable rule source of truth.
- Root `AGENTS.md` remains a router, not a full duplicate of the harness.
- Run and temporary artifacts stay ignored; harness source stays
  commit-eligible.
- Approval satisfaction is based on exact gate type, exact stage when relevant,
  approved decision, and current artifact hash when applicable.
- Stage manifests and Markdown contracts must agree structurally or `check`
  fails.
- No subsystem is considered complete until exercised by at least one public
  behavior test.
- Use selective golden-file tests for representative generated content; avoid
  broad snapshot tests for every generated file unless a later implementation
  review shows they add more value than churn.
- Do not introduce roadmap behavior unless it is exercised by the current phase
  or explicitly deferred.
- Keep generated content editable by humans and protected by preview-first
  update logic.
- Keep language-agnostic workflow contracts separate from stack-specific
  add-ons.
- Do not modify CI files in V0.
- Do not persist inspection caches in V0.
- Public docs must describe actual behavior, not planned behavior, except in
  this plan.

## Deferred Explicitly By PRD

- AI stage execution by the CLI.
- Web UI, daemon, hosted service, cloud sync, and runtime orchestration.
- Multi-profile workflow framework beyond one workflow id.
- Complex semantic merge of heavily edited generated files.
- Non-Python stack detectors beyond generic fallback.
- Automatic CI modification.
- Vulnerability scanning, license scanning, dependency update checks, and
  persistent inspection cache.
- Automatic application of harness-learning rule changes.
- Autonomous project source edits by generated scripts.
- Tight integration into the existing `agent_harness` package.
- Publishing, installer UX, release automation, or package registry work.

## Plan Investigation Ledger

- **Status**: passed after deep investigation.
- **Scope**: verify this plan against the PRD, interview log, repo state,
  `prd-to-plan` requirements, and `prd-plan-tdd-workflow` completion criteria.
- **Evidence checked**: phase structure, first RED tests, acceptance criteria,
  out-of-scope boundaries, PRD user-story coverage, behavioral-requirement
  coverage, implementation-decision coverage, testing-decision coverage,
  workflow-skill requirements, and current repository validation commands.
- **Resolved findings**:
  - Testing decision 39 was not explicitly mapped. It is now covered in Phase 5
    and repeated as a cross-phase invariant.
  - Current repo validation showed `python -m pytest -q` cannot run because
    pytest is not installed in the active Python environment. Phase 0 now
    requires reproducible pytest-based TDD setup through project metadata or
    documented environment setup without making pytest a runtime dependency.
- **Open findings**: none.

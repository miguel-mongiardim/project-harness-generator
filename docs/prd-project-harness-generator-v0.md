# PRD: Project Harness Generator V0

> Source context: `docs/interview-log.md`

## Source Evidence

The numbered interview log in `docs/interview-log.md` is the primary source for
user decisions. That log records the accepted decision that the existing
`agent_harness` repository should be inspected before PRD drafting.

A supplemental inspection of `C:\Users\mmarque9\agent_harness` was completed
after that accepted decision. The relevant takeaways are:

- the existing project is a separate repository at
  `C:\Users\mmarque9\agent_harness`, not the target implementation repository
  for this generator
- it already owns the `agent-harness` distribution and `agent-harness` CLI
  command, so V0 must use a non-colliding project and command name
- its `.agent-harness/` directory is currently treated as generated/runtime
  artifact state, so this generator must distinguish commit-eligible harness
  source from ignored run or temporary state
- its repo-local `AGENTS.md` treats `.agent-harness/` as generated state unless
  explicitly inspected or refreshed, which is a concrete collision the new
  generated harness model must avoid through provenance, router wording, and
  ignore policy

These takeaways are constraints for this PRD, not a decision to integrate with
the existing `agent_harness` package.

Inspection evidence for these takeaways came from the existing repository's
`pyproject.toml`, `AGENTS.md`, `.gitignore`, `agent-harness.yaml`, CLI module,
and current `.agent-harness/` directory contents.

## Problem Statement

Project-specific agent workflows are currently reconstructed from scattered
instructions, chat history, repo conventions, and manually maintained notes.
That makes non-trivial software work fragile: agents can skip discovery, write
PRDs from thin context, create horizontal plans, bypass TDD discipline, lose
review gates, or encode project rules in places that future agents do not load.

The user needs a generator that can attach a lightweight, project-local harness
to an existing repository. The harness should make the preferred workflow
visible and enforceable enough for agents to follow:

- inspect the current project before asking questions
- build context through a grill stage before PRD writing
- write a PRD before planning
- turn the PRD into vertical tracer-bullet phases
- execute implementation through TDD one observable behavior at a time
- review completed slices against acceptance criteria and project rules
- capture justified improvements to the harness itself

Without this system, each project needs bespoke agent instructions and manual
coordination. That increases the chance of stale context, skipped gates,
unreviewable generated artifacts, and workflow drift across repositories.

## Solution

Project Harness Generator V0 is a Python CLI package that inspects an existing
repository and generates a project-local `.agent-harness/` context-and-contract
harness. The generated harness is not a runtime orchestration framework. It is
a set of editable Markdown contracts, YAML manifests, stable references,
templates, and deterministic helper scripts that agents and humans use to run a
disciplined project workflow.

The V0 workflow is:

1. A maintainer runs the generator against a target repository.
2. The generator inspects files first and asks only for facts it cannot infer.
3. The generator previews the proposed harness files without writing by default.
4. With explicit generate apply, the generator creates a new project-local
   harness, including a root `AGENTS.md` router when needed; existing harness
   changes use the explicit update command instead.
5. The generated harness supports current-task discovery, grill context, PRD,
   vertical plan, TDD slice, phase review, and harness learning stages.
6. The generated helper scripts validate harness integrity, create run
   skeletons, and record artifact promotion metadata.
7. Agents execute the stages by reading the generated contracts and writing
   artifacts into per-run folders; the CLI does not execute AI stages.
8. The generated stage contracts make approval gates, required artifacts, task
   classification, and done definitions explicit enough to validate.

V0 optimizes for existing repositories first and greenfield repositories second.
It keeps volatile run artifacts out of normal committed source by default while
making durable harness source files visible and reviewable.

## User Stories

1. As a project maintainer, I want to inspect an existing repository before
   generating anything, so that the harness reflects real project structure
   instead of generic defaults.
2. As a project maintainer, I want generation to preview proposed files before
   writing them, so that I can review the workflow source before it changes my
   repository.
3. As a project maintainer, I want apply mode to avoid silent overwrites, so
   that generated harness updates do not destroy local edits.
4. As an agent using the repository, I want a root `AGENTS.md` router and
   project-local harness context, so that I can find the required workflow and
   project rules without relying on chat history.
5. As an agent doing non-trivial work, I want explicit stage contracts for
   discovery, grill context, PRD, plan, TDD, review, and harness learning, so
   that I know the required inputs, outputs, gates, and completion criteria.
6. As a project maintainer, I want stage contracts to reference global skills
   by name and include compact fallbacks, so that the harness remains portable
   without vendoring whole skill bodies.
7. As an agent executing a run, I want `new-run` support that creates isolated
   run folders and metadata, so that multiple features can proceed without
   overwriting each other's artifacts.
8. As a project maintainer, I want a harness self-check, so that missing files,
   manifest drift, ignored-run mistakes, and broken stage contracts are caught
   mechanically.
9. As an agent promoting durable artifacts, I want a standard promotion record,
   so that PRDs, plans, and other promoted outputs link back to their source
   run.
10. As a project maintainer, I want conservative update support, so that future
    generator improvements can be previewed and applied only when they are safe
    or manually reviewed.
11. As a security-conscious maintainer, I want generated automation limits and
    dependency-change rules, so that agents do not run risky commands, expose
    secrets, add dependencies casually, or mutate external systems without
    approval.
12. As a project maintainer, I want generated contracts to name required stage
    artifacts and approval gates, so that agents cannot treat the PRD workflow
    as optional guidance.
13. As a project maintainer, I want a simple local user config, so that personal
    defaults such as Codex Workspace integration and preferred doc paths do not
    have to be re-entered for every project.
14. As the generator maintainer, I want V0 to dogfood its own workflow on a
    small Python repository, so that the concept is proven end to end before
    broader expansion.

## Behavioral Requirements

1. A user can run the CLI help and invalid commands receive clear usage errors.
2. A user can inspect a target repository and receive an evidence-labeled
   summary of detected stack, package metadata, test configuration, command
   candidates, existing agent/context files, docs conventions, lightweight
   dependency inventory, and architecture signals.
3. Inspection output records every command candidate with command text, source,
   verification state, confidence, and notes.
4. Generator prompts or recommended answers after inspection are limited to
   facts that inspection could not infer with evidence; inferred facts are
   labeled with evidence and confidence instead of being re-asked.
5. Repository inspection reads files by default and does not execute project
   tests, builds, or other commands unless the user explicitly opts in.
6. Command verification distinguishes non-invasive command checks from opt-in
   test/build execution.
7. `--verify-commands` may resolve executables, read project metadata, and run
   bounded version/help probes for external tools, but it must not run target
   repository tests, builds, install commands, task scripts, package-manager
   mutation commands, or command candidates with side-effect verbs.
8. `--verify-commands` reports allowed probe outcomes, skipped unsafe probes,
   timeouts, and errors without converting skipped project checks into verified
   command confidence.
9. `--run-checks` is required before detected project tests or builds are
   executed, and executed checks must be reported separately from passive
   inspection and command verification evidence.
10. A user can generate a preview for a target repository and see the proposed
   harness files, intended write paths, overwrite/conflict status, and required
   `.gitignore` changes without modifying the repository.
11. A user can run the generator with no local user config and receive stable
   defaults.
12. A user can provide a simple local user config for personal defaults, including
   Codex Workspace integration, default PRD path, default plan path, the single
   default workflow identifier, and default update policy.
13. Invalid user config is rejected with actionable diagnostics before generation
   or update proceeds.
14. Local config supports these V0 fields and defaults: `workflow_id:
    prd-plan-tdd`, `default_prd_path: docs/prd.md`, `default_plan_path:
    plans/plan.md`, `update_policy: conservative`, and
    `codex_workspace.enabled: false`.
15. Local config validation rejects unknown fields, invalid value types, invalid
    `update_policy` values, workflow ids other than `prd-plan-tdd`, and path
    values that are absolute when a project-relative path is required. Explicit
    CLI arguments override local config defaults.
16. Config values are consumed only by commands that use the corresponding
    behavior: PRD and plan defaults are used by run creation, approval defaults,
    and generated contract defaults; workflow id selects the single supported
    workflow contract set; update policy is used by preview and update; Codex
    Workspace settings affect only optional generated Codex Workspace
    references.
17. A user can apply a generated harness to a target repository only through an
   explicit apply action.
18. Apply mode creates the root router, `.agent-harness/` source files, required
   references, stage contracts, stage manifests, helper scripts, templates,
   module map, harness manifest, changelog, and minimal ignore entries needed
   for volatile run artifacts.
19. Generated root router and harness-source files include provenance headers
    that name the generator, generator version, managed/update status, template
    or file id, last generated content hash when applicable, and the explicit
    expectation that human edits are allowed and must be protected by
    preview-first updates.
20. Apply mode never silently overwrites existing harness or router files; it
   either preserves them, reports a conflict, or requires an explicit update
   path.
21. Apply mode requires a Git worktree for write operations unless the user
   explicitly waives that requirement; inspect and preview can operate without
   Git.
22. A generated harness exposes a non-trivial workflow with current-task
    discovery, grill context, PRD, plan, TDD slice, phase review, and harness
    learning stages.
23. Stage contracts include inputs, process guidance, outputs, verification
    expectations, required approval gates, required skills by role/name, and
    compact fallback procedures.
24. Generated stage contracts are customized from project inspection evidence
    and remain editable generated defaults.
25. The grill context stage requires `interview_log.md`,
    `context_summary.md`, and `decision_register.md` outputs.
26. Downstream PRD work consumes `context_summary.md` by default; raw
    `interview_log.md` and `decision_register.md` remain available as source
    evidence but are not promoted downstream by default.
27. The grill context stage contract requires one controlling interview, allows
    focused sub-interviews for complex branches, recommends an answer with
    rationale for each decision point, proceeds one decision branch at a time by
    default, allows batched questions only for independent low-risk facts, and
    records evidence-backed premise challenges as explicit decisions.
28. The grill context stage requires inferred testing-strategy candidates to be
    confirmed, revised, or rejected before they become durable project rules.
29. The PRD stage may proceed only when every open question from the context
    summary is classified as blocking or non-blocking, and blocking questions
    prevent PRD approval.
30. Approval markers are run-local YAML artifacts under
    `.agent-harness/runs/<run-id>/approvals/<gate-id>.yaml` with gate id,
    approval type, optional stage id, optional artifact path and hash, decision,
    approver, timestamp, and optional note.
31. Artifact approval gates require `decision: approved` and an artifact hash
    that still matches the referenced artifact. Rejected approval markers are
    recorded audit evidence but never satisfy gates.
32. A user can create approval markers through a deterministic CLI command
    without executing an AI stage.
33. Non-trivial work uses two approval gate types: a stricter
    `context_summary_gate` and a lighter `prd_gate`.
34. A `context_summary_gate` approval requires the exact context summary
    artifact hash plus confirmation that every open question is classified and
    no blocking question remains unresolved.
35. The CLI derives `context_summary_gate` readiness by validating required
    sections in `context_summary.md` and its open-question classifications; the
    approval marker records the derived readiness result, not a user-supplied
    unchecked assertion.
36. A `prd_gate` approval requires the exact PRD artifact hash, approval
    decision, and approver, but does not reopen grill decisions or require a new
    context-summary review unless the PRD introduces new blocking questions.
37. The plan stage may proceed only after an approved `prd_gate` marker exists
    for the exact PRD artifact being planned.
38. Non-trivial work requires approved context-summary approval after
    `context_summary.md` before PRD writing and approved PRD approval after the
    PRD before planning.
39. A user can advance run stage status through a deterministic CLI command that
    treats the supplied stage id as the stage being completed, validates that
    stage's required artifacts, approval markers, and branch policy, then marks
    that stage complete and moves the next stage to active in run metadata.
40. Mandatory stage skips in non-trivial runs require a recorded reason and an
    approval marker with
    `decision: approved`, `approval_type: stage_skip`, and `stage_id` equal to
    the exact skipped stage.
41. Trivial and minor runs may skip non-applicable workflow stages by recording
    a skip reason in run metadata without approval, unless the skipped stage is
    explicitly marked security-sensitive or destructive.
42. The plan stage produces a durable tracer-bullet plan, per-slice execution
    summaries, and separately tracked cross-phase invariants included in every
    plan.
43. A walking-skeleton phase is allowed only when it proves observable
    end-to-end behavior under the tracer-bullet rule rather than creating a
    horizontal infrastructure phase.
44. The TDD slice stage records run-local progress while the phase review stage
    updates durable plan state only after review.
45. Phase review can fail a completed slice even when tests pass, and must check
    acceptance criteria, project rules, cross-phase invariants, structured
    self-review, high-risk independent review requirements, pre-commit review
    requirements when committing is in scope, and review gates before marking a
    slice complete.
46. Harness learning performs a lightweight check after each phase, separates
    edit-source opportunities from generator backlog items and local run notes,
    and proposes evidence-backed patches for durable harness-source changes
    without applying those changes automatically.
47. Harness-learning patch proposals cite the observed evidence, explain why the
    durable rule change is justified, name the target harness-source file, and
    remain unapplied until a user explicitly accepts them.
48. Generated local templates include current snapshot, context summary,
    decision register, phase review, harness learning, run metadata, stage
    manifest, module context, promotion record, and next action templates.
49. PRD, plan, slice, and TDD artifact formats are supplied by referenced
    workflow skills rather than generated as project-local templates. Generated
    stage contracts reference those workflow skill templates and include compact
    fallbacks when a skill is unavailable.
50. Stage manifests capture structural metadata for validation, and harness
    validation fails when manifest structure and Markdown contracts drift.
51. Stage manifest validation requires at least stage id, title, required
    inputs, required outputs, required gates, required skills, fallback
    procedure, verification expectations, and next-stage metadata.
52. Stage Markdown contract validation requires matching stage id plus structural
    headings or markers for purpose, inputs, process, outputs, approval gates,
    verification, required skills, fallback, and completion criteria.
53. `.agent-harness/references/` is the source of truth for durable
    agent/project workflow rules. Root routers and stage contracts may summarize
    those rules or link to them, but durable rule changes must be made in
    references first.
54. The generated harness includes project references for purpose, architecture
    candidates, commands, testing, workflow classification, quality bar,
    automation limits, minimal security baseline, dependency-change policy,
    generated check instructions, optional CI snippets, and optional Codex
    Workspace integration.
55. The generated harness keeps a language-agnostic workflow core and applies
    detected stack add-ons separately. V0 includes a generic add-on and a Python
    add-on; stack-specific guidance must not replace the core workflow
    contracts.
56. The commands reference preserves source, verification state, confidence, and
    notes for command candidates.
57. Optional Codex Workspace integration keeps project-local run artifacts and
    stage outputs separate from cross-session operational notes, and records how
    active run ids link to session notes without making Codex Workspace core
    generator behavior.
58. The minimal security baseline covers secret handling, risky command
    approval, external-system mutation approval, dependency-change approval, and
    untrusted-input handling for generated contracts.
59. Generated check instructions describe how to run harness self-check locally
    and may include optional CI snippets, but the generator never modifies CI
    files unless a later explicit opt-in feature is added.
60. The workflow classification reference includes a concrete
    trivial/minor/non-trivial escalation checklist based on public behavior,
    architecture impact, risk, uncertainty, and explicit user requests.
61. The quality-bar reference includes explicit done definitions for slice,
    feature, and run completion.
62. The quality-bar reference encodes integration-style testing through public
    interfaces as the default testing rule unless project evidence explicitly
    contradicts that default.
63. The generated harness supports one module-specific context layer selected
    by an editable path-based module map.
64. The generated harness ignores `.agent-harness/runs/` and temporary harness
    state by default while keeping harness source files commit-eligible.
65. A user can run a harness self-check that passes for a freshly generated
    valid harness.
66. The harness self-check fails with actionable diagnostics when required
    files are missing, run artifacts are not ignored, a stage manifest is
    incomplete, or a stage contract omits required structural items.
67. A user can create a new run with a deterministic run id, explicit task
    classification, detected or provided source branch, and optional branch
    waiver reason.
68. Run ids use `<YYYY-MM-DD>-<slug>` by default, using the target system's
    local date unless `--date YYYY-MM-DD` is provided for deterministic tests.
    Slugs are normalized to lowercase kebab case, may contain ASCII letters,
    digits, and hyphens, and existing run-id collisions fail with actionable
    diagnostics.
69. A new run receives a run skeleton containing metadata, stage output
    directories, and a `next_action.md` resume artifact.
70. Run metadata records run status, current stage, per-stage status, source
    branch, branch waiver when used, created date, and task classification.
71. Run status values are `active`, `paused`, `completed`, and `abandoned`.
    Stage status values are `pending`, `active`, `complete`, and `skipped`.
72. A user can pause a run by recording the next action and setting run status
    to `paused`, then resume that run by reading `next_action.md` and restoring
    run status to `active` without losing stage status.
73. Creating a non-trivial run in a Git worktree requires a source branch unless
    the user records an explicit branch waiver with a reason.
74. Harness self-check fails when a non-trivial run is missing both a source
    branch and a branch waiver.
75. A user can create a promotion record for a run artifact, including source
    artifact, destination path, promotion reason, review status, date, and
    backlinks between promoted durable files and their source run.
76. Promotion copies a run-local source artifact to an explicit durable
    destination path inside the target repository, writes a run-local promotion
    record, and refuses to overwrite an existing destination unless a later
    explicit overwrite option is added.
77. Promotion rejects source paths outside `.agent-harness/runs/<run-id>/` and
    destination paths outside the target repository or inside ignored volatile
    harness paths such as `.agent-harness/runs/` and `.agent-harness/tmp/`.
78. For Markdown destinations, promotion appends or updates a backlink line in
    the promoted file pointing to the source run and promotion record.
    Non-Markdown destinations receive a sidecar promotion metadata file next to
    the destination artifact.
79. A user can preview conservative updates for an existing harness and see
    which files are unchanged, safely addable, updateable, conflicted, or
    protected by update policy.
80. A user can explicitly apply a conservative update to an existing harness;
    generation apply mode reports existing-harness conflicts rather than
    silently treating generation as update.
81. Conservative update apply mode respects these `update_policy` values:
    `conservative` permits safe additions and generated-file replacements only
    when no protected human edits are detected; `manual_only` previews changes
    but refuses automatic update writes; `detached` records that the harness is
    intentionally disconnected from generator updates.
82. Conservative update edit detection uses generated-file records in
    `.agent-harness/harness.yaml` with file id, path, generator version,
    template version, update policy, and last generated SHA-256. A file whose
    current hash differs from the last generated hash is treated as protected
    unless the user explicitly chooses a manual update path.
83. If a provenance header and the generated-file registry disagree, the
    registry is authoritative for update decisions and self-check reports the
    header drift as a diagnostic.
84. Conservative update apply mode does not attempt complex semantic merges of
    heavily edited files.
85. Generated harness content encodes the no-dead-architecture rule, public
    behavior testing preference, structured self-review, high-risk independent
    review, pre-commit review when committing is in scope, dependency-change
    policy, minimal security baseline, and automation limits.
86. V0 can attach to a small Python repository and complete a narrow dogfood
    loop: inspect, preview, apply, check, create a run, promote a PRD or plan
    artifact record, and validate the resulting harness.

## Implementation Decisions

1. The product is a separate project from the existing `agent_harness`
   repository. It uses distribution name `project-harness-generator` and import
   package `project_harness_generator`.
2. The V0 public interface is CLI first. Library APIs may emerge behind the CLI
   but are not the primary user contract for V0.
3. The initial CLI command name is `project-harness`, using the supplemental
   `agent_harness` inspection evidence to avoid collision with the existing
   `agent-harness` package while keeping command usage short.
4. V0 CLI commands should cover these public behaviors:
   - `project-harness inspect <target> [--verify-commands] [--run-checks]`
   - `project-harness generate <target> [--prd-path <path>] [--plan-path <path>] [--workflow-id prd-plan-tdd]` with preview as the default
   - `project-harness generate <target> --apply [--prd-path <path>] [--plan-path <path>] [--workflow-id prd-plan-tdd]`
   - `project-harness check <target>`
   - `project-harness update <target> [--update-policy <conservative|manual_only|detached>]` with preview as the default
   - `project-harness update <target> --apply [--update-policy <conservative|manual_only|detached>]`
   - `project-harness new-run <target> <slug> --classification <trivial|minor|non-trivial> [--date <YYYY-MM-DD>] [--source-branch <branch>] [--branch-waiver <reason>] [--prd-path <path>] [--plan-path <path>] [--workflow-id prd-plan-tdd]`
   - `project-harness approve <target> <run-id> <gate-id> --type <context_summary_gate|prd_gate|artifact_gate|stage_skip> --decision <approved|rejected> --approved-by <name> [--artifact <path>] [--stage <stage-id>] [--note <text>]`
   - `project-harness advance <target> <run-id> <stage-id>`
   - `project-harness skip-stage <target> <run-id> <stage-id> --reason <reason> [--approval <gate-id>]`
   - `project-harness pause <target> <run-id> --next-action <text>`
   - `project-harness resume <target> <run-id>`
   - `project-harness promote <target> <run-id> <source> <destination> --reason <reason> --review-status <pending|reviewed|approved>`
   - `project-harness config validate [path]`
5. V0 uses Python 3.11+ and `argparse` to keep the CLI standard-library based.
6. V0 uses standard-library dataclasses plus explicit validation for internal
   models.
7. V0 parses Python project metadata from `pyproject.toml` using
   standard-library `tomllib`.
8. V0 uses plain Python render functions rather than a template engine.
9. Editable harness manifests use YAML. PyYAML is justified for V0 through an
   isolated adapter because humans will edit manifests and the generator must
   round-trip readable YAML safely enough for its limited schema.
10. Markdown is the human/agent contract surface; YAML manifests are the
    structural validation surface.
11. The generator should be organized around deep modules with stable public
    responsibilities:
    - repository inspection and evidence capture
    - command and stack detection
    - harness model validation
    - render plan construction
    - preview and conflict reporting
    - apply/update write policy
    - harness self-check
    - run skeleton management
    - promotion record management
    - YAML serialization adapter
12. Generated `.agent-harness/` source includes:
    - `CONTEXT.md`
    - `harness.yaml`
    - `CHANGELOG.md`
    - `references/`
    - `stages/<stage-id>/CONTEXT.md`
    - `stages/<stage-id>/stage.yaml`
    - `templates/`
    - `scripts/`
    - `modules/module_map.yaml`
13. Generated templates include:
    - `current_snapshot.md`
    - `context_summary.md`
    - `decision_register.md`
    - `phase_review.md`
    - `harness_learning.md`
    - `run_metadata.yaml`
    - `stage.yaml`
    - `module_context.md`
    - `promotion_record.md`
    - `next_action.md`
14. Generated stages are:
    - `00_project_discovery`
    - `01_grill_context`
    - `02_prd`
    - `03_plan`
    - `04_tdd_slice`
    - `05_phase_review`
    - `06_harness_learning`
15. The root `AGENTS.md` is a router only. It should point agents to
    `.agent-harness/CONTEXT.md` and summarize the non-trivial workflow without
    duplicating full stage contracts.
16. Generated stage contracts reference required global skills such as
    `grill-me`, `write-a-prd`, `prd-to-plan`, `tdd`,
    `prd-plan-tdd-workflow`, and `precommit-review` by role/name only.
17. Generated stage contracts include compact fallback procedures when a
    required global skill is unavailable.
18. Generated stage contracts define mandatory approval gates:
    - non-trivial runs require context summary approval before PRD writing
    - non-trivial runs require PRD approval before planning
    - mandatory stage skips require user approval
19. Approval markers are YAML artifacts under
    `.agent-harness/runs/<run-id>/approvals/` and contain `gate_id`,
    `approval_type`, optional `stage_id`, optional `artifact_path` and
    `artifact_sha256`, `decision`, `approved_by`, `approved_at`, and optional
    `note`.
20. Run metadata is the mechanical stage-state surface. The `advance` and
    `skip-stage` commands update run metadata only after validating required
    artifacts, stage manifests, approval markers, conditionally required skip
    approval, and branch policy.
21. Generated grill contracts define the accepted grill mechanics: one
    controlling interview, optional focused sub-interviews, recommended answers
    with rationale, one decision branch at a time by default, and explicit
    premise challenges with supporting evidence.
22. Generated plan, TDD, and review contracts define the handoff between durable
    tracer-bullet plan artifacts, per-slice execution summaries, run-local
    progress, cross-phase invariants, and phase-review plan updates. Walking
    skeletons are valid only when they prove an observable end-to-end behavior.
23. Generated phase-review contracts define structured self-review by default,
    independent review when risk is high, and a pre-commit review gate when
    committing is in scope.
24. Generated harness-learning contracts track edit-source opportunities and
    proposed patches separately from local observations and generator backlog
    candidates.
25. Generated workflow references define the trivial/minor/non-trivial task
    checklist and the slice/feature/run done definitions.
26. Generated workflow references name `.agent-harness/references/` as the
    durable rule source of truth.
27. Generated command references record command source, verification state,
    confidence, and notes.
28. Generated Codex Workspace references keep cross-session operational notes
    separate from project-local run artifacts and stage outputs.
29. Generated harness-source and root router files include provenance headers
    used by preview and update logic to distinguish generated baseline content,
    protected human edits, and detached/manual update policies.
30. `.agent-harness/harness.yaml` owns the generated-file registry used for
    update detection. Each generated-file record includes file id, path,
    generator version, template version, update policy, and last generated
    SHA-256.
31. Stage manifests include at minimum stage id, title, required inputs,
    required outputs, required gates, required skills, fallback procedure,
    verification expectations, and next-stage metadata.
32. Stage Markdown contracts include matching structural headings or markers for
    purpose, inputs, process, outputs, approval gates, verification, required
    skills, fallback, and completion criteria.
33. Generated quality references encode integration-style public-interface tests
    as the default testing rule unless project evidence contradicts it.
34. The generator writes project-local deterministic helper scripts only for
    mechanical support tasks. Scripts must not perform autonomous AI stage
    execution or unreviewed project source edits.
35. The generator does not persist inspection caches in V0. Optional temporary
    artifacts may live under ignored `.agent-harness/tmp/`.
36. The generator may infer architecture boundaries, test strategy, and command
    candidates, but inferred rules must be labeled with evidence, confidence,
    and confirmation status before becoming durable project rules.
37. Codex Workspace integration is optional user-specific harness content, not
    required core generator behavior.
38. V0 supports a simple local user config, not a profile system. The default
    candidate path is `~/.agent-harness/config.yaml`, with platform-appropriate
    path resolution on Windows.
39. V0 config fields are limited to `workflow_id`, `default_prd_path`,
    `default_plan_path`, `update_policy`, and `codex_workspace.enabled`. CLI
    flags override config values.
40. V0 supports one default workflow identifier only; multi-profile workflow
    selection is out of scope.
41. V0 supports generic and Python stack detection only.
42. V0 does not automatically modify CI. It generates check instructions and
    may include optional CI snippets for explicit opt-in.
43. V0 apply/update behavior is preview-first, conflict-aware, and conservative
    by default.

## Testing Decisions

1. Tests should verify public behavior through CLI entry points and generated
   filesystem artifacts, not private helper function names.
2. The main test harness should use temporary fixture repositories to exercise
   inspect, preview, apply, check, new-run, promote, and update behavior.
3. The first acceptance tests should prove that preview does not write files,
   apply creates a valid harness, and check validates the generated harness.
4. Inspection tests should cover a minimal Python repository with `pyproject.toml`
   and pytest configuration.
5. Safety tests should prove that project commands are not executed during
   default inspection.
6. Command-candidate tests should verify that inspection records command source,
   verification state, confidence, and notes.
7. Inspect-first tests should verify that generation asks only for facts not
   inferred from inspection evidence and labels inferred facts with evidence
   and confidence.
8. Conflict tests should prove that existing files are not silently overwritten.
9. Git policy tests should prove that apply requires a Git worktree or explicit
   waiver while inspect and preview do not.
10. Harness validation tests should cover missing required files, incomplete
   manifests, and drift between `stage.yaml` and stage `CONTEXT.md`.
11. Manifest/Markdown drift tests should verify the minimum `stage.yaml` fields
    and required Markdown headings or markers.
12. Run management tests should verify date-plus-slug run IDs, collision
    handling, explicit task classification, detected or supplied source branch,
    branch waiver reason, stage directories, run metadata, and `next_action.md`.
13. Command-verification tests should prove that default inspection runs no
    project commands, `--verify-commands` performs only non-invasive command
    checks, unsafe probes are reported as skipped, timeouts are bounded, and
    `--run-checks` is required before project tests or builds run.
14. Approval marker tests should verify marker schema, artifact hash binding,
    rejected decisions never satisfying gates, missing artifact diagnostics,
    distinct `context_summary_gate` and lighter `prd_gate` semantics,
    derived context-summary readiness, skip-stage marker `stage_id` binding,
    and marker creation through the public CLI.
15. Advancement tests should verify that non-trivial runs cannot advance from
    context summary to PRD or from PRD to plan without the required approval
    markers, that `advance` treats the supplied stage id as the stage being
    completed, that mandatory non-trivial stage skips require exact-stage
    approval, and that trivial/minor non-applicable stage skips can record a
    reason without approval unless security-sensitive or destructive.
16. Artifact-template tests should verify that the generated harness includes
    the required local templates and that the grill context stage names
    `interview_log.md`, `context_summary.md`, and `decision_register.md`.
17. Artifact-template tests should verify that the generated harness includes
    the current snapshot template.
18. Grill-contract tests should verify that the generated grill stage requires
    recommended answers with rationale, one-decision-branch pacing, focused
    sub-interview summaries when used, batched questions only for independent
    low-risk facts, testing-strategy confirmation during grill, downstream
    summary-only promotion by default, and evidence-backed premise challenges.
19. Plan/TDD/review tests should verify durable tracer-bullet plan output,
    per-slice execution summaries, cross-phase invariants tracked separately
    from acceptance criteria and included in every plan, walking-skeleton
    phases only when they prove observable end-to-end behavior, run-local TDD
    progress, phase-review plan updates, structured self-review, high-risk
    independent review, pre-commit review when committing is in scope, and the
    ability for review to fail a slice even when tests pass.
20. Harness-learning tests should verify edit-source opportunity tracking,
    evidence-backed patch proposal behavior, justification of durable rule
    changes, and absence of automatic durable rule application.
21. Workflow-reference tests should verify that generated references include the
    task escalation checklist, required escalation factors, `.agent-harness/references/`
    durable-rule ownership, and slice/feature/run done definitions.
22. Required-skill tests should verify that generated stage contracts reference
    required global skills by role/name and provide compact missing-skill
    fallbacks.
23. Workflow-skill template tests should verify that PRD, plan, slice, and TDD
    artifact formats are sourced from referenced workflow skills rather than
    generated as local project templates.
24. Codex Workspace integration tests should verify that optional generated
    instructions keep project-local run artifacts separate from cross-session
    operational notes.
25. Project-customization tests should verify that generated stage contracts
    incorporate project inspection evidence while remaining editable defaults.
26. Stack-layering tests should verify that generated harness output preserves a
    language-agnostic core and applies generic/Python stack add-ons separately.
27. Pause/resume tests should verify paused run status, `next_action.md`
    updates, and resume behavior restoring the run to active without losing
    stage state.
28. Generated-check tests should verify local check instructions and optional CI
    snippets without modifying CI files.
29. Security-baseline tests should verify generated minimal security guidance
    for secrets, risky commands, external mutation, dependency changes, and
    untrusted inputs.
30. Quality-reference tests should verify that integration-style tests through
    public interfaces are the default quality rule unless project evidence
    contradicts it.
31. Branch policy tests should verify that non-trivial runs require a source
    branch or explicit waiver and that harness self-check catches missing
    branch metadata.
32. User-config tests should verify missing-config defaults, valid config
    application, CLI-over-config precedence, unknown-field rejection, enum
    validation, path validation, and clear errors for invalid config.
33. Promotion tests should verify required CLI fields, copying from run-local
    source to durable destination, existing-destination refusal, source and
    destination path-boundary checks, rejection of ignored volatile harness
    destinations, run-local promotion records, Markdown destination backlinks,
    and sidecar metadata for non-Markdown destinations without depending on
    private formatting details.
34. Conservative update tests should cover add-only changes, unchanged generated
    files, edited-file protection by hash mismatch, update apply mode, update
    policy modes, and conflict reporting.
35. Generate/update boundary tests should verify that `generate --apply` reports
    existing harness conflicts while `update --apply` is the explicit public
    surface for existing harness updates.
36. Run-id tests should verify date source, `--date` override, slug
    normalization, allowed characters, collision diagnostics, and run/stage
    status values.
37. Provenance tests should verify that generated harness-source files and the
    root router include the required provenance header and that update logic
    honors generated-file registry hashes, managed, manually edited, and
    detached status, and reports header/registry drift with the registry
    treated as authoritative.
38. Selective golden-file tests are appropriate for the root router,
    `.agent-harness/CONTEXT.md`, one representative stage contract,
    `harness.yaml`, and one `stage.yaml`.
39. Broad snapshot tests for every generated file should be avoided unless a
    later implementation shows they provide more value than churn.
40. V0 acceptance requires a dogfood-style integration test or documented demo
    that attaches to a small Python repository and completes the core loop.

## Out of Scope

1. AI stage execution by the CLI.
2. Web UI, daemon, hosted service, or cloud sync.
3. Multi-profile workflow framework beyond one default workflow profile.
4. Complex semantic merge of heavily edited generated files.
5. Non-Python stack detectors beyond a generic fallback.
6. Automatic CI modification.
7. Vulnerability scanning, license scanning, or dependency update checks.
8. Persistent inspection cache.
9. Automatic application of harness-learning rule changes.
10. Autonomous project source edits by generated scripts.
11. Runtime orchestration framework for agents.
12. Tight integration into the existing `agent_harness` package.
13. Publishing, installer UX, release automation, or package registry work.
14. Full greenfield project generation beyond enough support to attach a
    harness to a minimal repository.

## Further Notes

- The central tradeoff is that V0 should make workflow discipline concrete
  without becoming an orchestration platform. Files remain the control surface.
- Generated harness files are expected to be edited by humans. Provenance
  headers should make that explicit rather than implying generated files are
  untouchable.
- The riskiest implementation areas are overwrite safety, update policy,
  generated contract drift, and avoiding accidental command execution.
- The next step after PRD approval is to convert this PRD into a vertical
  tracer-bullet implementation plan. A valid plan should avoid horizontal
  phases such as "build all schemas" or "build all scripts" unless each phase
  proves an observable end-to-end behavior.
- No blocking open questions remain for V0 planning. The exact generated prose
  for each contract can evolve during implementation, protected by focused
  golden-file tests and behavior tests.

# Project Harness Generator

Python CLI for generating project-specific agent harnesses from inspected
project context.

Implemented surface:

- `project-harness --help` lists the V0 command surface.
- `project-harness inspect <target>` performs read-only repository inspection
  and reports evidence-labeled findings.
- `project-harness inspect <target> --verify-commands` runs bounded,
  non-invasive help/version probes for allowed tools and reports unsafe
  candidates as skipped.
- `project-harness inspect <target> --run-checks` executes detected project
  checks such as pytest and reports results in a separate section.
- `project-harness config validate [path]` validates local user config or
  reports stable defaults when no config exists.
- `project-harness generate <target>` previews proposed harness write paths,
  categories, add/conflict/ignore status, provenance status, and required
  `.gitignore` entries without writing files.
- `project-harness generate <target> --apply` writes a new generated harness
  only after explicit apply, requires a Git worktree unless
  `--allow-non-git` is supplied, refuses existing harness conflicts, and keeps
  volatile `.agent-harness/runs/` and `.agent-harness/tmp/` state ignored.
- Generated harnesses include structural stage contracts for project discovery,
  grill context, PRD, plan, TDD slice, phase review, and harness learning,
  plus local templates for harness-owned run artifacts.
- Generated harness references include durable rule ownership, command evidence,
  workflow classification, quality bar, security baseline, automation and
  dependency policies, check instructions, optional Codex Workspace separation,
  and generic/Python stack add-ons.
- `project-harness check <target>` validates generated harness files,
  manifest and stage contract structure, provenance and registry hash
  consistency, volatile-state ignore policy, and run metadata branch/status
  invariants.
- `project-harness new-run <target> <slug> --classification <...>` creates
  isolated run skeletons with deterministic run ids, stage directories, run
  metadata, branch policy metadata, and `next_action.md`.
- `project-harness pause <target> <run-id> --next-action <text>` and
  `project-harness resume <target> <run-id>` update run status while
  preserving per-stage state.
- `project-harness update <target>` and
  later workflow commands remain preview or placeholder surfaces where noted.
- Unknown commands, missing commands, and missing command arguments fail with
  usage diagnostics and no traceback.

Harness update planning, approvals, advancement, stage skips, promotion, and
the remaining V0 commands are not implemented yet.

Development setup:

- Install test dependencies with `python -m pip install -e ".[test]"`.
- Run tests with `python -m pytest -q`.

Planning artifacts:

- `docs/interview-log.md` records the source grill interview and decisions.
- `docs/prd-project-harness-generator-v0.md` defines the V0 product boundary.
- `plans/project-harness-generator-v0.md` breaks the V0 PRD into vertical
  tracer-bullet implementation phases.

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
- `project-harness update <target>` and
  `project-harness new-run <target> <slug>` resolve local config and CLI
  overrides without writing files.
- Unknown commands, missing commands, and missing command arguments fail with
  usage diagnostics and no traceback.

Harness apply, harness update planning, run creation, and the remaining V0
commands are not implemented yet.

Development setup:

- Install test dependencies with `python -m pip install -e ".[test]"`.
- Run tests with `python -m pytest -q`.

Planning artifacts:

- `docs/interview-log.md` records the source grill interview and decisions.
- `docs/prd-project-harness-generator-v0.md` defines the V0 product boundary.
- `plans/project-harness-generator-v0.md` breaks the V0 PRD into vertical
  tracer-bullet implementation phases.

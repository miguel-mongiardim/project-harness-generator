"""Read-only repository inspection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib


PASSIVE_COMMAND_NOTE = "passive inspection did not execute target commands"
PROBE_TIMEOUT_SECONDS = 1
PROJECT_CHECK_TIMEOUT_SECONDS = 120
PROJECT_CHECK_COMMANDS = {"python -m pytest -q", "make test", "make build"}
MUTATION_COMMAND_TOKENS = (" install", " deploy", " publish", " release")


@dataclass(frozen=True)
class Finding:
    name: str
    value: str
    evidence: str
    confidence: str


@dataclass(frozen=True)
class CommandCandidate:
    command: str
    source: str
    verification_state: str
    confidence: str
    notes: str


@dataclass(frozen=True)
class CommandVerification:
    command: str
    status: str
    evidence: str
    notes: str


@dataclass(frozen=True)
class ProjectCheck:
    command: str
    status: str
    evidence: str
    notes: str


@dataclass(frozen=True)
class InspectionResult:
    target: Path
    repository: list[Finding] = field(default_factory=list)
    stack: list[Finding] = field(default_factory=list)
    package_metadata: list[Finding] = field(default_factory=list)
    test_configuration: list[Finding] = field(default_factory=list)
    docs_conventions: list[Finding] = field(default_factory=list)
    agent_context_files: list[Finding] = field(default_factory=list)
    dependencies: list[Finding] = field(default_factory=list)
    architecture_signals: list[Finding] = field(default_factory=list)
    command_candidates: list[CommandCandidate] = field(default_factory=list)
    command_verification: list[CommandVerification] = field(default_factory=list)
    project_checks: list[ProjectCheck] = field(default_factory=list)


class InspectionError(Exception):
    """Raised when the target cannot be inspected."""


def inspect_repository(
    target: Path,
    *,
    verify_commands: bool = False,
    run_checks: bool = False,
) -> InspectionResult:
    target = target.expanduser()
    if not target.exists():
        raise InspectionError(f"target path does not exist: {target}")
    if not target.is_dir():
        raise InspectionError(f"target path is not a directory: {target}")

    pyproject = target / "pyproject.toml"
    pyproject_data: dict[str, object] = {}
    if pyproject.exists():
        try:
            pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except OSError as exc:
            raise InspectionError(f"could not read pyproject.toml: {exc}") from exc
        except UnicodeDecodeError as exc:
            raise InspectionError(f"could not decode pyproject.toml as UTF-8: {exc}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise InspectionError(f"could not parse pyproject.toml: {exc}") from exc

    repository = [
        Finding(
            name="git worktree",
            value="yes" if _looks_like_git_worktree(target) else "no",
            evidence=".git" if _looks_like_git_worktree(target) else ".git not found",
            confidence="high",
        )
    ]

    stack: list[Finding] = []
    package_metadata: list[Finding] = []
    test_configuration: list[Finding] = []
    dependencies: list[Finding] = []
    command_candidates: list[CommandCandidate] = []

    if pyproject_data:
        stack.append(Finding("language", "Python", "pyproject.toml", "high"))
        command_candidates.append(
            CommandCandidate(
                command="python --version",
                source="pyproject.toml",
                verification_state="not_run",
                confidence="high",
                notes=PASSIVE_COMMAND_NOTE,
            )
        )
        project = _table(pyproject_data, "project")
        _append_project_metadata(package_metadata, dependencies, project)
        pytest_options = _table(_table(_table(pyproject_data, "tool"), "pytest"), "ini_options")
        if pytest_options:
            _append_pytest_configuration(test_configuration, pytest_options)

    tests_dir = target / "tests"
    if tests_dir.is_dir() and not any(item.name == "testpaths" for item in test_configuration):
        test_configuration.append(Finding("testpaths", "tests", "tests/", "medium"))

    if test_configuration:
        sources = [finding.evidence for finding in test_configuration]
        command_candidates.append(
            CommandCandidate(
                command="python -m pytest -q",
                source=", ".join(dict.fromkeys(sources)),
                verification_state="not_run",
                confidence="high",
                notes=PASSIVE_COMMAND_NOTE,
            )
        )
    command_candidates.extend(_detect_makefile_command_candidates(target))

    command_verification: list[CommandVerification] = []
    if verify_commands:
        command_verification = _verify_command_candidates(command_candidates, run_checks)

    project_checks: list[ProjectCheck] = []
    if run_checks:
        project_checks = _run_project_checks(target, command_candidates)

    return InspectionResult(
        target=target.resolve(),
        repository=repository,
        stack=stack,
        package_metadata=package_metadata,
        test_configuration=test_configuration,
        docs_conventions=_detect_docs_conventions(target),
        agent_context_files=_detect_agent_context_files(target),
        dependencies=dependencies,
        architecture_signals=_detect_architecture_signals(target),
        command_candidates=command_candidates,
        command_verification=command_verification,
        project_checks=project_checks,
    )


def format_inspection(result: InspectionResult) -> str:
    lines = [
        "Project Harness Inspection",
        f"Target: {result.target}",
        "",
    ]
    _format_findings(lines, "Repository", result.repository)
    _format_findings(lines, "Stack", result.stack)
    _format_findings(lines, "Package Metadata", result.package_metadata)
    _format_findings(lines, "Test Configuration", result.test_configuration)
    _format_findings(lines, "Docs Conventions", result.docs_conventions)
    _format_findings(lines, "Agent/Context Files", result.agent_context_files)
    _format_findings(lines, "Dependency Inventory", result.dependencies)
    _format_findings(lines, "Architecture Signals", result.architecture_signals)
    _format_command_candidates(lines, result.command_candidates)
    _format_command_verification(lines, result.command_verification)
    _format_project_checks(lines, result.project_checks)
    return "\n".join(lines).rstrip() + "\n"


def _verify_command_candidates(
    candidates: list[CommandCandidate],
    run_checks: bool,
) -> list[CommandVerification]:
    results: list[CommandVerification] = []
    for candidate in candidates:
        safety = _classify_command_safety(candidate.command)
        if safety == "project_check" and not run_checks:
            results.append(
                CommandVerification(
                    command=candidate.command,
                    status="skipped",
                    evidence="safety policy",
                    notes="this project check command requires --run-checks",
                )
            )
        elif safety == "mutation":
            results.append(
                CommandVerification(
                    command=candidate.command,
                    status="skipped",
                    evidence="safety policy",
                    notes="install, package-manager mutation, and side-effect commands are not verification probes",
                )
            )
        elif safety == "allowed_probe":
            results.append(_run_allowed_probe(candidate.command))
    return results


def _run_allowed_probe(command: str) -> CommandVerification:
    parts = command.split()
    executable = _probe_executable(parts[0])
    try:
        completed = subprocess.run(
            [executable, *parts[1:]],
            text=True,
            capture_output=True,
            check=False,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return CommandVerification(
            command=command,
            status="timeout",
            evidence=f"resolved executable: {executable}",
            notes="bounded version probe timed out",
        )
    except OSError as exc:
        return CommandVerification(
            command=command,
            status="error",
            evidence=f"resolved executable: {executable}",
            notes=f"bounded version probe failed: {exc}",
        )

    return CommandVerification(
        command=command,
        status="verified" if completed.returncode == 0 else "error",
        evidence=f"exit_code: {completed.returncode}",
        notes="bounded version probe completed",
    )


def _run_project_checks(target: Path, candidates: list[CommandCandidate]) -> list[ProjectCheck]:
    results: list[ProjectCheck] = []
    for candidate in candidates:
        if _classify_command_safety(candidate.command) != "project_check":
            continue
        if candidate.command == "python -m pytest -q":
            results.append(_run_pytest_check(target, candidate.command))
        elif candidate.command in {"make test", "make build"}:
            results.append(_run_command_check(target, candidate.command))
    return results


def _run_pytest_check(target: Path, command: str) -> ProjectCheck:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=target,
            text=True,
            capture_output=True,
            check=False,
            timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ProjectCheck(
            command=command,
            status="timeout",
            evidence=f"timeout: {PROJECT_CHECK_TIMEOUT_SECONDS}s",
            notes="project check timed out",
        )
    except OSError as exc:
        return ProjectCheck(
            command=command,
            status="error",
            evidence="execution failed",
            notes=str(exc),
        )

    return ProjectCheck(
        command=command,
        status="passed" if completed.returncode == 0 else "failed",
        evidence=f"exit_code: {completed.returncode}",
        notes="project check executed because --run-checks was set",
    )


def _run_command_check(target: Path, command: str) -> ProjectCheck:
    parts = command.split()
    executable = shutil.which(parts[0]) or parts[0]
    try:
        completed = subprocess.run(
            [executable, *parts[1:]],
            cwd=target,
            text=True,
            capture_output=True,
            check=False,
            timeout=PROJECT_CHECK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return ProjectCheck(
            command=command,
            status="timeout",
            evidence=f"timeout: {PROJECT_CHECK_TIMEOUT_SECONDS}s",
            notes="project check timed out",
        )
    except OSError as exc:
        return ProjectCheck(
            command=command,
            status="error",
            evidence="execution failed",
            notes=str(exc),
        )

    return ProjectCheck(
        command=command,
        status="passed" if completed.returncode == 0 else "failed",
        evidence=f"exit_code: {completed.returncode}",
        notes="project check executed because --run-checks was set",
    )


def _append_project_metadata(
    package_metadata: list[Finding],
    dependencies: list[Finding],
    project: dict[str, object],
) -> None:
    for key in ("name", "version", "requires-python"):
        value = project.get(key)
        if isinstance(value, str):
            package_metadata.append(
                Finding(key, value, f"pyproject.toml [project.{key}]", "high")
            )

    raw_dependencies = project.get("dependencies")
    if isinstance(raw_dependencies, list):
        dependency_values = [item for item in raw_dependencies if isinstance(item, str)]
        if dependency_values:
            dependencies.append(
                Finding(
                    "dependencies",
                    ", ".join(dependency_values),
                    "pyproject.toml [project.dependencies]",
                    "high",
                )
            )


def _append_pytest_configuration(
    test_configuration: list[Finding],
    pytest_options: dict[str, object],
) -> None:
    testpaths = pytest_options.get("testpaths")
    if isinstance(testpaths, list):
        values = [item for item in testpaths if isinstance(item, str)]
        if values:
            test_configuration.append(
                Finding(
                    "testpaths",
                    ", ".join(values),
                    "pyproject.toml [tool.pytest.ini_options.testpaths]",
                    "high",
                )
            )


def _detect_docs_conventions(target: Path) -> list[Finding]:
    findings: list[Finding] = []
    if (target / "README.md").exists():
        findings.append(Finding("README", "README.md", "README.md", "high"))
    if (target / "docs").is_dir():
        findings.append(Finding("docs directory", "docs/", "docs/", "high"))
    return findings


def _detect_agent_context_files(target: Path) -> list[Finding]:
    candidates = [
        "AGENTS.md",
        "AGENTS.override.md",
        ".agent-harness/CONTEXT.md",
        ".agent-harness/harness.yaml",
    ]
    return [
        Finding("agent context", candidate, candidate, "high")
        for candidate in candidates
        if (target / candidate).exists()
    ]


def _detect_architecture_signals(target: Path) -> list[Finding]:
    findings: list[Finding] = []
    src = target / "src"
    if src.is_dir():
        findings.append(Finding("layout", "src layout", "src/", "high"))
        packages = [
            path.name
            for path in src.iterdir()
            if path.is_dir()
            and (path / "__init__.py").exists()
            and not path.name.endswith(".egg-info")
        ]
        if packages:
            findings.append(Finding("packages", ", ".join(sorted(packages)), "src/", "medium"))
    if (target / "tests").is_dir():
        findings.append(Finding("tests", "tests directory", "tests/", "high"))
    return findings


def _detect_makefile_command_candidates(target: Path) -> list[CommandCandidate]:
    makefile = target / "Makefile"
    if not makefile.exists():
        return []

    discovered_targets: list[str] = []
    try:
        lines = makefile.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise InspectionError(f"could not read Makefile: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise InspectionError(f"could not decode Makefile as UTF-8: {exc}") from exc
    for line in lines:
        if line.startswith(("\t", " ")) or ":" not in line:
            continue
        name, _, remainder = line.partition(":")
        if remainder.strip():
            continue
        target_name = name.strip()
        if target_name in {"test", "build", "install"}:
            discovered_targets.append(target_name)

    return [
        CommandCandidate(
            command=f"make {target_name}",
            source="Makefile",
            verification_state="not_run",
            confidence="medium",
            notes=PASSIVE_COMMAND_NOTE,
        )
        for target_name in discovered_targets
    ]


def _format_findings(lines: list[str], title: str, findings: list[Finding]) -> None:
    lines.append(f"{title}:")
    if not findings:
        lines.append("- none detected")
    for finding in findings:
        lines.append(
            f"- {finding.name}: {finding.value} "
            f"(evidence: {finding.evidence}; confidence: {finding.confidence})"
        )
    lines.append("")


def _format_command_candidates(lines: list[str], candidates: list[CommandCandidate]) -> None:
    lines.append("Command Candidates:")
    if not candidates:
        lines.append("- none detected")
    for candidate in candidates:
        lines.extend(
            [
                f"- command: {candidate.command}",
                f"  source: {candidate.source}",
                f"  verification_state: {candidate.verification_state}",
                f"  confidence: {candidate.confidence}",
                f"  notes: {candidate.notes}",
            ]
        )
    lines.append("")


def _format_command_verification(
    lines: list[str],
    results: list[CommandVerification],
) -> None:
    if not results:
        return
    lines.append("Command Verification:")
    for result in results:
        lines.extend(
            [
                f"- command: {result.command}",
                f"  status: {result.status}",
                f"  evidence: {result.evidence}",
                f"  notes: {result.notes}",
            ]
        )
    lines.append("")


def _format_project_checks(lines: list[str], checks: list[ProjectCheck]) -> None:
    if not checks:
        return
    lines.append("Project Checks:")
    for check in checks:
        lines.extend(
            [
                f"- command: {check.command}",
                f"  status: {check.status}",
                f"  evidence: {check.evidence}",
                f"  notes: {check.notes}",
            ]
        )
    lines.append("")


def _looks_like_git_worktree(target: Path) -> bool:
    git_marker = target / ".git"
    if git_marker.is_dir():
        return (git_marker / "HEAD").is_file()
    if not git_marker.is_file():
        return False
    try:
        first_line = git_marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeDecodeError, IndexError):
        return False
    return first_line.startswith("gitdir: ")


def _classify_command_safety(command: str) -> str:
    if _is_allowed_probe(command):
        return "allowed_probe"
    if command in PROJECT_CHECK_COMMANDS:
        return "project_check"
    if any(token in command for token in MUTATION_COMMAND_TOKENS):
        return "mutation"
    return "unknown"


def _is_allowed_probe(command: str) -> bool:
    parts = command.split()
    if len(parts) != 2:
        return False
    executable, probe_arg = parts
    return executable == "python" and probe_arg in {"--version", "-V", "--help", "-h"}


def _probe_executable(executable: str) -> str:
    resolved = shutil.which(executable)
    if resolved:
        return resolved
    if executable == "python":
        return sys.executable
    return executable


def _table(data: dict[str, object], key: str) -> dict[str, object]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}

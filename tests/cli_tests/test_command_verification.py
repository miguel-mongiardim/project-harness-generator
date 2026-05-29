import os
import subprocess
import sys
import tempfile
from pathlib import Path
from textwrap import dedent


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def run_project_harness(
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_ROOT)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, "-m", "project_harness_generator", *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_verify_commands_skips_project_tests_without_run_checks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ).strip()
        )
        (target / "tests").mkdir()
        sentinel = target / "pytest-ran.txt"
        (target / "tests" / "test_side_effect.py").write_text(
            dedent(
                f"""
                from pathlib import Path

                def test_side_effect():
                    Path({str(sentinel)!r}).write_text("ran")
                """
            ).strip()
        )

        result = run_project_harness("inspect", str(target), "--verify-commands")

        assert result.returncode == 0, result.stderr
        assert "Command Candidates:" in result.stdout
        assert "command: python -m pytest -q" in result.stdout
        assert "verification_state: not_run" in result.stdout
        assert "Command Verification:" in result.stdout
        assert "status: skipped" in result.stdout
        assert "requires --run-checks" in result.stdout
        assert not sentinel.exists()


def test_verify_commands_runs_allowed_version_probe() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )

        result = run_project_harness("inspect", str(target), "--verify-commands")

        assert result.returncode == 0, result.stderr
        assert "Command Candidates:" in result.stdout
        assert "command: python --version" in result.stdout
        assert "Command Verification:" in result.stdout
        assert "command: python --version" in result.stdout
        assert "status: verified" in result.stdout
        assert "bounded version probe" in result.stdout


def test_verify_commands_reports_probe_errors_without_crashing() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = root / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )
        fake_bin = root / "bin"
        fake_bin.mkdir()
        for name in ("python", "python.cmd", "python.bat"):
            fake_python = fake_bin / name
            fake_python.write_text(
                "@echo off\necho forced probe failure 1>&2\nexit /b 17\n"
                if name.endswith((".cmd", ".bat"))
                else "#!/bin/sh\necho forced probe failure >&2\nexit 17\n"
            )
            fake_python.chmod(0o755)

        result = run_project_harness(
            "inspect",
            str(target),
            "--verify-commands",
            extra_env={
                "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            },
        )

        assert result.returncode == 0, result.stderr
        assert "Command Verification:" in result.stdout
        assert "command: python --version" in result.stdout
        assert "status: error" in result.stdout


def test_verify_commands_reports_probe_timeouts_without_crashing() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = root / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"
                """
            ).strip()
        )
        fake_bin = root / "bin"
        fake_bin.mkdir()
        if os.name == "nt":
            for name in ("python.cmd", "python.bat"):
                fake_python = fake_bin / name
                fake_python.write_text("@echo off\n:wait\ngoto wait\n")
                fake_python.chmod(0o755)
        else:
            fake_python = fake_bin / "python"
            fake_python.write_text("#!/bin/sh\nsleep 10\n")
            fake_python.chmod(0o755)

        result = run_project_harness(
            "inspect",
            str(target),
            "--verify-commands",
            extra_env={
                "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            },
        )

        assert result.returncode == 0, result.stderr
        assert "Command Verification:" in result.stdout
        assert "command: python --version" in result.stdout
        assert "status: timeout" in result.stdout


def test_run_checks_executes_project_tests_in_distinct_section() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "pyproject.toml").write_text(
            dedent(
                """
                [project]
                name = "sample-project"
                version = "1.0.0"

                [tool.pytest.ini_options]
                testpaths = ["tests"]
                """
            ).strip()
        )
        (target / "tests").mkdir()
        sentinel = target / "pytest-ran.txt"
        (target / "tests" / "test_side_effect.py").write_text(
            dedent(
                f"""
                from pathlib import Path

                def test_side_effect():
                    Path({str(sentinel)!r}).write_text("ran")
                """
            ).strip()
        )

        result = run_project_harness("inspect", str(target), "--run-checks")

        assert result.returncode == 0, result.stderr
        assert sentinel.read_text() == "ran"
        assert "Command Candidates:" in result.stdout
        assert "Project Checks:" in result.stdout
        assert "command: python -m pytest -q" in result.stdout
        assert "status: passed" in result.stdout
        assert "exit_code: 0" in result.stdout


def test_run_checks_reports_makefile_project_checks_in_distinct_section() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target = root / "sample_project"
        target.mkdir()
        (target / "Makefile").write_text(
            dedent(
                """
                test:
                \tmake-test

                build:
                \tmake-build
                """
            ).strip()
        )
        fake_bin = root / "bin"
        fake_bin.mkdir()
        if os.name == "nt":
            fake_make = fake_bin / "make.cmd"
            fake_make.write_text(
                "@echo off\r\n"
                "echo %1> make-%1-ran.txt\r\n"
                "exit /b 0\r\n"
            )
        else:
            fake_make = fake_bin / "make"
            fake_make.write_text(
                "#!/bin/sh\n"
                "printf '%s' \"$1\" > \"make-$1-ran.txt\"\n"
            )
        fake_make.chmod(0o755)

        result = run_project_harness(
            "inspect",
            str(target),
            "--run-checks",
            extra_env={
                "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                "PATHEXT": ".COM;.EXE;.BAT;.CMD",
            },
        )

        assert result.returncode == 0, result.stderr
        assert (target / "make-test-ran.txt").read_text().strip() == "test"
        assert (target / "make-build-ran.txt").read_text().strip() == "build"
        assert "Project Checks:" in result.stdout
        assert "command: make test" in result.stdout
        assert "command: make build" in result.stdout
        assert result.stdout.count("status: passed") == 2


def test_verify_commands_skips_unsafe_make_targets_without_run_checks() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample_project"
        target.mkdir()
        (target / "Makefile").write_text(
            dedent(
                """
                test:
                \tpython -c "from pathlib import Path; Path('test-ran.txt').write_text('ran')"

                build:
                \tpython -c "from pathlib import Path; Path('build-ran.txt').write_text('ran')"

                install:
                \tpython -c "from pathlib import Path; Path('install-ran.txt').write_text('ran')"
                """
            ).strip()
        )

        result = run_project_harness("inspect", str(target), "--verify-commands")

        assert result.returncode == 0, result.stderr
        for command in ("make test", "make build", "make install"):
            assert f"command: {command}" in result.stdout
        assert result.stdout.count("status: skipped") == 3
        assert not (target / "test-ran.txt").exists()
        assert not (target / "build-ran.txt").exists()
        assert not (target / "install-ran.txt").exists()

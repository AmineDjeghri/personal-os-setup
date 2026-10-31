"""Check Make command boundaries without installing software or running integration tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    os.name == "nt" or not (shutil.which("make") and shutil.which("bash")),
    reason="POSIX Make/Bash stub harness",
)


def test_windows_installer_passes_literal_powershell_variables(tmp_path):
    log = tmp_path / "powershell.json"
    powershell = tmp_path / "powershell"
    powershell.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "pathlib.Path(os.environ['COMMAND_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
    )
    powershell.chmod(0o755)
    makefile = tmp_path / "Makefile"
    makefile.write_text(f"SHELL := bash\ninclude {REPO}/makefiles/install.mk\n")
    result = subprocess.run(
        [shutil.which("make"), "--no-print-directory", "install-uv", "OS=Windows_NT"],
        cwd=tmp_path,
        env=dict(
            os.environ,
            PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
            COMMAND_LOG=str(log),
            ErrorActionPreference="EXPANDED_BY_BASH",
            uv="EXPANDED_BY_BASH",
        ),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    args = json.loads(log.read_text())
    assert args[:-1] == ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]
    script = args[-1]
    assert "$ErrorActionPreference = 'Stop'" in script
    assert "$uv = Get-Command uv" in script
    assert "if ($uv)" in script and "$uv.Source" in script
    assert "EXPANDED_BY_BASH" not in script


@pytest.fixture
def make_tests(tmp_path):
    log = tmp_path / "uv.jsonl"
    uv = tmp_path / "uv"
    uv.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys\n"
        "with pathlib.Path(os.environ['COMMAND_LOG']).open('a') as stream:\n"
        "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
    )
    uv.chmod(0o755)
    (tmp_path / "Makefile").write_text(
        f"SHELL := bash\nUV := {uv}\ninclude {REPO}/makefiles/test.mk\n"
        "build-package:\n\t@:\ntest-installation:\n\t@$(UV) fixture-installation\n"
    )

    def run(target, *args, **updates):
        env = dict(os.environ, COMMAND_LOG=str(log))
        env.pop("PYTEST_ADDOPTS", None)
        env.pop("PYTEST_ARGS", None)
        env.pop("MAKEFLAGS", None)
        env.pop("TEST_COVERAGE", None)
        result = subprocess.run(
            [shutil.which("make"), "--no-print-directory", target, *args],
            cwd=tmp_path,
            env=dict(env, **updates),
            capture_output=True,
            text=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return run


@pytest.mark.parametrize("target", ["test-all", "test-coverage", "test-integration"])
@pytest.mark.parametrize("option", ["--collect-only", "-k one", "-m unit", "--deselect=one"])
@pytest.mark.parametrize("variable", ["PYTEST_ARGS", "PYTEST_ADDOPTS"])
def test_comprehensive_targets_reject_reduced_runs(make_tests, target, option, variable):
    result, calls = make_tests(target, f"{variable}={option}")
    assert result.returncode != 0
    assert "test-local" in result.stderr, result.stderr
    assert not calls, "reject reduced runs before launching pytest or building artifacts"


@pytest.mark.parametrize("target", ["test-all", "test-coverage", "test-integration"])
def test_environment_cannot_reduce_comprehensive_checks(make_tests, target):
    result, calls = make_tests(target, PYTEST_ADDOPTS="--collect-only")
    assert result.returncode != 0 and not calls


def test_focused_target_accepts_filters(make_tests):
    result, calls = make_tests("test-local", "PYTEST_ARGS=-k one")
    assert result.returncode == 0, result.stderr
    assert calls[0][-2:] == ["-k", "one"]


@pytest.mark.parametrize("target", ["test-all", "test-coverage"])
@pytest.mark.parametrize("inherited_coverage", [None, "1"])
def test_full_targets_run_both_safe_suites_and_installation(
    make_tests, target, monkeypatch, inherited_coverage
):
    if inherited_coverage is None:
        monkeypatch.delenv("TEST_COVERAGE", raising=False)
    else:
        monkeypatch.setenv("TEST_COVERAGE", inherited_coverage)
    result, calls = make_tests(target)
    assert result.returncode == 0, result.stderr
    assert calls[0][:7] == [
        "run",
        "--no-sync",
        "python",
        "-m",
        "pytest",
        "tests/unit",
        "tests/skills",
    ]
    assert ("--cov=personal_os_setup" in calls[0]) == (target == "test-coverage")
    assert calls[1:] == [["fixture-installation"]]

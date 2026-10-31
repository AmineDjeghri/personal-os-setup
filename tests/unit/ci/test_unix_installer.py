"""Run the Unix installer against command stubs, never against the host package managers."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX installer harness")

STUB = r"""import json, os, pathlib, sys
root = pathlib.Path(os.environ['INSTALL_FIXTURE'])
name, args = pathlib.Path(sys.argv[0]).name, sys.argv[1:]
with (root / 'calls.jsonl').open('a') as stream:
    stream.write(json.dumps([name, args]) + '\n')
if name == 'git':
    if args == ['rev-parse', '--is-inside-work-tree']: print('true')
    elif args == ['rev-parse', '--show-toplevel']: print(root)
    elif args in (['pull'], ['pull', '--ff-only']): sys.exit(int(os.environ.get('FAIL_PULL', '0')))
    else: raise AssertionError(args)
elif name == 'make':
    assert args in (['install'], ['run']), args
    print('fixture ' + args[0], flush=True)
    sys.exit(int(os.environ.get('FAIL_' + args[0].upper(), '0')))
elif name == 'script':
    if os.environ['FIXTURE_OS'] == 'Darwin':
        assert args[:3] == ['-q', '-a', args[2]] and args[-2:] == ['make', 'run'], args
    else:
        assert '-e' in args and '-c' in args and 'make run' in args, args
    sys.exit(int(os.environ.get('FAIL_RUN', '0')))
elif name == 'uname': print(os.environ['FIXTURE_OS'])
elif name != 'chezmoi': raise AssertionError((name, args))
"""


@pytest.fixture(params=[shell for shell in (shutil.which("sh"), shutil.which("dash")) if shell])
def installer(tmp_path, request):
    root = tmp_path / "personal-os-setup"
    bins = root / "bin"
    bins.mkdir(parents=True)
    for name in ("git", "make", "script", "chezmoi", "uname"):
        path = bins / name
        path.write_text(f"#!{sys.executable}\n" + STUB)
        path.chmod(0o755)

    def run(terminal, system="Darwin", **settings):
        env = dict(
            os.environ,
            INSTALL_FIXTURE=str(root),
            FIXTURE_OS=system,
            PATH=str(bins) + os.pathsep + os.environ["PATH"],
            **settings,
        )
        args = [request.param, str(REPO / "install_unix.sh")]
        if terminal:
            import pty

            master, slave = pty.openpty()
            try:
                result = subprocess.run(
                    args,
                    cwd=root,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=slave,
                    stderr=slave,
                    timeout=15,
                )
            finally:
                os.close(master)
                os.close(slave)
        else:
            result = subprocess.run(args, cwd=root, env=env, capture_output=True, timeout=15)
        calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
        return result, calls, root

    return run


@pytest.mark.parametrize("terminal", [False, True])
@pytest.mark.parametrize("system", ["Darwin", "Linux"])
def test_failed_install_stops_before_launcher_or_app(installer, terminal, system):
    result, calls, root = installer(terminal, system, FAIL_INSTALL="23")
    assert result.returncode == 23
    assert [args for name, args in calls if name == "make"] == [["install"]]
    assert not any(name == "script" for name, _ in calls)
    assert "fixture install" in next((root / ".logs").glob("*.log")).read_text()


@pytest.mark.parametrize("terminal", [False, True])
@pytest.mark.parametrize("system", ["Darwin", "Linux"])
def test_app_exit_status_reaches_installer_caller(installer, terminal, system):
    result, _, _ = installer(terminal, system, FAIL_RUN="29")
    assert result.returncode == 29


def test_successful_install_keeps_logging_and_runs_app(installer):
    result, calls, root = installer(False)
    assert result.returncode == 0
    assert [args for name, args in calls if name == "make"] == [["install"], ["run"]]
    assert "fixture run" in next((root / ".logs").glob("*.log")).read_text()


def test_failed_pull_stops_before_installation(installer):
    result, calls, _ = installer(False, FAIL_PULL="19")
    assert result.returncode == 19
    assert not any(name == "make" for name, _ in calls)

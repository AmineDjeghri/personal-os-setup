"""Exercise checkout updates without Git, dependency installs or real restarts."""

import subprocess
import sys
from types import SimpleNamespace

import pytest

from personal_os_setup.tasks import self_update as update


class Restarted(Exception):
    """Stand in for an exec that replaces the current process."""


@pytest.fixture
def bootstrap(monkeypatch, tmp_path):
    state = SimpleNamespace(head="old", next_head="old", pull_error=None, sync_error=None, calls=[])
    monkeypatch.setattr(update, "_find_repo_root", lambda: tmp_path)
    monkeypatch.setattr(update.shutil, "which", lambda command: "uv-stub")

    def run(command, **kwargs):
        state.calls.append((command, kwargs))
        if command[0] == "git":
            if command[-2:] == ["rev-parse", "HEAD"]:
                return subprocess.CompletedProcess(command, 0, state.head, "")
            assert command[-2:] == ["pull", "--ff-only"]
            if isinstance(state.pull_error, Exception):
                raise state.pull_error
            if state.pull_error:
                return subprocess.CompletedProcess(command, 1, "", "offline")
            state.head = state.next_head
            return subprocess.CompletedProcess(command, 0, "localized Git output", "")
        assert command[0] == "uv-stub" and command[1] == "sync"
        if isinstance(state.sync_error, Exception):
            raise state.sync_error
        return subprocess.CompletedProcess(command, int(bool(state.sync_error)), "", "sync failure")

    def restart(executable, arguments):
        state.calls.append(("restart", (executable, arguments)))
        raise Restarted

    monkeypatch.setattr(update.subprocess, "run", run)
    monkeypatch.setattr(update.os, "execv", restart)
    return state


def test_wheel_install_does_not_update_a_parent_repository(bootstrap, monkeypatch):
    monkeypatch.setattr(update, "_find_repo_root", lambda: None)
    update.self_update()
    assert not bootstrap.calls


def test_missing_uv_leaves_source_and_environment_unchanged(bootstrap, monkeypatch):
    monkeypatch.setattr(update.shutil, "which", lambda command: None)
    update.self_update()
    assert not bootstrap.calls


def test_current_checkout_still_syncs_its_own_environment(bootstrap, capsys):
    update.self_update()
    command, options = bootstrap.calls[-1]
    assert command == [
        "uv-stub",
        "sync",
        "--locked",
        "--inexact",
        "--no-default-groups",
        "--python",
        sys.executable,
    ]
    assert options["env"]["UV_PROJECT_ENVIRONMENT"] == sys.prefix
    assert options["timeout"] == 120
    assert capsys.readouterr().out == ""


def test_changed_head_syncs_before_restarting_with_current_interpreter(bootstrap, monkeypatch):
    bootstrap.next_head = "new"
    monkeypatch.setattr(sys, "argv", ["launcher.exe", "--example"])
    with pytest.raises(Restarted):
        update.self_update()
    assert bootstrap.calls[-2][0][1] == "sync"
    assert bootstrap.calls[-1] == (
        "restart",
        (sys.executable, [sys.executable, "-m", "personal_os_setup.frontend.main", "--example"]),
    )


@pytest.mark.parametrize("error", [True, subprocess.TimeoutExpired("git", 10), OSError("offline")])
def test_offline_pull_keeps_current_app_but_checks_dependencies(bootstrap, error):
    bootstrap.pull_error = error
    update.self_update()
    assert bootstrap.calls[-1][0][1] == "sync"
    assert not any(command == "restart" for command, _ in bootstrap.calls)


@pytest.mark.parametrize(
    "error", [True, subprocess.TimeoutExpired("uv", 120), OSError("missing uv")]
)
def test_sync_failure_blocks_startup_and_is_retried_next_launch(bootstrap, error):
    bootstrap.next_head = "new"
    bootstrap.sync_error = error
    with pytest.raises(RuntimeError, match="synchronize app dependencies"):
        update.self_update()
    assert bootstrap.head == "new"
    bootstrap.sync_error = None
    update.self_update()
    assert sum(command[0] == "uv-stub" for command, _ in bootstrap.calls) == 2
    assert not any(command == "restart" for command, _ in bootstrap.calls)


@pytest.mark.parametrize("worktree", [False, True])
def test_repo_discovery_requires_this_project_identity(tmp_path, monkeypatch, worktree):
    root = tmp_path / "checkout"
    root.mkdir()
    if worktree:
        (root / ".git").write_text("gitdir: fixture\n")
    else:
        (root / ".git").mkdir()
    project = root / "pyproject.toml"
    project.write_text('[project]\nname = "unrelated-project"\n')
    monkeypatch.setattr(
        update, "__file__", str(root / "src/personal_os_setup/tasks/self_update.py")
    )
    assert update._find_repo_root() is None
    project.write_text('[project]\nname = "personal-os-setup"\n')
    assert update._find_repo_root() == root

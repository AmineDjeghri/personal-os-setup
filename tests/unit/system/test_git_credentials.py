"""Exercise the gh credential-helper setup without touching the real gitconfig."""

from __future__ import annotations

import pytest

from personal_os_setup.tasks.commands import CommandResult
from personal_os_setup.tasks.system import git_credentials as gc


@pytest.fixture
def env(monkeypatch):
    state = {"tools": {"gh", "git"}, "auth_rc": 0, "helpers": "", "setup_rc": 0, "calls": []}

    monkeypatch.setattr(gc.shutil, "which", lambda name: name if name in state["tools"] else None)

    def fake_run(argv, **kwargs):
        argv = list(argv)
        state["calls"].append(argv)
        if argv[:3] == ["gh", "auth", "status"]:
            return CommandResult(argv=argv, returncode=state["auth_rc"], stdout="", stderr="")
        if argv[:2] == ["git", "config"]:
            rc = 0 if state["helpers"] else 1
            return CommandResult(argv=argv, returncode=rc, stdout=state["helpers"], stderr="")
        assert argv[:3] == ["gh", "auth", "setup-git"]
        return CommandResult(argv=argv, returncode=state["setup_rc"], stdout="", stderr="boom")

    monkeypatch.setattr(gc, "run", fake_run)
    return state


def _setup_called(state) -> bool:
    return any(c[:3] == ["gh", "auth", "setup-git"] for c in state["calls"])


def test_missing_gh_is_reported_without_running_anything(env):
    env["tools"].discard("gh")
    res = gc.setup_gh_git_credentials()
    assert not res.ok and "gh" in res.summary
    assert env["calls"] == []


def test_not_logged_in_points_to_gh_auth_login(env):
    env["auth_rc"] = 1
    res = gc.setup_gh_git_credentials()
    assert not res.ok
    assert "gh auth login --hostname github.com" in res.details
    assert not _setup_called(env)


def test_existing_gh_helper_is_a_no_op(env):
    env["helpers"] = "\n!'/opt/homebrew/bin/gh' auth git-credential\n"
    res = gc.setup_gh_git_credentials()
    assert res.ok and "already" in res.summary
    assert not _setup_called(env)


def test_runs_setup_git_when_helper_missing(env):
    res = gc.setup_gh_git_credentials()
    assert res.ok
    assert ["gh", "auth", "setup-git", "--hostname", "github.com"] in env["calls"]


def test_setup_git_failure_is_reported(env):
    env["setup_rc"] = 1
    res = gc.setup_gh_git_credentials()
    assert not res.ok and "boom" in res.details

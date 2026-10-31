"""Unit tests for the best-effort git-pull self-update run at app launch."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from personal_os_setup.tasks.self_update import self_update


def test_no_op_when_not_a_git_checkout(capsys):
    with patch("personal_os_setup.tasks.self_update._find_repo_root", return_value=None):
        self_update()
    assert capsys.readouterr().out == ""


def test_prints_nothing_when_already_up_to_date(tmp_path, capsys):
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="Already up to date.\n", stderr=""
    )
    with (
        patch("personal_os_setup.tasks.self_update._find_repo_root", return_value=tmp_path),
        patch("personal_os_setup.tasks.self_update.subprocess.run", return_value=completed),
    ):
        self_update()
    assert capsys.readouterr().out == ""


def test_prints_summary_when_updated(tmp_path, capsys):
    completed = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="Updating abc123..def456\nFast-forward\n", stderr=""
    )
    with (
        patch("personal_os_setup.tasks.self_update._find_repo_root", return_value=tmp_path),
        patch("personal_os_setup.tasks.self_update.subprocess.run", return_value=completed),
    ):
        self_update()
    assert "personal-os-setup updated" in capsys.readouterr().out


def test_no_op_when_pull_fails(tmp_path, capsys):
    completed = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="not a git repository"
    )
    with (
        patch("personal_os_setup.tasks.self_update._find_repo_root", return_value=tmp_path),
        patch("personal_os_setup.tasks.self_update.subprocess.run", return_value=completed),
    ):
        self_update()
    assert capsys.readouterr().out == ""


def test_no_op_on_timeout(tmp_path, capsys):
    with (
        patch("personal_os_setup.tasks.self_update._find_repo_root", return_value=tmp_path),
        patch(
            "personal_os_setup.tasks.self_update.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10),
        ),
    ):
        self_update()
    assert capsys.readouterr().out == ""

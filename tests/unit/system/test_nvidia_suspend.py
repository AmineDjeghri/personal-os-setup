"""Exercise the NVIDIA suspend-service fix without touching systemd."""

from __future__ import annotations

import pytest

from personal_os_setup.tasks.commands import CommandResult
from personal_os_setup.tasks.system import nvidia_tasks as nt


@pytest.fixture
def env(monkeypatch):
    state = {"tools": {"nvidia-smi"}, "sudo": True, "rc": 0, "calls": []}
    monkeypatch.setattr(nt.shutil, "which", lambda name: name if name in state["tools"] else None)
    monkeypatch.setattr(nt, "sudo_non_interactive_ok", lambda: state["sudo"])

    def fake_run(argv, **kwargs):
        state["calls"].append(list(argv))
        return CommandResult(argv=list(argv), returncode=state["rc"], stdout="", stderr="")

    monkeypatch.setattr(nt, "run", fake_run)
    return state


def test_enables_all_sleep_services(env):
    assert nt.setup_nvidia_suspend().ok
    assert env["calls"] == [["sudo", "-n", "systemctl", "enable", *nt.NVIDIA_SLEEP_SERVICES]]


def test_missing_driver_runs_nothing(env):
    env["tools"].clear()
    assert not nt.setup_nvidia_suspend().ok
    assert env["calls"] == []


def test_missing_sudo_runs_nothing(env):
    env["sudo"] = False
    assert not nt.setup_nvidia_suspend().ok
    assert env["calls"] == []


def test_enable_failure_is_reported(env):
    env["rc"] = 1
    assert not nt.setup_nvidia_suspend().ok

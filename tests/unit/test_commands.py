"""Tests for the subprocess helpers in tasks/commands.py."""

from __future__ import annotations

import sys

from personal_os_setup.tasks.commands import QUIET_ENV, run, strip_terminal_noise


def test_strip_keeps_only_the_last_redraw_frame_and_drops_spinner_lines():
    raw = "\x1b[?25l\r◐  Cloning…\r◓  Cloning…\r◇  Repository cloned\n│\n◇  ──────╮\nplain line\n"
    assert strip_terminal_noise(raw) == "◇  Repository cloned\nplain line"


def test_strip_removes_color_codes():
    assert strip_terminal_noise("\x1b[0;31mFAILED\x1b[0m x") == "FAILED x"


def test_run_extends_the_environment_instead_of_replacing_it(monkeypatch):
    monkeypatch.setenv("KEEP_ME", "yes")
    code = "import os;print(os.environ['KEEP_ME'], os.environ['NO_COLOR'], os.environ['TERM'])"
    res = run([sys.executable, "-c", code], env=QUIET_ENV)
    assert res.stdout.split() == ["yes", "1", "dumb"]

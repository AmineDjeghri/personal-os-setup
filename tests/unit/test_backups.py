"""Tests for the shared pre-change backup helper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from personal_os_setup.tasks.backups import backup_file, backup_root, clean_backups


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))


def test_backup_lands_under_the_state_dir_mirroring_the_home_path(tmp_path):
    live = tmp_path / "home" / ".config" / "app" / "settings.json"
    live.parent.mkdir(parents=True)
    live.write_text("live")
    copy = backup_file(live, "20261125_120000")
    assert copy == backup_root() / "20261125_120000" / ".config" / "app" / "settings.json"
    assert copy.read_text() == "live"
    assert [p.name for p in live.parent.iterdir()] == ["settings.json"]  # nothing beside it


def test_backup_outside_home_keeps_the_path_without_its_anchor(tmp_path):
    live = tmp_path / "elsewhere" / "x.toml"
    live.parent.mkdir(parents=True)
    live.write_text("live")
    copy = backup_file(live, "S")
    assert copy is not None and copy.read_text() == "live"
    assert backup_root() in copy.parents


def test_missing_file_is_not_an_error(tmp_path):
    assert backup_file(tmp_path / "nope") is None


def test_clean_backups_removes_every_backup_set_and_nothing_else(tmp_path):
    live = tmp_path / "home" / "a.toml"
    live.parent.mkdir(parents=True)
    live.write_text("live")
    backup_file(live, "S1")
    backup_file(live, "S2")
    result = clean_backups()
    assert result.ok is True and "removed 2" in result.summary
    assert list(backup_root().iterdir()) == []
    assert live.read_text() == "live"


def test_clean_backups_with_no_backups_is_ok():
    assert clean_backups().ok is True


def test_clean_backups_reports_failures(tmp_path):
    live = tmp_path / "home" / "a.toml"
    live.parent.mkdir(parents=True)
    live.write_text("x")
    backup_file(live, "S1")
    with patch("shutil.rmtree", side_effect=PermissionError("denied")):
        result = clean_backups()
    assert result.ok is False and "1 failed" in result.summary

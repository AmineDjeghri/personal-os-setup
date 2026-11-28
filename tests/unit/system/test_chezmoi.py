"""Unit tests for tasks/system/chezmoi.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personal_os_setup.tasks.backups import backup_root
from personal_os_setup.tasks.system.chezmoi import (
    chezmoi_add,
    chezmoi_apply,
    chezmoi_diff,
    chezmoi_forget,
    chezmoi_managed_paths,
    chezmoi_preview,
    chezmoi_re_add,
    chezmoi_source_dir,
)

_RUN = "personal_os_setup.tasks.system.chezmoi.run"


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path, monkeypatch):
    """Keep backups (and clean-backups) away from the real ~/.local/state."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))


def _fake_chezmoi(*, status="", files_rc=0, scripts_rc=0, scripts_err=""):
    """A `run` stand-in: answers `status`, then the files phase, then the scripts phase."""
    calls: list[list[str]] = []

    def fake(argv, **kwargs):
        calls.append(list(argv))
        if "status" in argv:
            return MagicMock(returncode=0, stdout=status, stderr="")
        if "--exclude=scripts" in argv:
            return MagicMock(
                returncode=files_rc, stdout="wrote files", stderr="boom" * (files_rc > 0)
            )
        return MagicMock(returncode=scripts_rc, stdout="", stderr=scripts_err)

    return fake, calls


class TestChezmoiSourceDir:
    """Tests for chezmoi_source_dir()."""

    def test_points_at_vendored_dotfiles(self):
        """The source dir should exist and contain the vendored zsh dotfiles."""
        source_dir = chezmoi_source_dir()
        assert source_dir.is_dir()
        assert (source_dir / "dot_zshrc").is_file()
        assert (source_dir / "dot_p10k.zsh").is_file()


class TestChezmoiNotFound:
    """Tests that every chezmoi_* action handles a missing binary the same way."""

    def test_all_actions_fail_when_chezmoi_missing(self):
        """Each action should return ok=False with a 'chezmoi not found' summary."""
        with patch("shutil.which", return_value=None):
            for fn in (chezmoi_diff, chezmoi_apply, chezmoi_re_add):
                result = fn()
                assert result.ok is False
                assert "chezmoi not found" in result.summary

    def test_add_and_forget_fail_when_chezmoi_missing(self):
        with patch("shutil.which", return_value=None):
            assert chezmoi_add(Path("~/.bashrc")).ok is False
            assert chezmoi_forget([Path("~/.bashrc")]).ok is False

    def test_managed_paths_empty_when_chezmoi_missing(self):
        with patch("shutil.which", return_value=None):
            assert chezmoi_managed_paths() == []


class TestChezmoiDiff:
    """Tests for chezmoi_diff()."""

    def test_diff_with_changes(self):
        """diff() should return ok=True with the diff output in details."""
        mock_result = MagicMock(returncode=0, stdout="diff --git a/.zshrc...", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_diff()
        assert result.ok is True
        assert "diff --git" in result.details

    def test_diff_no_changes(self):
        """diff() should report 'no changes' when there's no output."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_diff()
        assert result.ok is True
        assert "no changes" in result.summary

    def test_diff_with_targets_appends_them_to_argv(self):
        """Passing targets should restrict the chezmoi command to just those paths."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run = MagicMock(return_value=mock_result)
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", mock_run),
        ):
            chezmoi_diff([Path("/home/user/.zshrc"), Path("/home/user/.p10k.zsh")])
        argv = mock_run.call_args[0][0]
        assert argv[-2:] == [str(Path("/home/user/.zshrc")), str(Path("/home/user/.p10k.zsh"))]


class TestChezmoiApply:
    """Tests for chezmoi_apply()."""

    def test_apply_success(self):
        """apply() should return ok=True when chezmoi exits with returncode 0."""
        mock_result = MagicMock(returncode=0, stdout="wrote .zshrc", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_apply()
        assert result.ok is True

    def test_apply_failure(self):
        """apply() should return ok=False when chezmoi exits with a non-zero code."""
        mock_result = MagicMock(returncode=1, stdout="", stderr="permission denied")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_apply()
        assert result.ok is False
        assert "permission denied" in result.details

    def test_apply_passes_force_flag(self):
        """apply() must pass --force."""
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run = MagicMock(return_value=mock_result)
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", mock_run),
        ):
            chezmoi_apply()
        argv = mock_run.call_args[0][0]
        assert "--force" in argv


class TestChezmoiApplyPhases:
    """chezmoi_apply() applies files first and scripts second so a script cannot block files."""

    def test_files_then_scripts_in_two_calls(self):
        fake, calls = _fake_chezmoi()
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            result = chezmoi_apply([Path("/h/.claude")])
        applies = [c for c in calls if "apply" in c]
        assert "--exclude=scripts" in applies[0] and "--include=scripts" in applies[1]
        assert all(c[-1] == str(Path("/h/.claude")) for c in applies)
        assert result.ok is True and result.warning is False

    def test_script_failure_after_files_is_a_warning_naming_the_script(self):
        err = "skills: DRIFT hermes-agent\nchezmoi: .claude/replay.sh: exit status 1"
        fake, _ = _fake_chezmoi(scripts_rc=1, scripts_err=err)
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            result = chezmoi_apply()
        assert result.ok is True and result.warning is True
        assert ".claude/replay.sh (exit 1)" in result.summary
        assert result.details.startswith("Failed step: .claude/replay.sh (exit 1)")
        assert "DRIFT hermes-agent" in result.details

    def test_file_failure_is_an_error_and_skips_scripts(self):
        fake, calls = _fake_chezmoi(files_rc=1)
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            result = chezmoi_apply()
        assert result.ok is False
        assert not any("--include=scripts" in c for c in calls)
        assert "Failed step: write files" in result.details

    def test_spinner_noise_is_removed_from_details(self):
        noisy = "\x1b[?25l\r◐  Cloning repository…\r◓  Cloning repository…\n│\nreal error line"
        fake, _ = _fake_chezmoi(scripts_rc=1, scripts_err=noisy)
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            result = chezmoi_apply()
        assert "real error line" in result.details
        assert "\x1b" not in result.details and "◐" not in result.details


class TestChezmoiApplyBackups:
    """Backups go to the state dir, only for files the apply would actually overwrite."""

    def test_backs_up_only_modified_files_outside_the_managed_tree(self, tmp_path):
        home = tmp_path / "home"
        changed = home / ".claude" / "skills" / "a" / "SKILL.md"
        same = home / ".claude" / "skills" / "b" / "SKILL.md"
        for f in (changed, same):
            f.parent.mkdir(parents=True)
            f.write_text("live")
        status = f" M {changed}\n A {home}/.claude/new.md\n"
        fake, _ = _fake_chezmoi(status=status)
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            result = chezmoi_apply([home / ".claude"])

        backups = [p for p in backup_root().rglob("*") if p.is_file()]
        assert [b.relative_to(backup_root()).parts[1:] for b in backups] == [
            (".claude", "skills", "a", "SKILL.md")
        ]
        assert backups[0].read_text() == "live"
        assert list(changed.parent.glob("*backup*")) == []  # nothing next to the live file
        assert "Backed up 1 file(s)" in result.details


class TestChezmoiPreview:
    def test_counts_creates_overwrites_and_scripts(self):
        status = " A /h/a\n M /h/b\n M /h/c\n R /h/.claude/replay.sh\n"
        fake, _ = _fake_chezmoi(status=status)
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            text = chezmoi_preview([Path("/h")])
        assert "1 file(s) to create, 2 to overwrite" in text
        assert "1 script(s) will run: replay.sh" in text

    def test_nothing_to_change(self):
        fake, _ = _fake_chezmoi(status="")
        with patch("shutil.which", return_value="/usr/bin/chezmoi"), patch(_RUN, fake):
            assert chezmoi_preview() == "Nothing to change."

    def test_empty_without_chezmoi(self):
        with patch("shutil.which", return_value=None):
            assert chezmoi_preview() == ""


class TestChezmoiReAdd:
    """Tests for chezmoi_re_add()."""

    def test_re_add_success(self):
        """re_add() should return ok=True with the chezmoi source dir mentioned in details."""
        mock_result = MagicMock(returncode=0, stdout="re-added .zshrc", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_re_add()
        assert result.ok is True
        assert "source dir" in result.details.lower()

    def test_re_add_failure(self):
        """re_add() should return ok=False when chezmoi exits with a non-zero code."""
        mock_result = MagicMock(returncode=1, stdout="", stderr="some error")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_re_add()
        assert result.ok is False

    def test_re_add_with_targets_appends_them_to_argv(self):
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run = MagicMock(return_value=mock_result)
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", mock_run),
        ):
            chezmoi_re_add([Path("/home/user/.zshrc")])
        argv = mock_run.call_args[0][0]
        assert argv[-1] == str(Path("/home/user/.zshrc"))


class TestChezmoiManagedPaths:
    """Tests for chezmoi_managed_paths()."""

    def test_parses_and_sorts_stdout_lines(self):
        mock_result = MagicMock(
            returncode=0, stdout="/home/user/.zshrc\n/home/user/.config/zed/settings.json\n"
        )
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            paths = chezmoi_managed_paths()
        assert paths == [
            Path("/home/user/.config/zed/settings.json"),
            Path("/home/user/.zshrc"),
        ]

    def test_empty_when_command_fails(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="boom")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            assert chezmoi_managed_paths() == []


class TestChezmoiAdd:
    """Tests for chezmoi_add()."""

    def test_add_success(self):
        mock_result = MagicMock(returncode=0, stdout="add .config/foo/config.toml", stderr="")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_add(Path("/home/user/.config/foo/config.toml"))
        assert result.ok is True
        assert "now tracked" in result.summary

    def test_add_failure(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="no such file")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_add(Path("/home/user/.config/missing.toml"))
        assert result.ok is False


class TestChezmoiForget:
    """Tests for chezmoi_forget()."""

    def test_forget_requires_targets(self):
        result = chezmoi_forget([])
        assert result.ok is False

    def test_forget_success_passes_force_flag(self):
        mock_result = MagicMock(returncode=0, stdout="forgot .zshrc", stderr="")
        mock_run = MagicMock(return_value=mock_result)
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", mock_run),
        ):
            result = chezmoi_forget([Path("/home/user/.zshrc")])
        assert result.ok is True
        argv = mock_run.call_args[0][0]
        assert "--force" in argv
        assert argv[-1] == str(Path("/home/user/.zshrc"))

    def test_forget_failure(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="not managed")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_forget([Path("/home/user/.zshrc")])
        assert result.ok is False


def test_every_script_runs_after_files_so_the_two_phase_apply_keeps_chezmoi_ordering():
    """`chezmoi_apply` applies files, then scripts: a run_before_ script would run too late."""
    scripts = [p.name for p in chezmoi_source_dir().rglob("run_*")]
    assert scripts, "expected chezmoi scripts in the source dir"
    assert [n for n in scripts if "_before_" in n or n.startswith("run_before")] == []

"""Unit tests for tasks/system/chezmoi.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from personal_os_setup.tasks.system.chezmoi import (
    chezmoi_add,
    chezmoi_apply,
    chezmoi_diff,
    chezmoi_forget,
    chezmoi_managed_paths,
    chezmoi_re_add,
    chezmoi_source_dir,
)


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
        assert argv[-2:] == ["/home/user/.zshrc", "/home/user/.p10k.zsh"]


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
        assert argv[-1] == "/home/user/.zshrc"


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
        assert argv[-1] == "/home/user/.zshrc"

    def test_forget_failure(self):
        mock_result = MagicMock(returncode=1, stdout="", stderr="not managed")
        with (
            patch("shutil.which", return_value="/usr/bin/chezmoi"),
            patch("personal_os_setup.tasks.system.chezmoi.run", return_value=mock_result),
        ):
            result = chezmoi_forget([Path("/home/user/.zshrc")])
        assert result.ok is False

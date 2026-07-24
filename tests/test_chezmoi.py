"""Unit tests for tasks/system/chezmoi.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from personal_os_setup.tasks.system.chezmoi import (
    chezmoi_apply,
    chezmoi_diff,
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

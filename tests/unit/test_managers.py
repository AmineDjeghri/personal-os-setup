"""Unit tests for package manager backends."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDarwinBrewManager:
    """Tests for the macOS Homebrew package manager backend."""

    def test_install_brew_not_found(self):
        """install() should return ok=False when brew is not on PATH."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        with patch("shutil.which", return_value=None):
            mgr = DarwinBrewManager()
            result = mgr.install("wget")
        assert result.ok is False
        assert "brew not found" in result.summary

    def test_install_success(self):
        """install() should return ok=True when brew exits with returncode 0."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch("shutil.which", return_value="/opt/homebrew/bin/brew"),
            patch("personal_os_setup.tasks.managers.darwin_brew.run", return_value=mock_result),
        ):
            mgr = DarwinBrewManager()
            result = mgr.install("wget")
        assert result.ok is True

    def test_install_failure(self):
        """install() should return ok=False when brew exits with a non-zero code."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        mock_result = MagicMock(returncode=1, stdout="err", stderr="not found")
        with (
            patch("shutil.which", return_value="/opt/homebrew/bin/brew"),
            patch("personal_os_setup.tasks.managers.darwin_brew.run", return_value=mock_result),
        ):
            mgr = DarwinBrewManager()
            result = mgr.install("wget")
        assert result.ok is False

    def test_is_installed(self):
        """is_installed() should reflect the returncode of the brew list command."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        with (
            patch("shutil.which", return_value="/opt/homebrew/bin/brew"),
            patch(
                "personal_os_setup.tasks.managers.darwin_brew.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            assert DarwinBrewManager().is_installed("wget") is True
        with (
            patch("shutil.which", return_value="/opt/homebrew/bin/brew"),
            patch(
                "personal_os_setup.tasks.managers.darwin_brew.run",
                return_value=MagicMock(returncode=1),
            ),
        ):
            assert DarwinBrewManager().is_installed("wget") is False


class TestUbuntuAptManager:
    """Tests for the Ubuntu apt-get package manager backend."""

    def test_install_no_sudo(self):
        """install() should fail immediately when sudo is not available."""
        from personal_os_setup.tasks.managers.ubuntu_apt import UbuntuAptManager

        with patch(
            "personal_os_setup.tasks.managers.ubuntu_apt.sudo_non_interactive_ok",
            return_value=False,
        ):
            mgr = UbuntuAptManager()
            result = mgr.install("curl")
        assert result.ok is False
        assert "sudo" in result.summary.lower()

    def test_install_success(self):
        """install() should return ok=True when apt-get exits with returncode 0."""
        from personal_os_setup.tasks.managers.ubuntu_apt import UbuntuAptManager

        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        with (
            patch(
                "personal_os_setup.tasks.managers.ubuntu_apt.sudo_non_interactive_ok",
                return_value=True,
            ),
            patch("personal_os_setup.tasks.managers.ubuntu_apt.run", return_value=mock_result),
        ):
            mgr = UbuntuAptManager()
            result = mgr.install("curl")
        assert result.ok is True

    def test_is_installed(self):
        """is_installed() should return True when dpkg shows 'install ok installed' status."""
        from personal_os_setup.tasks.managers.ubuntu_apt import UbuntuAptManager

        mock_result = MagicMock(returncode=0, stdout="Status: install ok installed\n")
        with patch("personal_os_setup.tasks.managers.ubuntu_apt.run", return_value=mock_result):
            assert UbuntuAptManager().is_installed("curl") is True


class TestArchPacmanManager:
    """Tests for the Arch pacman package manager backend."""

    def test_install_pacman_not_found(self):
        """install() should return ok=False when pacman is not on PATH."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        with patch("shutil.which", return_value=None):
            result = ArchPacmanManager().install("fd")
        assert result.ok is False
        assert "pacman not found" in result.summary

    def test_install_no_sudo(self):
        """install() should fail immediately when passwordless sudo is unavailable."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_pacman.sudo_non_interactive_ok",
                return_value=False,
            ),
        ):
            result = ArchPacmanManager().install("fd")
        assert result.ok is False
        assert "sudo" in result.summary.lower()

    def test_install_success(self):
        """install() should return ok=True and run pacman through sudo -n, since pacman writes as root."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_pacman.sudo_non_interactive_ok",
                return_value=True,
            ),
            patch("personal_os_setup.tasks.managers.arch_pacman.run", mock_run),
        ):
            result = ArchPacmanManager().install("fd")
        assert result.ok is True
        assert "pacman" in result.summary
        argv = mock_run.call_args[0][0]
        assert argv[:2] == ["sudo", "-n"]
        assert argv[-1] == "fd"

    def test_install_failure(self):
        """install() should return ok=False when pacman exits with a non-zero code."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        mock_result = MagicMock(returncode=1, stdout="", stderr="target not found")
        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_pacman.sudo_non_interactive_ok",
                return_value=True,
            ),
            patch("personal_os_setup.tasks.managers.arch_pacman.run", return_value=mock_result),
        ):
            result = ArchPacmanManager().install("nope")
        assert result.ok is False

    def test_is_installed(self):
        """is_installed() should reflect the returncode of `pacman -Q`."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_pacman.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            assert ArchPacmanManager().is_installed("git") is True
        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_pacman.run",
                return_value=MagicMock(returncode=1),
            ),
        ):
            assert ArchPacmanManager().is_installed("nope") is False


class TestArchParuManager:
    """Tests for the Arch paru AUR helper backend."""

    @staticmethod
    def _which_side_effect(paru_path, pacman_path="/usr/bin/pacman"):
        def _which(name):
            return {"paru": paru_path, "pacman": pacman_path}.get(name)

        return _which

    def test_install_bootstraps_paru_via_pacman_when_missing(self):
        """A missing paru is a normal pacman -S on CachyOS, not an AUR build."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        # First two `_paru()` checks (before/inside `_ensure_paru`) see nothing;
        # once the bootstrap "runs", later checks see paru on PATH.
        which_calls = iter([None, "/usr/bin/pacman", "/usr/bin/paru", "/usr/bin/paru"])
        bootstrap_result = MagicMock(returncode=0, stdout="", stderr="")
        install_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run = MagicMock(side_effect=[bootstrap_result, install_result])
        with (
            patch("shutil.which", side_effect=lambda name: next(which_calls)),
            patch(
                "personal_os_setup.tasks.managers.arch_paru.sudo_non_interactive_ok",
                return_value=True,
            ),
            patch("personal_os_setup.tasks.managers.arch_paru.run", mock_run),
        ):
            result = ArchParuManager().install("brave-browser")
        assert result.ok is True
        bootstrap_argv = mock_run.call_args_list[0][0][0]
        assert bootstrap_argv == [
            "sudo",
            "-n",
            "/usr/bin/pacman",
            "-S",
            "--needed",
            "--noconfirm",
            "paru",
        ]

    def test_install_no_pacman_and_no_paru(self):
        """Without pacman on PATH there is no way to bootstrap paru at all."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        with patch("shutil.which", side_effect=self._which_side_effect(None, None)):
            result = ArchParuManager().install("brave-browser")
        assert result.ok is False
        assert "pacman" in result.details.lower()
        assert "not found" in result.details.lower()

    def test_install_no_sudo_does_not_bootstrap(self):
        """Without passwordless sudo, bootstrapping must not attempt pacman -S."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        mock_run = MagicMock()
        with (
            patch("shutil.which", side_effect=self._which_side_effect(None)),
            patch(
                "personal_os_setup.tasks.managers.arch_paru.sudo_non_interactive_ok",
                return_value=False,
            ),
            patch("personal_os_setup.tasks.managers.arch_paru.run", mock_run),
        ):
            result = ArchParuManager().install("brave-browser")
        assert result.ok is False
        assert "sudo" in result.details.lower()
        mock_run.assert_not_called()

    def test_install_success(self):
        """install() should return ok=True and must not prefix paru with sudo, since paru escalates on its own."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
        with (
            patch("shutil.which", side_effect=self._which_side_effect("/usr/bin/paru")),
            patch("personal_os_setup.tasks.managers.arch_paru.run", mock_run),
        ):
            result = ArchParuManager().install("brave-browser")
        assert result.ok is True
        assert "paru" in result.summary
        argv = mock_run.call_args[0][0]
        assert argv[0] == "/usr/bin/paru"
        assert "sudo" not in argv

    def test_install_failure(self):
        """install() should return ok=False when paru exits with a non-zero code."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        mock_result = MagicMock(returncode=1, stdout="", stderr="build failed")
        with (
            patch("shutil.which", side_effect=self._which_side_effect("/usr/bin/paru")),
            patch("personal_os_setup.tasks.managers.arch_paru.run", return_value=mock_result),
        ):
            result = ArchParuManager().install("nope")
        assert result.ok is False

    def test_is_installed_queries_pacman(self):
        """AUR packages land in pacman's local DB, so is_installed() uses pacman -Q."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        with (
            patch("shutil.which", return_value="/usr/bin/pacman"),
            patch(
                "personal_os_setup.tasks.managers.arch_paru.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            assert ArchParuManager().is_installed("pycharm") is True


class TestWebInstallManager:
    """Tests for the web-based (browser-open) install backend."""

    def test_is_installed_always_false(self):
        """is_installed() always returns False — web installs cannot be verified."""
        from personal_os_setup.tasks.managers.webinstall import WebInstallManager

        assert WebInstallManager().is_installed("https://example.com") is False

    def test_install_opens_browser(self):
        """install() should open the URL in the default browser and return ok=True."""
        from personal_os_setup.tasks.managers.webinstall import WebInstallManager

        with patch("webbrowser.open") as mock_open:
            result = WebInstallManager().install("https://example.com/download")
        assert result.ok is True
        mock_open.assert_called_once_with("https://example.com/download")

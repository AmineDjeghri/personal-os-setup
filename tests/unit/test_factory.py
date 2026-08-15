"""Unit tests for the OS-conditional system-action/package-manager factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from personal_os_setup.detect_os import PackageRef
from personal_os_setup.tasks.factory import get_package_manager, get_system_action_sections
from personal_os_setup.tasks.managers.base import InstallResult


def _section_names(system: str, distro: str, *, info: str | None = None) -> list[str]:
    return [name for name, _ in get_system_action_sections(system=system, distro=distro, info=info)]


def _actions_in(system: str, distro: str, section_name: str) -> list[str]:
    for name, actions in get_system_action_sections(system=system, distro=distro, info=None):
        if name == section_name:
            return [a.label for a in actions]
    raise AssertionError(f"section {section_name!r} not found")


def _action_in(system: str, distro: str, section_name: str, label: str, *, packages=None):
    for name, actions in get_system_action_sections(
        system=system, distro=distro, info=None, packages=packages
    ):
        if name == section_name:
            for action in actions:
                if action.label == label:
                    return action
    raise AssertionError(f"action {label!r} not found in section {section_name!r}")


class TestPackageManagerSections:
    """Only the primary manager(s) for each distro should get their own section."""

    def test_ubuntu_shows_only_apt(self):
        names = _section_names("linux", "ubuntu")
        assert names[0] == "apt"
        assert "snap" not in names
        assert "webinstall" not in names

    def test_darwin_shows_only_brew(self):
        names = _section_names("darwin", "darwin")
        assert names[0] == "brew"
        assert "cask" not in names

    def test_cachyos_merges_pacman_and_paru_into_one_section(self):
        names = _section_names("linux", "cachyos")
        assert names[0] == "cachyos"
        assert "pacman" not in names
        assert "paru" not in names

    def test_cachyos_section_has_manager_prefixed_labels(self):
        labels = _actions_in("linux", "cachyos", "cachyos")
        assert labels == [
            "pacman: update",
            "pacman: upgrade",
            "pacman: cleanup",
            "paru: update",
            "paru: upgrade",
            "paru: cleanup",
        ]

    def test_unsupported_distro_has_no_package_manager_section(self):
        names = _section_names("linux", "debian")
        assert "apt" not in names
        assert "pacman" not in names

    def test_package_manager_section_has_update_upgrade_cleanup(self):
        labels = _actions_in("darwin", "darwin", "brew")
        assert labels == ["update", "upgrade", "cleanup"]


class TestLinuxDarwinSections:
    """Start appears on every OS; zsh/chezmoi sections only appear on Linux and macOS."""

    def test_darwin_gets_start_and_dotfiles_sections(self):
        names = _section_names("darwin", "darwin")
        assert "🚀 Start" in names
        assert "Sync dotfiles" in names

    def test_windows_gets_start_but_no_dotfiles_sections(self):
        names = _section_names("windows", "windows")
        assert "🚀 Start" in names
        assert "Sync dotfiles" not in names

    def test_start_section_has_documentation_link(self):
        labels = _actions_in("darwin", "darwin", "🚀 Start")
        assert labels == [
            "open documentation site",
            "open apps configuration and shortcuts doc",
        ]


class TestZshPrereqPackages:
    """The "install zsh setup prerequisites" action is scoped to zsh, not all dotfiles."""

    def test_action_present_without_packages(self):
        action = _action_in("darwin", "darwin", "Sync dotfiles", "install zsh setup prerequisites")
        assert action.confirm is True
        assert "No zsh setup prerequisites" in action.confirm_message

    def test_confirm_message_lists_terminal_tools_packages(self):
        packages = [
            PackageRef(name="git", manager="apt", category="terminal_tools"),
            PackageRef(name="bat", manager="apt", category="terminal_tools"),
            PackageRef(name="docker-compose", manager="apt", category="Dev_tools"),
        ]
        action = _action_in(
            "linux",
            "ubuntu",
            "Sync dotfiles",
            "install zsh setup prerequisites",
            packages=packages,
        )
        assert "git" in action.confirm_message
        assert "bat" in action.confirm_message
        assert "docker-compose" not in action.confirm_message

    def test_category_match_is_case_insensitive(self):
        packages = [PackageRef(name="git", manager="brew", category="Terminal_Tools")]
        action = _action_in(
            "darwin",
            "darwin",
            "Sync dotfiles",
            "install zsh setup prerequisites",
            packages=packages,
        )
        assert "git" in action.confirm_message

    def test_run_installs_missing_and_skips_installed_packages(self):
        packages = [
            PackageRef(name="git", manager="apt", category="terminal_tools"),
            PackageRef(name="curl", manager="apt", category="terminal_tools"),
        ]
        action = _action_in(
            "linux",
            "ubuntu",
            "Sync dotfiles",
            "install zsh setup prerequisites",
            packages=packages,
        )

        fake_pm = type(
            "FakePM",
            (),
            {
                "is_installed": lambda self, name: name == "git",
                "install": lambda self, name: InstallResult(ok=True, summary=f"Installed {name}"),
            },
        )()

        with patch("personal_os_setup.tasks.factory.get_package_manager", return_value=fake_pm):
            result = action.run()

        assert result.ok is True
        assert "2/2" in result.summary
        assert "already installed" in result.details
        assert "Installed curl" in result.details

    def test_run_reports_failure_when_manager_missing(self):
        packages = [PackageRef(name="git", manager="apt", category="terminal_tools")]
        action = _action_in(
            "linux",
            "ubuntu",
            "Sync dotfiles",
            "install zsh setup prerequisites",
            packages=packages,
        )

        with patch("personal_os_setup.tasks.factory.get_package_manager", return_value=None):
            result = action.run()

        assert result.ok is False
        assert "0/1" in result.summary


class TestDotfilesTrackNewFile:
    """Whole-tree chezmoi buttons were replaced by a per-file selection list.

    The selection list now lives in the frontend (app.py); this section should only
    expose a 'track a new file' prompt action that runs chezmoi_add() on the given path.
    """

    def test_whole_tree_chezmoi_buttons_are_gone(self):
        labels = _actions_in("darwin", "darwin", "Sync dotfiles")
        assert "chezmoi: diff" not in labels
        assert "chezmoi: apply" not in labels
        assert "chezmoi: re-add" not in labels

    def test_track_a_new_file_action_is_prompted(self):
        action = _action_in("darwin", "darwin", "Sync dotfiles", "chezmoi: track a new file")
        assert action.run_with_prompt is not None
        assert action.prompt_label is not None
        assert action.confirm is False

    def test_track_a_new_file_calls_chezmoi_add_with_expanded_path(self):
        action = _action_in("darwin", "darwin", "Sync dotfiles", "chezmoi: track a new file")
        with patch("personal_os_setup.tasks.factory.chezmoi_add") as mock_add:
            mock_add.return_value = InstallResult(ok=True, summary="ok")
            action.run_with_prompt("~/.config/foo/config.toml")
        mock_add.assert_called_once_with(Path.home() / ".config/foo/config.toml")


class TestSystemSectionExtras:
    """Docker post-install lives in "system", gated by distro."""

    def test_ubuntu_and_cachyos_get_docker_action(self):
        docker_label = "docker: post-install (run without sudo)"
        assert docker_label in _actions_in("linux", "ubuntu", "system")
        assert docker_label in _actions_in("linux", "cachyos", "system")

    def test_darwin_has_no_system_section_and_windows_has_no_docker_action(self):
        assert "system" not in _section_names("darwin", "darwin")
        assert "docker: post-install (run without sudo)" not in _actions_in(
            "windows", "windows", "system"
        )


class TestNvidiaSection:
    """The single OS-specific "setup nvidia" action should match system/distro/WSL."""

    def test_windows_gets_windows_nvidia_action(self):
        labels = _actions_in("windows", "windows", "system")
        assert "setup nvidia (windows)" in labels

    def test_ubuntu_gets_ubuntu_nvidia_action(self):
        with patch("personal_os_setup.tasks.factory._is_wsl", return_value=False):
            labels = _actions_in("linux", "ubuntu", "system")
        assert "setup nvidia (ubuntu)" in labels

    def test_cachyos_gets_arch_nvidia_action(self):
        with patch("personal_os_setup.tasks.factory._is_wsl", return_value=False):
            labels = _actions_in("linux", "cachyos", "system")
        assert "setup nvidia (cachyos)" in labels

    def test_wsl_takes_priority_over_distro_specific_action(self):
        """Inside WSL, the WSL guidance action should win even on Ubuntu."""
        with patch("personal_os_setup.tasks.factory._is_wsl", return_value=True):
            labels = _actions_in("linux", "ubuntu", "system")
        assert "setup nvidia (wsl)" in labels
        assert "setup nvidia (ubuntu)" not in labels

    def test_unimplemented_distro_gets_fallback_action(self):
        with patch("personal_os_setup.tasks.factory._is_wsl", return_value=False):
            labels = _actions_in("linux", "debian", "system")
        assert "setup nvidia (debian)" in labels

    def test_darwin_has_no_nvidia_section(self):
        assert "system" not in _section_names("darwin", "darwin")


class TestWindowsOnlySections:
    """WSL/Windows-utility sections should only appear on Windows."""

    def test_windows_gets_wsl_sections(self):
        names = _section_names("windows", "windows")
        assert "WSL" in names
        assert "Advanced WSL" in names
        assert "Windows utilities" in names

    def test_linux_and_darwin_have_no_wsl_sections(self):
        for system, distro in [("linux", "ubuntu"), ("darwin", "darwin")]:
            names = _section_names(system, distro)
            assert "WSL" not in names
            assert "Advanced WSL" not in names
            assert "Windows utilities" not in names


class TestGetPackageManager:
    """`get_package_manager` should resolve known (distro, manager) pairs and reject unknown ones."""

    def test_known_pairs_resolve(self):
        assert get_package_manager(distro="ubuntu", manager="apt") is not None
        assert get_package_manager(distro="darwin", manager="brew") is not None
        assert get_package_manager(distro="windows", manager="winget") is not None
        assert get_package_manager(distro="cachyos", manager="paru") is not None

    def test_unknown_distro_returns_none(self):
        assert get_package_manager(distro="plan9", manager="apt") is None

    def test_unknown_manager_for_known_distro_returns_none(self):
        assert get_package_manager(distro="ubuntu", manager="brew") is None

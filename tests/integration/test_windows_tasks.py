"""Integration tests for Windows task functions.

These tests run on a real Windows system (GitHub Actions runner or local).
They are deliberately read-only: no installs, no reboots, no WSL/system state changes,
because the hosted Windows runner has no winget and no WSL distro to play with.

Run with: make test-integration  (or: uv run pytest tests/integration -v)
"""

from __future__ import annotations

import shutil

import pytest

from personal_os_setup.detect_os import detect_os

# Skip the entire module unless running on Windows.
pytestmark = pytest.mark.skipif(
    detect_os().family != "windows", reason="Integration tests require a Windows system"
)

_NO_WINGET = shutil.which("winget") is None


class TestWingetManager:
    """Integration tests for WindowsWingetManager on a real Windows system."""

    def test_is_installed_nonexistent_package(self):
        """A clearly fake package id should not be reported as installed (winget or not)."""
        from personal_os_setup.tasks.managers.windows_winget import WindowsWingetManager

        assert WindowsWingetManager().is_installed("This.Package.Does.Not.Exist.Xyz") is False

    def test_cleanup_is_noop(self):
        """The winget backend has no cleanup step; it must succeed without touching anything."""
        from personal_os_setup.tasks.managers.windows_winget import WindowsWingetManager

        assert WindowsWingetManager().cleanup().ok is True

    @pytest.mark.skipif(not _NO_WINGET, reason="only meaningful when winget is absent")
    def test_missing_winget_is_reported_not_raised(self):
        """Without winget (e.g. Windows Server runners) every action fails gracefully."""
        from personal_os_setup.tasks.managers.windows_winget import WindowsWingetManager

        mgr = WindowsWingetManager()
        install = mgr.install("Some.Package")
        assert install.ok is False
        assert "winget" in install.summary
        assert mgr.update().ok is False
        assert mgr.upgrade().ok is False


class TestMsStoreManager:
    """Integration tests for WindowsMSStoreManager on a real Windows system."""

    def test_is_installed_nonexistent_package(self):
        """A clearly fake product id should not be reported as installed (winget or not)."""
        from personal_os_setup.tasks.managers.windows_msstore import WindowsMSStoreManager

        assert WindowsMSStoreManager().is_installed("9ZZZZZZZZZZZ") is False

    def test_cleanup_is_noop(self):
        """The MS Store backend has no cleanup step; it must succeed without touching anything."""
        from personal_os_setup.tasks.managers.windows_msstore import WindowsMSStoreManager

        assert WindowsMSStoreManager().cleanup().ok is True

    @pytest.mark.skipif(not _NO_WINGET, reason="only meaningful when winget is absent")
    def test_missing_winget_is_reported_not_raised(self):
        """Without winget the MS Store backend fails gracefully instead of raising."""
        from personal_os_setup.tasks.managers.windows_msstore import WindowsMSStoreManager

        mgr = WindowsMSStoreManager()
        install = mgr.install("9ZZZZZZZZZZZ")
        assert install.ok is False
        assert "winget" in install.summary
        assert mgr.update().ok is False
        assert mgr.upgrade().ok is False


class TestDetectOS:
    """Integration tests for OS detection helpers on Windows."""

    def test_detect_os_returns_windows(self):
        """detect_os() should return family='windows', distro='windows' on Windows."""
        info = detect_os()
        assert info.family == "windows"
        assert info.distro == "windows"

    def test_is_wsl_false_on_native_windows(self):
        """_is_wsl() inspects /proc, which does not exist on native Windows."""
        from personal_os_setup.detect_os import _is_wsl

        assert _is_wsl() is False


class TestWslHelpers:
    """Read-only WSL helpers; the runner has the wsl.exe stub but no installed distro."""

    @pytest.mark.skipif(shutil.which("wsl") is None, reason="wsl.exe not available")
    def test_wsl_version_returns_task_result(self):
        """wsl_version() must return a TaskResult (ok or not) without crashing."""
        from personal_os_setup.tasks.system.windows_wsl_tasks import wsl_version
        from personal_os_setup.tasks.task import TaskResult

        result = wsl_version()
        assert isinstance(result, TaskResult)
        assert isinstance(result.ok, bool)

    @pytest.mark.skipif(shutil.which("wsl") is None, reason="wsl.exe not available")
    def test_wsl_list_verbose_returns_task_result(self):
        """wsl_list_verbose() must return a TaskResult even with no distro installed."""
        from personal_os_setup.tasks.system.windows_wsl_tasks import wsl_list_verbose
        from personal_os_setup.tasks.task import TaskResult

        result = wsl_list_verbose()
        assert isinstance(result, TaskResult)
        assert isinstance(result.ok, bool)


class TestFactoryAndPackages:
    """Wiring tests: factory + packages.yaml resolve correctly on Windows."""

    def test_factory_resolves_windows_managers(self):
        """get_package_manager() should hand back the winget/msstore backends."""
        from personal_os_setup.tasks.factory import get_package_manager

        winget = get_package_manager(distro="windows", manager="winget")
        msstore = get_package_manager(distro="windows", manager="msstore")
        assert winget is not None and winget.name == "winget"
        assert msstore is not None and msstore.name == "msstore"

    def test_system_action_sections_build_without_running_anything(self):
        """Building the Windows sections only constructs actions; it must not execute them."""
        from personal_os_setup.tasks.factory import get_system_action_sections

        sections = get_system_action_sections(system="windows", distro="windows", info=None)
        names = [name for name, _ in sections]
        assert any("WSL" in n for n in names)
        assert all(actions for _, actions in sections)

    def test_build_packages_for_os(self):
        """build_packages_for_os() should detect Windows and return winget packages."""
        from personal_os_setup.detect_os import build_packages_for_os

        system, distro, info, packages = build_packages_for_os()
        assert system == "windows"
        assert distro == "windows"
        assert any(p.manager == "winget" for p in packages)

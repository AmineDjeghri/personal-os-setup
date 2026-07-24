"""Integration tests for CachyOS task functions.

These tests run on a real CachyOS system.

Run with: make test-integration
"""

from __future__ import annotations

import pytest

from personal_os_setup.detect_os import detect_os

# Skip the entire module unless running on CachyOS specifically.
pytestmark = pytest.mark.skipif(
    detect_os().distro != "cachyos", reason="Integration tests require a CachyOS system"
)


class TestArchPacmanManager:
    """Integration tests for ArchPacmanManager on a real CachyOS system."""

    def test_is_installed_known_package(self):
        """Pacman should report 'pacman' itself as installed on any CachyOS runner."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        assert ArchPacmanManager().is_installed("pacman") is True

    def test_is_installed_nonexistent_package(self):
        """Pacman should report a clearly fake package as not installed."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        assert ArchPacmanManager().is_installed("this-package-does-not-exist-xyz") is False

    def test_update_succeeds(self):
        """Pacman -Sy should succeed given passwordless sudo."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        result = ArchPacmanManager().update()
        assert result.ok is True, f"pacman update failed: {result.summary}\n{result.details}"

    def test_cleanup_succeeds(self):
        """Pacman -Sc (with --noconfirm) should succeed given passwordless sudo."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        result = ArchPacmanManager().cleanup()
        assert result.ok is True, f"pacman cleanup failed: {result.summary}\n{result.details}"

    def test_install_and_check_curl(self):
        """Installing curl via pacman should succeed and be detectable via is_installed()."""
        from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager

        mgr = ArchPacmanManager()
        result = mgr.install("curl")
        assert result.ok is True, f"pacman install curl failed: {result.summary}\n{result.details}"
        assert mgr.is_installed("curl") is True


class TestArchParuManager:
    """Integration tests for ArchParuManager on a real CachyOS system."""

    def test_is_installed_nonexistent_package(self):
        """Pacman's local DB should report a clearly fake AUR package as not installed."""
        from personal_os_setup.tasks.managers.arch_paru import ArchParuManager

        assert ArchParuManager().is_installed("this-package-does-not-exist-xyz") is False

    def test_paru_is_bootstrapped_or_bootstrappable(self):
        """CachyOS ships paru as a repo package, so it must be on PATH or pacman-installable."""
        import shutil

        assert shutil.which("paru") is not None or shutil.which("pacman") is not None


class TestDetectOS:
    """Integration tests for OS detection helpers on CachyOS."""

    def test_detect_os_returns_linux_cachyos(self):
        """detect_os() should return family='linux', distro='cachyos' on a CachyOS box."""
        from personal_os_setup.detect_os import detect_os

        info = detect_os()
        assert info.family == "linux"
        assert info.distro == "cachyos"

    def test_is_wsl_false_on_native_runner(self):
        """A native CachyOS install is not WSL."""
        from personal_os_setup.detect_os import _is_wsl

        assert _is_wsl() is False


class TestPackagesConfig:
    """Integration tests for packages.yaml loading on CachyOS."""

    def _cachyos_packages(self):
        from importlib import resources

        import yaml

        from personal_os_setup.detect_os import PackageCatalog, iter_packages

        pkg = resources.files("personal_os_setup")
        data = yaml.safe_load((pkg / "config" / "packages.yaml").read_text(encoding="utf-8")) or {}
        catalog = PackageCatalog(data=data)
        return list(iter_packages(catalog.for_distro("cachyos")))

    def test_cachyos_packages_load(self):
        """iter_packages() should yield at least one CachyOS package without error."""
        assert len(self._cachyos_packages()) > 0

    def test_cachyos_pacman_packages_present(self):
        """At least one pacman package should be defined for CachyOS."""
        pacman_packages = [p for p in self._cachyos_packages() if p.manager == "pacman"]
        assert len(pacman_packages) > 0

    def test_build_packages_for_os(self):
        """build_packages_for_os() should detect CachyOS and return a non-empty package list."""
        from personal_os_setup.detect_os import build_packages_for_os

        system, distro, info, packages = build_packages_for_os()
        assert system == "linux"
        assert distro == "cachyos"
        assert len(packages) > 0

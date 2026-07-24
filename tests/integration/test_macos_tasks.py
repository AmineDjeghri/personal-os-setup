"""Integration tests for macOS task functions.

These tests run on a real macOS system (GitHub Actions runner or local).

Run with: make test-integration
"""

from __future__ import annotations

import platform
import shutil

import pytest

# Skip the entire module if not running on macOS
pytestmark = pytest.mark.skipif(
    platform.system().lower() != "darwin",
    reason="Integration tests require a macOS system",
)


class TestBrewManager:
    """Integration tests for DarwinBrewManager on a real macOS system."""

    def test_brew_is_on_path(self):
        """Brew must be available on PATH on any standard macOS runner."""
        assert shutil.which("brew") is not None, "Homebrew not found — is it installed?"

    def test_is_installed_nonexistent_formula(self):
        """A clearly fake formula should not be reported as installed."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        assert DarwinBrewManager().is_installed("this-formula-does-not-exist-xyz") is False

    def test_install_and_check_formula(self):
        """Installing wget should succeed and be detectable via is_installed()."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        mgr = DarwinBrewManager()
        result = mgr.install("wget")
        assert result.ok is True, f"brew install wget failed: {result.summary}\n{result.details}"
        assert mgr.is_installed("wget") is True

    def test_cleanup_succeeds(self):
        """Brew cleanup should succeed."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager

        result = DarwinBrewManager().cleanup()
        assert result.ok is True, f"brew cleanup failed: {result.summary}\n{result.details}"


class TestBrewCaskManager:
    """Integration tests for DarwinBrewCaskManager."""

    def test_is_installed_nonexistent_cask(self):
        """A clearly fake cask should not be reported as installed."""
        from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewCaskManager

        assert DarwinBrewCaskManager().is_installed("this-cask-does-not-exist-xyz") is False


class TestDetectOS:
    """Integration tests for OS detection helpers on macOS."""

    def test_detect_os_returns_darwin(self):
        """detect_os() should return family='darwin', distro='darwin' on macOS."""
        from personal_os_setup.detect_os import detect_os

        info = detect_os()
        assert info.family == "darwin"
        assert info.distro == "darwin"

    def test_is_wsl_false_on_macos(self):
        """_is_wsl() must always be False on macOS."""
        from personal_os_setup.detect_os import _is_wsl

        assert _is_wsl() is False


class TestPackagesConfig:
    """Integration tests for packages.yaml loading on macOS."""

    def _darwin_packages(self):
        from personal_os_setup.detect_os import PackageCatalog, iter_packages
        from importlib import resources
        import yaml

        pkg = resources.files("personal_os_setup")
        data = yaml.safe_load((pkg / "config" / "packages.yaml").read_text(encoding="utf-8")) or {}
        catalog = PackageCatalog(data=data)
        return list(iter_packages(catalog.for_distro("darwin")))

    def test_darwin_brew_packages_present(self):
        """At least one brew package should be defined for macOS."""
        brew_packages = [p for p in self._darwin_packages() if p.manager == "brew"]
        assert len(brew_packages) > 0

    def test_darwin_cask_packages_present(self):
        """At least one cask package should be defined for macOS."""
        cask_packages = [p for p in self._darwin_packages() if p.manager == "cask"]
        assert len(cask_packages) > 0

    def test_build_packages_for_os(self):
        """build_packages_for_os() should detect darwin and return a non-empty package list."""
        from personal_os_setup.detect_os import build_packages_for_os

        system, distro, info, packages = build_packages_for_os()
        assert system == "darwin"
        assert distro == "darwin"
        assert len(packages) > 0

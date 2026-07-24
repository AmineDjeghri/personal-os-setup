from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers._shared import (
    command_details,
    missing_executable_install_result,
    missing_executable_task_result,
)
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult

_BREW_HINT = "Install Homebrew from https://brew.sh and ensure `brew` is available on your PATH."


def _ensure_brew() -> str | None:
    """Return the path to the `brew` executable if available.

    This allows callers to provide a clear, actionable error when Homebrew
    is not installed on macOS.
    """
    return shutil.which("brew")


def _run_brew_subcommand(args: list[str], *, action: str) -> TaskResult:
    """Run a `brew` maintenance subcommand, reporting failures uniformly."""
    brew = _ensure_brew()
    if brew is None:
        return missing_executable_task_result(action, "brew", _BREW_HINT)

    res = run([brew, *args], check=False)
    if res.returncode == 0:
        return TaskResult(ok=True, summary=f"{action}: done")
    return TaskResult(ok=False, summary=f"{action}: failed", details=command_details(res))


class DarwinBrewManager:
    """Homebrew formula manager for macOS (`brew`)."""

    name = "brew"

    def is_installed(self, package: str) -> bool:
        brew = _ensure_brew()
        if brew is None:
            # If brew itself is missing, we cannot reliably report per-package
            # status; treat as not installed.
            return False

        # `brew list --formula <name>` exits 0 if installed, non-zero otherwise.
        res = run([brew, "list", "--formula", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        brew = _ensure_brew()
        if brew is None:
            return missing_executable_install_result("brew", _BREW_HINT)

        logger.info(f"Installing {package} via {self.name}...")
        res = run([brew, "install", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")
        return InstallResult(
            ok=False, summary=f"Failed to install {package}", details=command_details(res)
        )

    def update(self) -> TaskResult:
        return _run_brew_subcommand(["update"], action="brew update")

    def upgrade(self) -> TaskResult:
        return _run_brew_subcommand(["upgrade"], action="brew upgrade")

    def cleanup(self) -> TaskResult:
        return _run_brew_subcommand(["cleanup"], action="brew cleanup")


class DarwinBrewCaskManager:
    """Homebrew cask manager for macOS (`brew install --cask`)."""

    name = "cask"

    def is_installed(self, package: str) -> bool:
        brew = _ensure_brew()
        if brew is None:
            return False

        # `brew list --cask <name>` exits 0 if the cask is installed.
        res = run([brew, "list", "--cask", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        brew = _ensure_brew()
        if brew is None:
            return missing_executable_install_result("brew", _BREW_HINT)

        logger.info(f"Installing cask {package} via brew...")
        res = run([brew, "install", "--cask", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed cask {package}")
        return InstallResult(
            ok=False, summary=f"Failed to install cask {package}", details=command_details(res)
        )

    def update(self) -> TaskResult:
        # There is no dedicated "cask-only" update; reuse `brew update`.
        return _run_brew_subcommand(["update"], action="brew update (casks)")

    def upgrade(self) -> TaskResult:
        return _run_brew_subcommand(["upgrade", "--cask"], action="brew upgrade --cask")

    def cleanup(self) -> TaskResult:
        # `brew cleanup` also covers casks.
        return _run_brew_subcommand(["cleanup"], action="brew cleanup (casks)")

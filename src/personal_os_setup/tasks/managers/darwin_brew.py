from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult


def _ensure_brew() -> str | None:
    """Return the path to the `brew` executable if available.

    This allows callers to provide a clear, actionable error when Homebrew
    is not installed on macOS.
    """
    return shutil.which("brew")


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
            return InstallResult(
                ok=False,
                summary="brew not found on PATH",
                details=(
                    "Homebrew is not installed. Install it from https://brew.sh "
                    "and ensure `brew` is available on your PATH."
                ),
            )

        logger.info(f"Installing {package} via {self.name}...")
        res = run([brew, "install", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")

        details = (res.stdout + "\n" + res.stderr).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew update: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "update"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew update: done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew update: failed", details=details)

    def upgrade(self) -> TaskResult:
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew upgrade: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "upgrade"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew upgrade: done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew upgrade: failed", details=details)

    def cleanup(self) -> TaskResult:
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew cleanup: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "cleanup"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew cleanup: done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew cleanup: failed", details=details)


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
            return InstallResult(
                ok=False,
                summary="brew not found on PATH",
                details=(
                    "Homebrew is not installed. Install it from https://brew.sh "
                    "and ensure `brew` is available on your PATH."
                ),
            )

        logger.info(f"Installing cask {package} via brew...")
        res = run([brew, "install", "--cask", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed cask {package}")

        details = (res.stdout + "\n" + res.stderr).strip()
        return InstallResult(ok=False, summary=f"Failed to install cask {package}", details=details)

    def update(self) -> TaskResult:
        # There is no dedicated "cask-only" update; reuse `brew update`.
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew cask update: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "update"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew update (casks): done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew update (casks): failed", details=details)

    def upgrade(self) -> TaskResult:
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew cask upgrade: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "upgrade", "--cask"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew upgrade --cask: done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew upgrade --cask: failed", details=details)

    def cleanup(self) -> TaskResult:
        # `brew cleanup` also covers casks.
        brew = _ensure_brew()
        if brew is None:
            return TaskResult(
                ok=False,
                summary="brew cask cleanup: failed",
                details=(
                    "brew not found on PATH. Install Homebrew from https://brew.sh and try again."
                ),
            )

        res = run([brew, "cleanup"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="brew cleanup (casks): done")

        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="brew cleanup (casks): failed", details=details)

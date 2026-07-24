"""CachyOS `pacman` package manager backend.

This backend covers official-repository packages only. AUR packages need an AUR
helper -- see `arch_paru.ArchParuManager`.

Notes:
    - `pacman` needs root for anything that writes, so install/update/upgrade/cleanup
      go through `sudo -n`. Read-only queries (`-Q`) do not.
"""

from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers._shared import (
    format_failed_command,
    missing_executable_install_result,
    missing_executable_task_result,
    sudo_required_install_result,
    sudo_required_task_result,
)
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok
from personal_os_setup.tasks.task import TaskResult

_PACMAN_HINT = "Ensure `pacman` is installed."


class ArchPacmanManager:
    """`pacman` manager for CachyOS."""

    name = "pacman"

    def _pacman(self) -> str | None:
        """Return the path to the `pacman` binary, or `None` if it's not on PATH."""
        return shutil.which("pacman")

    def _run_privileged(self, args: list[str], *, action: str) -> TaskResult:
        """Run a root-requiring pacman subcommand, reporting failures uniformly."""
        pacman = self._pacman()
        if pacman is None:
            return missing_executable_task_result(action, "pacman", _PACMAN_HINT)
        if not sudo_non_interactive_ok():
            return sudo_required_task_result(f"pacman {action}")

        res = run(["sudo", "-n", pacman, *args, "--noconfirm"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary=f"pacman {action}: done")
        return TaskResult(
            ok=False, summary=f"pacman {action}: failed", details=format_failed_command(res)
        )

    def is_installed(self, package: str) -> bool:
        """Return whether the given package is already installed, via `pacman -Q`."""
        pacman = self._pacman()
        if pacman is None:
            return False
        res = run([pacman, "-Q", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        """Install a package via `pacman -S`."""
        pacman = self._pacman()
        if pacman is None:
            return missing_executable_install_result("pacman", _PACMAN_HINT)
        if not sudo_non_interactive_ok():
            return sudo_required_install_result(package)

        logger.info(f"Installing {package} via pacman...")
        res = run(
            ["sudo", "-n", pacman, "-S", "--needed", "--noconfirm", package],
            check=False,
        )
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"{package}: installed (pacman)")
        return InstallResult(
            ok=False,
            summary=f"{package}: install failed (pacman)",
            details=format_failed_command(res),
        )

    def update(self) -> TaskResult:
        """Refresh the package database via `pacman -Sy`."""
        return self._run_privileged(["-Sy"], action="sync")

    def upgrade(self) -> TaskResult:
        """Upgrade all official-repo packages via `pacman -Syu`."""
        return self._run_privileged(["-Syu"], action="-Syu")

    def cleanup(self) -> TaskResult:
        """Remove unused packages from the cache via `pacman -Sc`."""
        return self._run_privileged(["-Sc"], action="cache cleanup")

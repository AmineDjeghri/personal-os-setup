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
from personal_os_setup.tasks.commands import join_argv, run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok, sudo_required_details
from personal_os_setup.tasks.task import TaskResult


def _format_failed(argv: list[str], stdout: str, stderr: str) -> str:
    """Render a failed command's argv and output as human-readable details text."""
    details = [f"$ {join_argv(argv)}"]
    if stdout.strip():
        details.append(stdout.strip())
    if stderr.strip():
        details.append(stderr.strip())
    return "\n".join(details).strip()


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
            return TaskResult(
                ok=False,
                summary=f"pacman {action}: failed",
                details="`pacman` not found on PATH.",
            )
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary=f"pacman {action}: failed (sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )

        res = run(["sudo", "-n", pacman, *args, "--noconfirm"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary=f"pacman {action}: done")
        return TaskResult(
            ok=False,
            summary=f"pacman {action}: failed",
            details=_format_failed(res.argv, res.stdout, res.stderr),
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
            return InstallResult(
                ok=False,
                summary="pacman not found on PATH",
                details="Ensure `pacman` is installed.",
            )
        if not sudo_non_interactive_ok():
            return InstallResult(
                ok=False,
                summary=f"{package}: install failed (sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )

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
            details=_format_failed(res.argv, res.stdout, res.stderr),
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

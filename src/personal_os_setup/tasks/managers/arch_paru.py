"""CachyOS `paru` package manager backend.

`paru` is an AUR helper covering both official repositories and the AUR.

Notes:
    - `paru` calls `sudo` itself when it needs root, so commands are not prefixed
      with `sudo -n` here. It still needs a usable sudo credential cache.
"""

from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers._shared import (
    format_failed_command,
    sudo_required_task_result,
)
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok
from personal_os_setup.tasks.task import TaskResult


class ArchParuManager:
    """`paru` AUR helper for CachyOS."""

    name = "paru"

    def _paru(self) -> str | None:
        """Return the path to the `paru` binary, or `None` if it's not on PATH."""
        return shutil.which("paru")

    def _ensure_paru(self) -> TaskResult:
        """Install `paru` via pacman if it's missing."""
        if self._paru() is not None:
            return TaskResult(ok=True, summary="paru: found")

        pacman = shutil.which("pacman")
        if pacman is None:
            return TaskResult(
                ok=False,
                summary="paru: missing (pacman not found)",
                details="`pacman` not found on PATH.",
            )
        if not sudo_non_interactive_ok():
            return sudo_required_task_result("paru bootstrap")

        res = run(["sudo", "-n", pacman, "-S", "--needed", "--noconfirm", "paru"], check=False)
        if res.returncode != 0:
            return TaskResult(
                ok=False,
                summary="paru: bootstrap failed",
                details=format_failed_command(res),
            )

        if self._paru() is None:
            return TaskResult(
                ok=False,
                summary="paru: installed but not found on PATH",
                details="`paru` was installed but is still not found on PATH. Restart your shell and try again.",
            )
        return TaskResult(ok=True, summary="paru: installed")

    def _run(self, args: list[str], *, action: str) -> TaskResult:
        """Run a paru subcommand, bootstrapping paru first and reporting failures uniformly."""
        ensure = self._ensure_paru()
        if not ensure.ok:
            return TaskResult(ok=False, summary=f"paru {action}: failed", details=ensure.details)

        paru = self._paru()
        res = run([paru, *args, "--noconfirm"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary=f"paru {action}: done")
        return TaskResult(
            ok=False, summary=f"paru {action}: failed", details=format_failed_command(res)
        )

    def is_installed(self, package: str) -> bool:
        """Return whether the given package is already installed."""
        pacman = shutil.which("pacman")
        if pacman is None:
            return False
        res = run([pacman, "-Q", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        """Install a package via paru, bootstrapping paru first if needed."""
        ensure = self._ensure_paru()
        if not ensure.ok:
            return InstallResult(
                ok=False,
                summary=f"{package}: install failed (paru missing)",
                details=ensure.details,
            )

        paru = self._paru()
        logger.info(f"Installing {package} via paru...")
        res = run([paru, "-S", "--needed", "--noconfirm", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"{package}: installed (paru)")
        return InstallResult(
            ok=False,
            summary=f"{package}: install failed (paru)",
            details=format_failed_command(res),
        )

    def update(self) -> TaskResult:
        """Refresh the package database via `paru -Sy`."""
        return self._run(["-Sy"], action="sync")

    def upgrade(self) -> TaskResult:
        """Upgrade all packages (repo and AUR) via `paru -Syu`."""
        return self._run(["-Syu"], action="-Syu")

    def cleanup(self) -> TaskResult:
        """Remove unused packages from the cache via `paru -Sc`."""
        return self._run(["-Sc"], action="cache cleanup")

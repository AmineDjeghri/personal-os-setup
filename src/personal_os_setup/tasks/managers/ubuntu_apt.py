"""Ubuntu `apt` installer backend.

This installer wraps `apt-get` to provide a simple, uniform interface for the
setup application.

Notes:
    - Commands are executed via `personal_os_setup.commands.run`.
    - Logging goes through `personal_os_setup.logger`.
    - `install()` currently runs `apt-get update` before installing each
      package. This is safe but can be slow; batching may be added later.
"""

from __future__ import annotations

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run

from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok, sudo_required_details
from personal_os_setup.tasks.task import TaskResult


class UbuntuAptManager:
    """Ubuntu `apt-get` package manager backend.

    This backend provides both package installation and system maintenance
    operations.
    """

    name = "apt"

    def is_installed(self, package: str) -> bool:
        """Return whether the given package is already installed."""
        res = run(["dpkg", "-s", package], check=False)
        if res.returncode != 0:
            return False

        # `dpkg -s` can still exit 0 when a package is removed but config files remain
        # (e.g. `Status: deinstall ok config-files`). Only treat `install ok installed`
        # as installed.
        for line in res.stdout.splitlines():
            if not line.startswith("Status:"):
                continue
            status = line.removeprefix("Status:").strip().lower()
            return status == "install ok installed"

        # If we can't find the status line, be conservative and assume it's not installed.
        return False

    def install(self, package: str) -> InstallResult:
        """Install a package using `apt-get`."""
        if not sudo_non_interactive_ok():
            return InstallResult(
                ok=False,
                summary=f"Failed to install {package} (sudo password required). Run an interactive command first to cache your sudo credentials.)",
                details=sudo_required_details(),
            )
        logger.info(f"Installing {package} via {self.name}...")
        update_res = run(["sudo", "-n", "apt-get", "update"], check=False)
        install_res = run(["sudo", "-n", "apt-get", "install", "-y", package], check=False)
        if update_res.returncode == 0 and install_res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")

        details = (
            (update_res.stdout + "\n" + update_res.stderr).strip()
            + "\n"
            + (install_res.stdout + "\n" + install_res.stderr).strip()
        ).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="apt update: sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )
        res = run(["sudo", "-n", "apt-get", "update"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="apt update: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="apt update: failed", details=details)

    def upgrade(self) -> TaskResult:
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="apt upgrade: sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )
        res = run(["sudo", "-n", "apt-get", "upgrade", "-y"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="apt upgrade: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="apt upgrade: failed", details=details)

    def cleanup(self) -> TaskResult:
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="apt cleanup: sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )
        res = run(["sudo", "-n", "apt-get", "autoremove", "-y"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="apt cleanup (autoremove): done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="apt cleanup (autoremove): failed", details=details)

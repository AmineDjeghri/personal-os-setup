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
from personal_os_setup.tasks.managers._shared import (
    command_details,
    sudo_required_install_result,
    sudo_required_task_result,
)
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok
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
            return sudo_required_install_result(package)

        logger.info(f"Installing {package} via {self.name}...")
        update_res = run(["sudo", "-n", "apt-get", "update"], check=False)
        install_res = run(["sudo", "-n", "apt-get", "install", "-y", package], check=False)
        if update_res.returncode == 0 and install_res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")

        details = (command_details(update_res) + "\n" + command_details(install_res)).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        return self._run_apt_subcommand(["apt-get", "update"], action="apt update")

    def upgrade(self) -> TaskResult:
        return self._run_apt_subcommand(["apt-get", "upgrade", "-y"], action="apt upgrade")

    def cleanup(self) -> TaskResult:
        return self._run_apt_subcommand(
            ["apt-get", "autoremove", "-y"], action="apt cleanup (autoremove)"
        )

    def _run_apt_subcommand(self, argv: list[str], *, action: str) -> TaskResult:
        """Run an `apt-get` maintenance subcommand under `sudo -n`, reporting failures uniformly."""
        if not sudo_non_interactive_ok():
            return sudo_required_task_result(action)

        res = run(["sudo", "-n", *argv], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary=f"{action}: done")
        return TaskResult(ok=False, summary=f"{action}: failed", details=command_details(res))

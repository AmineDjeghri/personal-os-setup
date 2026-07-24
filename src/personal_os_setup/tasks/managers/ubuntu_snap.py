from __future__ import annotations

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok, sudo_required_details
from personal_os_setup.tasks.task import TaskResult


class UbuntuSnapManager:
    name = "snap"

    def is_installed(self, package: str) -> bool:
        res = run(["snap", "list", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        logger.info(f"Installing {package} via {self.name}...")
        if not sudo_non_interactive_ok():
            return InstallResult(
                ok=False,
                summary=f"Failed to install {package} (sudo password required). Run an interactive command first to cache your sudo credentials.)",
                details=sudo_required_details(),
            )
        argv = ["sudo", "-n", "snap", "install", package]
        res = run(argv, check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")
        details = (res.stdout + "\n" + res.stderr).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="snap refresh: sudo password required). Run an interactive command first to cache your sudo credentials.",
                details=sudo_required_details(),
            )
        res = run(["sudo", "-n", "snap", "refresh"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="snap refresh: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="snap refresh: failed", details=details)

    def upgrade(self) -> TaskResult:
        return self.update()

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="snap cleanup: no-op")

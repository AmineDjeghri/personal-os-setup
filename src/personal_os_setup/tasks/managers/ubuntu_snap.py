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


class UbuntuSnapManager:
    name = "snap"

    def is_installed(self, package: str) -> bool:
        res = run(["snap", "list", package], check=False)
        return res.returncode == 0

    def install(self, package: str) -> InstallResult:
        if not sudo_non_interactive_ok():
            return sudo_required_install_result(package)

        logger.info(f"Installing {package} via {self.name}...")
        res = run(["sudo", "-n", "snap", "install", package], check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")
        return InstallResult(
            ok=False, summary=f"Failed to install {package}", details=command_details(res)
        )

    def update(self) -> TaskResult:
        if not sudo_non_interactive_ok():
            return sudo_required_task_result("snap refresh")

        res = run(["sudo", "-n", "snap", "refresh"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="snap refresh: done")
        return TaskResult(ok=False, summary="snap refresh: failed", details=command_details(res))

    def upgrade(self) -> TaskResult:
        return self.update()

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="snap cleanup: no-op")

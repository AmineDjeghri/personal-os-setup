from __future__ import annotations

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers._shared import (
    command_details,
    missing_executable_install_result,
    missing_executable_task_result,
    winget_list_shows_installed,
    winget_path,
)
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult

_WINGET_HINT = "Install App Installer (winget) from Microsoft Store, then restart the terminal."


class WindowsWingetManager:
    name = "winget"

    def is_installed(self, package: str) -> bool:
        winget = winget_path()
        return winget is not None and winget_list_shows_installed(winget, package)

    def install(self, package: str) -> InstallResult:
        winget = winget_path()
        if winget is None:
            return missing_executable_install_result("winget", _WINGET_HINT)

        logger.info(f"Installing {package} via {self.name}...")
        argv = [
            winget,
            "install",
            "-e",
            "--id",
            package,
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        res = run(argv, check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package}")
        return InstallResult(
            ok=False, summary=f"Failed to install {package}", details=command_details(res)
        )

    def update(self) -> TaskResult:
        return self._run_winget_subcommand(["source", "update"], action="winget source update")

    def upgrade(self) -> TaskResult:
        return self._run_winget_subcommand(
            ["upgrade", "--all", "--accept-package-agreements", "--accept-source-agreements"],
            action="winget upgrade --all",
        )

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="winget cleanup: no-op")

    def _run_winget_subcommand(self, args: list[str], *, action: str) -> TaskResult:
        winget = winget_path()
        if winget is None:
            return missing_executable_task_result(action, "winget", _WINGET_HINT)

        res = run([winget, *args], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary=f"{action}: done")
        return TaskResult(ok=False, summary=f"{action}: failed", details=command_details(res))

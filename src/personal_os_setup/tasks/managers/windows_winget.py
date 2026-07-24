from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult


class WindowsWingetManager:
    name = "winget"

    def _ensure_winget(self) -> str | None:
        return shutil.which("winget")

    def is_installed(self, package: str) -> bool:
        winget = self._ensure_winget()
        if winget is None:
            return False

        # `winget list` returns 0 even when the package is not found in some cases,
        # so we also check output content.
        res = run([winget, "list", "-e", "--id", package], check=False)
        text = (res.stdout + "\n" + res.stderr).lower()
        if "no installed package" in text or "no package found" in text:
            return False
        return package.lower() in text and res.returncode == 0

    def install(self, package: str) -> InstallResult:
        winget = self._ensure_winget()
        if winget is None:
            return InstallResult(
                ok=False,
                summary="winget not found on PATH",
                details="Install App Installer (winget) from Microsoft Store, then restart the terminal.",
            )

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
        details = (res.stdout + "\n" + res.stderr).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        winget = self._ensure_winget()
        if winget is None:
            return TaskResult(
                ok=False,
                summary="winget update: failed",
                details="winget not found on PATH (install App Installer).",
            )

        # `winget source update` refreshes metadata.
        res = run([winget, "source", "update"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="winget source update: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="winget source update: failed", details=details)

    def upgrade(self) -> TaskResult:
        winget = self._ensure_winget()
        if winget is None:
            return TaskResult(
                ok=False,
                summary="winget upgrade: failed",
                details="winget not found on PATH (install App Installer).",
            )

        argv = [
            winget,
            "upgrade",
            "--all",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        res = run(argv, check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="winget upgrade --all: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="winget upgrade --all: failed", details=details)

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="winget cleanup: no-op")

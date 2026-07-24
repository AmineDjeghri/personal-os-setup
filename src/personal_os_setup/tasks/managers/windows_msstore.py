from __future__ import annotations

import shutil

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult


class WindowsMSStoreManager:
    name = "msstore"

    def _ensure_winget(self) -> str | None:
        return shutil.which("winget")

    def is_installed(self, package: str) -> bool:
        winget = self._ensure_winget()
        if winget is None:
            return False

        # Check if package is installed from msstore source
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

        logger.info(f"Installing {package} via {self.name} (MS Store)...")
        argv = [
            winget,
            "install",
            package,
            "-s",
            "msstore",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        res = run(argv, check=False)
        if res.returncode == 0:
            return InstallResult(ok=True, summary=f"Installed {package} from MS Store")
        details = (res.stdout + "\n" + res.stderr).strip()
        return InstallResult(ok=False, summary=f"Failed to install {package}", details=details)

    def update(self) -> TaskResult:
        winget = self._ensure_winget()
        if winget is None:
            return TaskResult(
                ok=False,
                summary="msstore update: failed",
                details="winget not found on PATH (install App Installer).",
            )

        # `winget source update` refreshes metadata for all sources including msstore
        res = run([winget, "source", "update"], check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="msstore source update: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="msstore source update: failed", details=details)

    def upgrade(self) -> TaskResult:
        winget = self._ensure_winget()
        if winget is None:
            return TaskResult(
                ok=False,
                summary="msstore upgrade: failed",
                details="winget not found on PATH (install App Installer).",
            )

        # Upgrade all packages from msstore source
        argv = [
            winget,
            "upgrade",
            "--all",
            "-s",
            "msstore",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]
        res = run(argv, check=False)
        if res.returncode == 0:
            return TaskResult(ok=True, summary="msstore upgrade --all: done")
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(ok=False, summary="msstore upgrade --all: failed", details=details)

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="msstore cleanup: no-op")

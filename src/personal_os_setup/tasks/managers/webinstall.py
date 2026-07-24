from __future__ import annotations

import webbrowser

from personal_os_setup.settings import logger
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.task import TaskResult


class WebInstallManager:
    name = "webinstall"

    def is_installed(self, package: str) -> bool:
        # Web-based installers can't be checked for installation status
        # Always return False to allow re-opening the download link
        return False

    def install(self, package: str) -> InstallResult:
        """Opens the download URL in the default browser.

        Args:
            package: The URL to open in the browser
        """
        logger.info(f"Opening download page in browser: {package}")

        try:
            # Open the URL in the default browser
            webbrowser.open(package)
            return InstallResult(
                ok=True,
                summary=f"Opened download page in browser",
                details=f"URL: {package}\nPlease download and install manually from the opened page.",
            )
        except Exception as e:
            return InstallResult(
                ok=False, summary=f"Failed to open browser", details=f"Error: {str(e)}"
            )

    def update(self) -> TaskResult:
        return TaskResult(
            ok=True,
            summary="webinstall update: no-op",
            details="Web-based installers don't support automatic updates. Visit the download pages manually.",
        )

    def upgrade(self) -> TaskResult:
        return TaskResult(
            ok=True,
            summary="webinstall upgrade: no-op",
            details="Web-based installers don't support automatic upgrades. Visit the download pages manually.",
        )

    def cleanup(self) -> TaskResult:
        return TaskResult(ok=True, summary="webinstall cleanup: no-op")

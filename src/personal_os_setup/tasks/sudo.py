from __future__ import annotations

import platform
import shutil
import subprocess
import threading
import time

from personal_os_setup.settings import logger
from personal_os_setup.tasks.commands import run


def sudo_non_interactive_ok() -> bool:
    res = run(["sudo", "-n", "true"], check=False)
    return res.returncode == 0


def sudo_required_details() -> str:
    return (
        "This app runs non-interactively; it cannot prompt for your sudo password.\n"
        "Before starting the UI, run:\n"
        "  sudo -v\n"
        "Then re-run the app."
    )


def sudo_preauth() -> None:
    if platform.system().lower() != "linux":
        return
    if shutil.which("sudo") is None:
        return

    res = subprocess.run(["sudo", "-v"], check=False)
    if res.returncode != 0:
        logger.warning("sudo authentication failed; sudo-required actions may not work")
        return

    def _keepalive() -> None:
        while True:
            time.sleep(55)
            subprocess.run(
                ["sudo", "-n", "-v"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    threading.Thread(
        target=_keepalive, name="personal-os-setup-sudo-keepalive", daemon=True
    ).start()

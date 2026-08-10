from __future__ import annotations

import getpass
import os
import platform
import shutil
from pathlib import Path

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok, sudo_required_details
from personal_os_setup.tasks.task import TaskResult


def set_zsh_as_default_shell() -> TaskResult:
    system = platform.system().lower()
    if system not in {"linux", "darwin"}:
        return TaskResult(ok=False, summary=f"Unsupported OS for setting default shell: {system}")

    zsh_path = shutil.which("zsh")
    if zsh_path is None:
        return TaskResult(ok=False, summary="zsh not found on PATH")

    current_shell = os.environ.get("SHELL", "").strip()
    if current_shell and Path(current_shell).resolve() == Path(zsh_path).resolve():
        return TaskResult(ok=True, summary="zsh is already the default shell")

    chsh_path = shutil.which("chsh")
    if chsh_path is None:
        return TaskResult(
            ok=False,
            summary="chsh not found on PATH",
            details=f"Run manually: chsh -s {zsh_path}",
        )

    if system == "linux":
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="failed to set default shell to zsh (sudo password required). Run an interactive command first to cache your sudo credentials.)",
                details=sudo_required_details(),
            )

        user = getpass.getuser()
        res = run(["sudo", "-n", chsh_path, "-s", zsh_path, user], check=False)
    else:
        res = run([chsh_path, "-s", zsh_path], check=False)

    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(
            ok=True,
            summary="default shell set to zsh",
            details=f"{details}\nreboot your PC".strip() if details else "reboot your PC",
        )

    hint = f"Run manually: chsh -s {zsh_path}"
    if details:
        hint = hint + "\n" + details
    return TaskResult(ok=False, summary="failed to set default shell to zsh", details=hint)

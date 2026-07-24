from __future__ import annotations

import getpass
import os
import platform
import shutil
from pathlib import Path

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.sudo import sudo_non_interactive_ok, sudo_required_details
from personal_os_setup.tasks.task import TaskResult


def uninstall_oh_my_zsh_and_p10k() -> TaskResult:
    home = Path.home()
    candidates = [
        home / ".oh-my-zsh",
        home / ".p10k.zsh",
        home / ".zshrc",
        home / ".fzf.zsh",
        home / ".zsh_history",
    ]

    actions: list[str] = []
    try:
        for p in candidates:
            if not p.exists():
                actions.append(f"skip: {p} (not found)")
                continue

            if p.is_dir():
                shutil.rmtree(p)
                actions.append(f"removed dir: {p}")
            else:
                p.unlink()
                actions.append(f"removed file: {p}")
    except Exception as e:  # noqa: BLE001
        return TaskResult(ok=False, summary="uninstall zsh config: failed", details=str(e))

    return TaskResult(
        ok=True,
        summary="uninstalled: oh-my-zsh + p10k files",
        details="\n".join(actions).strip(),
    )


def uninstall_zsh_apt() -> TaskResult:
    system = platform.system().lower()
    if system != "linux":
        return TaskResult(ok=False, summary=f"Unsupported OS for uninstalling zsh: {system}")

    # First, attempt to switch the user's default shell back to bash.
    # This mirrors the shell script behavior and reduces the chance of locking the user out.
    res_shell = set_bash_as_default_shell()
    actions: list[str] = [res_shell.summary]
    if res_shell.details:
        actions.append(res_shell.details)

    apt_get = shutil.which("apt-get")
    if apt_get is None:
        return TaskResult(
            ok=False,
            summary="apt-get not found",
            details="This action currently supports Debian/Ubuntu-like systems.",
        )

    cmd = ["sudo", "-n", apt_get, "remove", "-y", "zsh"]
    res = run(cmd, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    actions.append(f"ran: {' '.join(cmd)}")
    if details:
        actions.append(details)

    if res.returncode == 0:
        actions.append(
            "Please restart your terminal to complete the uninstallation. "
            "If there is an error to access WSL, run in PowerShell: wsl ~ -e bash"
        )
        return TaskResult(
            ok=True, summary="zsh uninstalled (apt)", details="\n".join(actions).strip()
        )

    if "a password is required" in details.lower() or "sudo:" in details.lower():
        actions.append(
            "sudo needs a password. Run manually in a terminal:\nsudo apt-get remove -y zsh"
        )
        return TaskResult(
            ok=False,
            summary="zsh uninstall requires sudo password",
            details="\n".join(actions).strip(),
        )

    return TaskResult(
        ok=False, summary="failed to uninstall zsh (apt)", details="\n".join(actions).strip()
    )


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


def set_bash_as_default_shell() -> TaskResult:
    system = platform.system().lower()
    if system not in {"linux", "darwin"}:
        return TaskResult(ok=False, summary=f"Unsupported OS for setting default shell: {system}")

    bash_path = shutil.which("bash")
    if bash_path is None:
        return TaskResult(ok=False, summary="bash not found on PATH")

    current_shell = os.environ.get("SHELL", "").strip()
    if current_shell and Path(current_shell).resolve() == Path(bash_path).resolve():
        return TaskResult(ok=True, summary="bash is already the default shell")

    chsh_path = shutil.which("chsh")
    if chsh_path is None:
        return TaskResult(
            ok=False,
            summary="chsh not found on PATH",
            details=f"Run manually: chsh -s {bash_path}",
        )

    if system == "linux":
        if not sudo_non_interactive_ok():
            return TaskResult(
                ok=False,
                summary="failed to set default shell to bash (sudo password required). Run an interactive command first to cache your sudo credentials.)",
                details=sudo_required_details(),
            )

        user = getpass.getuser()
        res = run(["sudo", "-n", chsh_path, "-s", bash_path, user], check=False)
    else:
        res = run([chsh_path, "-s", bash_path], check=False)

    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        logout_hint = (
            "You must fully log out of your desktop/graphical session and log back in "
            "(or reboot) for this to take effect — opening a new terminal window is not "
            "enough, since the running session's environment (e.g. systemd --user) still "
            "has the old shell cached until you start a new login session."
        )
        return TaskResult(
            ok=True,
            summary="default shell set to bash",
            details=f"{details}\n{logout_hint}".strip() if details else logout_hint,
        )

    hint = f"Run manually: chsh -s {bash_path}"
    if details:
        hint = hint + "\n" + details
    return TaskResult(ok=False, summary="failed to set default shell to bash", details=hint)

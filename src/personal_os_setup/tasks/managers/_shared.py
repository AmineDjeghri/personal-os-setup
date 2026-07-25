"""Shared helpers to remove boilerplate duplicated across package manager backends.

Each manager still performs its own `shutil.which(...)` / `sudo_non_interactive_ok()`
checks locally rather than through these helpers, so that unit tests can keep
patching those functions at their own module path; these helpers only centralize
the repetitive *result construction* that follows such a check.
"""

from __future__ import annotations

import shutil

from personal_os_setup.tasks.commands import CommandResult, join_argv, run
from personal_os_setup.tasks.managers.base import InstallResult
from personal_os_setup.tasks.sudo import sudo_required_details
from personal_os_setup.tasks.task import TaskResult


def command_details(res: CommandResult) -> str:
    """Join a finished command's stdout/stderr into a single details blob."""
    return (res.stdout + "\n" + res.stderr).strip()


def format_failed_command(res: CommandResult) -> str:
    """Render a failed command's argv and output as human-readable details text."""
    lines = [f"$ {join_argv(res.argv)}"]
    if res.stdout.strip():
        lines.append(res.stdout.strip())
    if res.stderr.strip():
        lines.append(res.stderr.strip())
    return "\n".join(lines).strip()


def sudo_required_task_result(action: str) -> TaskResult:
    """Build the failure `TaskResult` for an action that needs passwordless sudo."""
    return TaskResult(
        ok=False,
        summary=f"{action}: failed (sudo password required — run an interactive sudo "
        f"command first to cache credentials)",
        details=sudo_required_details(),
    )


def sudo_required_install_result(package: str) -> InstallResult:
    """Build the failure `InstallResult` for an install that needs passwordless sudo."""
    return InstallResult(
        ok=False,
        summary=f"Failed to install {package} (sudo password required — run an "
        f"interactive sudo command first to cache credentials)",
        details=sudo_required_details(),
    )


def missing_executable_task_result(action: str, exe: str, hint: str = "") -> TaskResult:
    """Build the failure `TaskResult` for an action whose required executable is missing."""
    details = f"`{exe}` not found on PATH." + (f" {hint}" if hint else "")
    return TaskResult(ok=False, summary=f"{action}: failed", details=details)


def missing_executable_install_result(exe: str, hint: str = "") -> InstallResult:
    """Build the failure `InstallResult` for an install whose required executable is missing."""
    details = f"`{exe}` not found on PATH." + (f" {hint}" if hint else "")
    return InstallResult(ok=False, summary=f"{exe} not found on PATH", details=details)


def winget_path() -> str | None:
    """Return the path to `winget`, or `None` if it's not on PATH.

    Shared by the `winget` and `msstore` backends, both of which shell out to `winget`.
    """
    return shutil.which("winget")


def winget_list_shows_installed(winget: str, package: str) -> bool:
    """Return whether `winget list` output indicates `package` is installed."""
    res = run([winget, "list", "-e", "--id", package], check=False)
    text = (res.stdout + "\n" + res.stderr).lower()
    if "no installed package" in text or "no package found" in text:
        return False
    return package.lower() in text and res.returncode == 0

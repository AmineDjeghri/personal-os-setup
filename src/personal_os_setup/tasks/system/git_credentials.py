from __future__ import annotations

import shutil

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.task import TaskResult

_GH_HELPER_MARKER = "auth git-credential"


def setup_gh_git_credentials(hostname: str = "github.com") -> TaskResult:
    """Make plain `git` (and GUI clients like Obsidian Git) use `gh`'s token for HTTPS."""
    if shutil.which("gh") is None:
        return TaskResult(ok=False, summary="gh (GitHub CLI) not found on PATH; install it first")
    if shutil.which("git") is None:
        return TaskResult(ok=False, summary="git not found on PATH")

    status = run(["gh", "auth", "status", "--hostname", hostname], check=False)
    if status.returncode != 0:
        return TaskResult(
            ok=False,
            summary=f"not logged in to {hostname}",
            details=f"Run: gh auth login --hostname {hostname}",
        )

    current = run(
        ["git", "config", "--global", "--get-all", f"credential.https://{hostname}.helper"],
        check=False,
    )
    if _GH_HELPER_MARKER in current.stdout:
        return TaskResult(ok=True, summary=f"git already uses gh for https://{hostname}")

    res = run(["gh", "auth", "setup-git", "--hostname", hostname], check=False)
    if res.returncode != 0:
        details = (res.stdout + "\n" + res.stderr).strip()
        return TaskResult(
            ok=False,
            summary=f"failed to configure git credential helper for {hostname}",
            details=details or f"Run manually: gh auth setup-git --hostname {hostname}",
        )
    return TaskResult(ok=True, summary=f"git now uses gh for https://{hostname}")

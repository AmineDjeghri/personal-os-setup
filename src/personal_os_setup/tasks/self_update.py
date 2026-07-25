"""Best-effort self-update: `git pull` the installed checkout on every launch."""

from __future__ import annotations

import subprocess
from pathlib import Path

from personal_os_setup.settings import logger


def _find_repo_root() -> Path | None:
    """Walk up from this file to the nearest ancestor containing a `.git` dir."""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").is_dir():
            return parent
    return None


def self_update() -> None:
    """Fast-forward the installed git checkout, if any, before the app starts."""
    repo_root = _find_repo_root()
    if repo_root is None:
        return

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "pull", "--ff-only"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug(f"self-update skipped: {exc}")
        return

    if result.returncode != 0:
        logger.debug(f"self-update skipped: {result.stderr.strip()}")
        return

    if "Already up to date" not in result.stdout:
        print(f"personal-os-setup updated: {result.stdout.strip()}")

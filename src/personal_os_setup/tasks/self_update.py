"""Update an installed checkout before importing application dependencies.

Keep this bootstrap module stdlib-only: dependency synchronization and a restart must
finish before settings, Textual or other application modules are loaded.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

_LOG = logging.getLogger(__name__)


def _find_repo_root() -> Path | None:
    """Find this project's checkout, including worktrees, without selecting an unrelated repo."""
    for parent in Path(__file__).resolve().parents:
        project = parent / "pyproject.toml"
        if not (parent / ".git").exists() or not project.is_file():
            continue
        try:
            metadata = tomllib.loads(project.read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        if metadata.get("project", {}).get("name") == "personal-os-setup":
            return parent
    return None


def _head(repo_root: Path) -> str:
    """Read the checkout revision, independently of Git's localized progress output."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    return result.stdout.strip()


def self_update() -> None:
    """Pull, synchronize this virtual environment and restart after a source update."""
    repo_root = _find_repo_root()
    if repo_root is None or sys.prefix == sys.base_prefix:
        return
    uv = shutil.which("uv")
    if uv is None:
        _LOG.debug("self-update skipped: uv is unavailable")
        return

    changed = False
    try:
        before = _head(repo_root)
    except (OSError, subprocess.SubprocessError) as error:
        _LOG.debug("self-update skipped: %s", error)
    else:
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_root), "pull", "--ff-only"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            if result.returncode:
                _LOG.debug("self-update pull skipped: %s", result.stderr.strip())
        except (OSError, subprocess.SubprocessError) as error:
            _LOG.debug("self-update pull skipped: %s", error)
        try:
            changed = _head(repo_root) != before
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError(
                "Cannot verify the updated checkout; rerun the installer."
            ) from error

    # Check every launch so a failed sync is retried even when HEAD no longer changes.
    # Inexact sync retains developer tools; target the interpreter's own environment.
    try:
        result = subprocess.run(
            [
                uv,
                "sync",
                "--locked",
                "--inexact",
                "--no-default-groups",
                "--python",
                sys.executable,
            ],
            cwd=repo_root,
            env=dict(os.environ, UV_PROJECT_ENVIRONMENT=sys.prefix),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError("Cannot synchronize app dependencies; rerun the installer.") from error
    if result.returncode:
        raise RuntimeError(
            "Cannot synchronize app dependencies; rerun the installer.\n" + result.stderr.strip()
        )
    if changed:
        print("personal-os-setup updated; restarting with synchronized dependencies.", flush=True)
        try:
            os.execv(
                sys.executable,
                [sys.executable, "-m", "personal_os_setup.frontend.main", *sys.argv[1:]],
            )
        except OSError as error:
            raise RuntimeError(
                "Cannot restart after updating; launch personal-os-setup again."
            ) from error

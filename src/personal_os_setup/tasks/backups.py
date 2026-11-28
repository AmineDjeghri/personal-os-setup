"""Pre-change backups, kept in one place outside every managed tree."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from personal_os_setup.tasks.task import TaskResult


def backup_root() -> Path:
    """Directory holding every backup: `<state>/personal-os-setup/backups/<timestamp>/...`."""
    state_home = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_home) / "personal-os-setup" / "backups"


def new_stamp() -> str:
    """One timestamp to share between the files of a single action."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_file(path: Path, stamp: str | None = None) -> Path | None:
    """Copy `path` to `backup_root()/<stamp>/<path relative to ~>`; `None` if it is not a file.

    Backups never sit next to the live file, so they cannot pollute a managed tree (e.g. a skill
    folder) or trip drift checks. Raises `OSError` if the copy fails.
    """
    if not path.is_file():
        return None
    try:
        relative = path.relative_to(Path.home())
    except ValueError:
        relative = Path(*path.parts[1:])
    destination = backup_root() / (stamp or new_stamp()) / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination


def clean_backups() -> TaskResult:
    """Delete every backup under `backup_root()`; live files are never touched."""
    root = backup_root()
    if not root.is_dir():
        return TaskResult(ok=True, summary="clean backups: nothing to remove")
    removed: list[Path] = []
    failed: list[str] = []
    for stamped in sorted(root.iterdir()):
        try:
            if stamped.is_dir():
                shutil.rmtree(stamped)
            else:
                stamped.unlink()
        except OSError as e:
            failed.append(f"{stamped}: {e}")
        else:
            removed.append(stamped)
    details = "\n".join([*(str(p) for p in removed), *(f"FAILED {f}" for f in failed)])
    if failed:
        return TaskResult(
            ok=False,
            summary=f"clean backups: removed {len(removed)}, {len(failed)} failed",
            details=details,
        )
    return TaskResult(
        ok=True, summary=f"clean backups: removed {len(removed)} backup set(s)", details=details
    )

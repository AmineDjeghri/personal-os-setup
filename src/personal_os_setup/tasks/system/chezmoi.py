from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.task import TaskResult


def chezmoi_source_dir() -> Path:
    return Path(str(resources.files("personal_os_setup") / "config" / "chezmoi"))


def _chezmoi_path() -> str | None:
    return shutil.which("chezmoi")


def chezmoi_diff() -> TaskResult:
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    res = run([chezmoi_path, "--source", str(chezmoi_source_dir()), "diff"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    return TaskResult(
        ok=True,
        summary="chezmoi diff" if details else "chezmoi diff: no changes",
        details=details,
    )


def chezmoi_apply() -> TaskResult:
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    res = run([chezmoi_path, "--source", str(chezmoi_source_dir()), "apply", "-v"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="chezmoi apply: ok", details=details)
    return TaskResult(ok=False, summary="chezmoi apply: failed", details=details)


def chezmoi_re_add() -> TaskResult:
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    res = run([chezmoi_path, "--source", str(chezmoi_source_dir()), "re-add", "-v"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    commit_hint = (
        "Pulled your current ~/.zshrc, ~/.p10k.zsh, and ~/.config/zed/settings.json back "
        "into the repo's chezmoi source dir."
    )
    if res.returncode == 0:
        return TaskResult(
            ok=True,
            summary="chezmoi re-add: ok",
            details=f"{details}\n{commit_hint}".strip() if details else commit_hint,
        )
    return TaskResult(ok=False, summary="chezmoi re-add: failed", details=details)

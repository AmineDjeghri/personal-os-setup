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


def chezmoi_managed_paths() -> list[Path]:
    """List the destination paths chezmoi currently manages from this repo's source dir.

    Includes regular files, scripts (e.g. `run_onchange_*`), and symlinks (`symlink_*`).

    Returns an empty list if chezmoi isn't installed or the command fails, so callers
    (e.g. populating a UI selection list) can degrade gracefully instead of raising.
    """
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return []

    res = run(
        [
            chezmoi_path,
            "--source",
            str(chezmoi_source_dir()),
            "managed",
            "--include=files,scripts,symlinks",
            "--path-style=absolute",
        ],
        check=False,
    )
    if res.returncode != 0:
        return []
    return sorted(Path(line) for line in res.stdout.splitlines() if line.strip())


def chezmoi_diff(targets: list[Path] | None = None) -> TaskResult:
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    argv = [
        chezmoi_path,
        "--source",
        str(chezmoi_source_dir()),
        "diff",
        "--refresh-externals=never",
    ]
    argv.extend(str(t) for t in targets or [])
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    return TaskResult(
        ok=True,
        summary="chezmoi diff" if details else "chezmoi diff: no changes",
        details=details,
    )


def chezmoi_apply(targets: list[Path] | None = None) -> TaskResult:
    """Apply the selected dotfile(s) to the home directory without refreshing git-repo externals."""
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    argv = [
        chezmoi_path,
        "--source",
        str(chezmoi_source_dir()),
        "apply",
        "-v",
        "--force",
        "--parent-dirs",
        "--refresh-externals=never",
    ]
    argv.extend(str(t) for t in targets or [])
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="chezmoi apply: ok", details=details)
    return TaskResult(ok=False, summary="chezmoi apply: failed", details=details)


def chezmoi_refresh_zsh_externals() -> TaskResult:
    """Force-refresh oh-my-zsh, its custom plugins, and its theme from upstream.

    https://www.chezmoi.io/user-guide/include-files-from-elsewhere/
    """
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    argv = [
        chezmoi_path,
        "--source",
        str(chezmoi_source_dir()),
        "apply",
        "-v",
        "--force",
        "--refresh-externals=always",
        str(Path.home() / ".oh-my-zsh"),
    ]
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="chezmoi: sync zsh plugins/theme: ok", details=details)
    return TaskResult(ok=False, summary="chezmoi: sync zsh plugins/theme: failed", details=details)


def chezmoi_re_add(targets: list[Path] | None = None) -> TaskResult:
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    argv = [
        chezmoi_path,
        "--source",
        str(chezmoi_source_dir()),
        "re-add",
        "-v",
        "--refresh-externals=never",
    ]
    argv.extend(str(t) for t in targets or [])
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    commit_hint = "Pulled the selected file(s) back into the repo's chezmoi source dir."
    if res.returncode == 0:
        return TaskResult(
            ok=True,
            summary="chezmoi re-add: ok",
            details=f"{details}\n{commit_hint}".strip() if details else commit_hint,
        )
    return TaskResult(ok=False, summary="chezmoi re-add: failed", details=details)


def chezmoi_add(path: Path) -> TaskResult:
    """Start tracking a new file: copies it into the repo's chezmoi source dir."""
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    argv = [chezmoi_path, "--source", str(chezmoi_source_dir()), "add", "-v", str(path)]
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(
            ok=True,
            summary=f"chezmoi add: ok ({path} is now tracked in the repo)",
            details=details,
        )
    return TaskResult(ok=False, summary="chezmoi add: failed", details=details)


def chezmoi_forget(targets: list[Path]) -> TaskResult:
    """Stop tracking the given files: removes them from the repo's chezmoi source dir.

    Leaves the live file on disk untouched -- only the repo's copy is removed.
    """
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")
    if not targets:
        return TaskResult(ok=False, summary="chezmoi forget: no targets given")

    argv = [
        chezmoi_path,
        "--source",
        str(chezmoi_source_dir()),
        "--force",
        "forget",
        *(str(t) for t in targets),
    ]
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="chezmoi forget: ok", details=details)
    return TaskResult(ok=False, summary="chezmoi forget: failed", details=details)

from __future__ import annotations

import re
import shutil
from importlib import resources
from pathlib import Path

from personal_os_setup.tasks.backups import backup_file, backup_root, new_stamp
from personal_os_setup.tasks.commands import QUIET_ENV, run, strip_terminal_noise
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


def _status_entries(chezmoi_path: str, targets: list[Path]) -> list[tuple[str, Path]]:
    """Return `(status, path)` for entries an apply would touch: A=create, M=overwrite, R=run script.

    Status is the second column of `chezmoi status` (actual state vs target state).
    """
    res = run(
        [
            chezmoi_path,
            "--source",
            str(chezmoi_source_dir()),
            "status",
            "--include=files,scripts",
            "--path-style=absolute",
            *(str(t) for t in targets),
        ],
        check=False,
    )
    if res.returncode != 0:
        return []
    entries: list[tuple[str, Path]] = []
    for line in res.stdout.splitlines():
        if len(line) > 3 and line[1] in "AMR" and line[2] == " ":
            entries.append((line[1], Path(line[3:])))
    return entries


def chezmoi_preview(targets: list[Path] | None = None) -> str:
    """Summarize what applying `targets` would do, for the confirm dialog ("" if unknown)."""
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return ""
    entries = _status_entries(chezmoi_path, targets or [])
    created = sum(1 for status, _ in entries if status == "A")
    changed = sum(1 for status, _ in entries if status == "M")
    scripts = [path for status, path in entries if status == "R"]
    if not entries:
        return "Nothing to change."
    lines = [f"{created} file(s) to create, {changed} to overwrite."]
    if scripts:
        lines.append(f"{len(scripts)} script(s) will run: " + ", ".join(p.name for p in scripts))
    return "\n".join(lines)


def _backup_before_overwrite(chezmoi_path: str, targets: list[Path]) -> list[Path]:
    """Copy every file the apply will overwrite into one timestamped backup directory.

    Only files whose content chezmoi would actually change are copied (see `backups.backup_file`
    for where they go); a file that cannot be copied is skipped, not treated as an error.
    """
    stamp = new_stamp()
    backed_up: list[Path] = []
    for status, path in _status_entries(chezmoi_path, targets):
        if status != "M":
            continue
        try:
            destination = backup_file(path, stamp)
        except OSError:
            continue
        if destination is not None:
            backed_up.append(destination)
    return backed_up


_SCRIPT_FAILURE_RE = re.compile(r"chezmoi: (?P<script>.+?): exit status (?P<code>\d+)")


def _apply_phase(chezmoi_path: str, selector: str, targets: list[Path]):  # type: ignore[no-untyped-def]
    return run(
        [
            chezmoi_path,
            "--source",
            str(chezmoi_source_dir()),
            "apply",
            "-v",
            "--force",
            "--parent-dirs",
            "--refresh-externals=never",
            selector,
            *(str(t) for t in targets),
        ],
        check=False,
        env=QUIET_ENV,
    )


def _output_of(res) -> str:  # type: ignore[no-untyped-def]
    return strip_terminal_noise((res.stdout + "\n" + res.stderr).strip())


def _last_lines(text: str, count: int = 6) -> str:
    return "\n".join(text.splitlines()[-count:])


def chezmoi_apply(targets: list[Path] | None = None) -> TaskResult:
    """Apply the selected dotfile(s) to the home directory without refreshing git-repo externals.

    Files are applied first and scripts second, in two chezmoi calls, because chezmoi stops at
    the first failing entry: a failing `run_*` script must never keep the files from deploying.
    A script failure after the files landed is reported as a warning, not as a failed apply.
    """
    chezmoi_path = _chezmoi_path()
    if chezmoi_path is None:
        return TaskResult(ok=False, summary="chezmoi not found on PATH")

    targets = targets or []
    backed_up = _backup_before_overwrite(chezmoi_path, targets)
    header = ""
    if backed_up:
        header = f"Backed up {len(backed_up)} file(s) before overwriting, under {backup_root()}\n\n"

    files = _apply_phase(chezmoi_path, "--exclude=scripts", targets)
    files_output = _output_of(files)
    if files.returncode != 0:
        return TaskResult(
            ok=False,
            summary="chezmoi apply: failed while writing files (nothing ran after it)",
            details=f"{header}Failed step: write files\nLast output:\n{_last_lines(files_output)}"
            f"\n\nFull output:\n{files_output}".strip(),
        )

    scripts = _apply_phase(chezmoi_path, "--include=scripts", targets)
    scripts_output = _output_of(scripts)
    full = "\n".join(part for part in (files_output, scripts_output) if part)
    if scripts.returncode == 0:
        return TaskResult(ok=True, summary="chezmoi apply: ok", details=f"{header}{full}".strip())

    match = _SCRIPT_FAILURE_RE.search(scripts_output)
    script = f"{match['script']} (exit {match['code']})" if match else "a script"
    return TaskResult(
        ok=True,
        warning=True,
        summary=f"chezmoi apply: files applied, but {script} failed",
        details=f"{header}Failed step: {script}\nLast output:\n{_last_lines(scripts_output)}"
        f"\n\nFull output:\n{full}".strip(),
    )


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

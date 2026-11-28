"""Agent-skills management for the TUI "Skills" tab (the `make skills-*` targets, in Python).

Authored skills live in the chezmoi source (`dot_claude/skills`) and are deployed to
`~/.claude/skills`; third-party skills are installed by `npx skills` and recorded in a lock file
that is copied into the repo. The shared `skills_support.py` helper (stdlib only, also used by
chezmoi and Make) does the link/verify/drift work; this module orchestrates it and reports
`TaskResult`s the TUI can show.
"""

from __future__ import annotations

import filecmp
import json
import os
import shutil
import sys
from pathlib import Path

from personal_os_setup.tasks.commands import QUIET_ENV, CommandResult, run, strip_terminal_noise
from personal_os_setup.tasks.system.chezmoi import chezmoi_source_dir
from personal_os_setup.tasks.task import TaskResult

_LOCK_NAME = "third-party-skills.lock.json"
_KEEP_NAME = "skills.keep"
_IGNORED = (".DS_Store", "__pycache__")
_AGENTS = "claude-code codex"
_EXIT_DRIFT = 2  # mirrors skills_support.EXIT_DRIFT (advisory: the lock needs a review)
_STATE_LABELS = {
    "ok": "OK          ",
    "missing": "NOT DEPLOYED",
    "repo-newer": "REPO NEWER  ",
    "live-newer": "LIVE NEWER  ",
}


def _dot_claude() -> Path:
    return chezmoi_source_dir() / "dot_claude"


def authored_dir() -> Path:
    """Repo-side authored skills (the chezmoi source)."""
    return _dot_claude() / "skills"


def live_dir() -> Path:
    """Where Claude Code and Hermes read skills from."""
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "skills"


def codex_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def repo_root() -> Path | None:
    """The checkout holding the third-party lock, or `None` for an installed wheel."""
    for parent in chezmoi_source_dir().parents:
        if (parent / _LOCK_NAME).is_file():
            return parent
    return None


def live_lock_path() -> Path:
    """The npx lock: XDG state first, the older `~/.agents` location second."""
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    modern = state / "skills" / ".skill-lock.json"
    legacy = Path.home() / ".agents" / ".skill-lock.json"
    return legacy if not modern.is_file() and legacy.is_file() else modern


def _support(*args: str, extra_env: dict[str, str] | None = None) -> CommandResult:
    return run(
        [sys.executable, "-I", str(_dot_claude() / "skills_support.py"), *args],
        check=False,
        env={**QUIET_ENV, **(extra_env or {})},
    )


def _link_args() -> list[str]:
    return [
        "link",
        "--source",
        str(authored_dir()),
        "--claude",
        str(live_dir()),
        "--codex",
        str(codex_dir()),
    ]


def _third_party_args(lock: Path) -> list[str]:
    return [
        "--lock",
        str(lock),
        "--live-lock",
        str(live_lock_path()),
        "--agents",
        _AGENTS,
        "--claude",
        str(live_dir()),
        "--codex",
        str(codex_dir()),
    ]


def _files(root: Path) -> dict[str, float]:
    """Relative path -> mtime of every real file under `root`, ignoring tool litter."""
    found: dict[str, float] = {}
    base = root.resolve()
    for path in base.rglob("*"):
        relative = path.relative_to(base)
        if path.is_file() and not any(part in _IGNORED for part in relative.parts):
            found[relative.as_posix()] = path.stat().st_mtime
    return found


def _newest_dir(root: Path) -> float:
    """Newest directory mtime under `root`: a deleted file shows only here, not in `_files`."""
    base = root.resolve()
    dirs = [base, *(p for p in base.rglob("*") if p.is_dir())]
    return max(
        d.stat().st_mtime
        for d in dirs
        if not any(part in _IGNORED for part in d.relative_to(base).parts)
    )


def _same_content(left: Path, right: Path) -> bool:
    return filecmp.cmp(left, right, shallow=False)


def _mirror(source: Path, target: Path) -> None:
    """Make `target` an exact copy of `source` (tool litter excluded), deletions included.

    The copy goes to a sibling staging dir first, so a failed copy leaves `target` untouched.
    """
    staging = target.with_name(f".{target.name}.staging")
    if staging.exists():
        shutil.rmtree(staging)
    try:
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns(*_IGNORED))
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.exists():
        shutil.rmtree(target)
    staging.rename(target)


def _compare(name: str) -> tuple[str, str]:
    """Classify one authored skill against its live copy: `(state, note)`.

    State is `ok`, `missing`, `repo-newer` or `live-newer`.
    """
    source, live = authored_dir() / name, live_dir() / name
    if not live.exists():
        return "missing", ""
    repo_files, live_files = _files(source), _files(live)
    differing = sorted(
        path
        for path in repo_files.keys() | live_files.keys()
        if path not in repo_files
        or path not in live_files
        or not _same_content(source / path, live / path)
    )
    if not differing:
        return "ok", ""
    note = ", ".join(differing[:3]) + (
        f" (+{len(differing) - 3} more)" if len(differing) > 3 else ""
    )
    live_newest = max([*live_files.values(), _newest_dir(live)])
    repo_newest = max([*repo_files.values(), _newest_dir(source)])
    return ("live-newer" if live_newest > repo_newest else "repo-newer"), note


def _authored_names() -> list[str]:
    return sorted(
        p.parent.name
        for p in authored_dir().glob("*/SKILL.md")
        if not p.parent.name.startswith(".")
    )


def skills_status() -> TaskResult:
    """Read-only report: repo vs live copies, Codex links and the third-party lock."""
    lines: list[str] = []
    counts = {"ok": 0, "missing": 0, "repo-newer": 0, "live-newer": 0}
    for name in _authored_names():
        state, note = _compare(name)
        counts[state] += 1
        lines.append(f"{_STATE_LABELS[state]} {name}" + (f"  [{note}]" if note else ""))

    problems: list[str] = []
    warning = False
    link = _support(*_link_args(), "--check")
    if link.returncode != 0:
        problems.append(strip_terminal_noise(link.stderr or link.stdout))

    root = repo_root()
    lock = root / _LOCK_NAME if root else None
    if lock is not None and live_lock_path().is_file():
        for command in ("verify", "drift"):
            result = _support(command, *_third_party_args(lock))
            text = strip_terminal_noise(result.stderr or result.stdout)
            if result.returncode == _EXIT_DRIFT:
                warning = True
                lines.append(f"THIRD-PARTY  {text}")
            elif result.returncode != 0:
                problems.append(text)
    else:
        lines.append("THIRD-PARTY  no live npx lock: nothing installed via npx here")

    lines.extend(f"PROBLEM      {p}" for p in problems)
    needs_deploy = counts["missing"] + counts["repo-newer"]
    summary = (
        f"skills: {counts['ok']} in sync, {needs_deploy} to deploy, "
        f"{counts['live-newer']} edited live"
        + (f", {len(problems)} problem(s)" if problems else "")
    )
    if problems or counts["live-newer"]:
        return TaskResult(ok=False, summary=summary, details="\n".join(lines))
    return TaskResult(
        ok=True, warning=warning or bool(needs_deploy), summary=summary, details="\n".join(lines)
    )


def skills_deploy(*, force: bool = False) -> TaskResult:
    """Copy authored skills repo -> live and link them for Codex.

    Refuses (unless `force`) when a live copy was edited after the repo's version, so live-only
    work is not overwritten silently; save it to the repo first.
    """
    names = _authored_names()
    if not names:
        return TaskResult(
            ok=False, summary=f"skills deploy: no authored skills in {authored_dir()}"
        )
    edited = [name for name in names if _compare(name)[0] == "live-newer"]
    if edited and not force:
        return TaskResult(
            ok=False,
            summary=f"skills deploy: aborted, {len(edited)} live skill(s) are newer than the repo",
            details=(
                "Edited live: "
                + ", ".join(edited)
                + "\nUse 'save live skills to repo' first, or 'force deploy' to overwrite them."
            ),
        )

    preflight = _support(*_link_args(), "--preflight")
    if preflight.returncode != 0:
        return TaskResult(
            ok=False,
            summary="skills deploy: Codex link conflict, nothing was copied",
            details=strip_terminal_noise(preflight.stderr or preflight.stdout),
        )
    try:
        live_dir().mkdir(parents=True, exist_ok=True)
        for name in names:
            _mirror(authored_dir() / name, live_dir() / name)
    except OSError as e:
        return TaskResult(ok=False, summary="skills deploy: copy failed", details=str(e))
    linked = _support(*_link_args())
    if linked.returncode != 0:
        return TaskResult(
            ok=False,
            summary="skills deploy: copied, but linking for Codex failed",
            details=strip_terminal_noise(linked.stderr or linked.stdout),
        )
    return TaskResult(
        ok=True,
        summary=f"skills deploy: {len(names)} skill(s) -> {live_dir()}",
        details=", ".join(names),
    )


def _third_party_names(lock: Path) -> set[str]:
    return set(json.loads(lock.read_text()).get("skills", {}))


def skills_save_live(name: str = "") -> TaskResult:
    """Copy live skill(s) into the repo and list them in `skills.keep`.

    An empty `name` or `all` saves every live skill the repo does not yet list and that is not
    third-party; anything else names exactly one live skill.
    """
    root = repo_root()
    if root is None:
        return TaskResult(
            ok=False, summary="skills save: not running from a repo checkout (no skills.keep)"
        )
    keep = root / _KEEP_NAME
    listed = {
        line.strip()
        for line in (keep.read_text().splitlines() if keep.is_file() else [])
        if line.strip() and not line.lstrip().startswith("#")
    }
    name = name.strip()
    if name in ("", "all"):
        third_party = _third_party_names(root / _LOCK_NAME)
        names = sorted(
            p.name
            for p in live_dir().glob("*")
            if p.is_dir()
            and not p.is_symlink()
            and not p.name.startswith(".")
            and p.name not in listed | third_party
        )
    elif Path(name).name != name or name.startswith("."):
        return TaskResult(
            ok=False, summary=f"skills save: {name!r} is not a skill name (no paths or dot-names)"
        )
    else:
        names = [name]
    if not names:
        return TaskResult(ok=True, summary="skills save: no unlisted live skill to capture")

    saved: list[str] = []
    skipped: list[str] = []
    for skill in names:
        source = live_dir() / skill
        if not (source / "SKILL.md").is_file():
            skipped.append(f"{skill}: not a live skill at {source}")
            continue
        try:
            _mirror(source, authored_dir() / skill)
        except OSError as e:
            skipped.append(f"{skill}: {e}")
            continue
        saved.append(skill)
        if skill not in listed:
            with keep.open("a") as handle:
                handle.write(f"{skill}\n")
    details = "\n".join([*(f"saved {s}" for s in saved), *(f"SKIPPED {s}" for s in skipped)])
    return TaskResult(
        ok=not skipped,
        summary=f"skills save: {len(saved)} saved, {len(skipped)} skipped",
        details=details,
    )


def skills_thirdparty_install(*, force: bool = False) -> TaskResult:
    """Install or repair third-party skills with `npx skills` (network), then verify them.

    Refuses (unless `force`) when an installed copy was hand-edited after install. Lock drift
    after a successful install is a warning, not a failure.
    """
    root = repo_root()
    if root is None:
        return TaskResult(
            ok=False, summary=f"skills install: no {_LOCK_NAME} (not a repo checkout)"
        )
    lock = root / _LOCK_NAME
    if shutil.which("bash") is None:
        return TaskResult(ok=False, summary="skills install: bash not found on PATH")
    if not force:
        drift = _support("drift", *_third_party_args(lock))
        if drift.returncode != 0:
            return TaskResult(
                ok=False,
                summary="skills install: aborted, installed copies were edited after install",
                details=strip_terminal_noise(drift.stderr or drift.stdout)
                + "\nPort the edit somewhere safe, or use 'force reinstall'.",
            )
    res = run(
        ["bash", str(_dot_claude() / "run_after_replay-third-party-skills.sh")],
        check=False,
        env={
            **QUIET_ENV,
            "STRICT": "1",
            "LOCK": str(lock),
            "SKILLS_DST": str(live_dir()),
            "SKILLS_CODEX_DST": str(codex_dir()),
            "LIVE_SKILLS_LOCK": str(live_lock_path()),
            "SKILLS_PYTHON": sys.executable,
            "FORCE": "1" if force else "0",
        },
    )
    output = strip_terminal_noise((res.stdout + "\n" + res.stderr).strip())
    if res.returncode == 0:
        return TaskResult(
            ok=True, summary="skills install: third-party skills are installed", details=output
        )
    if res.returncode == _EXIT_DRIFT:
        return TaskResult(
            ok=True,
            warning=True,
            summary="skills install: installed, but the live lock differs from the repo lock",
            details=f"{output}\nReview upstream, then use 'save live lock to repo'.",
        )
    last = "\n".join(output.splitlines()[-6:])
    return TaskResult(
        ok=False,
        summary=f"skills install: failed (exit {res.returncode})",
        details=f"Last output:\n{last}\n\nFull output:\n{output}",
    )


def skills_thirdparty_save_lock() -> TaskResult:
    """Record the live npx lock in the repo (the lock we ship)."""
    root = repo_root()
    if root is None:
        return TaskResult(ok=False, summary=f"skills lock: no {_LOCK_NAME} (not a repo checkout)")
    live = live_lock_path()
    if not live.is_file():
        return TaskResult(ok=False, summary=f"skills lock: no live lock at {live}")
    try:
        data = json.loads(live.read_text())
        (root / _LOCK_NAME).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    except (OSError, ValueError) as e:
        return TaskResult(ok=False, summary="skills lock: could not save", details=str(e))
    return TaskResult(
        ok=True,
        summary=f"skills lock: saved {len(data.get('skills', {}))} entries to {_LOCK_NAME}",
        details="Review the diff and commit it yourself.",
    )

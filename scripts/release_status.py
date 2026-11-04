"""Report whether `make release` can run. Read-only: nothing here changes the repository."""

import json
from pathlib import Path
import subprocess
import tomllib


def run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a command and capture its text output."""
    return subprocess.run(args, capture_output=True, text=True, check=False)


def git(*args: str) -> str:
    """Return stripped git output, or an empty string when the command fails."""
    result = run("git", *args)
    return result.stdout.strip() if result.returncode == 0 else ""


def release_state(tag: str) -> str:
    """Describe the GitHub release for a tag."""
    if run("gh", "auth", "status").returncode != 0:
        return "unknown (run: gh auth login)"
    result = run("gh", "release", "view", tag, "--json", "isDraft,assets")
    if result.returncode != 0:
        return "no GitHub release"
    data = json.loads(result.stdout)
    return f"{'draft' if data['isDraft'] else 'published'}, {len(data['assets'])} assets"


def main() -> None:
    """Print the guard conditions of `make release`, the tag state and the verdict."""
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    tag = f"v{project['version']}"
    branch = git("rev-parse", "--abbrev-ref", "HEAD") or "detached"
    changed = [
        line[3:] for line in run("git", "status", "--porcelain").stdout.splitlines() if line.strip()
    ]
    counts = git("rev-list", "--left-right", "--count", f"{branch}...origin/{branch}").split()
    in_sync = counts == ["0", "0"]
    sync = (
        "in sync"
        if in_sync
        else (f"ahead {counts[0]}, behind {counts[1]}" if counts else f"no origin/{branch}")
    )
    tagged = git("rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")
    tag_at_head = bool(tagged) and tagged == git("rev-parse", "HEAD")

    problems = []
    if branch not in ("main", "dev"):
        problems.append("branch: release from main or dev")
    if changed:
        problems.append("dirty tree: commit or stash")
    if not in_sync:
        problems.append("origin: pull or push first")

    print(f"branch   {branch}")
    print(f"tree     {'clean' if not changed else ', '.join(changed)}")
    print(f"origin   {sync}")
    print(f"tag      {tag} {'at HEAD' if tag_at_head else 'not at HEAD'}")
    print(f"release  {release_state(tag)}")
    print("STATUS   " + ("blocked: " + "; ".join(problems) if problems else "ready to release"))


if __name__ == "__main__":
    main()

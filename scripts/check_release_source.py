"""Bind publication to the CI revision, allowing only its exact semantic-release bump on retry."""

from pathlib import Path
import subprocess
import sys
import tomllib


def git(*args: str) -> str:
    """Read repository state without changing it."""
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def check_release_source(expected: str) -> None:
    """Accept the tested commit or its tagged, metadata-only release commit."""
    expected = git("rev-parse", "--verify", f"{expected}^{{commit}}")
    head = git("rev-parse", "HEAD")
    if head == expected:
        return
    if git("rev-list", "--parents", "-n", "1", "HEAD").split() != [head, expected]:
        raise ValueError("HEAD is not the revision that passed CI or its release commit")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = project["project"]["version"]
    if git("rev-parse", f"refs/tags/v{version}^{{commit}}") != head:
        raise ValueError("retry requires the version tag at HEAD")
    if git("log", "-1", "--format=%B") != f"chore(release): v{version} [skip ci]":
        raise ValueError("retry requires the semantic-release commit message")
    changed = set(git("diff", "--name-only", expected, "HEAD").splitlines())
    if not changed <= {"pyproject.toml", "uv.lock", "CHANGELOG.md"}:
        raise ValueError("untested source changes after the CI revision")
    old_project = tomllib.loads(git("show", f"{expected}:pyproject.toml"))
    old_project["project"]["version"] = version
    if old_project != project:
        raise ValueError("untested project configuration changes after the CI revision")
    old_lock = tomllib.loads(git("show", f"{expected}:uv.lock"))
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    for package in old_lock["package"]:
        if package["name"] == project["project"]["name"]:
            package["version"] = next(
                p["version"] for p in lock["package"] if p["name"] == package["name"]
            )
    if old_lock != lock:
        raise ValueError("untested dependency changes after the CI revision")


if __name__ == "__main__":
    check_release_source(sys.argv[1])

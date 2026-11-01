"""Bind publication to the CI revision, allowing only its exact semantic-release bump on retry."""

from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any

from packaging.utils import canonicalize_name
from packaging.version import Version


def git(*args: str) -> str:
    """Read repository state without changing it."""
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def root_package(project: dict[str, Any], lock: dict[str, Any]) -> dict[str, Any]:
    """Require one root lock entry with the project's exact normalized version."""
    name = canonicalize_name(project["project"]["name"])
    roots = [p for p in lock["package"] if canonicalize_name(p["name"]) == name]
    if len(roots) != 1:
        raise ValueError("lock must contain exactly one root package")
    if Version(roots[0]["version"]) != Version(project["project"]["version"]):
        raise ValueError("root lock version must match project.version")
    return roots[0]


def check_release_source(expected: str) -> str:
    """Identify the tested source or its exact release child, even before tag publication."""
    expected = git("rev-parse", "--verify", f"{expected}^{{commit}}")
    head = git("rev-parse", "HEAD")
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))
    root = root_package(project, lock)
    if head == expected:
        return "source"
    if git("rev-list", "--parents", "-n", "1", "HEAD").split() != [head, expected]:
        raise ValueError("HEAD is not the revision that passed CI or its release commit")
    version = project["project"]["version"]
    # A fresh checkout after a successful branch push can lack the tag entirely.
    # An existing tag still has to resolve to this release commit; other Git errors fail closed.
    tag = f"refs/tags/v{version}"
    try:
        git("show-ref", "--verify", "--quiet", tag)
    except subprocess.CalledProcessError as error:
        if error.returncode != 1:
            raise
    else:
        if git("rev-parse", f"{tag}^{{commit}}") != head:
            raise ValueError("retry requires the version tag at HEAD when it exists")
    if git("log", "-1", "--format=%B") != f"chore(release): v{version} [skip ci]":
        raise ValueError("retry requires the semantic-release commit message")
    changed = set(git("diff", "--name-only", expected, "HEAD").splitlines())
    if not changed <= {"pyproject.toml", "uv.lock", "CHANGELOG.md"}:
        raise ValueError("untested source changes after the CI revision")
    old_project = tomllib.loads(git("show", f"{expected}:pyproject.toml"))
    old_lock = tomllib.loads(git("show", f"{expected}:uv.lock"))
    old_root = root_package(old_project, old_lock)
    if Version(version) <= Version(old_project["project"]["version"]):
        raise ValueError("retry requires an increased release version")
    old_project["project"]["version"] = version
    if old_project != project:
        raise ValueError("untested project configuration changes after the CI revision")
    old_root["version"] = root["version"]
    if old_lock != lock:
        raise ValueError("untested dependency changes after the CI revision")
    return "release"


if __name__ == "__main__":
    print(check_release_source(sys.argv[1]))

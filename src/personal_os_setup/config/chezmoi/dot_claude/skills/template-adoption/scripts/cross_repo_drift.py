#!/usr/bin/env python3
"""Read-only drift check across the sibling gate-stack repos.

Compares the same paths on a committed ref across repos and classifies each as
IDENTICAL (equal git blob SHA), DIFFERS, or MISSING. Fetch first
(`git fetch --prune origin` per repo); this script never touches refs or files.

Usage:
  python3 cross_repo_drift.py --workspace ~/git \
      --repo personal-os-setup \
      --repo generative-ai-project-template \
      --repo python-package-template

  # narrower run
  python3 cross_repo_drift.py --ref origin/main --path makefiles/test.mk

Exit code: 0 when every listed path is identical in every repo, 1 otherwise
(so it can later be wired into a gate).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DEFAULT_PATHS = [
    ".pre-commit-config.yaml",
    ".markdownlint-cli2.yaml",
    ".github/actions/install-python-deps/action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/quality-and-tests.yml",
    "makefiles/common.mk",
    "makefiles/build.mk",
    "makefiles/check_format.mk",
    "makefiles/install.mk",
    "makefiles/test.mk",
    "makefiles/release.mk",
    "scripts/emoji_commit_parser.py",
    "scripts/gen_doc_stubs.py",
    "scripts/gen_example_pages.py",
]


def git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or r.stderr).strip()


def blob_sha(repo: Path, ref: str, path: str) -> str | None:
    rc, out = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}:{path}")
    return out if rc == 0 and out else None


def has_cr(repo: Path, sha: str) -> bool:
    r = subprocess.run(["git", "-C", str(repo), "cat-file", "-p", sha], capture_output=True)
    return b"\r" in (r.stdout or b"")


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare shared paths across repos by blob SHA.")
    ap.add_argument("--workspace", default=str(Path.cwd().parent), help="directory holding the clones (default: parent of cwd)")
    ap.add_argument("--repo", action="append", required=True, help="repo directory name (repeatable)")
    ap.add_argument("--ref", default="origin/main", help="git ref to compare (default origin/main)")
    ap.add_argument("--path", action="append", help="path to compare (repeatable; defaults to the shared manifest)")
    args = ap.parse_args()

    ws = Path(args.workspace)
    repos = [ws / r for r in args.repo]
    for p in repos:
        if not (p / ".git").exists():
            print(f"not a git clone: {p}", file=sys.stderr)
            return 2
    paths = args.path or DEFAULT_PATHS

    width = max(len(p) for p in paths) + 2
    header = "path".ljust(width) + "".join(r.name[:22].ljust(24) for r in repos) + "verdict"
    print(header)
    print("-" * len(header))

    differ = 0
    cr_warned = []
    for path in paths:
        shas = []
        cells = []
        for repo in repos:
            sha = blob_sha(repo, args.ref, path)
            shas.append(sha)
            if sha is None:
                cells.append("—".ljust(24))
            else:
                cells.append(sha[:10].ljust(24))
                if has_cr(repo, sha):
                    cr_warned.append(f"{repo.name}:{path}")
        present = [s for s in shas if s]
        if len(present) < len(repos):
            verdict = "MISSING in some repo"
            differ += 1
        elif len(set(present)) == 1:
            verdict = "IDENTICAL"
        else:
            verdict = "DIFFERS"
            differ += 1
        print(path.ljust(width) + "".join(cells) + verdict)

    if cr_warned:
        print("\nCR bytes present (a 'differs' verdict may be CRLF noise): " + ", ".join(cr_warned))
    print(f"\n{len(paths) - differ}/{len(paths)} paths identical across {len(repos)} repos at {args.ref}")
    return 0 if differ == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

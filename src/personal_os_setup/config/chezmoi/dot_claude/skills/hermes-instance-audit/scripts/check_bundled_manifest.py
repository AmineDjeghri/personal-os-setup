#!/usr/bin/env python3
r"""Compare installed bundled skills against .bundled_manifest origin hashes.

Replicates the REAL hash algorithms used by tools/skills_sync.py:
  - _dir_hash(): md5 over (rel-path utf-8 + file bytes) of every file in the
    skill dir, files sorted by relative path.
  - _content_hash() -> tools/skills_guard._content_digest(): sha256 over
    (rel-path + b"\\x00" + file bytes) of every file, sorted.
The manifest format says "MD5" but sync prefers the sha256 digest when
skills_guard is importable -- so this script tries BOTH and reports which one
matched (either matching means the skill is unmodified).

NEVER compare md5 of SKILL.md alone against the manifest: the manifest hashes
cover the whole skill directory, and a SKILL.md-only probe reports every skill
as "user-modified" (verified false-positive 2026-08).

Usage:
    python3 check_bundled_manifest.py [skills_dir] [repo_skills_dir]
Defaults: /config/.hermes/skills  /config/.hermes/hermes-agent/skills

Read-only (no writes, no network). Exit 0. Output classification:
  - USER-DELETED:      in manifest, absent on disk -> sync respects this, NOT a bug
  - USER-MODIFIED:     on disk, but neither hash matches the manifest entry
  - UPSTREAM-CHANGED:  repo dir hash != manifest hash -> next sync would update
  - CURRENT:           matches stock (everything not listed in the other buckets)
"""

import hashlib
import sys
from pathlib import Path


def dir_hash_md5(d: Path) -> str:
    """tools/skills_sync.py::_dir_hash -- md5 over rel-path + bytes, sorted."""
    h = hashlib.md5()
    for f in sorted(d.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(d)).encode("utf-8"))
            h.update(f.read_bytes())
    return h.hexdigest()


def content_digest_sha256(d: Path) -> str:
    """tools/skills_guard.py::_content_digest -- sha256, rel + NUL + bytes."""
    h = hashlib.sha256()
    if d.is_dir():
        entries = sorted((f.relative_to(d).as_posix(), f) for f in d.rglob("*") if f.is_file())
        for rel, f in entries:
            h.update(rel.encode("utf-8") + b"\x00")
            h.update(f.read_bytes())
    else:
        h.update(d.read_bytes())
    return h.hexdigest()


def find_skill(root: Path, name: str):
    """Locate <category>/<name> or deeper (e.g. mlops/inference/obliteratus)."""
    for depth in ("*", "*/*", "*/*/*"):
        for p in root.glob(f"{depth}/{name}"):
            if p.is_dir():
                return p
    return None


def main() -> int:
    skills_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "/config/.hermes/skills")
    repo_dir = Path(sys.argv[2] if len(sys.argv) > 2 else "/config/.hermes/hermes-agent/skills")
    manifest = skills_dir / ".bundled_manifest"
    if not manifest.exists():
        print(f"no manifest at {manifest}")
        return 1

    entries = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if ":" in line:
            name, h = line.split(":", 1)
            entries[name] = h

    user_deleted, user_modified, upstream_changed, current = [], [], [], []
    for name, man_hash in sorted(entries.items()):
        installed = find_skill(skills_dir, name)
        repo = find_skill(repo_dir, name)
        if installed is None:
            user_deleted.append(name)
            continue
        m_md5 = dir_hash_md5(installed)
        m_sha = content_digest_sha256(installed)
        if m_md5 == man_hash or m_sha == man_hash:
            current.append(name)
        else:
            user_modified.append(name)
        if repo is not None:
            r_md5 = dir_hash_md5(repo)
            r_sha = content_digest_sha256(repo)
            if r_md5 != man_hash and r_sha != man_hash:
                upstream_changed.append(name)

    def dump(label, names):
        print(f"{label} ({len(names)})")
        for n in names:
            print(f"  {n}")

    dump("USER-DELETED (in manifest, absent on disk -- respected by sync)", user_deleted)
    dump("USER-MODIFIED (on disk, neither hash matches manifest)", user_modified)
    dump("UPSTREAM-CHANGED (repo != manifest -- next sync would update)", upstream_changed)
    print(f"CURRENT ({len(current)}) -- everything not listed above matches stock")
    return 0


if __name__ == "__main__":
    sys.exit(main())

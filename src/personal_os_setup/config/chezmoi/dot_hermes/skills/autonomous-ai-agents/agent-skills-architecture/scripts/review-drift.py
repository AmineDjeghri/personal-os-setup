#!/usr/bin/env python3
"""Review source-vs-live drift for agent skills before choosing port or force-deploy.

Usage:
  review-drift.py <source-root> <live-root> <rel-dir> [<rel-dir> ...]
  review-drift.py <source-root> <live-root> --all

  <source-root>  the git/chezmoi tree, e.g. <repo>/src/personal_os_setup/config/chezmoi/dot_hermes/skills
  <live-root>    the deployed store, e.g. /config/.hermes/skills
  <rel-dir>      skill dir relative to BOTH roots, e.g. devops/hermes-instance-audit
  --all          every skill present in both trees; unchanged ones print OK
  --out DIR      where the .diff files go (default: the current directory)

Per drifted skill it writes <out>/drift-<skill>.diff (unified, source -> live) and prints the line census,
added word count and scrub hits, so the user can judge the delta before anything is kept or overwritten:

  source-only=0            pure addition -> copying live->source loses nothing
  source-only>0            REWRITE -> read those lines first: they may be a rule the live side corrected

Exit 1 when a drift is a rewrite or a scrub hit is found, 0 otherwise, so a caller can gate on it.
The scan list below is deliberately small and generic; the full identifier list for a public repo is in
references/sanitizing-skills-for-public-repos.md -- extend PII to match it before porting.
"""

import difflib
import re
import sys
from pathlib import Path

PII = {
    "ipv4": re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "mac": re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"),
    "addon_config_hash": re.compile(r"/addon_configs/[0-9a-f]{8}"),
    "numeric_github_id": re.compile(r"\b\d{6,9}\+[A-Za-z]"),
    "home_path": re.compile(r"/home/[a-z][\w.-]*"),
}


def skills_in(root):
    """Map relative skill dir -> SKILL.md path for a skills root."""
    found = {}
    for p in sorted(Path(root).rglob("SKILL.md")):
        if "/.git/" in str(p):
            continue
        found[str(p.parent.relative_to(root))] = p
    return found


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    if len(args) < 2:
        print(__doc__)
        return 2
    src_root, live_root = Path(args[0]), Path(args[1])
    wanted = args[2:]
    out = Path(".")
    if "--out" in argv:
        out = Path(argv[argv.index("--out") + 1])

    src, live = skills_in(src_root), skills_in(live_root)
    names = sorted(set(src) | set(live)) if ("--all" in flags or not wanted) else wanted

    drifted = bad = 0
    for name in names:
        a, b = src.get(name), live.get(name)
        if a is None or b is None:
            side = "source" if a is None else "live"
            print(f"{name}: MISSING in {side} -- deploy/port decision, not a diff")
            bad += 1
            continue
        la, lb = (
            a.read_text(encoding="utf-8").splitlines(keepends=True),
            b.read_text(encoding="utf-8").splitlines(keepends=True),
        )
        if la == lb:
            if "--all" in flags:
                print(f"{name}: OK")
            continue
        drifted += 1
        diff = list(
            difflib.unified_diff(
                la, lb, fromfile=f"source:{name}/SKILL.md", tofile=f"live:{name}/SKILL.md", n=2
            )
        )
        minus = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        plus = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        added = "".join(l[1:] for l in diff if l.startswith("+") and not l.startswith("+++"))
        hits = {k: len(rx.findall(added)) for k, rx in PII.items()}
        hits = {k: v for k, v in hits.items() if v}
        slug = name.replace("/", "_")
        (out / f"drift-{slug}.diff").write_text("".join(diff), encoding="utf-8")
        kind = (
            "pure addition (live->source is lossless)"
            if minus == 0
            else f"REWRITE: {minus} source-only line(s) -- read them"
        )
        print(
            f"{name}: live-only={plus} source-only={minus} added_words={len(added.split())} -> {out / ('drift-' + slug + '.diff')}"
        )
        print(f"   {kind}; scrub={'clean' if not hits else hits}")
        if minus or hits:
            bad += 1
    print(f"\n{drifted} drifted skill(s) among {len(names)} selected")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

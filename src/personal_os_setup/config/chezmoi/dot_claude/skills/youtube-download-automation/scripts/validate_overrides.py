#!/usr/bin/env python3
r"""Coverage check: are all downloadable plan IDs covered by the overrides map?

Usage: python3 validate_overrides.py <plan.txt> <overrides.json>

Args:
  plan.txt      — output of a yt-dlp --plan / metadata-only run (lines like
                  "[  3] sE4KoUAFppg  Panic! At The Disco - High Hopes ...",
                  ERROR lines carry the unavailable IDs)
  overrides.json— the per-video metadata map keyed by video ID

Prints counts (plan entries / unique IDs / unavailable / overrides) and three
reports: MISSING (downloadable ID with no override — must be empty), EXTRA
(override for an ID not in the plan — usually a dup occurrence or a typo),
DUPLICATES (IDs listed more than once in the playlist — downloaded once, one
override entry is enough). Exit 0 iff MISSING is empty.

Gotchas baked in:
  * YouTube IDs are [A-Za-z0-9_-]{11} — \w misses hyphen IDs like -ZvsGmYKhcU.
  * Unavailable videos appear as INDEX GAPS in the plan (omitted from the
    listing), not as inline errors — dedupe against the ERROR lines only.
  * Duplicate playlist entries must be deduped before reporting "missing".
"""

import json
import re
import sys

ID_RE = re.compile(r"^\[\s*\d+\] ([A-Za-z0-9_-]{11})  ", re.M)
ERR_RE = re.compile(r"ERROR: \[youtube\] ([A-Za-z0-9_-]{11})")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    plan_path, overrides_path = sys.argv[1], sys.argv[2]
    plan = open(plan_path, encoding="utf-8").read()
    ids = ID_RE.findall(plan)
    unavailable = set(ERR_RE.findall(plan))
    unique = set(ids)
    overrides = set(json.load(open(overrides_path, encoding="utf-8")).keys())

    missing = sorted(i for i in unique if i not in overrides and i not in unavailable)
    extra = sorted(i for i in overrides if i not in unique)
    dups = sorted({i for i in ids if ids.count(i) > 1})

    print(
        f"plan entries: {len(ids)} | unique: {len(unique)} "
        f"| unavailable: {len(unavailable)} | overrides: {len(overrides)}"
    )
    print(f"downloadable unique = {len(unique - unavailable)}")
    print(f"MISSING: {missing}")
    print(f"EXTRA: {extra}")
    print(f"DUPLICATES (one override entry is enough): {dups}")
    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())

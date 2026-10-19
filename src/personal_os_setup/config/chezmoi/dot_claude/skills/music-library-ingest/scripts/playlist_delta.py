#!/usr/bin/env python3
r"""Report which items of a YouTube playlist are not yet ingested.

Usage:
    # from the yt-dlp pipeline folder:
    uv run --no-project yt_dl.py --plan <playlist-url> > plan.txt
    python playlist_delta.py plan.txt <pipeline_dir>

<pipeline_dir> is the folder holding .archive.txt (and overrides.json if present).
Prints declared/listed/duplicate/unavailable/already-ingested/new counts and then the
new items with links. A plan that parses to zero items aborts: that is almost always a
parser bug, and reporting "nothing new" from it is a silent false negative.

The plan index is right-aligned and space-padded ("[  1]", or "[  ?]" for a single-video
plan), so a naive ^\[\d+\] regex matches NOTHING. Keep the padding-tolerant, anchored
pattern below if you edit this file.
"""

import json
import pathlib
import re
import sys

ITEM = re.compile(r"^\[\s*(\d+|\?)\s*\]\s+(\S+)\s+(.*)$")
ERR = re.compile(r"^\s*ERROR:.*?([A-Za-z0-9_-]{11}):\s*(.*)$")
HDR = re.compile(r"^##\s+Playlist:.*\((\d+)\s+videos?\)")


def parse_plan(path):
    items, errors, declared = [], [], None
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        m = HDR.match(line)
        if m:
            declared = int(m.group(1))
            continue
        m = ITEM.match(line)
        if m:
            items.append({"idx": m.group(1), "id": m.group(2), "title": m.group(3).strip()})
            continue
        m = ERR.match(line)
        if m:
            errors.append({"id": m.group(1), "reason": m.group(2).strip()})
    return items, errors, declared


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    plan_file, pipe_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    items, errors, declared = parse_plan(plan_file)
    if not items:
        sys.exit(
            "No plan items parsed -- the plan file is empty or its format changed. "
            "Re-capture the raw --plan output and check the ITEM regex before "
            "trusting a 'nothing new' answer."
        )

    archive_path = pipe_dir / ".archive.txt"
    archive = set(archive_path.read_text().split()) if archive_path.exists() else set()
    ov_path = pipe_dir / "overrides.json"
    try:
        known = set(json.loads(ov_path.read_text())) if ov_path.exists() else set()
    except (OSError, ValueError):
        known = set()

    seen, dups, new = set(), [], []
    for it in items:
        if it["id"] in seen:
            dups.append(it)
            continue
        seen.add(it["id"])
        if it["id"] not in archive and it["id"] not in known:
            new.append(it)

    print(f"declared by YouTube : {declared}")
    print(
        f"listed items        : {len(items)} ({len(seen)} unique, {len(dups)} duplicate listings)"
    )
    print(f"unavailable/private : {len(errors)}")
    print(f"already ingested    : {len(seen) - len(new)}")
    print(f"NEW                 : {len(new)}")
    if declared is not None and declared != len(items) + len(errors):
        print(
            f"NOTE: declared {declared} != listed {len(items)} + unavailable {len(errors)} "
            "-- re-check before reporting."
        )
    for it in new:
        print(f"  [{it['idx']}] https://youtu.be/{it['id']}  {it['title']}")
    for it in dups:
        print(f"  duplicate listing: {it['id']}  {it['title']}")
    if errors:
        print("unavailable/private:")
        for e in errors:
            print(f"  {e['id']}  {e['reason']}")
    missing = sorted(archive - seen)
    if missing:
        print(f"archive ids not in this playlist (from other runs): {len(missing)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""Plan-file tools for the yt-dlp ingest pipeline (read-only, stdlib only).

Usage:
    plan_tools.py delta    <plan.txt> <pipeline_dir>   # what in the plan is new?
    plan_tools.py coverage <plan.txt> <overrides.json> # does every plan ID have an override?

Capture the plan first, from the pipeline folder:
    uv run --no-project yt_dl.py --plan <url> > plan.txt

Both subcommands share one parser, so they cannot disagree about the plan format:
  * The index is right-aligned and space-padded ("[  1]", "[  ?]" for a single video),
    so a naive ^\[\d+\] matches nothing. A plan that parses to zero items aborts (exit 2):
    reporting "nothing new" / "nothing missing" from it is a silent false negative.
  * Video IDs are [A-Za-z0-9_-]{11}; \w misses IDs that start with "-" or "_".
  * Unavailable/private videos come from ERROR lines (and show up as index gaps);
    they are never counted as new or missing.
  * A playlist may list the same video twice: IDs are deduped, duplicates reported apart.

Exit codes: 0 ok · 1 coverage has MISSING ids · 2 bad input (empty parse, unreadable JSON).
"""

import json
import pathlib
import re
import sys

ID = r"[A-Za-z0-9_-]{11}"
ITEM = re.compile(rf"^\[\s*(\d+|\?)\s*\]\s+({ID})(?:\s+(.*))?$")
ERR = re.compile(rf"^\s*ERROR:\s*(?:\[[^\]]+\]\s*)?({ID}):\s*(.*)$")
HDR = re.compile(r"^##\s+Playlist:.*\((\d+)\s+videos?\)")


def die(msg):
    """Print `msg` to stderr and exit 2 (bad input)."""
    print(msg, file=sys.stderr)
    sys.exit(2)


def parse_plan(path):
    """Return (items, errors, declared) parsed from a `--plan` capture."""
    items, errors, declared = [], [], None
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if m := HDR.match(line):
            declared = int(m.group(1))
        elif m := ITEM.match(line):
            items.append({"idx": m.group(1), "id": m.group(2), "title": (m.group(3) or "").strip()})
        elif m := ERR.match(line):
            errors.append({"id": m.group(1), "reason": m.group(2).strip()})
    if not items:
        die(
            "No plan items parsed -- the plan file is empty or its format changed. "
            "Re-capture the raw --plan output and check the ITEM regex before trusting "
            "a 'nothing new' / 'nothing missing' answer."
        )
    return items, errors, declared


def load_ids(path):
    """Return the set of keys of a JSON object file; abort on unreadable/invalid JSON."""
    try:
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        die(f"Cannot read {path}: {exc} -- refusing to treat it as empty.")
    if not isinstance(data, dict):
        die(f"{path} must be a JSON object keyed by video ID.")
    return set(data)


def split_items(items):
    """Return ({id: first item}, duplicate items)."""
    seen, dups = {}, []
    for it in items:
        if it["id"] in seen:
            dups.append(it)
        else:
            seen[it["id"]] = it
    return seen, dups


def delta(plan_file, pipe_dir):
    items, errors, declared = parse_plan(plan_file)
    pipe_dir = pathlib.Path(pipe_dir)
    archive_path = pipe_dir / ".archive.txt"
    archive = set(archive_path.read_text().split()) if archive_path.exists() else set()
    ov_path = pipe_dir / "overrides.json"
    known = load_ids(ov_path) if ov_path.exists() else set()

    unique, dups = split_items(items)
    new = [it for vid, it in unique.items() if vid not in archive and vid not in known]

    print(f"declared by YouTube : {declared}")
    print(f"listed items        : {len(items)} ({len(unique)} unique, {len(dups)} duplicate)")
    print(f"unavailable/private : {len(errors)}")
    print(f"already ingested    : {len(unique) - len(new)}")
    print(f"NEW                 : {len(new)}")
    if declared is not None and declared != len(items) + len(errors):
        print(
            f"NOTE: declared {declared} != listed {len(items)} + unavailable {len(errors)}; re-check."
        )
    for it in new:
        print(f"  [{it['idx']}] https://youtu.be/{it['id']}  {it['title']}")
    for it in dups:
        print(f"  duplicate listing: {it['id']}  {it['title']}")
    for e in errors:
        print(f"  unavailable: {e['id']}  {e['reason']}")
    other = len(archive - set(unique))
    if other:
        print(f"archive ids not in this playlist (other runs): {other}")
    return 0


def coverage(plan_file, overrides_file):
    items, errors, _ = parse_plan(plan_file)
    overrides = load_ids(overrides_file)
    unique, dups = split_items(items)
    unavailable = {e["id"] for e in errors}

    missing = sorted(set(unique) - overrides - unavailable)
    extra = sorted(overrides - set(unique))
    print(
        f"plan entries: {len(items)} | unique: {len(unique)} "
        f"| unavailable: {len(unavailable)} | overrides: {len(overrides)}"
    )
    print(f"MISSING (must be empty): {missing}")
    print(f"EXTRA (dup occurrence or typo): {extra}")
    print(f"DUPLICATES (one override is enough): {sorted({d['id'] for d in dups})}")
    return 1 if missing else 0


def main(argv):
    if len(argv) != 4 or argv[1] not in ("delta", "coverage"):
        die(__doc__)
    return (delta if argv[1] == "delta" else coverage)(argv[2], argv[3])


if __name__ == "__main__":
    sys.exit(main(sys.argv))

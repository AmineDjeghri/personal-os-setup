#!/usr/bin/env python3
"""Pad markdown tables so markdownlint MD060 (style: aligned) passes.

MD060 measures DISPLAY width: an emoji presentation sequence (a codepoint followed
by U+FE0F) and any East-Asian W/F codepoint occupy two columns, while variation
selectors, ZWJ and combining marks occupy none. markdown-table-formatter and
str.ljust() pad by codepoints, so emoji tables stay ragged and keep failing.

Usage:
    python3 align_md_tables.py PATH [PATH ...]          # rewrite in place
    python3 align_md_tables.py --check PATH [PATH ...]  # report only, exit 1 if dirty

PATH is a markdown file or a directory (walked recursively, skipping .git,
.venv, node_modules, site, dist). Fenced code blocks are skipped. Each table
keeps its own separator style (``| --- |`` vs ``|---|``) so an already-aligned
separator line is never rewritten; only the rows that are actually ragged move.

Limitation: cells are split on unescaped ``|`` only, so a literal pipe inside a
code span (``a | b``) inflates the column count. Verify with the linter after a
run; MD060 is the arbiter.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "site", "dist", ".ruff_cache", ".pytest_cache"}
FENCE = re.compile(r"^\s*(```|~~~)")
SEP_CELL = re.compile(r"^:?-{1,}:?$")


def display_width(text: str) -> int:
    width = 0
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\ufe0f\ufe0e\u200d" or unicodedata.combining(ch):
            i += 1
            continue
        if i + 1 < n and text[i + 1] == "\u200d":  # ZWJ cluster: one 2-column glyph
            width += 2
            i += 2
            while i + 1 < n and text[i + 1] == "\u200d":
                i += 2
            i += 1
            continue
        if i + 1 < n and text[i + 1] == "\ufe0f":  # emoji presentation
            width += 2
            i += 2
            continue
        width += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        i += 1
    return width


def is_row(line: str) -> bool:
    return line.lstrip().startswith("|")


def split_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    cells, current, escaped = [], [], False
    for ch in body:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip())
    return cells


def pipe_columns(line: str) -> list[int]:
    columns, col = [], 0
    for ch in line:
        if ch == "|":
            columns.append(col)
        col += display_width(ch)
    return columns


def repad(block: list[str]) -> list[str]:
    rows = [split_cells(line) for line in block]
    ncols = max(len(r) for r in rows)
    for row in rows:
        row.extend([""] * (ncols - len(row)))
    is_sep = len(rows) > 1 and all(SEP_CELL.match(c) for c in rows[1] if c)
    widths = [
        max(display_width(row[c]) for idx, row in enumerate(rows) if not (is_sep and idx == 1))
        for c in range(ncols)
    ]
    out = []
    for idx, row in enumerate(rows):
        cells = []
        for c, value in enumerate(row):
            target = widths[c]
            if is_sep and idx == 1:
                left = value.startswith(":")
                right = value.endswith(":") and len(value) > 1
                body = "-" * max(1, target - int(left) - int(right))
                cells.append((":" if left else "") + body + (":" if right else ""))
            else:
                cells.append(value + " " * max(0, target - display_width(value)))
        out.append("| " + " | ".join(cells) + " |")
    # Keep the original separator line verbatim when its pipes already line up.
    if is_sep and pipe_columns(out[1]) == pipe_columns(block[1]):
        out[1] = block[1]
    return out


def process(path: Path, check: bool) -> bool:
    """Return True when the file needed (or, with --check, would need) a change."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    changed = False
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if not in_fence and is_row(line):
            j = i
            while j + 1 < len(lines) and is_row(lines[j + 1]):
                j += 1
            block = lines[i : j + 1]
            if len(block) >= 3:
                new_block = repad(block)
                if new_block != block:
                    changed = True
                    print(f"{'misaligned' if check else 'aligned'}: {path}: table at line {i + 1}")
                    block = block if check else new_block
            out.extend(block)
            i = j + 1
            continue
        out.append(line)
        i += 1
    if changed and not check:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def iter_markdown(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in targets:
        path = Path(raw)
        if path.is_dir():
            files.extend(
                p for p in sorted(path.rglob("*.md")) if not (set(p.parts) & SKIP_DIRS)
            )
        elif path.suffix == ".md":
            files.append(path)
    return files


def main(argv: list[str]) -> int:
    check = "--check" in argv
    targets = [a for a in argv if a != "--check"]
    if not targets:
        print(__doc__.strip().splitlines()[0])
        print("usage: align_md_tables.py [--check] PATH [PATH ...]", file=sys.stderr)
        return 2
    dirty = [f for f in iter_markdown(targets) if process(f, check)]
    if check:
        print(f"\n{len(dirty)} file(s) with misaligned tables")
        return 1 if dirty else 0
    print(f"\n{len(dirty)} file(s) rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

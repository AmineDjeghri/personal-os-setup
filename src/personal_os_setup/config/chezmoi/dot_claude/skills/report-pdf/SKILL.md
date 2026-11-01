---
name: report-pdf
description: Use when a big review list needs a PDF instead of chat.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# PDF reports for heavy review tasks

A pass that touches hundreds of items (files, records, config entries, dependencies, findings,
renames) cannot be signed off from chat: the message carries the counts and the decision, the PDF
carries the evidence and every item. Same artefact before a write (`nothing written yet — proposal`)
and after it (`applied, N/N re-read`). Headless chromium, no LaTeX, no extra dependency. Domain-neutral:
the spec's columns, labels and grouping key are whatever the task needs.

## When to Use

- more than ~30 rows to review: per-item `old → new`, file lists, bulk renames or migrations,
  dependency or config audits, scan/review findings, metadata or tag audits
- the user must approve before you write, or verify what you wrote afterwards
- an audit whose whole value is the full enumeration
- **Don't use for:** a handful of rows (answer in chat), or a list nobody will re-open

## Report shape

Build these sections in this order — opening with methodology earns "how many items did you change?".

1. **Subtitle** — state the state of the world in one line: `Nothing written yet — this is the proposal`
   or `Applied 27 Oct 2026, 03:35 · 214/214 re-read`.
2. **Stat cards** — items changed, items scanned, result count, defects left (0 mixed, 0 lost).
3. **What was wrong** — the defect in two or three sentences, with the evidence that proves it, and
   explicitly what it was *not* caused by when that was checked.
4. **What was written** — one bullet per field: its source, its rule, and what was left untouched.
5. **Change list** — one row per item: identifier (path, name, key), old value (red), new value
   (green), grouped by the *resulting* value, never by where the item came from.
6. **Still to do on your side** — the exact commands left to the user (resync, rescan), verbatim.

Counts come from re-reading the targets after the write, not from the earlier proposal.

## How to Run

1. Keep the pass log machine-readable while you work — one JSON object per item
   `{path, before, after, source}`. It doubles as the rollback record and the report input.
2. Write a spec (schema below) from that log.
3. Render:

```bash
uv run --no-project scripts/report_pdf.py spec.json --out /config/<task>-<date>.pdf
```

4. Send the PDF as `MEDIA:/config/...pdf` with a few lines of chat: the leading count, the one
   caveat that matters, the commands left to the user.

### Spec schema

```json
{
  "title": "Dependency pin cleanup — services/*",
  "subtitle": "Applied 27 Oct 2026, 03:35 · 214/214 re-read",
  "stats": [{"n": "214", "l": "entries changed"}, {"n": "0", "l": "conflicts left"}],
  "sections": [
    {"type": "para", "title": "What was wrong", "text": "…"},
    {"type": "bullets", "title": "What was written", "items": ["…", "…"]},
    {"type": "table", "title": "Change list", "group_by": "after",
     "columns": [{"key": "path", "label": "Item", "cls": "p"},
                 {"key": "before", "label": "Old value", "cls": "o"},
                 {"key": "after", "label": "New value", "cls": "n"},
                 {"key": "note", "label": "Note"}],
     "rows": [{"path": "services/api/pyproject.toml", "before": "httpx==0.24", "after": "httpx==0.27", "note": "…"}]},
    {"type": "table", "title": "Unchanged", "columns": [], "rows": []}
  ]
}
```

Rows may be plain lists instead of dicts when you pass `columns` as a header-only list.

## Verification

- The script prints `wrote <path> · N page(s) · X KB` and fails loudly on a zero-page render.
- `--shot page1.png` renders the first page for a `vision_analyze` pass: cards aligned, table headers
  present, nothing overflowing.
- A report that says *applied* must quote a read-back count produced by the writer itself
  (`214/214 match their intended value`), not a success count of the command it ran.

## Pitfalls

- **No `pdftoppm` on this box.** Don't reach for it to eyeball the PDF; use `--shot` (chromium's own
  screenshot) on the HTML source instead.
- **chromium's dbus warning is noise.** `Failed to call method: … NameHasOwner` appears on every run
  and does not affect the output.
- **Rows split across pages** without `page-break-inside: avoid` — the CSS ships with it, keep it if
  you edit the template.
- **Long paths overflow** the first column: `overflow-wrap: anywhere` (also ship the fix for Arabic
  and Hebrew cells: `unicode-bidi: plaintext`, or the row renders reversed).
- **Trust the HTML, not a low-res screenshot, for characters.** A `/` in a path can look like a `\`
  once downscaled — grep the rendered HTML before "fixing" a separator.
- **A PDF is not an approval.** Attaching a proposal still waits for an explicit yes; a timed-out
  prompt is not consent, and the report must keep saying `nothing written yet` until it is applied.
- **Don't paste the list into chat as well.** Two copies drift; the chat keeps the counts only.
- **Exotic filename characters render as tofu** (`⧸`, emoji) if the font lacks them — the row is still
  correct, so don't chase it; the underlying path is unchanged.

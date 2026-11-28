# Reports: one spec → PDF, HTML or PNG

A pass that touches hundreds of items (files, records, config entries, dependencies, findings,
renames) cannot be signed off from chat: the message carries the counts and the decision, the report
carries the evidence and every item. Same artefact before a write (`nothing written yet — proposal`)
and after it (`applied, N/N re-read`). Domain-neutral: the spec's columns, labels and grouping key are
whatever the task needs. Headless Chromium, no LaTeX, no extra dependency.

## When to Use

- more than ~30 rows to review: per-item `old → new`, file lists, bulk renames or migrations,
  dependency or config audits, scan/review findings, metadata or tag audits
- the user must approve before you write, or verify what you wrote afterwards
- an audit whose whole value is the full enumeration
- **Don't use for:** a handful of rows (answer in chat), or a list nobody will re-open

## Pick the output

| Output | Flag | Layout | Use it when |
|---|---|---|---|
| PDF | `--pdf` | A4 print | a document to keep, attach or print |
| HTML | `--html` | screen, responsive, one self-contained file | the reader opens it in a browser, searches, scrolls; no browser needed to build |
| PNG | `--png` | screen layout screenshot, 2× scale | the reader needs an image (a chat that only shows pictures, a README, an issue) |

Combine flags to get several from the same spec in one run. Ask the user when the right one is unclear.
Never hand-write a second template: every output comes from this spec.

## Report shape

Build these sections in this order — opening with methodology earns "how many items did you change?".

1. **Subtitle** — the state of the world in one line: `Nothing written yet — this is the proposal`
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
3. Render (paths relative to the skill directory, the parent of `references/`; put outputs where the user will look, with the date
   in the name):

```bash
uv run --no-project scripts/report.py spec.json --pdf out/<task>-<date>.pdf
uv run --no-project scripts/report.py spec.json --html out/<task>-<date>.html
uv run --no-project scripts/report.py spec.json --png out/<task>-<date>.png
```

4. Deliver the file(s) with a few lines of chat: the leading count, the one caveat that matters, the
   commands left to the user.

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

Column classes: `p` path/identifier (monospace, wraps), `o` old value (red), `n` new value (green).
`group_by` gathers rows by that key, in first-seen order; `group_meta_key` adds a note to each group header.

## Screenshots

`--pdf` and `--png` need a Chromium-based browser; see Browser in [SKILL.md](../SKILL.md).
`--html` needs no browser.

`--png` measures the full page and screenshots it at 1100 px wide. A page taller than `--slice`
(default 3000 CSS px) becomes numbered slices `<name>-1.png`, `<name>-2.png`... `--scale` sets the
pixel density (default 2).

## Verification

- The script prints one `wrote <path> · <format> · …` line per file and fails loudly when the browser
  produces nothing or the PDF has zero pages.
- Look at it: open a PNG (or render one with `--png` next to the PDF) and check that cards are aligned,
  table headers are present and nothing overflows.
- HTML is one line; count sections with `grep -o '<h2>' <file> | wc -l` (not `grep -c`).
- A report that says *applied* must quote a read-back count produced by the writer itself
  (`214/214 match their intended value`), not a success count of the command it ran.

## Pitfalls

- **The browser's dbus warning is noise.** `Failed to call method: … NameHasOwner` does not affect the output.
- **Rows split across pages** without `page-break-inside: avoid` — the CSS ships with it; keep it if
  you edit the template. PNG slices cut at a fixed height and may split a row; that is cosmetic.
- **Long paths overflow** the first column: `overflow-wrap: anywhere` (and `unicode-bidi: plaintext`
  for Arabic and Hebrew cells, or the row renders reversed) — both ship in the CSS.
- **Trust the HTML, not a low-res screenshot, for characters.** A `/` can look like a `\` once
  downscaled — grep the HTML before "fixing" a separator.
- **Exotic characters render as tofu** (`⧸`, emoji) if the font lacks them — the data is still correct.
- **A report is not an approval.** Attaching a proposal still waits for an explicit yes; a timed-out
  prompt is not consent, and the report must keep saying `nothing written yet` until it is applied.
- **Don't paste the list into chat as well.** Two copies drift; the chat keeps the counts only.
- **Strip secrets, tokens, hostnames and other people's names** from the spec — the outputs sit on
  disk in plain text and may be shared or committed later.

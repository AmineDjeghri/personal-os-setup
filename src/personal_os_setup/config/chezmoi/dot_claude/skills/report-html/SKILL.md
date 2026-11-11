---
name: report-html
description: "Use when a report should open in the Hermes Webapp."
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [report, html, webapp, preview, delivery]
    related_skills: [report-pdf, artifact-delivery]
---

# HTML reports for the Hermes Webapp

The Webapp (`webapp.enabled: true`, served by the gateway, behind its own sign-in) renders an `.html` file
live from its **file tree** (verified on this box). Its **Artifacts** view is documented to list session
outputs too, but that path is unverified here. That makes it the right viewer
for a report he has to scroll, search or follow — nothing is published, no URL to clean up afterwards.
Telegram cannot render HTML (it arrives as a file), so on Telegram the answer stays PDF.

## When to Use

- He says he can open the Hermes web UI / Desktop, or asks for an HTML report, "a link", or "something I can check".
- A review list, audit or comparison that is too big for chat (same threshold as `report-pdf`: ~30+ rows).
- **Not for:** a handful of rows (answer in chat), or a chat that only reaches him through Telegram (send the PDF).

## How to Run

1. Build the **same JSON spec** `report-pdf` uses (title, subtitle, stats, sections — schema in that skill).
   One source, two exits; never hand-write a second HTML template.
2. Render the screen layout next to the earlier reports, with the date in the name:

```bash
uv run --no-project ~/.claude/skills/report-pdf/scripts/report_pdf.py spec.json --html /config/<task>-<date>.html
# add --out /config/<task>-<date>.pdf to get the PDF fallback from the same spec in one run
```

   `--html` alone skips chromium entirely (pure string render); the output is one self-contained file —
   inline CSS, no external requests, a viewport meta so it also works on a phone.
3. Tell him where to open it, in one line: **Webapp → file tree → `/config/<task>-<date>.html`**
   (or Artifacts, unverified). Port and address are his; do not paste the sign-in link or any credential.

## Why the Webapp and not HA `www/`

| | Webapp file tree | HA `www/reports/` |
|---|---|---|
| Who can read it | the signed-in Hermes user | every client on the LAN, **no login** |
| Cleanup | none, it is a local file | must delete afterwards |
| Write path | plain file write | `ha_write_file`, needs a ha-mcp *Tool Security Policies* approval that expires in ~4 min |

Use `www/` only when the reader has no Hermes login (a guest, a family member), and then follow the hosting
rules in `artifact-delivery`.

## Verify before you hand it over

- The script prints `wrote <path> · screen html · N KB`. The file is one line, so count sections with
  `grep -o '<h2>' <file> | wc -l` (not `grep -c`).
- Eyeball it: `chromium --headless --no-sandbox --disable-gpu --hide-scrollbars --window-size=1100,1500
  --screenshot=out.png file:///…/report.html`, then `vision_analyze` (cards in a row, headers present, no
  clipped ids).
- A session on Telegram **cannot** confirm the Webapp renders it (no `desktop_preview`, no sign-in). Say so,
  give the path, and let him confirm; fall back to the PDF if it does not render.

## Content rules (inherited from `report-pdf`)

- State the world in the subtitle: `nothing written yet — proposal` or `applied, N/N re-read`.
- The chat message carries the counts and the decision; the page carries the evidence. Never paste the same
  list into chat as well.
- Strip secrets, tokens, hostnames and other people's names before writing the file — it sits on disk in
  plain text and may later be committed by accident.

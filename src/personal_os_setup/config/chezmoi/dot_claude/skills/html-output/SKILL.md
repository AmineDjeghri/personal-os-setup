---
name: html-output
description: Build HTML and render it to PDF or PNG with a headless browser, in three modes. Report - a review list, audit or comparison too big for chat (~30+ rows) as PDF, HTML page or PNG screenshots from one JSON spec. Diagram - an architecture, infrastructure, deployment, data-pipeline, CI/CD or request-flow schema with real product logos, rendered to PNG for docs, READMEs or slides. Deck - an offline HTML slide presentation with editable schemas and real product icons, instead of PowerPoint or Google Slides.
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [report, pdf, png, screenshot, diagram, architecture, presentation, slides, html]
---

# HTML output: reports, diagrams, decks

Everything here is HTML first, then optionally printed or screenshotted by a headless Chromium-based
browser. The HTML is the source: edit it and re-render instead of redrawing an image. Offline, no
build step, Python standard library only (plus Node for the optional deck render).

## Pick the mode, then read only its page

| The user wants | Mode | Read | Entry point |
|---|---|---|---|
| a big list, audit or before/after review as PDF, HTML or PNG | report | [references/report.md](references/report.md) | `scripts/report.py` |
| an architecture / flow / topology picture (PNG) | diagram | [references/diagram.md](references/diagram.md), then [design rules](references/design-rules.md) | `scripts/diagram.py` |
| slides to present in a browser | deck | [references/deck.md](references/deck.md), then [layouts](references/deck-layouts.md) | `scripts/deck.py`, `scripts/render.mjs` |

A deck slide that needs a schema uses the diagram design rules and `scripts/diagram.py icons`.
Resolve every path relative to this skill directory.

## Browser (shared)

`report.py` (`--pdf`, `--png`) and `diagram.py render` share [scripts/browser.py](scripts/browser.py).
It takes, in order: `--browser`, `CHROME_BIN`, known names on `PATH` (Chromium, Chrome, Edge, Brave,
Helium, Vivaldi, Opera, Thorium), the macOS apps in `/Applications`, the Windows installs under
`%ProgramFiles%`, `%ProgramFiles(x86)%` and `%LOCALAPPDATA%` (Edge ships with Windows 10/11), then any
`PATH` executable named like a Chromium fork. If none is found, look before giving up
(`ls /usr/bin /opt | grep -i -E 'chrom|helium|brave|edge|vivaldi'`, `flatpak list`, `ls /Applications`,
`where /r "%ProgramFiles%" msedge.exe`) and pass `--browser`. Install nothing implicitly.

The deck's `render.mjs` uses an existing Playwright + Chromium instead (see the deck page).

## Rules for every mode

- Always look at the rendered PNG/PDF before delivering: the checks do not catch clipping, wrapped
  titles or crossed arrows. If nothing could be rendered, say so; do not claim visual verification.
- Never draw or approximate a product logo: fetch it with `scripts/diagram.py icons` (pinned sources,
  recorded in `icons/SOURCES.md`) or use a neutral line icon.
- Strip secrets, tokens, hostnames and other people's names from the content: outputs sit on disk in
  plain text and get shared.
- Run the destination repository's own checks when the output is added to a repository.

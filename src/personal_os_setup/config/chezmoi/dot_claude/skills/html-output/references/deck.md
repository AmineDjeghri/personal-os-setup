# Decks: offline HTML slide presentations

Reuse the approved visual system in [the layout starter](../assets/deck-template/index.html):
Blue, restrained red accents, spacious 16:9 slides, configurable branding, editable text
and diagrams. Keep the topic and slide count appropriate to the new request.
The starter's sample content is placeholder text, not a requirement for future presentations.

## Create or edit

Resolve paths below relative to the skill directory (the parent of `references/`). For a new presentation:

```bash
python3 scripts/deck.py new /path/to/new-deck --title "Presentation title"
```

The destination must not exist. The default team label is **Presentation**.
Optional `--team`, `--footer` and `--logo` flags customize branding. The output is portable: HTML, CSS, JavaScript and local assets,
with no build step or CDN. Copy the complete output directory when sharing.

Edit the new deck's slide sections and `deck.css`. Choose examples from the
starter or read [layout guidance](deck-layouts.md). Maintain the existing
appearance when editing an approved deck. Source claims from the user's materials
and add source links inside each slide's `.notes` element. Illustrative starter
text is not factual source material.

For a deck covering several stages, consider section-divider slides at major
transitions. Show the overall flow and highlight the segment being discussed,
with the other stages de-emphasized. Add these only when they help orientation,
and respect requested positions. See [section dividers](deck-layouts.md#section-dividers).

Set shared branding once on `#deck`: `data-team`, `data-logo`, `data-logo-alt`,
`data-footer`, and `data-min-scale`. The player creates logos, footers, accessible
slide labels, overview entries and page totals. Do not repeat those in each slide.
Give slides unique stable ids so shared links keep working after reordering.

## Shared code and assets

The canonical `theme.css` and `player.js` live in `assets/deck-template/`. Generated
decks contain independent copies so they work outside this repository. Refresh
those copies explicitly after a shared improvement:

```bash
python3 scripts/deck.py sync /path/to/existing-deck
```

This updates only the shared CSS and player. It preserves content, `deck.css`
and logos. Make presentation-specific changes in `deck.css`.

## Schemas and icons on demand

The skill bundles no icons or logos. When a slide needs an architecture or flow schema, use
real product icons from popular, maintained GitHub repositories, downloaded into the deck so
it stays offline. Never draw or approximate a logo.

Fetch icons with the diagram helper (`scripts/diagram.py icons`), which pins
each source and records it in `icons/SOURCES.md` inside the deck:

```bash
python3 scripts/diagram.py icons /path/to/deck simple:postgresql aws:lambda simple:kubernetes
```

Use the first source that has the logo:

1. `simple:<slug>`: [Simple Icons](https://github.com/simple-icons/simple-icons) (CC0), brand colors added.
2. `aws:<service>` / `logos:<slug>`: [gilbarbara/logos](https://github.com/gilbarbara/logos) (CC0), full-color, incl. AWS services.
3. `devicon:<slug>`: [devicon](https://github.com/devicons/devicon) (MIT).
4. `lucide:<slug>`: [Lucide](https://github.com/lucide-icons/lucide) (ISC), neutral line icons for components without a public logo (`lucide:database`, `lucide:server`).
5. `url:<name>=<raw.githubusercontent.com URL>`: another repo with thousands of stars, recent
   commits and a reusable license (check with `gh api repos/<owner>/<repo>`), pinned to a commit.

A component without a public logo gets a neutral line icon on a colored tile. Logos stay
trademarks of their owners. Preserve proportions and brand colors. Use the user's supplied
logo or an authorized brand asset through `--logo`; a logo is optional and the default header
shows the team name.

For a full schema (zones, node cards, request/answer/lookup arrows, numbered badges, legend),
follow the [diagram design rules](design-rules.md) and place
the diagram markup in a slide's `.content` using the deck's 1440px coordinate space and unique
SVG marker ids. For a standalone schema image, follow [diagrams](diagram.md) instead.

## Verify and deliver

```bash
python3 scripts/deck.py check /path/to/deck --runtime
```

This checks offline dependencies, settings, unique ids, arrow markers and player
controls. It does not prove visual quality. When an existing Playwright and
Chromium installation are available, render every slide and a PDF:

```bash
node scripts/render.mjs /path/to/deck --output /path/to/review
```

Use `--playwright /path/to/playwright` and `--browser /path/to/chromium` when the
installations are outside normal module/browser discovery. Do not install tools
implicitly. Inspect the screenshots and PDF, then fix clipping and crowded slides.
The player exposes layout warnings through the toolbar and
`window.presentation.inspect()`. Its fitting floor is 85%, with a 17px minimum
for checked body text on the slide canvas. Shorten or split dense content rather
than reducing that floor. Canvas font sizes scale with the viewing window.

Retain keyboard navigation, overview, notes, fullscreen and print controls. If
browser rendering is unavailable, report visual/PDF verification as unperformed.
Deliver the deck entry point and explain that its adjacent files travel with it.
Run the destination repository's own required checks when modifying repository files.

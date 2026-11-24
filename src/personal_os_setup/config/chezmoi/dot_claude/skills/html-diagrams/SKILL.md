---
name: html-diagrams
description: Create any architecture, infrastructure, deployment, data-pipeline, CI/CD or request-flow diagram as a self-contained HTML page with real product logos where they exist, then screenshot it to a PNG. Use when asked for an architecture schema, "what runs where" diagram or flow picture for docs, READMEs or slides, or to restyle an existing diagram image with colors and icons. Technology-neutral: cloud, on-prem, Kubernetes, SaaS or mixed.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# HTML diagrams

Build the diagram as HTML, then render it to PNG with a headless browser. The HTML is the
source: edit it and re-render instead of redrawing an image. The look is the approved one:
tinted zones, white node cards with a colored accent and logo tile, blue request / red answer /
grey dashed lookup arrows, numbered step badges and a legend. The starter is a neutral
client / service / database / external API sample, not a requirement: replace everything, and
drop the arrow kinds, badges or chip your diagram does not need.

## Create

Resolve paths relative to this skill directory.

```bash
python3 scripts/diagram.py new /path/to/diagram --title "Diagram title"
```

The destination must not exist. It receives `index.html` (one file, CSS inline). The starter
uses only built-in line icons, so nothing is downloaded. Add logos for your components with
`--icons simple:postgresql aws:lambda` or later with the `icons` command below.

Edit `index.html`: replace the sample zones, nodes, edges and badges. Read
[design rules](references/design-rules.md) first: it lists the classes, colors, the layout
recipe per diagram type (request flow, deployment topology, pipeline, C4 context) and the
geometry rules for edges.

## Icons

Logos are downloaded on demand into the diagram's `icons/` and recorded, with the pinned
source, in `icons/SOURCES.md`:

```bash
python3 scripts/diagram.py icons /path/to/diagram simple:kubernetes aws:sqs aws:logo simple:terraform
```

Use the first source that has the logo:

1. `simple:<slug>`: [Simple Icons](https://github.com/simple-icons/simple-icons) (26k stars, CC0,
   pinned to a release). Monochrome, so known brand colors are applied (PostgreSQL, Terraform,
   Kubernetes, Redis, Docker, Grafana, JFrog, Helm...); an unlisted slug gets a neutral dark color. It no longer carries AWS service logos.
2. `aws:<service>` / `logos:<slug>`: [gilbarbara/logos](https://github.com/gilbarbara/logos)
   (6.8k stars, CC0, pinned to a commit). Full-color logos, including the AWS service icons
   (`aws:lambda`, `aws:s3`, `aws:dynamodb`, `aws:eventbridge`, `aws:sqs`, `aws:api-gateway`...) and
   `aws:logo` for the AWS mark. `logos:<slug>` takes any file name from its `logos/` folder.
3. `devicon:<slug>`: [devicon](https://github.com/devicons/devicon) (11.9k stars, MIT, pinned to a
   commit), original variant.
4. Still missing: look in another **popular, maintained** repository and pass its raw file with
   `url:<name>=https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>.svg`. Popular means
   thousands of stars and recent commits, with a license that allows reuse. Check both with
   `gh api repos/<owner>/<repo>`. Do not use a small or abandoned repository, even if it has the
   exact icon; pick a neighbouring logo from a popular one, or a neutral line icon, instead. Pin a
   commit, never a branch.

Do not draw or approximate a logo. A component with no public logo (an internal API, a client,
an unnamed service) gets a neutral line icon from the sprite in the starter, on a colored tile.
Logos remain trademarks of their owners (AWS icons follow the AWS trademark guidelines). Keep
`SOURCES.md` next to the diagram.

## Check and render

```bash
python3 scripts/diagram.py check /path/to/diagram
python3 scripts/diagram.py render /path/to/diagram -o /path/to/diagram.png
```

`check` is offline: icons referenced exist, no remote URLs, nodes inside the canvas and not
overlapping, arrow markers defined, step badges unique. `render` runs the check, then takes the
screenshot with the first Chromium-based browser found (Chrome, Edge, Brave, Chromium;
`--browser` or `CHROME_BIN` to choose). It needs no Playwright and installs nothing. Scale
defaults to 2 (a 2000x830 canvas gives a 4000x1660 PNG).

Always open the PNG and look at it: `check` does not catch a wrapped title, an arrow that
crosses a card or a badge sitting on a label. Fix, re-render, look again. If no browser is
available, say the PNG was not rendered.

## Deliver

Keep `index.html` and `icons/` together as the source and put the PNG where it is used.
Describe the diagram in the alt text of the image (the numbered steps, in order). Run the
destination repository's own checks when adding files to it.

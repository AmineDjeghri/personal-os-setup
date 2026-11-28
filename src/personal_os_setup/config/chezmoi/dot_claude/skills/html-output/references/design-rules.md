# Design rules

The starter `assets/diagram-template/index.html` is the reference. A diagram is a fixed canvas
(`#canvas`, size also in `<meta name="diagram-size">`) with absolutely positioned elements.

## Elements

- **Zone** `div.zone.<platform|cloud|workload>`: a tinted rounded box grouping nodes (a cluster,
  a cloud account, a VPC, a network segment, a trust boundary). The three names are only color
  slots: any grouping can use any of them. Its `.tag` is the title with a logo. Add a color by defining
  `--x`, `--x-bg`, `--x-line` and a `.zone.x` rule.
- **Node** `div.node.<color>-c`: a white card, `left/top/width/height` in px inline. Content is a
  `.ic` tile plus `<b>` (name, one line) and `<small>` (technology).
  - `.ic.brand`: a full-color logo that carries its own colored square (AWS service icons).
  - `.ic.logo`: a monochrome or brand logo on a white tile (PostgreSQL, Redis).
  - `.ic` with `<svg><use href="#i-..."></svg>`: neutral line icon on the node color.
  - `.node.col`: stacked layout for narrow cards (databases, buckets).
  - `.node.dashed.ext-c`: external or optional component, no accent bar.
- **Node colors** by category, not by team or vendor: `platform-c` (shared services),
  `cloud-c` (managed or cloud services), `workload-c` (your applications), `data-c` (data
  stores), `ext-c` (external), `client-c` (callers).
- **Edge**: an SVG `path` in `svg.edges`, in canvas coordinates, using only horizontal and
  vertical segments. Start and end exactly on a node side (the arrow marker ends on the edge of
  the card, never inside it). Three kinds only:
  - blue, solid: request (the path of the call going in);
  - red, solid: answer (the path coming back);
  - grey, dashed: lookup and data (reads, storage, configuration).
- **Badge** `div.badge.req|ans`: a numbered circle centered on an edge segment, numbered in the <!-- codespell:ignore ans -->
  order the flow happens. Blue for requests, red for answers. Describe the numbered steps in the
  image alt text. Optional: leave badges out of diagrams that show structure, not a sequence.
- **Chip** `div.chip`: a small pill for a cross-cutting fact (for example the tool that provisions
  a zone). Optional.
- **Legend**: `div.legend`, only the line kinds actually used.

## Diagram types

Pick the recipe that matches the question the diagram answers. Arrow kinds and badges are tools,
not requirements: use only those the story needs.

| Type | Zones | Edges | Badges |
|---|---|---|---|
| Request flow | callers, platform, workloads, left to right | blue request, red answer, grey lookups | yes, in order |
| Deployment / infrastructure topology | one zone per cluster, account, VPC or site | grey dashed for connections; blue only for the main traffic path | no |
| Data pipeline | sources, processing, storage, consumers, left to right | one solid direction (blue), grey for config and lookups | optional |
| CI/CD | one zone per stage or environment | blue for promotion, grey for artifacts and secrets | yes, per stage |
| System context (C4 level 1) | one zone for the system, externals around it | grey dashed, labelled in the node `<small>` | no |

## Layout

- Read left to right: callers, then the path in the middle, then workloads, with data stores
  and external services below or on the right.
- Keep 40 to 60 px between cards and at least 25 px between a card and its zone border; titles
  stay on one line.
- Route an edge around a card, never through it. Where two edges would cross, move a card
  before adding a bend. A long dashed lookup may run along the bottom, behind a chip.
- Do not add a node, color or arrow kind that the story does not need. One diagram tells one
  flow.
- Text: node names 27 to 34 px, technology 22 px, zone titles 24 px. A name that wraps means the
  card is too narrow: widen it.

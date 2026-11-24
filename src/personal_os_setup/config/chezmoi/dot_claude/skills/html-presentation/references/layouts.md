# Layouts and authoring

Open `assets/template/index.html` for seven rendered examples. The canvas is
1600 × 900 and scales as one composition. Keep each slide focused on one topic.

## Slide contract

```html
<section class="slide" id="slide-topic">
  <main>
    <p class="eyebrow">Section label</p>
    <h1>A concise subject</h1>
    <p class="subtitle">Optional context for the diagram or explanation.</p>
    <div class="content">
      <!-- The slide body goes here. -->
    </div>
  </main>
  <aside class="notes">
    <h3>Presenter notes</h3>
    <p>Explanation for the presenter, including material caveats.</p>
  </aside>
</section>
```

The player adds the header and footer. Retain the outer controls from the starter.
Use stable ids for links, one `h1` per slide, and unique SVG marker ids throughout
the whole document. Keep diagrams inside `.content` so fitting can measure them.

## Available examples

| Layout | Markup | Best use |
| --- | --- | --- |
| Cover | `.slide.cover`, `.lead`, optional `.cover-track` | Minimal introduction |
| Process | `.diagram.flow` with `.node` children | A simple sequence |
| Comparison | `.compare`, `.column-title`, `.steps` | Parallel alternatives |
| Commands | `.command-layout`, `.terminal`, `.command-steps` | Commands and expected results |
| Definitions | `.definitions` with `article` children | A few related concepts |
| Table | `.comparison-table` | Compare the same criteria |
| References | `.reference-layout`, `.reference`, `.closing` | Source links and next steps |

The process example uses flexible HTML nodes with simple connecting arrows.
For branches, preserve the original deck's editable SVG connector approach:
`.diagram` is a 1440px coordinate space, nodes use `left`, `top`, `width` and
`min-height`, and an SVG beneath them contains paths and arrow markers. Keep
arrows out of text. Explicitly size the diagram to include the lowest node.

## Section dividers

Use an orientation slide when the presentation moves to another major stage of
an architecture, process or workflow. Place it before that stage's detailed
slides, or at the positions requested by the user. A short deck or a simple
narrative may not need any. Do not prescribe a fixed count or slide numbers.

Show a simplified version of the overall flow, keeping the same service order
and reusing the deck's existing icons. Highlight the current segment with a clear
label and color or underline. De-emphasize the remaining stages while keeping
their labels readable. Use a short title naming the upcoming subject and avoid
adding detailed commands or dense explanations.

For example, a deck about a release process can introduce its build section by
highlighting the build stage of the flow, then its deployment section by
highlighting the deploy stage. Adapt the stages to the new topic. These examples
do not require any particular services or bundled icons in the skill.

## Customization

Set deck-wide labels on `#deck`. `data-logo=""` gives a text-only team header.
Use the standard CSS custom properties (`--blue`, `--red`, `--ink`, `--muted`,
`--paper`, `--line`, `--green`) in `deck.css` to adapt colors. The skill contains no brand images. Keep supplied logos
unchanged apart from supported brand color variants and preserve their proportions.

Copy complete slide sections to add layouts. Remove unused examples and service
icons when they do not help the new deck. Do not replace the narrative with a
fixed seven-slide sequence. The player calculates numbering from the actual slides.

## Readability and verification

Aim for the starter's 58px titles and 25px body text. Notes and source links may
be denser because the presenter opens them separately. Fitting may reduce body
content to 85% of its authored size. The layout report flags further overflow and
checked body text below 17px. Diagram labels and other small text still need visual
inspection. Shorten copy, simplify a diagram or split a slide when it is crowded.

Keyboard controls: arrows/Space, Home/End, O for overview, N for notes, F for
fullscreen, P for print and Escape to close overlays. Print uses a 16 × 9 inch
page with backgrounds. PDF page count and visual layout require browser review.

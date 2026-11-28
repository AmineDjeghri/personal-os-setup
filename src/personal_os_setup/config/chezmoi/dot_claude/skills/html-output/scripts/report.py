#!/usr/bin/env -S uv run --no-project --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render one JSON report spec to PDF, HTML and/or PNG screenshots with a headless Chromium browser.

    uv run --no-project report.py spec.json --pdf out/report.pdf
    uv run --no-project report.py spec.json --html out/report.html
    uv run --no-project report.py spec.json --png out/report.png
    uv run --no-project report.py spec.json --pdf r.pdf --html r.html --png r.png   # all three at once

Spec (all keys optional except title/sections):

    {
      "title": "Dependency pin cleanup",
      "subtitle": "Applied 27 Oct 2026, 03:35 · 214/214 re-read",
      "stats": [{"n": "214", "l": "entries changed"}],
      "sections": [
        {"type": "para",    "title": "...", "text": "..."},
        {"type": "bullets", "title": "...", "items": ["..."]},
        {"type": "table",   "title": "...", "group_by": "after",
         "columns": [{"key": "path", "label": "Item", "cls": "p"}],
         "rows": [{"path": "services/api/pyproject.toml"}]}
      ]
    }

--html needs no browser. --pdf and --png need a Chromium-based one (see browser.py): --browser,
CHROME_BIN, known names and install paths on Linux/macOS/Windows, then a PATH scan. A page taller than --slice px is written as
numbered PNG slices (report-1.png, report-2.png, ...). Exit code is non-zero when nothing is produced.
"""

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from browser import find_browser

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 9.4pt; color: #1a1a1a; }
h1 { font-size: 19pt; margin: 0 0 2mm; }
h2 { font-size: 12.5pt; margin: 7mm 0 2mm; border-bottom: 1px solid #ddd; padding-bottom: 1mm; }
.sub { color: #666; margin: 0 0 5mm; }
.stats { display: flex; gap: 4mm; margin: 4mm 0 2mm; }
.card { border: 1px solid #ddd; border-radius: 3px; padding: 3mm 4mm; flex: 1; }
.card .n { font-size: 15pt; font-weight: 600; }
.card .l { font-size: 8pt; color: #666; text-transform: uppercase; letter-spacing: .04em; }
table { width: 100%; border-collapse: collapse; }
td, th { padding: 1.1mm 1.6mm; text-align: left; vertical-align: top; border-bottom: .4px solid #eee; }
th { font-size: 8pt; text-transform: uppercase; color: #666; border-bottom: 1px solid #bbb; }
tr.grp td { background: #f5f6f8; padding-top: 2mm; }
tr { page-break-inside: avoid; }
.p { font-size: 8pt; color: #333; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.o { color: #b02020; font-size: 8pt; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.n { color: #175c2a; font-size: 8pt; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.meta { color: #666; font-size: 8pt; }
ul { margin: 1mm 0 0 4mm; padding: 0; }
li { margin: .8mm 0; }
code { background: #f2f2f2; padding: 0 1mm; border-radius: 2px; font-size: 8.4pt; }
"""

# Screen layout for a browser tab and PNG screenshots: fluid width, real pixel sizes, scrolling tables.
# The print CSS above is A4-in-points and reads tiny on a monitor.
SCREEN_CSS = """
body { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; font-size: 15px; line-height: 1.5;
  color: #1a1a1a; max-width: 980px; margin: 0 auto; padding: 20px 16px 60px; background: #fff; }
h1 { font-size: 26px; margin: 0 0 4px; }
h2 { font-size: 18px; margin: 30px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
.sub { color: #666; margin: 0 0 18px; }
.stats { display: flex; flex-wrap: wrap; gap: 10px; margin: 14px 0; }
.card { border: 1px solid #ddd; border-radius: 6px; padding: 10px 14px; flex: 1 1 140px; }
.card .n { font-size: 24px; font-weight: 600; color: #175c2a; }
.card .l { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: .04em; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
td, th { padding: 6px 8px; text-align: left; vertical-align: top; border-bottom: 1px solid #eee; }
th { font-size: 11px; text-transform: uppercase; color: #666; border-bottom: 1px solid #bbb; }
tr.grp td { background: #f5f6f8; }
.p { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.o { color: #b02020; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.n { color: #175c2a; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px; overflow-wrap: anywhere; unicode-bidi: plaintext; }
.meta { color: #666; font-size: 12px; }
ul { margin: 4px 0 0 20px; padding: 0; }
li { margin: 5px 0; }
code { background: #f2f2f2; padding: 0 4px; border-radius: 3px; font-size: 12px; }
"""


def esc(v):
    return html.escape("" if v is None else str(v))


def render_section(sec):
    kind = sec.get("type", "para")
    title = f"<h2>{esc(sec['title'])}</h2>" if sec.get("title") else ""
    if kind == "para":
        body = f"<p>{esc(sec.get('text', ''))}</p>"
    elif kind == "bullets":
        body = "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in sec.get("items", [])) + "</ul>"
    elif kind == "table":
        cols = sec.get("columns", [])
        rows = sec.get("rows", [])
        head = "".join(f"<th>{esc(c.get('label', c.get('key')))}</th>" for c in cols)
        group_by = sec.get("group_by")
        if group_by:  # stable sort so each group appears once, rows keep their order inside it
            key = lambda r: str(r.get(group_by, "") if isinstance(r, dict) else r[0])  # noqa: E731
            order = {}
            for r in rows:
                order.setdefault(key(r), len(order))
            rows = sorted(rows, key=lambda r: order[key(r)])
        out, last = [f"<table><tr>{head}</tr>"], object()
        for row in rows:
            if group_by:
                gval = row.get(group_by) if isinstance(row, dict) else row[0]
                if gval != last:
                    last = gval
                    n = sum(
                        1
                        for r in rows
                        if (r.get(group_by) if isinstance(r, dict) else r[0]) == gval
                    )
                    meta = row.get(sec.get("group_meta_key", ""), "")
                    tail = (
                        f' <span class="meta">— {esc(meta)} · {n} item(s)</span>'
                        if meta
                        else f' <span class="meta">— {n} item(s)</span>'
                    )
                    span = len(cols) or 1
                    out.append(
                        f'<tr class="grp"><td colspan="{span}"><b>{esc(gval)}</b>{tail}</td></tr>'
                    )
            cells = []
            for c in cols:
                val = row.get(c["key"], "") if isinstance(row, dict) else ""
                cells.append(f'<td class="{esc(c.get("cls", ""))}">{esc(val)}</td>')
            out.append("<tr>" + "".join(cells) + "</tr>")
        body = "".join(out) + "</table>"
    else:
        raise SystemExit(f"unknown section type: {kind}")
    return title + body


def build_html(spec, css=CSS):
    stats = "".join(
        f'<div class="card"><div class="n">{esc(s.get("n"))}</div>'
        f'<div class="l">{esc(s.get("l"))}</div></div>'
        for s in spec.get("stats", [])
    )
    blocks = "".join(render_section(s) for s in spec.get("sections", []))
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(spec.get("title", "Report"))}</title><style>{css}</style></head><body>
<h1>{esc(spec.get("title", "Report"))}</h1>
<p class="sub">{esc(spec.get("subtitle", ""))}</p>
{('<div class="stats">' + stats + "</div>") if stats else ""}
{blocks}
</body></html>"""


SCREEN_WIDTH = 1100  # px; the screen layout is max 980px wide plus gutters


def run_browser(browser, args):
    """Run the headless browser with the flags every render shares."""
    base = [browser, "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=180)


def write_pdf(browser, spec, out, workdir):
    """Print the A4 layout to a PDF and verify it has pages."""
    source = workdir / "print.html"
    source.write_text(build_html(spec), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = run_browser(browser, ["--no-pdf-header-footer", f"--print-to-pdf={out}", source.as_uri()])
    if not out.exists():
        print(proc.stdout[-800:], proc.stderr[-800:], sep="\n", file=sys.stderr)
        raise SystemExit("the browser produced no PDF")
    pages = len(re.findall(rb"/Type\s*/Page[^s]", out.read_bytes()))
    if pages == 0:
        raise SystemExit(f"{out} has no pages — template or input is broken")
    print(f"wrote {out} · pdf · {pages} page(s) · {out.stat().st_size // 1024 or 1} KB")


def page_height(browser, screen_html, workdir):
    """Measure the screen layout's full height by letting the browser lay it out once."""
    probe = workdir / "probe.html"
    script = "<script>document.body.dataset.h=document.documentElement.scrollHeight</script>"
    probe.write_text(screen_html.replace("</body>", script + "</body>"), encoding="utf-8")
    proc = run_browser(browser, [f"--window-size={SCREEN_WIDTH},800", "--dump-dom", probe.as_uri()])
    match = re.search(r'data-h="(\d+)"', proc.stdout)
    if not match:
        print(proc.stderr[-800:], file=sys.stderr)
        raise SystemExit("could not measure the page height for the screenshot")
    return int(match.group(1))


def write_png(browser, screen_html, out, workdir, slice_px, scale):
    """Screenshot the screen layout: one PNG, or numbered slices when taller than slice_px."""
    height = page_height(browser, screen_html, workdir)
    count = max(1, -(-height // slice_px))
    out.parent.mkdir(parents=True, exist_ok=True)
    targets = [out] if count == 1 else [out.with_name(f"{out.stem}-{i}{out.suffix}") for i in range(1, count + 1)]
    for index, target in enumerate(targets):
        offset = index * slice_px
        size = min(slice_px, height - offset)
        shift = f"<style>html{{overflow:hidden}}body{{margin-top:-{offset}px}}</style>"
        source = workdir / f"shot-{index}.html"
        source.write_text(screen_html.replace("</head>", shift + "</head>"), encoding="utf-8")
        run_browser(
            browser,
            [
                f"--window-size={SCREEN_WIDTH},{size}",
                f"--force-device-scale-factor={scale}",
                f"--screenshot={target}",
                source.as_uri(),
            ],
        )
        if not target.exists():
            raise SystemExit(f"screenshot failed: {target}")
        print(f"wrote {target} · png · {SCREEN_WIDTH}x{size} css px · scale {scale}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="JSON spec path")
    ap.add_argument("--pdf", help="write the A4 print layout as a PDF here")
    ap.add_argument("--html", help="write the self-contained screen layout here (no browser needed)")
    ap.add_argument("--png", help="screenshot the screen layout to this PNG (sliced when tall)")
    ap.add_argument("--slice", type=int, default=3000, help="max CSS px per PNG slice (default 3000)")
    ap.add_argument("--scale", type=float, default=2, help="PNG device scale factor (default 2)")
    ap.add_argument("--browser", help="path to a Chromium-based browser (else CHROME_BIN, then auto)")
    args = ap.parse_args()
    if not (args.pdf or args.html or args.png):
        ap.error("give at least one of --pdf, --html, --png")

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    screen_html = build_html(spec, SCREEN_CSS)
    if args.html:
        out = Path(args.html)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(screen_html, encoding="utf-8")
        print(f"wrote {out} · html · {out.stat().st_size // 1024 or 1} KB")
    if not (args.pdf or args.png):
        return
    browser = find_browser(args.browser)
    with tempfile.TemporaryDirectory(prefix="report_") as tmp:
        workdir = Path(tmp)
        if args.pdf:
            write_pdf(browser, spec, Path(args.pdf), workdir)
        if args.png:
            write_png(browser, screen_html, Path(args.png), workdir, args.slice, args.scale)


if __name__ == "__main__":
    main()

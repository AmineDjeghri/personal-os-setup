#!/usr/bin/env -S uv run --no-project --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Render a PDF report from a JSON spec with headless chromium.

    uv run --no-project report_pdf.py spec.json --out /config/report-2026-10-27.pdf [--shot page1.png]

Spec (all keys optional except title/sections):

    {
      "title": "Album restore — YouTube folders",
      "subtitle": "Applied 27 Oct 2026, 03:35 · 214/214 re-read",
      "stats": [{"n": "214", "l": "files changed"}],
      "sections": [
        {"type": "para",    "title": "...", "text": "..."},
        {"type": "bullets", "title": "...", "items": ["..."]},
        {"type": "table",   "title": "...", "group_by": "after",
         "columns": [{"key": "path", "label": "File", "cls": "p"}],
         "rows": [{"path": "Live/001 - x.m4a"}]}
      ]
    }

Exit code is non-zero when chromium produces no page, so a broken template fails the task
instead of shipping an empty document.
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def build_html(spec):
    stats = "".join(
        f'<div class="card"><div class="n">{esc(s.get("n"))}</div>'
        f'<div class="l">{esc(s.get("l"))}</div></div>'
        for s in spec.get("stats", [])
    )
    blocks = "".join(render_section(s) for s in spec.get("sections", []))
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{esc(spec.get("title", "Report"))}</title><style>{CSS}</style></head><body>
<h1>{esc(spec.get("title", "Report"))}</h1>
<p class="sub">{esc(spec.get("subtitle", ""))}</p>
{('<div class="stats">' + stats + "</div>") if stats else ""}
{blocks}
</body></html>"""


def chromium():
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("no chromium/chrome on PATH")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", help="JSON spec path")
    ap.add_argument("--out", required=True, help="output PDF path")
    ap.add_argument("--shot", help="also render page 1 to this PNG (for a vision check)")
    ap.add_argument("--keep-html", help="write the intermediate HTML here instead of a temp file")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    html_doc = build_html(spec)
    html_path = (
        Path(args.keep_html)
        if args.keep_html
        else Path(tempfile.mkdtemp(prefix="report_pdf_")) / "report.html"
    )
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html_doc, encoding="utf-8")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    base = [chromium(), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars"]
    proc = subprocess.run(
        base + ["--no-pdf-header-footer", f"--print-to-pdf={out}", f"file://{html_path.resolve()}"],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if not out.exists():
        print(proc.stdout[-800:], proc.stderr[-800:], sep="\n", file=sys.stderr)
        raise SystemExit("chromium produced no PDF")

    pages = len(re.findall(rb"/Type\s*/Page[^s]", out.read_bytes()))
    if pages == 0:
        raise SystemExit(f"{out} has no pages — template or input is broken")
    print(f"wrote {out} · {pages} page(s) · {out.stat().st_size // 1024} KB · html: {html_path}")

    if args.shot:
        shot = Path(args.shot)
        subprocess.run(
            base
            + ["--window-size=1200,1500", f"--screenshot={shot}", f"file://{html_path.resolve()}"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if not shot.exists():
            raise SystemExit("screenshot failed")
        print(f"screenshot: {shot}")


if __name__ == "__main__":
    main()

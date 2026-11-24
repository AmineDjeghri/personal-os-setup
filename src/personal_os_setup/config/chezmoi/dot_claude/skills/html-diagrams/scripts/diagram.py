#!/usr/bin/env python3
"""Create, check and render offline HTML diagrams of any architecture with the standard library."""

import argparse
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen


SKILL = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL / "assets" / "template" / "index.html"

SIMPLE_ICONS_TAG = "16.38.1"
SIMPLE_ICONS_URL = "https://raw.githubusercontent.com/simple-icons/simple-icons/{tag}/icons/{slug}.svg"
LOGOS_COMMIT = "875d71c5a8e4aa90a33f8b3ea15b8945de9cc183"  # pragma: allowlist secret
LOGOS_URL = "https://raw.githubusercontent.com/gilbarbara/logos/{commit}/logos/{slug}.svg"
DEVICON_COMMIT = "32fe1d3b3f36ad11f90ab94f7db59738139c2bf6"  # pragma: allowlist secret
DEVICON_URL = "https://raw.githubusercontent.com/devicons/devicon/{commit}/icons/{slug}/{slug}-{variant}.svg"
RAW_HOST = "https://raw.githubusercontent.com/"
# Colour applied to the monochrome Simple Icons so the logos keep their brand identity.
BRAND_COLORS = {
    "postgresql": "4169E1", "redhatopenshift": "EE0000", "terraform": "844FBA",
    "kubernetes": "326CE5", "redis": "FF4438", "mongodb": "47A248", "mysql": "4479A1",
    "docker": "2496ED", "github": "181717", "githubactions": "2088FF", "python": "3776AB",
    "fastapi": "009688", "nginx": "009639", "grafana": "F46800", "prometheus": "E6522C",
    "opentelemetry": "425CC7", "apachekafka": "231F20", "rabbitmq": "FF6600",
    "elasticsearch": "005571", "openai": "412991", "anthropic": "D97757",
    "jfrog": "40BE46", "helm": "0F1689", "argo": "EF7B4D", "keycloak": "4D4D4D",
}
DEFAULT_COLOR = "171A3B"
BROWSERS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge",
    "chrome", "msedge",
)


def fetch(url):
    request = Request(url, headers={"User-Agent": "html-diagrams-skill"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except (URLError, OSError) as error:
        raise SystemExit(f"Cannot download {url}: {error}") from error


def resolve_icon(spec):
    """Return (file name, svg text, source line) for one icon spec.

    simple:<slug>      Simple Icons (monochrome, brand color added)
    logos:<slug>       gilbarbara/logos (full-color logos, many products and AWS services)
    aws:<service>      shortcut for logos:aws-<service>; aws:logo is the AWS mark
    devicon:<slug>     devicons/devicon (original variant)
    url:<name>=<url>   any raw.githubusercontent.com file, for a popular repo not listed above
    """
    kind, _, name = spec.partition(":")
    if kind == "simple" and name:
        svg = fetch(SIMPLE_ICONS_URL.format(tag=SIMPLE_ICONS_TAG, slug=name))
        color = BRAND_COLORS.get(name, DEFAULT_COLOR)
        svg = svg.replace("<svg ", f'<svg fill="#{color}" ', 1)
        source = f"simple-icons v{SIMPLE_ICONS_TAG} icons/{name}.svg (CC0, fill #{color} added)"
        return name, svg, source
    if kind == "aws" and name:
        slug = "aws" if name == "logo" else f"aws-{name.lower()}"
        kind, name = "logos", slug
    if kind == "logos" and name:
        svg = fetch(LOGOS_URL.format(commit=LOGOS_COMMIT, slug=name))
        source = f"gilbarbara/logos {LOGOS_COMMIT[:7]} logos/{name}.svg (CC0; logos remain trademarks of their owners)"
        return name, svg, source
    if kind == "devicon" and name:
        svg = fetch(DEVICON_URL.format(commit=DEVICON_COMMIT, slug=name, variant="original"))
        source = f"devicons/devicon {DEVICON_COMMIT[:7]} icons/{name}/{name}-original.svg (MIT; logos remain trademarks of their owners)"
        return name, svg, source
    if kind == "url" and "=" in name:
        file, _, url = name.partition("=")
        if not url.startswith(RAW_HOST) or not re.fullmatch(r"[\w.-]+", file):
            raise SystemExit(f"url: needs <name>=<{RAW_HOST}...> and a plain file name, got '{spec}'.")
        svg = fetch(url)
        source = f"{url} (popular repository; check its license and star count before use)"
        return file, svg, source
    raise SystemExit(
        f"Invalid icon '{spec}'. Use simple:<slug>, logos:<slug>, aws:<service>, aws:logo, "
        "devicon:<slug> or url:<name>=<raw.githubusercontent.com URL>."
    )


def write_icons(directory, specs):
    icons = directory / "icons"
    icons.mkdir(exist_ok=True)
    sources = icons / "SOURCES.md"
    lines = sources.read_text().splitlines() if sources.exists() else ["# Icon sources", ""]
    for spec in specs:
        file, svg, source = resolve_icon(spec)
        (icons / f"{file}.svg").write_text(svg)
        entry = f"- `{file}.svg`: {source}."
        lines = [line for line in lines if not line.startswith(f"- `{file}.svg`")] + [entry]
        print(f"icons/{file}.svg  <- {spec}")
    sources.write_text("\n".join(lines) + "\n")


def command_new(args):
    directory = Path(args.directory)
    if directory.exists():
        raise SystemExit(f"{directory} already exists; choose a new directory.")
    directory.mkdir(parents=True)
    html = TEMPLATE.read_text().replace("{{TITLE}}", args.title)
    (directory / "index.html").write_text(html)
    if args.icons:
        write_icons(directory, [spec for spec in args.icons])
    elif TEMPLATE_ICONS and not args.no_icons:
        write_icons(directory, TEMPLATE_ICONS)
    print(f"Created {directory}/index.html")


def command_icons(args):
    directory = Path(args.directory)
    if not (directory / "index.html").exists():
        raise SystemExit(f"{directory}/index.html not found")
    write_icons(directory, args.specs)


TEMPLATE_ICONS = []  # the starter uses only built-in line icons


class DiagramParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.size = None
        self.references = []
        self.nodes = []
        self.badges = []
        self.edge_markers = set()
        self.marker_ids = set()
        self.text_stack = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = (attrs.get("class") or "").split()
        if tag == "meta" and attrs.get("name") == "diagram-size":
            self.size = attrs.get("content")
        for key in ("src", "href"):
            value = attrs.get(key)
            if value and not value.startswith("#"):
                self.references.append(value)
        if tag == "marker" and attrs.get("id"):
            self.marker_ids.add(attrs["id"])
        if attrs.get("marker-end"):
            self.edge_markers.add(attrs["marker-end"])
        if "node" in classes:
            self.nodes.append(attrs.get("style") or "")
        if "badge" in classes:
            self.badges.append(None)
            self.text_stack.append(len(self.badges) - 1)
        elif self.text_stack:
            self.text_stack.append(None)

    def handle_data(self, data):
        if self.text_stack and self.text_stack[-1] is not None:
            index = self.text_stack[-1]
            self.badges[index] = ((self.badges[index] or "") + data).strip()

    def handle_endtag(self, tag):
        if self.text_stack:
            self.text_stack.pop()


def box(style):
    values = {}
    for key in ("left", "top", "width", "height"):
        match = re.search(rf"(?:^|;)\s*{key}\s*:\s*(-?\d+(?:\.\d+)?)px", style)
        if not match:
            return None
        values[key] = float(match.group(1))
    return values["left"], values["top"], values["width"], values["height"]


def diagram_size(parser):
    match = re.fullmatch(r"(\d+)x(\d+)", parser.size or "")
    if not match:
        raise SystemExit('Add <meta name="diagram-size" content="WIDTHxHEIGHT"> to the diagram.')
    return int(match.group(1)), int(match.group(2))


def check(directory):
    index = directory / "index.html"
    if not index.exists():
        raise SystemExit(f"{index} not found")
    text = index.read_text()
    parser = DiagramParser()
    parser.feed(text)
    problems = []
    width, height = diagram_size(parser)
    for reference in parser.references:
        if re.match(r"[a-z]+:", reference, re.I):
            problems.append(f"Remote or absolute reference (must be offline): {reference}")
        elif not (directory / reference).exists():
            problems.append(f"Missing file: {reference} (fetch it with: diagram.py icons {directory} <icon>)")
    boxes = []
    for style in parser.nodes:
        rect = box(style)
        if rect is None:
            problems.append(f"Node without left/top/width/height in px: {style!r}")
            continue
        left, top, w, h = rect
        if left < 0 or top < 0 or left + w > width or top + h > height:
            problems.append(f"Node outside the {width}x{height} canvas: {style!r}")
        boxes.append(rect)
    for i, (ax, ay, aw, ah) in enumerate(boxes):
        for bx, by, bw, bh in boxes[i + 1:]:
            if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                problems.append(f"Nodes overlap at ({ax:.0f},{ay:.0f}) and ({bx:.0f},{by:.0f})")
    for marker in parser.edge_markers:
        match = re.fullmatch(r"url\(#([^)]+)\)", marker)
        if not match or match.group(1) not in parser.marker_ids:
            problems.append(f"Arrow marker not defined: {marker}")
    numbers = [badge for badge in parser.badges if badge]
    if len(numbers) != len(set(numbers)):
        problems.append(f"Duplicate step badges: {numbers}")
    return problems, (width, height), len(boxes)


def command_check(args):
    problems, size, nodes = check(Path(args.directory))
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{nodes} nodes, canvas {size[0]}x{size[1]}: {'OK' if not problems else str(len(problems)) + ' problem(s)'}")
    return 1 if problems else 0


def find_browser(explicit):
    candidates = [explicit] if explicit else [os.environ.get("CHROME_BIN")] + list(BROWSERS)
    for candidate in filter(None, candidates):
        found = shutil.which(candidate) or (candidate if Path(candidate).exists() else None)
        if found:
            return found
    raise SystemExit(
        "No Chromium-based browser found (Chrome, Edge, Brave, Chromium). "
        "Pass --browser /path/to/browser or set CHROME_BIN. The PNG was not rendered."
    )


def command_render(args):
    directory = Path(args.directory).resolve()
    problems, (width, height), _ = check(directory)
    if problems and not args.force:
        for problem in problems:
            print(f"FAIL {problem}")
        raise SystemExit("Fix the problems above, or pass --force to render anyway.")
    output = Path(args.output) if args.output else directory / "diagram.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    browser = find_browser(args.browser)
    with tempfile.TemporaryDirectory() as profile:
        command = [
            browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            f"--user-data-dir={profile}", f"--force-device-scale-factor={args.scale}",
            f"--window-size={width},{height}", f"--screenshot={output.resolve()}",
            (directory / "index.html").as_uri(),
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if not output.exists() or output.stat().st_size == 0:
        print(result.stderr[-800:], file=sys.stderr)
        raise SystemExit("The browser did not produce a screenshot.")
    print(f"{output} ({width * args.scale}x{height * args.scale}px)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="create a diagram from the approved template")
    new.add_argument("directory")
    new.add_argument("--title", default="Architecture diagram")
    new.add_argument("--icons", nargs="*", help="fetch only these icons (simple:<slug>, aws:<service>)")
    new.add_argument("--no-icons", action="store_true", help="do not download the template's icons")
    new.set_defaults(run=command_new)
    icons = sub.add_parser("icons", help="download logos into <directory>/icons")
    icons.add_argument("directory")
    icons.add_argument("specs", nargs="+", metavar="ICON")
    icons.set_defaults(run=command_icons)
    checker = sub.add_parser("check", help="offline layout and dependency check")
    checker.add_argument("directory")
    checker.set_defaults(run=command_check)
    render = sub.add_parser("render", help="screenshot index.html to a PNG")
    render.add_argument("directory")
    render.add_argument("-o", "--output", help="PNG path (default: <directory>/diagram.png)")
    render.add_argument("--scale", type=int, default=2, help="device scale factor (default 2)")
    render.add_argument("--browser", help="Chromium-based browser executable")
    render.add_argument("--force", action="store_true", help="render even if check reports problems")
    render.set_defaults(run=command_render)
    args = parser.parse_args()
    sys.exit(args.run(args) or 0)


if __name__ == "__main__":
    main()

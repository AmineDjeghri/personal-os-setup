---
name: docs-site
description: Use when adding/editing documentation pages, or building/previewing/deploying the properdocs (mkdocs) site — "add a doc page", "preview the docs site", "deploy docs", "why isn't my new page showing up". Covers properdocs.yml's docs_dir:. quirk, the exclude-glob trap for new top-level directories, and the auto-generated API reference/example pages.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Docs site (`properdocs`/mkdocs) in personal-os-setup

The config file is `properdocs.yml` at repo root (not the conventional `mkdocs.yml`).

## The one thing to know before touching anything here

**`docs_dir: .`** — the entire repo root is the mkdocs source, not a `docs/` subfolder in the usual sense. This is why `README.md`, `CHANGELOG.md`, and `CONTRIBUTING.md` at repo root are directly part of the published site (see the `nav:` block). It also means **any new top-level directory you add to the repo is crawled into the docs build unless excluded**. The `mkdocs-exclude` plugin's glob list in `properdocs.yml` is what keeps `.venv/**`, `dist/**`, `.ruff_cache/**`, `.github/**`, etc. out.

**If you add a new top-level directory** (a cache dir, a build output dir, a new tool's data dir) — add it to that exclude list in `properdocs.yml`, or it may get published. The `mkdocs-same-dir` plugin is the other half of making `docs_dir: .` work at all.

## Auto-generated pages — don't hand-maintain these

- `scripts/gen_doc_stubs.py` (via the `gen-files` plugin) walks `src/**/*.py` and generates one API-reference stub per module under `package/<path>.md` (`::: <dotted.module.path>` mkdocstrings directive) plus `package/SUMMARY.md`. **Adding a new Python module under `src/` automatically gets an API-reference page** — no manual nav edit needed. Skips `__init__.py` files.
- `scripts/gen_example_pages.py` does the same for `docs/examples/**/*.py`, pulling each file's module docstring (via `ast.get_docstring`) into `docs/examples/index.md`'s table. A `SyntaxError` in an example file is swallowed silently — the build won't fail, the example just loses its description in the index.
- `literate-nav` (`nav_file: SUMMARY.md`) drives the `API Reference:`/examples sub-navs from those generated `SUMMARY.md` files.

## Adding a genuinely new hand-written doc page

Files added under `docs/` generally surface automatically via `same-dir`/mkdocs-material's directory conventions. If it needs a specific slot in the top-level nav, edit `properdocs.yml`'s `nav:` list directly. **Always verify with a local preview** — don't assume placement; auto-discovery interacting with `docs_dir: .` is not always intuitive.

## Building/previewing

- `make deploy-doc-local` → `install-dev` then `properdocs build && properdocs serve` — local live preview, run this after any docs change before opening a PR (per `CONTRIBUTING.md`).
- `make deploy-doc-gh` → `properdocs build && properdocs gh-deploy` — **pushes directly to the `gh-pages` branch**. This is a remote-mutating action; only run it deliberately (normally CI does this for you, see below), and confirm with the user before running it yourself.

## When docs actually go live in CI

`main-release.yml` deploys docs **only if `main-release`'s semantic-release step actually cut a release** (`if: needs.release.outputs.released == 'true'`). A PR containing only `docs:`/`chore:`-type commits merged to `main` will **not** trigger a docs deploy, even though the docs content changed — because those commit types don't trigger a version bump. If docs need to go live immediately, either bundle the doc change with a releasable commit (`feat`/`fix`/`perf`), or run `make deploy-doc-gh` manually (after confirming with the user — it pushes to a shared branch).

First-time GitHub Pages setup (not usually needed again): repo Settings → Actions → General → Workflow permissions → "Read and write permissions"; GitHub Pages settings → "Deploy from a branch" → `gh-pages`.

## Restructuring an existing page (splits, moves)

Two-track shape for a reader-facing guide: a *Quick start* part (numbered steps, ending in an "if
something doesn't work" symptom→fix list) followed by an *Advanced* part (how the pieces relate,
then one section per feature). When one page is serving two audiences, split it by topic instead of
deepening it further — cross-link both halves at top and bottom so a reader landing on either finds
the other.

When splitting: write the new page, trim the old one to its own topic, add the index bullet in
`docs/index.md` (nav is filesystem-derived — a new page appears on its own, but `docs/index.md`'s
link list is manual), cross-link both ways, and keep a moved page's images in whichever file still
references them (relative image paths break silently if the page leaves its PNGs behind). A page
move also needs every reference repointed in the same pass — including skill files, since a stale
pointer sends a future reader hunting for content that's moved.

**Verify with a URL-coverage check, not a re-read** — this passes the approval gate (a heredoc or
`python -c` for the same check does not):

```bash
git show HEAD:docs/<dir>/<old>.md | grep -oE 'https?://[^ )>`"]+' | sort -u > /tmp/old.urls
grep -hoE 'https?://[^ )>`"]+' docs/<dir>/<new>.md docs/<dir>/readme.md docs/index.md | sort -u > /tmp/new.urls
comm -23 /tmp/old.urls /tmp/new.urls    # anything here is a link the rewrite DROPPED
comm -13 /tmp/old.urls /tmp/new.urls    # only deliberate additions should show up here
```

`comm -23` output must be empty (or explained) before calling the restructure done. The URL check
says nothing about prose, though — re-read the new page for the small stuff a rewrite tends to thin
out (UI workarounds, screenshot captions, caveats).

## Repo files are CRLF with no `.gitattributes`

Unlike a repo that ships `text=auto` (which re-normalizes on every commit and can produce whole-file
diffs), this repo's files are CRLF-as-committed with autocrlf unset — git stores bytes as-is. A
surgical, CRLF-preserving edit therefore yields a small diff; check for a `.gitattributes` with
`text=auto` before assuming an edit here will force a whole-file rewrite (it won't, unless one gets
added later). A line-based patch tool may insert LF lines among CRLF ones — harmless mixed endings,
pre-commit hooks still pass.

## Published docs are public — some findings don't belong here

`docs/` is crawled into the published site (`docs_dir: .`), so anything written under it is public
advice. Never document a specific live exposure finding about a real deployment here (which network
path bypasses a specific safeguard, a real router/firewall state) — that's chat-only guidance for
whoever asked, never a doc section, even as a "for context" aside. When a security caveat is
deliberately kept out of a doc, say so in chat and name where the real fix lives instead of silently
omitting it. Before pushing anything to a public doc: scan for URLs, UUID/email/IPv4/hostname-shaped
values, and long token-shaped strings — a debrid/API key can hide percent-encoded inside a manifest
URL that looks harmless at a glance.

## Linked Files

- `references/docs-build.md` — how the mkdocstrings auto-stub walker works, the hyphenated-module-path
  trap when vendoring code that ships `.py` under a data dir, local build verification (`--python 3.14`
  gotcha), and the restructuring coverage-check procedure in full.

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

**`docs_dir: .`** — the entire repo root is the mkdocs source, not a `docs/` subfolder in the usual sense. That's why `README.md`, `CHANGELOG.md` and `CONTRIBUTING.md` at repo root are part of the published site (see the `nav:` block), and why **any new top-level directory you add is crawled into the docs build unless excluded**. The `mkdocs-exclude` plugin's glob list in `properdocs.yml` keeps `.venv/**`, `dist/**`, `.ruff_cache/**`, `.github/**`, etc. out; `mkdocs-same-dir` is the other half of making `docs_dir: .` work.

**If you add a new top-level directory** (a cache dir, a build output dir, a new tool's data dir) — add it to that exclude list, or it may get published.

## Auto-generated pages — don't hand-maintain these

- `scripts/gen_doc_stubs.py` (via the `gen-files` plugin) walks `src/**/*.py` and generates one API-reference stub per module under `package/<path>.md` (`::: <dotted.module.path>` mkdocstrings directive) plus `package/SUMMARY.md`. **A new module under `src/` automatically gets an API-reference page** — no manual nav edit. Skips `__init__.py`.
- `scripts/gen_example_pages.py` does the same for `docs/examples/**/*.py`, pulling each file's module docstring (via `ast.get_docstring`) into `docs/examples/index.md`'s table. A `SyntaxError` in an example is swallowed silently — the build won't fail, the example just loses its description.
- `literate-nav` (`nav_file: SUMMARY.md`) drives the `API Reference:`/examples sub-navs from those generated files.

## Adding a genuinely new hand-written doc page

Files added under `docs/` generally surface automatically via `same-dir`/mkdocs-material conventions. If a page needs a specific slot in the top-level nav, edit `properdocs.yml`'s `nav:` list directly. **Always verify with a local preview** — auto-discovery interacting with `docs_dir: .` isn't always intuitive.

## Building/previewing

- `make deploy-doc-local` → `install-dev` then `properdocs build && properdocs serve` — local live preview; run it after any docs change before opening a PR.
- `make deploy-doc-gh` → `properdocs build && properdocs gh-deploy` — **pushes directly to the `gh-pages` branch**. Remote-mutating: run it deliberately (CI normally does it), and confirm with the user first.

## When docs actually go live in CI

`main-release.yml` deploys docs **only if its semantic-release step cut a release**. A PR with only `docs:`/`chore:` commits merged to `main` will **not** deploy docs even though the content changed — those types don't bump the version. To publish immediately, bundle the doc change with a releasable commit (`feat`/`fix`/`perf`), or run `make deploy-doc-gh` after confirming with the user (it pushes to a shared branch).

First-time GitHub Pages setup (rarely needed again): repo Settings → Actions → General → Workflow permissions → "Read and write permissions"; Pages settings → "Deploy from a branch" → `gh-pages`.

## Restructuring an existing page (splits, moves)

Shape a reader-facing guide two-track: a *Quick start* part (numbered steps ending in a "if something doesn't work" symptom→fix list) then an *Advanced* part (how the pieces relate, then one section per feature). When one page serves two audiences, split it by topic rather than deepening it — cross-link both halves top and bottom.

When splitting: write the new page, trim the old one to its own topic, add the index bullet in `docs/index.md` (nav is filesystem-derived, but that link list is manual), cross-link both ways, and keep a moved page's images in whichever file still references them (relative image paths break silently). Repoint every reference in the same pass — including skill files, since a stale pointer sends a reader hunting for moved content.

**Verify a restructure with the URL-coverage check, not a re-read** — the procedure is in `references/docs-build.md`. It catches dropped links; it says nothing about prose, so still re-read the new page for the small things a rewrite thins out (workarounds, captions, caveats).

## Published docs are public — some findings don't belong here

`docs/` is crawled into the published site, so anything written under it is public advice. Never document a specific live exposure finding about a real deployment (which network path bypasses a safeguard, a real router/firewall state) — that's chat-only guidance. When a security caveat is deliberately kept out of a doc, say so in chat and name where the real fix lives. Before pushing to a public doc: scan for URLs, UUID/email/IPv4/hostname-shaped values and long token-shaped strings — a debrid/API key can hide percent-encoded inside a manifest URL that looks harmless.

## Linked Files

- `references/docs-build.md` — how the mkdocstrings auto-stub walker works, the hyphenated-module-path
  trap when vendoring code that ships `.py` under a data dir, local build verification (`--python 3.14`
  gotcha), and the URL-coverage check for restructures.

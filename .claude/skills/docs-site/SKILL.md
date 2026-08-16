---
name: docs-site
description: Use when adding/editing documentation pages, or building/previewing/deploying the properdocs (mkdocs) site — "add a doc page", "preview the docs site", "deploy docs", "why isn't my new page showing up". Covers properdocs.yml's docs_dir:. quirk, the exclude-glob trap for new top-level directories, and the auto-generated API reference/example pages.
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

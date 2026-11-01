# Docs build & deploy (properdocs/mkdocs)

Pipeline: `make deploy-doc-gh` → `properdocs gh-deploy -f properdocs.yml --strict` (CI Release workflow on
main; `deploy-doc-local` builds + serves). Docs build breaking on main = Release workflow fails.

## How the site is assembled (`docs_dir: .`)

- mkdocs crawls the REPO ROOT; the `exclude` plugin glob list in `properdocs.yml` keeps non-site
  content out (dot-dirs, `node_modules/**`, `venv/**` + `.venv/**`, and `src/personal_os_setup/config/**`,
  `AGENTS.md`, `CLAUDE.md`).
- gen-files runs `scripts/gen_doc_stubs.py`: it walks `src/**/*.py`, writes `package/<module>.md`
  (`::: <ident>`) plus a literate `package/SUMMARY.md`; mkdocstrings then resolves every stub
  against `paths: [src, docs]`. `nav:` maps `package/` = API Reference.

## Pitfall: the auto-stub walker aborts on data-tree .py

mkdocstrings kills the whole build (`Aborted with a BuildError!`, `Could not collect '<ident>'`)
when a generated stub names a module that is not importable. That happens whenever `.py` code
ships under a package DATA dir whose parents contain hyphens (`config/chezmoi/dot_claude/skills/
skill-creator/...` — hyphens are invalid in module paths). `gen_doc_stubs.py` therefore skips
everything under `src/personal_os_setup/config/` — data, not API. When vendoring third-party code that
ships `.py` inside the package tree, you need BOTH: (1) skip that subtree in the stub walker, (2) exclude
it from the mkdocs crawl — or the deploy breaks on merge, not locally.

## Local verification (reproduce CI before pushing)

```bash
make install-dev  # once, locked dev/docs tools in .venv
make docs-build   # strict build into a cleaned temporary directory
```

- Material's native Mermaid integration uses the SuperFences `fence_code_format` formatter.
  No additional Mermaid plugin or build-time CDN probe is needed.
- The strict build validates links and anchors. Published diagrams load in the browser.
- New top-level output folders must join the exclude glob because `docs_dir: .` crawls the root.

## URL-coverage check for a page restructure (split/move)

Run this instead of a re-read — it passes the approval gate, where a heredoc or `python -c` for the
same check does not:

```bash
git show HEAD:docs/<dir>/<old>.md | grep -oE 'https?://[^ )>`"]+' | sort -u > /tmp/old.urls
grep -hoE 'https?://[^ )>`"]+' docs/<dir>/<new>.md docs/<dir>/readme.md docs/index.md | sort -u > /tmp/new.urls
comm -23 /tmp/old.urls /tmp/new.urls    # anything here is a link the rewrite DROPPED
comm -13 /tmp/old.urls /tmp/new.urls    # only deliberate additions should show up here
```

`comm -23` output must be empty (or explained) before calling the restructure done. The check says
nothing about prose: re-read the new page for the small stuff a rewrite thins out (UI workarounds,
screenshot captions, caveats).

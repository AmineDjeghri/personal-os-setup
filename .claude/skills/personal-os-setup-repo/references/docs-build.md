# Docs build & deploy (properdocs/mkdocs)

Pipeline: `make deploy-doc-gh` → `properdocs build && properdocs gh-deploy` (CI Release workflow on
main; `deploy-doc-local` builds + serves). Docs build breaking on main = Release workflow fails.

## How the site is assembled (`docs_dir: .`)
- mkdocs crawls the REPO ROOT; the `exclude` plugin glob list in `properdocs.yml` keeps non-site
  content out (dot-dirs, `node_modules/**`, `venv/**` + `.venv/**`, and since 2026-09:
  `src/personal_os_setup/config/**`, `AGENTS.md`, `CLAUDE.md`).
- gen-files runs `scripts/gen_doc_stubs.py`: it walks `src/**/*.py`, writes `package/<module>.md`
  (`::: <ident>`) plus a literate `package/SUMMARY.md`; mkdocstrings then resolves every stub
  against `paths: [src, docs]`. `nav:` maps `package/` = API Reference.

## Pitfall: the auto-stub walker aborts on data-tree .py
mkdocstrings kills the whole build (`Aborted with a BuildError!`, `Could not collect '<ident>'`)
when a generated stub names a module that is not importable. That happens whenever `.py` code
ships under a package DATA dir whose parents contain hyphens (`config/chezmoi/dot_claude/skills/
skill-creator/...` — hyphens are invalid in module paths). Fix (2026-09): `gen_doc_stubs.py`
skips everything under `src/personal_os_setup/config/` — data, not API; the rule replaced an older
dead `seqly` special-case. When vendoring any third-party code that ships `.py` inside the package
tree, you need BOTH: (1) skip that subtree in the stub walker, (2) exclude it from the mkdocs
crawl — or the deploy breaks on merge, not locally.

## Local verification (reproduce CI before pushing)
```
uv sync --all-groups --python 3.14   # creates venv/ (gitignored); rewrites the version string in uv.lock → revert before commit
./venv/bin/properdocs build          # invoke the synced env directly
```
- `uv run` mis-resolves the interpreter to a cached 3.11 despite `requires-python ==3.14.*` —
  always pass `--python 3.14`, or call `venv/bin/...` binaries directly.
- A green build ends with `Documentation built in N seconds`; pre-existing anchor INFO warnings
  are noise, `ERROR` lines are not.
- mkdocs crawls the local `venv/` created by the sync unless the exclude glob lists it — keep
  `venv/**` in the glob list (`.venv/**` alone is not enough when uv creates `venv/`).

## Restructuring pages (splits, moves) and the coverage check

Splitting a page: write the new page, trim the old one down to its own topic, add the index bullet in
`docs/index.md`, cross-link both ways. Keep a moved page's images in the folder that still holds them —
relative image paths break silently if the page leaves its PNGs behind.

Then verify coverage with plain shell one-liners (they pass the approval gate; heredocs, `python -c` and
the `execute_code` tool stall on it):

```
git show HEAD:docs/<dir>/<old>.md | grep -oE 'https?://[^ )>`"]+' | sort -u > /tmp/old.urls
grep -hoE 'https?://[^ )>`"]+' docs/<dir>/<new>.md docs/<dir>/readme.md docs/index.md | sort -u > /tmp/new.urls
comm -23 /tmp/old.urls /tmp/new.urls    # anything here is a link the rewrite DROPPED
comm -13 /tmp/old.urls /tmp/new.urls    # only deliberate additions belong here
```

- `comm -23` output must be empty (or explained) before the restructure is called done; a re-run over the
  whole rewritten set is cheap, and the URL set is the part of a rewrite that is otherwise unfalsifiable.
- The URL check says nothing about *prose*, so also re-read the new page for the small stuff a rewrite
  thins out — UI workarounds ("put anything in the field, then disable the addon"), screenshot captions
  and caveats are the first casualties.
- Repoint references before reporting: `grep -rn '<old-path>' docs/ src/ --include=*.md` plus the skill
  tree, and confirm every relative link in the new page resolves to a real file in its folder.

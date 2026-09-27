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

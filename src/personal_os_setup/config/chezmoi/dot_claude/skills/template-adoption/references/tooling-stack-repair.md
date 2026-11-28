# Repairing the shared tooling stack (pre-commit → lint → CI → semantic-release)

The house templates (`python-package-template`, `generative-ai-project-template`) and `personal-os-setup` share one
stack: uv + ruff + pre-commit + markdownlint-cli2 + codespell + commitizen + python-semantic-release + Renovate +
properdocs. A fix or a version in one usually belongs in all three. Diagnosing a red run first:
`github-pr-workflow` → `references/ci-failure-diagnosis.md`.

## Standing rules

1. **Fix the mechanism, never paper over drift.** Rejected on sight: a `markdownlint-disable` comment for a table the
   formatter cannot align, and an extra CI step that only *detects* a desync ("verify the lockfile").
2. **Prove behaviour, don't cite it.** Reproduce locally and quote the output (`uv lock --check`, a local
   `semantic-release … --no-push`, `markdownlint-cli2@<same rev> "**/*.md"`).
3. **Hook revisions move together** across the sibling repos; re-run every tool after a bump.
4. **Verification battery before pushing**, each command its own call (never a pager inside an `&&` chain):
   `markdownlint-cli2@<rev> "**/*.md"`, `uv tool run --from ruff==<rev> ruff check .` and `format --check .`,
   `uv tool run pre-commit validate-config`, `actionlint` on touched workflows, `uv lock --check`, `bash -n` on
   release scripts, `make help`.
5. **Terse config comments; unrequested knobs are proposed in the PR body, not shipped.** A comment the user deleted
   stays deleted.
6. **Quote a new hook's cost beside its benefit**: one env per hook (a `language: node` hook ≈ 8 s per hosted run), a
   `repo: local` hook's version sits in `additional_dependencies` where Renovate never looks.

## Release blocked by a stale `uv.lock`

Symptom: the release job dies at the version step with `Uncommitted changes: commit or stash first` while quality
jobs pass, one release *after* the cause. `uv.lock` records the root project's own version, which semantic-release
bumps in `pyproject.toml` only; the next `uv sync` rewrites the lock and dirties the tree.

```bash
git status --porcelain && uv sync --all-groups >/dev/null && git status --porcelain   # → M uv.lock
```

Fix per PSR's uv integration guide — `build_command` runs after the version write, before the commit:

```toml
[tool.semantic_release]
build_command = """
uv lock --upgrade-package "$PACKAGE_NAME"
git add uv.lock
"""
```

- **Workspace** (`version_toml` stamps several members): plain `uv lock` instead; `--upgrade-package` names one
  package. Check `git diff uv.lock | grep -c '^+name = '` → `0` (no dependency moved).
- `build_command` is release hygiene, **not** the drift gate: it runs inside `semantic-release version`, after a
  make-level clean-tree pre-flight that may abort first. The gate is `UV_LOCKED=1` on the CI install step.
- A lock already stale before your change: commit the re-locked file in the same PR.
- Verify without releasing, in a throwaway clone on the release branch:

  ```bash
  uv sync --all-groups >/dev/null
  env GIT_COMMIT_AUTHOR="test <test@example.com>" PYTHONPATH=. \
    uv run --group dev semantic-release -v version --no-push --no-tag --no-vcs-release --no-changelog
  git show --stat --oneline HEAD        # must list pyproject.toml AND uv.lock
  ```

## Markdown tables (MD060)

`markdownlint-cli2` ≥ 0.24.0 enables MD060/table-column-style (`aligned` default). It measures **display** width:
emoji presentation sequences and East-Asian W/F codepoints take 2 columns, variation selectors/ZWJ/combining marks 0.

- Pin `MD060: {style: aligned}` and pad with `scripts/align_md_tables.py` (`--check` to report); re-lint after.
- `markdown-table-formatter` pads by codepoints (wide-char tables stay ragged); `markdownlint-cli2 --fix` and
  `rumdl --fix` only produce compact tables.
- Keep each table's separator style; a single-column table never triggers MD060 (probe with 3 columns).
- prettier/mdformat normalise lists to 2 spaces, which breaks `MD007: {indent: 4}` (Python-Markdown flattens
  2/3-space nested lists silently, `build --strict` stays green) — not adoptable while properdocs renders the docs.
- Replacing a tool: run the **incumbent** linter over the candidate's output and require 0 issues; benchmark on the
  repo's own files; check exit codes without pipes.

## Formatter bumps and Renovate

- ruff ≥ 0.17 formats Python fences inside Markdown and can change meaning (`CommandDef(...),` → a one-element
  tuple). Read every touched `.md` diff. Exclude verbatim-deployed trees: `[tool.ruff] extend-exclude =
  ["src/<pkg>/config/**"]` (wins under `--force-exclude`). Keep the pyproject pin equal to the hook rev.
- Renovate's `pre-commit` manager is **off by default** (`"pre-commit": {"enabled": true}`), and
  `lockFileMaintenance` is opt-in. `dependencyDashboardApproval` gates majors.
- `uv-pre-commit`'s rev must track the uv CI installs; an older resolver rewrites `uv.lock` ("files were modified").

## Aggregate gate wiring

- `check` = `pre-commit` → `test-all` → `docs-build` as recipe lines (`@$(MAKE) --no-print-directory <t>`), not
  prerequisites (parallel under `make -j`, and make drops a shared prerequisite).
- A new gate name is a tree-wide edit in the same commit: `AGENTS.md`, `CONTRIBUTING.md`,
  `.github/pull_request_template.md`, and every deployed skill that names the old target.
- A target shows in `make help` only with a `## description` comment.

## Gates that pass having run nothing

- **Per-platform test jobs:** fail when zero tests passed, and force exit 5 (no tests collected) to failure — make
  targets often translate it into success. Wire it through step-level `PYTEST_ADDOPTS`; keep job ids (branch
  protection keys on them).
- **Install checks:** build the wheel and load the console script from an isolated env
  (`uv run --isolated --no-project --with "<wheel>"`), not `uv run <entrypoint>` in the dev env.
- **Docs builds:** `properdocs build --strict --site-dir "$(mktemp -d)"`, or the gate writes `./site` and dirties the tree.

## Porting the stack between the repos

0. **Measure first** with `scripts/cross_repo_drift.py` (blob SHAs on committed refs). Sharing instead of copying was
   decided against (`SKILL.md` §5) — don't re-propose a shared actions repo.
1. Presence matrix across repos (`.pre-commit-config.yaml`, `.markdownlint-cli2.yaml`, `pyproject.toml [tool.*]`,
   workflows, actions, `renovate.json`, `properdocs.yml`, makefiles, developer docs); diff only differing cells.
2. Never port template-only machinery into the real repo (Python matrices, Ollama/docker jobs, publishing,
   `deploy-doc-gh`); list what was not ported in the PR body.
3. Prefer the repo's own surfaces (a tested `scripts/release.sh` over inline make logic).
4. Rename tree-wide in the same commit; re-run the battery.
5. Have the diff audited independently (a delegated read-only review of templates vs diff), verify each claim, fix
   in the same branch.

# Passing a target repo's hooks on copied skill files

A skill copied verbatim into a repo carries helper scripts and templates that the repo's own hooks have never
seen. Expect failures on the first pass and fix them before committing.

## Running the hooks

- Run the repo's gate on the staged files: `pre-commit run --files <files>` or the repo's own make target.
- `pre-commit` may not be on PATH in the agent container: `uv run --no-project --with pre-commit pre-commit run
  --files <files>` works without a project; bare `uvx` may be absent.
- Installed on this box (Sep 2026) so a plain invocation works from any cwd: `personal-os-setup/.venv/bin/pre-commit`
  (POS ships it as a dev dep — `make install-dev` = `uv sync --all-groups`) and `ha-addons/.venv/bin/pre-commit`
  (that repo has NO Makefile/pyproject, so the venv is a bare `uv venv .venv` + `uv pip install pre-commit`; `.venv`
  is gitignored). Run it with `--files` from the worktree whose config you want — the CLI resolves `.pre-commit-config.yaml`
  from the CWD, and hook environments build in `~/.cache/pre-commit` on first use.
- Auto-fixers (ruff format, end-of-file, trailing whitespace) rewrite files and make the pass fail by design:
  `git add` again and re-run until a pass is green, then commit.
- Commit hooks also validate the message (conventional commits) — keep the subject conventional or the commit is
  rejected after the work is done.

## Recurring lint fixes on copied scripts

| rule | fix |
|---|---|
| EXE001 shebang present but not executable | drop the shebang (docs say `python3 script.py`) or set the exec bit — follow the repo's convention, which is usually 100644 with the container setting +x |
| SIM115 open without a context manager | wrap in `with open(...) as f:` and build the result inside |
| FURB122 `f.write` inside a loop | `f.write("\n".join(items) + "\n")` |
| E741 ambiguous name `l` | rename to `line` — common in copied comprehension snippets |

## The `.yml` that is not YAML

A template saved as `templates/<name>.yml` but written as prose wrapped around a fenced ```yaml block fails
`check-yaml`. Convert it to valid YAML: turn the surrounding prose into `#` comments (keep the run notes as a
comment block at the end) so the file can be copied straight into its destination (e.g. `.github/workflows/`),
then confirm it parses.

## Report honestly

Some repos run automated checks on only part of their tree — a PR touching other paths gets **zero** checks. Verify
locally, say the gate was local, and never tell the user "CI will confirm this".

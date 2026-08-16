---
name: repo-gotchas
description: Use before trusting CONTRIBUTING.md/Makefile/pre-commit claims literally, or when something documented doesn't behave as expected — "why doesn't X work", "is this hook actually active", "make help is missing stuff". Documents known drift between this repo's docs and its actual behavior.
---

# Known drift between docs and reality in personal-os-setup

Cross-check these before assuming documentation is current — several claims in `CONTRIBUTING.md`/`Makefile` don't match the code as of this writing.

## Makefile

- **`make help`'s "Development:" section is broken**: it greps `makefiles/dev.mk`, which doesn't exist — the real file is `makefiles/check_format.mk`. Running `make help` prints a `grep: ... No such file or directory` and shows an empty Development section, even though `make lint`/`make format`/`make pre-commit`/`make pre-commit-install` all work fine when invoked directly.
- **`make test-installation`** (`uv run --directory . hello`) looks stale/broken — no `hello` console-script is registered in `pyproject.toml`'s `[project.scripts]` (only `personal-os-setup` is). Don't rely on it.
- **`make install` installs zero dev/docs dependencies** — `pyproject.toml` sets `default-groups = []`, so plain `uv sync` (what `make install` runs) gets you only runtime deps. Use `make install-dev` (`uv sync --all-groups`) to get pytest/ruff/pre-commit/mkdocs tooling.
- `common.mk`'s `$(UV)` variable falls back to `~/.local/bin/uv` if `uv` isn't on `PATH` — if it's installed somewhere else, every target fails with a plain "command not found" rather than a clear error.

## `.pre-commit-config.yaml` vs `CONTRIBUTING.md` § 3.1 "Security"

CONTRIBUTING.md claims `actionlint`, `zizmor`, and `pip-audit` are active local pre-commit security hooks. **They're commented out in `.pre-commit-config.yaml`** — not actually running. `bandit` and `markdown-link-check` are also present-but-commented-out. Nothing currently lints/security-scans the GitHub Actions workflow YAML itself — hand-review workflow diffs carefully, especially for script-injection via untrusted `${{ }}` interpolation, since no tool catches it here.

- `commitizen`'s hook only fires at git's `commit-msg` stage — `pre-commit run --all-files` (what `make pre-commit` runs) does **not** exercise it. A clean `make pre-commit` says nothing about whether your commit message is well-formed. See [[ship-feature]].
- `detect-secrets` runs **stateless** (no `--baseline` file configured) — false positives on new files must be suppressed with an inline `# pragma: allowlist secret` comment, not by adding the whole file to `--exclude-files` in `.pre-commit-config.yaml` (explicit repo convention).
- `end-of-file-fixer`/`trailing-whitespace`/`ruff --fix`/`ruff-format` all auto-rewrite files in place and fail the *first* run — re-`git add` and commit again, nothing is actually wrong.

## CONTRIBUTING.md references that don't exist

- `make docker-prod` / `make docker-dev` — **no such targets exist** in any `makefiles/*.mk`. There is no Docker-based dev workflow in this repo (only `make act`, which uses Docker to run GitHub Actions locally).
- "`make test` ... requires `.env` file" — not actually true; `common.mk` tolerates a missing `.env` (`-include .env`), and no unit test hard-requires one.
- "run `make pre-commit install`" (with a space) — the real target is `pre-commit-install` (hyphenated). As literally written this parses as two separate make targets (`pre-commit` and `install`), which happen to both exist, so it "works" by accident, not for the reason implied.

## `properdocs.yml` / docs site

See [[docs-site]] for the full `docs_dir: .` gotcha (any new top-level directory in the repo needs an entry in the `exclude` plugin's glob list, or it gets crawled into the published docs site).

## `packages.yaml`

No schema validation beyond one Python-level test asserting every `(distro, manager)` pair resolves to a real backend (`tests/unit/test_detect_os.py::TestPackagesYaml`). A malformed entry (wrong nesting, list where a dict is expected) surfaces as a `TypeError`/`AttributeError` at load time, not a clear validation error. See [[add-system-action]] for the required manager-registration step when adding a new manager name.

## Misc

- `src/awesome_os/` is dead — stale `__pycache__` from a prior package name, not live code (already flagged in `CLAUDE.md`, repeated here since it's easy to stumble on).
- `tests/archlinux/` is an orphaned Docker smoke-test harness, not wired into `make`/CI. See [[run-tests]].

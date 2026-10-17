---
name: repo-gotchas
description: Use before trusting CONTRIBUTING.md/Makefile/pre-commit claims literally, or when something documented doesn't behave as expected — "why doesn't X work", "is this hook actually active". Documents known drift between this repo's docs and its actual behavior.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Known drift between docs and reality in personal-os-setup

Cross-check these before assuming documentation is current — several claims in `CONTRIBUTING.md`/`Makefile` don't match the code.

## Makefile

- **`make test-installation` is stale** (`uv run --directory . awesome-os`) — the target invokes an `awesome-os` console script, but `pyproject.toml`'s `[project.scripts]` registers only `personal-os-setup`. Don't rely on it.
- **`make install` installs zero dev/docs dependencies** — `pyproject.toml` sets `default-groups = []`, so plain `uv sync` (what `make install` runs) gets you only runtime deps. Use `make install-dev` (`uv sync --all-groups`) for pytest/ruff/pre-commit/mkdocs tooling.
- `common.mk`'s `$(UV)` variable falls back to `~/.local/bin/uv` if `uv` isn't on `PATH` — if it's installed somewhere else, every target fails with a plain "command not found" rather than a clear error.

## `.pre-commit-config.yaml` vs `CONTRIBUTING.md` § 3.1 "Security"

CONTRIBUTING.md claims `actionlint`, `zizmor`, and `pip-audit` are active local pre-commit security hooks. **They're commented out in `.pre-commit-config.yaml`** — not actually running. `bandit` and `markdown-link-check` are also present-but-commented-out. Nothing lints/security-scans the GitHub Actions workflow YAML, so hand-review workflow diffs — especially script-injection via untrusted `${{ }}` interpolation, which no tool catches here.

- `commitizen`'s hook only fires at git's `commit-msg` stage — `pre-commit run --all-files` (what `make pre-commit` runs) does **not** exercise it. A clean `make pre-commit` says nothing about whether your commit message is well-formed. See [[ship-feature]].
- `detect-secrets` runs **stateless** (no `--baseline` file configured) — suppress a false positive on a new file with an inline `# pragma: allowlist secret` comment, not by adding the file to `--exclude-files` (explicit repo convention).
- `end-of-file-fixer`/`trailing-whitespace`/`ruff --fix`/`ruff-format` auto-rewrite files in place and fail the *first* run — re-`git add` and commit again, nothing is actually wrong.

## CONTRIBUTING.md references that don't exist

- `make docker-prod` / `make docker-dev` — **no such targets exist** in any `makefiles/*.mk`. There is no Docker-based dev workflow (only `make act`, which runs GitHub Actions locally in Docker).
- "`make test` ... requires `.env` file" — false; `common.mk` tolerates a missing `.env` (`-include .env`), and no unit test hard-requires one.
- "run `make pre-commit install`" (with a space) — the real target is `pre-commit-install` (hyphenated). As written it parses as two targets (`pre-commit` and `install`) which both happen to exist, so it "works" by accident, not for the implied reason.

## Other

- **`properdocs.yml` / docs site** — see [[docs-site]] for the `docs_dir: .` gotcha: any new top-level directory needs an entry in the `exclude` plugin's glob list or it gets crawled into the published site.
- **`packages.yaml`** — no schema validation beyond `tests/unit/test_detect_os.py::TestPackagesYaml`, which asserts every `(distro, manager)` pair resolves to a real backend. A malformed entry surfaces as a `TypeError`/`AttributeError` at load time, not a clear validation error. See [[add-system-action]] for the manager-registration step.
- **`tests/archlinux/`** is an orphaned Docker smoke-test harness, not wired into `make`/CI. See [[run-tests]].

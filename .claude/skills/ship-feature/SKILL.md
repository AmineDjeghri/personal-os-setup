---
name: ship-feature
description: Use when starting new work in this repo, committing, or opening a PR — "start a new feature", "commit this", "open a PR", "what branch should this target". Covers the branch-naming, conventional-commit, and dev→main release flow specific to this repo (semantic-release, squash merge).
---

# Shipping a change in personal-os-setup

This repo drives releases from commit messages via `python-semantic-release`, so the branch/PR/commit conventions are load-bearing, not stylistic.

⚠️ Committing is local and reversible — fine to do once asked. But `git push`, opening a PR, and especially anything touching `main`/release branches are visible-to-others/hard-to-reverse actions: confirm with the user before pushing or opening a PR, even if they already asked for the feature itself. This is the general repo-wide rule from `CLAUDE.md` § "Safety: always confirm before system-mutating actions", applied to git/GitHub actions specifically.

## Branching

- All work branches off **`dev`**, never `main`. Naming: `feature/your-feature-name` or `bugfix/your-bug-name`.
- `dev` → `main` is a separate promotion PR done later by a maintainer — don't target `main` directly for feature work.
- `git checkout dev && git pull` before branching, to start from a fast-forward-clean base.

## Commit messages

Conventional Commits, gitmoji prefix optional: `[emoji] <type>[(<scope>)][!]: <description>`.

| type                                                        | release bump |
|-------------------------------------------------------------|--------------|
| `fix`, `perf`                                               | patch        |
| `feat`                                                      | minor        |
| `feat!` / `BREAKING CHANGE:` footer                         | major        |
| `chore`, `ci`, `docs`, `style`, `refactor`, `test`, `build` | no release   |

Examples: `✨ feat(auth): add GitHub App token rotation`, `🐛 fix(llm): handle null response from API`. Full type/emoji table and scope list in `CONTRIBUTING.md`.

**Never manually bump the version in `pyproject.toml`** — semantic-release does it on merge. **Never create tags manually.**

⚠️ `commitizen`'s commit-message check only runs at git's `commit-msg` hook stage — `make pre-commit` (`pre-commit run --all-files`) does **not** exercise it. Passing `make pre-commit` gives no signal about whether your commit message itself is well-formed; only a real `git commit` does. See [[repo-gotchas]].

## Before opening a PR

1. `make test` — unit tests only (`uv run pytest tests/unit`). Safe to run anytime.
2. `make pre-commit` — installs hooks then runs them on all files (ruff check+format, detect-secrets, check-yaml/json/toml, uv-lock sync). CI runs this exact command, so a local pass means CI's pre-commit job passes. See [[run-tests]] for what `make test` does *not* cover (integration tests are destructive — don't run them casually).
3. If the branch is behind `dev`: `git merge dev` (if already pushed, safe) or `git rebase dev` (if only local, cleaner history) — either is fine since PR merge always squashes anyway. Re-run `make test`/`make pre-commit` after syncing.

## Opening the PR

- Target **`dev`**, not `main`.
- **PR title must follow the commit convention** (e.g. `feat: add new plugin`) — all PRs squash-merge, and the PR title becomes the commit message semantic-release evaluates.
- CI (`ci.yml` → `quality-and-tests.yml`) runs `make pre-commit` then, in parallel, `make test` plus OS-specific `make test-integration` jobs (`integration-ubuntu`, `integration-macos` — these genuinely install/upgrade real packages on the CI runner, that's expected there, just never run `test-integration` on your own machine).

## What happens after merge

- Merge to `dev` → `🔶 Release — Dev` cuts an RC prerelease (`v1.1.0-rc.1`, incrementing per releasable commit).
- Later, a maintainer opens `dev` → `main`; merging that → `🚀 Release — Main` cuts the stable release + GitHub Release, and deploys docs **only if a release actually happened** (an all-`docs:`/`chore:` PR won't trigger a docs deploy even if docs content changed — see [[docs-site]]).
- Don't worry about `main`↔`dev` sync conflicts (`CHANGELOG.md`/`pyproject.toml`) — that's a maintainer step, not part of a normal feature PR.

Full step-by-step with exact git commands: `CONTRIBUTING.md` § "4.4 Pushing your work" and § "Step-by-step: shipping a feature to production" (note: a few CONTRIBUTING.md claims about local tooling are stale — see [[repo-gotchas]] before trusting it literally).

For test conventions specific to frontend/factory code (never invoke real package managers from a test), see [[add-system-action]] and [[run-tests]].

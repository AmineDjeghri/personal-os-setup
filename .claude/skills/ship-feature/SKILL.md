---
name: ship-feature
description: Use when starting new work in this repo, committing, or opening a PR — "start a new feature", "commit this", "open a PR", "what branch should this target". Covers branch-naming, conventional commits, and the main-targeted squash-merge release flow (semantic-release).
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Shipping a change in personal-os-setup

This repo drives releases from commit messages via `python-semantic-release`, so the branch/PR/commit conventions are load-bearing, not stylistic.

⚠️ Committing is local and reversible — fine to do once asked. But `git push`, opening a PR, and anything touching `main`/release branches are visible-to-others/hard-to-reverse actions: confirm with the user before pushing or opening a PR, even if they already asked for the feature itself. This is the repo-wide rule from `AGENTS.md` § "Safety", applied to git/GitHub actions specifically. If a confirmation prompt times out, stop — silence is not consent.

## Branching

- All work branches off **`main`** and is named `feature/<name>` or `bugfix/<name>`.
- **The `dev` branch is retired** — it no longer exists on `origin`. Anything describing a `dev` → `main` promotion PR, or a `🔶 Release — Dev` RC prerelease, is stale: PRs target `main` directly.
- `git checkout main && git pull` before branching, to start from a fast-forward-clean base.

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
3. If the branch is behind `main`: `git merge main` (if already pushed, safe) or `git rebase main` (if only local, cleaner history) — either is fine since PR merge always squashes anyway. Re-run `make test`/`make pre-commit` after syncing.

## Opening the PR

- Target **`main`**.
- **PR title must follow the commit convention** (e.g. `feat: add new plugin`) — all PRs squash-merge, and the PR title becomes the commit message semantic-release evaluates.
- CI (`ci.yml` → `quality-and-tests.yml`) runs `make pre-commit` then, in parallel, `make test` plus OS-specific `make test-integration` jobs (`integration-ubuntu`, `integration-macos` — these genuinely install/upgrade real packages on the CI runner, that's expected there, just never run `test-integration` on your own machine).

## What happens after merge

- Merging to `main` → `🚀 Release — Main` (`.github/workflows/main-release.yml`, triggered by the push to `main` and by a PR closed into `main`) runs semantic-release: it bumps the version from the conventional commit(s), tags, cuts the GitHub Release *if the merged commits were releasable*, and deploys docs **only if a release actually happened** (an all-`docs:`/`chore:` PR triggers no release and no docs deploy even if docs content changed — see [[docs-site]]).
- A non-releasable merge is a normal outcome, not a failure: `chore:`/`docs:` PRs land with no version bump.
- `.github/workflows/dev-release.yml` (`🔶 Release — Dev`) still exists but is inert — its trigger is the deleted `dev` branch. Ignore it; don't recreate `dev`.

Full step-by-step with exact git commands: `CONTRIBUTING.md` § "4.4 Pushing your work" and § "Step-by-step: shipping a feature to production" (note: a few CONTRIBUTING.md claims about local tooling are stale — check [[repo-gotchas]] before trusting it literally, and its `dev`-branch passages are obsolete).

For test conventions specific to frontend/factory code (never invoke real package managers from a test), see [[add-system-action]] and [[run-tests]].

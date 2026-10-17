---
name: ship-feature
description: Use when starting new work in this repo, committing, or opening a PR — "start a new feature", "commit this", "open a PR", "what branch should this target". Covers branch-naming, conventional commits, and the main-targeted squash-merge release flow (semantic-release).
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Shipping a change in personal-os-setup

This repo drives releases from commit messages via `python-semantic-release`, so the branch/PR/commit conventions are load-bearing, not stylistic.

⚠️ **Commit and push each need their own approval.** Nothing here is pre-approved: ask per action, even if the user already asked for the feature. `git push`, merging and anything touching `main`/release branches need the same per-action yes. If a confirmation prompt times out, stop — silence is not consent. Canon: `AGENTS.md` § "Safety: confirm before system-mutating actions (MANDATORY)".

## Branching

- All work branches off **`main`** and is named `feature/<name>` or `bugfix/<name>`.
- **The `dev` branch is retired** — it no longer exists on `origin`. Anything describing a `dev` → `main` promotion PR, or a `🔶 Release — Dev` prerelease, is stale: PRs target `main` directly.
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

⚠️ `commitizen`'s commit-message check only runs at git's `commit-msg` hook stage — `make pre-commit` does **not** exercise it, so a passing `make pre-commit` says nothing about whether your commit message is well-formed; only a real `git commit` does. See [[repo-gotchas]].

## Before opening a PR

1. `make test` — unit tests only. Safe to run anytime; see [[run-tests]] for what it does *not* cover (integration tests are destructive — don't run them casually).
2. `make pre-commit` — installs hooks then runs them on all files. CI runs this exact command, so a local pass means CI's pre-commit job passes.
3. If the branch is behind `main`: `git merge main` (if already pushed, safe) or `git rebase main` (if only local, cleaner history) — either is fine since PR merge always squashes. Re-run both checks after syncing.

## Opening the PR

- Target **`main`**.
- **The PR title must follow the commit convention** (e.g. `feat: add new plugin`) — all PRs squash-merge, and the PR title becomes the commit message semantic-release evaluates.
- CI (`ci.yml` → `quality-and-tests.yml`) runs `make pre-commit` then, in parallel, `make test` plus OS-specific `make test-integration` jobs. Those genuinely install/upgrade real packages on the CI runner — expected there, never on your own machine.

## What happens after merge

- Merging to `main` → `🚀 Release — Main` runs semantic-release: it bumps the version from the conventional commit(s), tags, cuts the GitHub Release *if the merged commits were releasable*, and deploys docs **only if a release actually happened** (an all-`docs:`/`chore:` PR triggers neither — see [[docs-site]]). A non-releasable merge is a normal outcome, not a failure.
- `.github/workflows/dev-release.yml` (`🔶 Release — Dev`) still exists but is inert — its trigger is the deleted `dev` branch. Ignore it; don't recreate `dev`.

Exact git commands: `CONTRIBUTING.md` § "4.4 Pushing your work" (its `dev`-branch passages are obsolete, and a few CONTRIBUTING.md claims about local tooling are stale — check [[repo-gotchas]] before trusting it literally).

For test conventions specific to frontend/factory code (never invoke real package managers from a test), see [[add-system-action]] and [[run-tests]].

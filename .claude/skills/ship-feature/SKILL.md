---
name: ship-feature
description: Use when starting work, committing or opening a PR — "start a new feature", "commit this", "what branch should this target". Covers branch naming, conventional commits and the dev-to-main squash-merge release flow.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Shipping a change in personal-os-setup

This repo drives releases from commit messages via `python-semantic-release`, so the branch/PR/commit conventions are load-bearing, not stylistic.

⚠️ **Commit and push each need their own approval.** Nothing here is pre-approved: ask per action, even if the user already asked for the feature. `git push`, merging and anything touching `main`/release branches need the same per-action yes. If a confirmation prompt times out, stop — silence is not consent. Canon: `AGENTS.md` § "Safety: confirm before system-mutating actions (MANDATORY)".

## Branching

- All work branches off **`dev`** and is named `feature/<name>` or `bugfix/<name>`.
- Feature PRs target `dev` for release candidates; promote `dev` to `main` for stable releases.
- After a stable release, merge `main` back into `dev`; keep stable version/changelog metadata and regenerate `uv.lock`. Commit and push each require approval.
- `git checkout dev && git pull` before branching, to start from a fast-forward-clean base.

## Commit messages

Conventional Commits, gitmoji prefix optional: `[emoji] <type>[(<scope>)][!]: <description>`.

| type                                                        | release bump |
|-------------------------------------------------------------|--------------|
| `fix`, `perf`                                               | patch        |
| `feat`                                                      | minor        |
| `feat!` / `BREAKING CHANGE:` footer                         | major        |
| `chore`, `ci`, `docs`, `style`, `refactor`, `test`, `build` | no release   |

Examples: `✨ feat(auth): add GitHub App token rotation`, `🐛 fix(llm): handle null response from API`.
Full type/emoji table and scopes: `docs/developer/3.conventions.md`, “Commit convention”.

**Never manually bump the version in `pyproject.toml`** — semantic-release does it on merge. **Never create tags manually.**

⚠️ `commitizen`'s commit-message check only runs at git's `commit-msg` hook stage — `make pre-commit` does **not** exercise it, so a passing `make pre-commit` says nothing about whether your commit message is well-formed; only a real `git commit` does. See [[run-tests]].

## Before opening a PR

1. `make check` — static/docs hooks, full safe unit/skills suites and artifact/runtime checks.
   Dependencies/hooks must already be installed. For new files, pass explicit paths through
   `FILES="<paths>"`; the default covers tracked files.
2. Use `make test-local ARGS="..."` for focused debugging. Full validation targets reject
   `ARGS` and `PYTEST_ADDOPTS`. See [[run-tests]] for isolation and platform boundaries.
3. If the branch is behind `dev`: `git merge dev` (if already pushed) or `git rebase dev`
   (if only local). Re-run `make check` after syncing.

## Opening the PR

- Target **`dev`** for features/fixes; **`main`** for the stable promotion from `dev`.
- **The PR title must follow the commit convention** (e.g. `feat: add new plugin`) — all PRs squash-merge, and the PR title becomes the commit message semantic-release evaluates.
- CI (`ci.yml` → `quality-and-tests.yml`) runs static checks and full safe suites plus platform
  integration. Linux/macOS integration installs real packages; Windows integration is read-only.
  Run these only on disposable CI hosts. A local pass does not establish hosted CI success.

## What happens after merge

- Merging to `main` → `🚀 Release — Main / Dev` runs semantic-release: it bumps the version from the conventional commit(s), tags, cuts the GitHub Release *if the merged commits were releasable*, and deploys docs **only if a release actually happened** (an all-`docs:`/`chore:` PR triggers neither — see [[docs-site]]). A non-releasable merge is a normal outcome, not a failure.
- Merging releasable changes to `dev` publishes an `rc` prerelease without deploying docs. GitHub Actions automatically binds both release branches to the tested `GITHUB_SHA`. Locally, run `make release` from clean, synchronized `main` or `dev`; it uses `HEAD`. Both paths verify artifacts before publication and resume interrupted uploads.

Branch/PR flow: `docs/developer/3.conventions.md`, “Branches and pull requests”.

For test conventions specific to frontend/factory code (never invoke real package managers from a test), see [[add-system-action]] and [[run-tests]].

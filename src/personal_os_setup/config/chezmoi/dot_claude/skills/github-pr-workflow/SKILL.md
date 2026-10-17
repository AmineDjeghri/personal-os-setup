---
name: github-pr-workflow
description: "GitHub PR lifecycle: branch, commit, open, CI, merge."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [GitHub, Pull-Requests, CI/CD, Git, Automation, Merge]
    related_skills: [github-auth, github-code-review]
---

# GitHub Pull Request Workflow

Complete guide for managing the PR lifecycle with the `gh` CLI. No `gh`? Install it (see `github-auth`) — fallback: `github-auth/references/rest-api-fallback.md`.

Needs `gh` auth (`github-auth` — ask to install `gh` if it's missing) inside a git repository with a GitHub remote.

## 1. Branch Creation

This part is pure `git` — identical either way:

```bash
# Make sure you're up to date
git fetch origin
git checkout main && git pull origin main

# Create and switch to a new branch
git checkout -b feat/add-user-authentication
```

Branch naming conventions:
- `feat/description` — new features
- `fix/description` — bug fixes
- `refactor/description` — code restructuring
- `docs/description` — documentation
- `ci/description` — CI/CD changes

## 2. Making Commits

```bash
# Stage specific files
git add src/auth.py src/models/user.py tests/test_auth.py

# Commit with a conventional commit message
git commit -m "feat: add JWT-based user authentication"
```

Commit message format (Conventional Commits):
```
type(scope): short description

Longer explanation if needed. Wrap at 72 characters.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

Use `!` or a `BREAKING CHANGE:` footer for majors.

Mandatory pre-push checklist: see the `repo-conventions` skill (line endings: see the `git-line-endings` skill).

## 3. Pushing and Creating a PR

### Push the Branch (same either way)

```bash
git push -u origin HEAD
```

### Create the PR

**With gh:**

```bash
gh pr create \
  --title "feat: add JWT-based user authentication" \
  --body "## Summary
- Adds login and register API endpoints
- JWT token generation and validation

## Test Plan
- [ ] Unit tests pass

Closes #42"
```

Follow-up commits: confirm where the open PR's branch is checked out first (`gh pr list --state open`, `git worktree list`) — never push leftover commits of a branch whose PR is already merged.

## 4. Monitoring CI Status

### Check CI Status

**With gh:**

```bash
# One-shot check
gh pr checks

# Watch until all checks finish (polls every 10s)
gh pr checks --watch
```

## 5. Auto-Fixing CI Failures

```bash
gh run list --branch $(git branch --show-current) --limit 5   # recent runs on this branch
gh run view <RUN_ID> --log-failed                            # failed logs
```

Loop: check CI (`gh pr checks`) → read the failure logs → fix the code → **ask the user for approval to commit, and separately to push** (each is its own per-action approval; never fold `git add`/`git commit`/`git push` into one command) → re-check CI. After 3 failed attempts, stop and ask the user.

CI failure facts worth checking:
- a missing `permissions:` block in the workflow, or secrets that fork PRs never get (by design) — needs the user;
- a hung job → add `timeout-minutes:` to the step;
- `ModuleNotFoundError` in CI = a dependency missing in CI;
- compare the local vs CI Python/Node version.

## 6. Merging

Merging needs the user's per-action approval.

**With gh:**

```bash
# Squash merge + delete branch (cleanest for feature branches)
gh pr merge --squash --delete-branch

# Enable auto-merge (merges when all checks pass)
gh pr merge --auto --squash --delete-branch
```

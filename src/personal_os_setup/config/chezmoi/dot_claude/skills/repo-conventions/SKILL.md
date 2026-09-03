---
name: repo-conventions
description: Use before committing, pushing, or opening a PR in any of the repos. Per-repo matrices (personal-os-setup vs ha-addons) for branching, commits, PRs, release, and CI, plus the mandatory pre-push checklist.
---

# Repo Conventions

Per-repo rules that differ — check the right row before committing/pushing/opening a PR.

## 0. Pre-push checklist (MANDATORY — every repo)

Run BEFORE every push. Skipping these caused real incidents (wrong commit attribution, whole-file diffs, CI rejection).

1. **Verify git author identity BEFORE committing.** GitHub attributes commits by email only; a wrong email links your commit to a different account and pollutes PR participants (unfixable once merged).
   - Check: `git config user.name` / `git config user.email`
   - Email MUST be `<numeric-id>+<username>@users.noreply.github.com` — get the id via `gh api user -q .id`. **Never guess** (e.g. `example@users.noreply...` ≠ `12345678+example_user@users.noreply.github.com`).
   - Fix before pushing: `git commit --amend --author="Real Name <id+username@users.noreply.github.com>" --no-edit`
2. **Run pre-commit on changed files** (if `.pre-commit-config.yaml` exists): `pre-commit run --files <files...>`. Hooks must pass; if one auto-fixes, re-add and re-commit.
3. **Conventional commit + conventional PR title.** Squash-merge makes the PR title the commit on main; CI often validates it against `(feat|fix|docs|chore|ci|...)(scope)?: ...`.
4. **Line endings.** Repo files may be CRLF while pastes write LF → whole-file diffs. Check: `diff <(git show HEAD:path | tr -d '\r') <(tr -d '\r' < path)`. Fix with repo-native endings or `.gitattributes` (doesn't retroactively fix existing blobs).
5. **Force-push etiquette.** NEVER force-push without explicit user approval. Prefer `--force-with-lease` over `--force`. Force-pushing an OPEN PR fixes attribution; a merged PR is frozen.

## personal-os-setup

| Rule | Value |
|---|---|
| Branch from | `main` (dev is retired) |
| Branch naming | `feature/<name>` / `bugfix/<name>` |
| Commits | Conventional + optional gitmoji: `feat`→minor, `fix`/`perf`→patch, `feat!`/`BREAKING CHANGE:`→major, others→no release |
| Version | Never bump `pyproject.toml`; never create tags (python-semantic-release) |
| Before PR | `make test` + `make pre-commit` (local pass == CI pass). commitizen fires only at `git commit` (commit-msg hook) — `make pre-commit` does NOT check commit messages |
| PR target | `main` — squash-merge; PR title = release-determining message |
| CI | `make pre-commit`; then `make test` + `test-integration` (CI-only, never local) |
| Release | semantic-release cuts version + GitHub Release on merge; docs deploy only when a release happens |
| Renovate | 7-day cooldown on dependency PRs |
| Docs drift | trust `.claude/skills/repo-gotchas` over CONTRIBUTING.md |

## ha-addons

| Rule | Value |
|---|---|
| Branch from | `main` |
| Commits | Conventional |
| PR | Squash-merge to `main` — PR title becomes the commit message (keep it conventional) |
| CI | Scoped to `addons/personal-app/**` ONLY — other addon PRs (hermes-webui, beets, ...) run no CI; don't expect checks |
| Dev installs | `install-dev` is personal-app-scoped only |
| Deep workflow | `home-assistant-addon-dev` skill (Hermes side); addon repos get AGENTS.md/CLAUDE.md + `.claude/skills/` as they grow |

## Global rules (all repos)

- gh OAuth device flow preferred over PATs for interactive auth (PATs only for CI secrets).
- Approval prompts often time out → prefer approval-free git ops (regular push, new commit, merge over rebase, no force-push/remote deletes).
- Re-check `gh pr` state before assuming — PRs get merged fast.

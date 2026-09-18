---
name: repo-conventions
description: Use before committing, pushing, or opening a PR in ANY repo. Universal pre-push checklist plus how to discover each repo's own conventions (AGENTS.md/CLAUDE.md/CONTRIBUTING.md/.claude/skills) — repo-specific rules are NOT encoded here, they live in the repo itself.
---

# Repo conventions (general)

Two layers: **universal rules** that apply to every repo, and **per-repo conventions** that differ.
Per-repo specifics live in the repo itself (AGENTS.md / CLAUDE.md / CONTRIBUTING.md / `.claude/skills/`)
and are auto-loaded when working there — do NOT duplicate them in shared skills.

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

## 1. Find the repo's OWN conventions FIRST

Never assume a repo follows another repo's flow. Before committing/pushing/opening a PR in a repo:

1. Read `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` at the repo root
2. Read its project skills: `.claude/skills/` (e.g. ship-feature, repo-gotchas) and `.agents/skills/`
3. If conventions files are **missing** → flag it and offer to create them; do NOT silently apply defaults from memory
4. Fallbacks when docs are silent: branch from the default branch; conventional PR title; check whether CI is path-scoped (some repos only test a subdirectory)

## 2. Global rules (all repos)

- gh OAuth device flow preferred over PATs for interactive auth (PATs only for CI secrets).
- Approval prompts often time out → prefer approval-free git ops (regular push, new commit, merge over rebase, no force-push/remote deletes).
- Re-check `gh pr` state before assuming — PRs get merged fast.

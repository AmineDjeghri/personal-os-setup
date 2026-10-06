---
name: repo-conventions
description: "Use before committing, pushing, or opening a PR in ANY repo: universal pre-push checklist + how to find each repo's own conventions (repo-specific rules live in the repo)."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Repo conventions (general)

Two layers: **universal rules** that apply to every repo, and **per-repo conventions** that differ.
Per-repo specifics live in the repo itself (AGENTS.md / CLAUDE.md / CONTRIBUTING.md / `.claude/skills/`)
and are auto-loaded when working there — do NOT duplicate them in shared skills.

## 0. Pre-push checklist (MANDATORY — every repo)

Run BEFORE every push.

1. **Verify git author identity BEFORE committing.** GitHub attributes commits by email only; a wrong email links your commit to a different account and pollutes PR participants (unfixable once merged).
   - Check: `git config user.name` / `git config user.email`
   - Email MUST be `<numeric-id>+<username>@users.noreply.github.com` — get the id via `gh api user -q .id`. **Never guess.**
   - Fix before pushing: `git commit --amend --author="Real Name <id+username@users.noreply.github.com>" --no-edit`
2. **Run pre-commit on changed files** (if `.pre-commit-config.yaml` exists): `pre-commit run --files <files...>`. Hooks must pass; if one auto-fixes, re-add and re-commit.
   **Stage before you trust a green gate.** `pre-commit run --all-files` only covers files git already tracks, so a newly created file passes that run and then fails the commit hook. Gate the staged paths, or stage first, or the gate is answering about a different set of files than the commit will contain.
3. **Conventional commit + conventional PR title.** Squash-merge makes the PR title the commit on main; CI often validates it against `(feat|fix|docs|chore|ci|...)(scope)?: ...`.
4. **Line endings:** see `git-line-endings`.
5. **Force-push etiquette.** NEVER force-push without explicit user approval. Prefer `--force-with-lease` over `--force`. Force-pushing an OPEN PR fixes attribution; a merged PR is frozen.

## 1. Find the repo's OWN conventions FIRST

Never assume a repo follows another repo's flow. Before committing/pushing/opening a PR in a repo:

1. Read `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` at the repo root
2. Read its project skills: `.claude/skills/` (e.g. ship-feature, repo-gotchas) and `.agents/skills/`
3. If conventions files are **missing** → flag it and offer to create them; do NOT silently apply defaults from memory
4. Fallbacks when docs are silent: branch from the default branch; conventional PR title; check whether CI is path-scoped (some repos only test a subdirectory)

## 2. Global rules (all repos)

- Approval prompts often time out → prefer approval-free git ops (regular push, new commit, merge over rebase, no force-push/remote deletes). **Technique, not permission:** this line is not a standing yes — `git commit` and `git push` each still need the user's explicit per-action approval.

---
name: coding-workflow
description: "Use for coding work in any repo (plan, confirm, implement, verify, open a PR) and ALWAYS before committing, pushing or opening a PR: pre-push checklist + how to find each repo's own conventions."
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Coding workflow (any repo, any coding agent)

Applies to every repo the user works on. The repo's own rules win: read `AGENTS.md` / `CLAUDE.md` /
`CONTRIBUTING.md` and its `.claude/skills/` before touching anything.

## 1. Plan first

For anything non-trivial: restate the goal and the constraints, name the files you will touch and the
test/validation strategy, and get an explicit go-ahead before mutating. If asked to be grilled, resolve
the design branch by branch until nothing is left open.

## 2. Confirm before mutating

- Per-action approval for `git commit` and `git push`, system changes (package installs, `chezmoi apply`,
  driver/VM/WSL work, `sudo`), destructive commands, opening/merging a PR and release actions.
- A previous "yes", a plan, a task description or "implement this" is NOT standing approval — ask again, every
  time, and run exactly what was approved. Commit and push are separate approvals: a yes to one is not a yes to
  the other. When the repo's own rules say nothing about committing, ask before the FIRST commit of a task. A
  delegated brief must never pre-authorise a commit the user did not approve for that task.
- Never fold `git commit`/`git push` into a compound command — the gate becomes the scanner, not the user. Ask
  in chat, wait for the yes, run the git action as its own command.
- Never bypass a tool's own confirmation dialog.

## 3. Work in reviewable steps

- One concern per change; keep diffs small enough to read.
- Run the repo's own gates before proposing a PR: its `make test` / `make pre-commit` (or the documented
  CI-equivalent) — a local pass is the only signal before CI.
- Review your own diff against the base branch before pushing.
- Never commit secrets; follow the repo's convention for suppression (inline allowlist comments, never
  whole-file excludes).

## 4. Open the PR, then verify

- Branch from the repo's base branch (`main` unless the repo says otherwise); conventional commit and PR
  title — most repos squash-merge, so the PR title becomes the released commit message.
- Verify the real artifact, not the summary: the diff, the CI run status, the PR state.

## 5. Repo conventions and the pre-push checklist

Two layers: **universal rules** that apply to every repo, and **per-repo conventions** that differ.
Per-repo specifics live in the repo itself (AGENTS.md / CLAUDE.md / CONTRIBUTING.md / `.claude/skills/`)
and are auto-loaded when working there — do NOT duplicate them in shared skills.

### Pre-push checklist (MANDATORY — every repo)

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

### Find the repo's OWN conventions FIRST

Never assume a repo follows another repo's flow. Before committing/pushing/opening a PR in a repo:

1. Read `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` at the repo root
2. Read its project skills: `.claude/skills/` (e.g. ship-feature, repo-gotchas) and `.agents/skills/`
3. If conventions files are **missing** → flag it and offer to create them; do NOT silently apply defaults from memory
4. Fallbacks when docs are silent: branch from the default branch; conventional PR title; check whether CI is path-scoped (some repos only test a subdirectory)

### Global rules (all repos)

- Approval prompts often time out → prefer approval-free git ops (regular push, new commit, merge over rebase, no force-push/remote deletes). **Technique, not permission:** this line is not a standing yes — `git commit` and `git push` each still need the user's explicit per-action approval.

## 6. Hermes orchestrator only

If you are the Hermes orchestrator (not the coding delegate itself): the division of labor, how to brief the
Claude Code delegate and how to verify its work are in `references/hermes-delegation.md`.

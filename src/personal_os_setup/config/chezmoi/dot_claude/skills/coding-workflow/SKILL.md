---
name: coding-workflow
description: Use when starting any coding work across the repos. Division of labor between Hermes and Claude Code, plan-first workflow, confirm-before-mutate, review, and per-repo PR flows (see repo-conventions).
---

# Coding Workflow — Hermes & Claude Code

Shared workflow rules for coding tasks. Both agents read this skill; rules are agent-agnostic (terminal/git/gh only).

## 1. Division of labor

| Task | Agent |
|---|---|
| Home Assistant, Hermes gateway/admin, scheduling (cron), memory, audits, container/system ops | **Hermes** |
| In-repo code changes, features, bugfixes, PRs (personal-os-setup, ha-addons, ...) | **Claude Code** (Hermes delegates via `claude -p` or interactive) |
| Repo docs (docs/, README, skills) | Either — follow repo-conventions |

Hermes orchestrates and can delegate coding to Claude Code. Claude Code works inside a repo; it does NOT manage the Hermes agent, HA gateway, or cron.

## 2. Plan first (MANDATORY)

Never jump straight into editing. For anything non-trivial:
1. Restate the goal and constraints in your own words.
2. Read the repo's AGENTS.md/CLAUDE.md and `.claude/skills/`; explore the relevant files.
3. Write the plan (files to touch, approach, test strategy) and get explicit user approval before mutating.
4. If the user says "grill me" / "stress-test this" — interview them about the plan branch by branch until the design tree is resolved.

## 3. Confirm before mutating (MANDATORY)

- Per-action approval for: system changes, `git push`, opening PRs, anything destructive.
- A prior "yes" is not standing approval — re-confirm scope.
- Prefer approval-free git ops: regular push, new commit, merge over rebase; no force-push without explicit approval.

## 4. Review

- Run the repo's checks before any PR: `make test` + `make pre-commit` (personal-os-setup) or the repo's CI-equivalent.
- Verify git identity before committing (wrong email = phantom PR participants — see repo-conventions).
- Review your own diff before pushing; for PRs, diff against the base branch.

## 5. Per-repo PR flows

Load `repo-conventions` and follow the row for that repo. Default when unsure: branch from the default branch, conventional commit, squash-merge PR with a conventional title.

## 6. Skills & docs maintenance

- General/shared skills live in personal-os-setup's chezmoi source (`dot_claude/skills/`) — both agents read them. Repo-specific skills live in each repo's `.claude/skills/`.
- Community skills (via `npx skills`) are vendored into the shared dir, pinned, and updated through git PRs.
- Chat-made decisions get encoded into the governing skill (this one, repo-conventions, or the repo skill) — never left only in memory.

---
name: coding-workflow
description: "Use when doing coding work in any repo: plan, confirm, implement, verify, open a PR."
---

# Coding workflow (any repo, any coding agent)

Applies to every repo the user works on. The repo's own rules win: read `AGENTS.md` / `CLAUDE.md` /
`CONTRIBUTING.md` and its `.claude/skills/` before touching anything.

## 1. Plan first

For anything non-trivial: restate the goal and the constraints, name the files you will touch and the
test/validation strategy, and get an explicit go-ahead before mutating. If asked to be grilled, resolve
the design branch by branch until nothing is left open.

## 2. Confirm before mutating

- Per-action approval for system changes (package installs, `chezmoi apply`, driver/VM/WSL work, `sudo`),
  destructive commands, `git push`, opening/merging a PR and release actions.
- A previous "yes", a plan or a task description is NOT standing approval — ask again, every time, and run
  exactly what was approved.
- Never bypass a tool's own confirmation dialog.

## 3. Work in reviewable steps

- One concern per change; keep diffs small enough to read.
- Run the repo's own gates before proposing a PR: its `make test` / `make pre-commit` (or the documented
  CI-equivalent) — a local pass is the only signal before CI.
- Review your own diff against the base branch before pushing; check git identity first (a wrong email
  creates phantom commit authors).
- Never commit secrets; follow the repo's convention for suppression (inline allowlist comments, never
  whole-file excludes).

## 4. Open the PR, then verify

- Branch from the repo's base branch (`main` unless the repo says otherwise); conventional commit and PR
  title — most repos squash-merge, so the PR title becomes the released commit message.
- Target the base branch the repo uses; follow its review/merge policy.
- Verify the real artifact, not the summary: the diff, the CI run status, the PR state.

## 5. Per-repo specifics

Repo-level conventions (pre-push checklist, identity, line endings, force-push etiquette, per-repo flow)
live in the `repo-conventions` skill and in each repo's own files.

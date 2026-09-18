---
name: hermes-coding-workflow
description: Use when the Hermes orchestrator plans, delegates or reviews coding work (Hermes-only).
---

# Coding Workflow — Hermes & Claude Code

Hermes-only orchestration rules for coding tasks: how the Hermes orchestrator plans work, briefs the Claude Code delegate, and verifies the result. Claude Code does not read this skill — it follows each repo's own `AGENTS.md` / `CLAUDE.md`.

## 1. Division of labor

| Task | Agent |
|---|---|
| Home Assistant, Hermes gateway/admin, scheduling (cron), memory, audits, container/system ops | **Hermes** |
| **Every in-repo file change** — code, workflows/CI, docs, READMEs, skills, and one-line edits — in any repo the user works on | **Claude Code**, driven by Hermes via `claude -p` (or interactive) |
| Reading a repo, writing the spec/plan, reviewing a diff or PR, verifying CI state | **Hermes** |

**Every in-repo edit is delegated — including the small and the mechanical.** "It is only one
line" or "it is just a YAML tweak" is not a reason to reach for the orchestrating agent's own file
tools: the delegate owns the edit, the repo's pre-commit hooks, the commit and the push. Bypassing
it skips the delegate's checks and leaves the work without its normal verification trail.

Rules that follow from this:

- **Follow-ups stay on the branch that is already open** ("same branch as PR #52"): brief the
  delegate to add a commit there — never a new PR, never a force-push.
- **Brief precisely:** goal, exact files, the constraints that matter (repo conventions, what NOT
  to touch, which validation commands to run), and the shape of the answer wanted back.
- **Verify the artifact, never the summary.** The delegate's report is a self-report: afterwards
  check the real thing — `git diff origin/main...origin/<branch>`, `gh pr checks`, `gh run list`,
  `gh api repos/<owner>/<repo>/actions/runs/<id>/jobs`. Only then report success to the user.
- **Approvals still gate the outward actions** (push, PR, merge, force-push) — per action, every
  time. A delegation does not inherit a previous yes.

Claude Code works inside a repo; it does NOT manage the Hermes agent, the HA gateway or cron.
Hermes orchestrates, writes the specs/briefs and reviews.

## 2. Shared rules (not duplicated here)

The agent-agnostic workflow — plan first, confirm before mutating, reviewable steps, PR flow — lives in the
shared `coding-workflow` skill (Track 1, read by Hermes and by the delegate). Per-repo specifics live in
`repo-conventions` and in each repo's own `AGENTS.md`. Do not copy those rules into this file.

## 3. Skills & plugins maintenance

- **2-track governance** (encoded in the shared AGENTS.md): Track 1 = curated skills, versioned in the chezmoi source, deployed via `skill-deployment`; Track 2 = third-party suites as Claude Code plugins (e.g. superpowers). Never hand-copy a Track-2 suite into Track 1 — it fights its own updater.
- Chat-made decisions get encoded into the governing skill (this one, `repo-conventions`, or the repo's own skill) — never left only in memory.

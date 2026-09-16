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

- Run the repo's own checks before any PR: its `make test`/`make pre-commit` where defined, or the CI-equivalent.
- Verify git identity before committing (wrong email = phantom PR participants — see repo-conventions).
- Review your own diff before pushing; for PRs, diff against the base branch.

## 5. Per-repo PR flows

Load `repo-conventions` and follow the row for that repo. Default when unsure: branch from the default branch, conventional commit, squash-merge PR with a conventional title.

## 6. Skills & plugins maintenance

- **2-track governance** (encoded in the shared AGENTS.md): Track 1 = curated skills, versioned in the chezmoi source, deployed via `skill-deployment`; Track 2 = third-party suites as Claude Code plugins (e.g. superpowers). Never hand-copy a Track-2 suite into Track 1 — it fights its own updater.
- Chat-made decisions get encoded into the governing skill (this one, `repo-conventions`, or the repo's own skill) — never left only in memory.

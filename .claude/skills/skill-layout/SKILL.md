---
name: skill-layout
description: Use when adding/modifying agent skills in this repo, or when figuring out how skills are organized here.
---

# Skill layout in this repo

- **Canonical skills:** `.claude/skills/<name>/SKILL.md` — edit here (Claude Code reads this natively)
- **Cross-agent view:** `.agents/skills/<name>` are git symlinks → `../../.claude/skills/<name>`
  (Hermes, Codex, OpenCode and the skills CLI read `.agents/skills`)
- **Add a skill:** create `.claude/skills/<name>/SKILL.md`, then run `make skills-link`
- **Verify:** `make skills-check`
- Never edit through a symlink — always edit the canonical file
- Windows note: git symlinks need `core.symlinks=true` on native Windows checkouts

## A repo-bound runbook is a skill, not a `docs/` page

Anything under `docs/` is crawled into the published site unless specifically excluded, and a doc
only helps a human who remembers to go read it — a skill loads itself at task time, for both agents.
If a doc starts describing how to *do* something (a procedure, not reference material for readers),
that's the signal to move it into a skill instead.

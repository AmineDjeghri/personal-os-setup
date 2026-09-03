---
name: skill-layout
description: Use when adding/modifying agent skills in this repo, or when figuring out how skills are organized here.
---

# Skill layout in this repo

- **Canonical skills:** `.claude/skills/<name>/SKILL.md` — edit here (Claude Code reads this natively)
- **Cross-agent view:** `.agents/skills/<name>` are git symlinks → `../.claude/skills/<name>`
  (Hermes, Codex, OpenCode and the skills CLI read `.agents/skills`)
- **Add a skill:** create `.claude/skills/<name>/SKILL.md`, then run `make skills-link`
- **Verify:** `make skills-check`
- Never edit through a symlink — always edit the canonical file
- Windows note: git symlinks need `core.symlinks=true` on native Windows checkouts

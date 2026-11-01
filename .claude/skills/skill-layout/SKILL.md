---
name: skill-layout
description: Use when adding/modifying agent skills in this repo, or when figuring out how skills are organized here.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Skill layout in this repo

- **Canonical skills:** `.claude/skills/<name>/SKILL.md` — edit here (Claude Code reads this natively)
- **Cross-agent view:** `.agents/skills/<name>` are git symlinks → `../../.claude/skills/<name>`
  (Hermes, Codex, OpenCode and the skills CLI read `.agents/skills`)
- **Add a skill:** create `.claude/skills/<name>/SKILL.md`, then run `make skills-link`
- **Verify:** `make skills-check`
- Never edit through a symlink — always edit the canonical file
- Windows note: git symlinks need `core.symlinks=true` on native Windows checkouts

Every skill's frontmatter records its origin in `metadata.hermes.origin` (`agent` | `repo:<name>` |
`vendored` + `source:` | `hub`), plus `exposure: private` when it must never be published; bundled
addon-shipped skills carry no marker. The marker travels with the file — a deploy or copy never adds or
strips it. Values and their consequences: `agent-skills-architecture`.

## A repo-bound runbook is a skill, not a `docs/` page

Anything under `docs/` is crawled into the published site unless excluded, and a doc only helps a human
who remembers to go read it — a skill loads itself at task time, for both agents. When a doc starts
describing how to *do* something (a procedure, not reference material for readers), move it into a skill.

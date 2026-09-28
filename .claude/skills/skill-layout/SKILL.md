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

## Every skill carries its origin in the frontmatter

Frontmatter records who owns the canonical copy, so a reader can tell a repo skill from one the agent
created on its own:

```yaml
metadata:
  hermes:
    origin: repo:personal-os-setup   # agent | repo:<name> | vendored | hub
    exposure: private                # ONLY when the skill must never be published
```

- `origin: agent` — created in the Hermes own store by the agent, no git backing.
- `origin: repo:<name>` — the canonical copy lives in that repo (this file's case).
- `origin: vendored` + `source: <owner>/<repo>` — a whole-folder third-party copy.
- `origin: hub` — installed from the skills hub; tool-managed, never vendored into git.
- `exposure: private` — never promote, publish or copy into a public repo as-is; sanitize first.
  Absent = publishable (the default).
- Addon-shipped (bundled) skills carry **no** marker — editing one freezes its sync forever, and their
  provenance is already authoritative in `.bundled_manifest` and the addon's own `skills/` tree.

The marker travels with the file (a deploy or copy never adds or strips it). Canonical spec:
the `agent-skills-architecture` skill.

## A repo-bound runbook is a skill, not a `docs/` page

Anything under `docs/` is crawled into the published site unless specifically excluded, and a doc
only helps a human who remembers to go read it — a skill loads itself at task time, for both agents.
If a doc starts describing how to *do* something (a procedure, not reference material for readers),
that's the signal to move it into a skill instead.

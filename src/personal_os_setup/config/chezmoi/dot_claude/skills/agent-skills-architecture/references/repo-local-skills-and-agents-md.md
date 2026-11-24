# Repo-local skills + AGENTS.md ↔ CLAUDE.md

- Canonical file `<repo>/.claude/skills/<name>/SKILL.md`; `make skills-link` refreshes the git-tracked
  `.agents/skills/<name>` symlink and `make skills-check` must print `OK <name>` for each one. A repo with no skill
  tooling yet gets that layout by hand — relative symlink, modes normalized (a copy out of the own store arrives
  `700`, git wants `644`), plus a `## Skills` section in its `AGENTS.md` naming the skills and the placement rule,
  else the next session invents a second layout.
- This repo itself: canonical `.claude/skills/<name>/SKILL.md`; `.agents/skills/<name>` are git symlinks to it (Hermes, Codex,
  OpenCode and the skills CLI read `.agents/skills`). Add a skill → create it, then `make skills-link`; verify with
  `make skills-check`. Never edit through a symlink. Native Windows checkouts need `core.symlinks=true`.
  A repo-bound runbook (a procedure, not reader-facing reference) is a skill, not a `docs/` page.
- Keep repo-bound runbooks OUT of `docs/`: `properdocs.yml` uses `docs_dir: .` and excludes only what its glob
  lists, so a new `docs/<topic>/` page is PUBLISHED publicly. Skills sit outside `docs/`.
- `AGENTS.md` = canonical rules for ALL agents, sent with EVERY prompt → <150 lines, index-shaped (orientation
  table + pointers), invariants and gotchas only. `CLAUDE.md` = `@AGENTS.md` + Claude-only depth; never duplicate a
  rule across the two (divergence is the #1 documented failure mode).
- Pick the tier first: repo-bound → that repo's `.claude/skills/`; cross-machine curated → the chezmoi
  `dot_claude/skills` source + deploy; fast-moving upstream → plugin pack or `npx`, never hand-copied into the authored tree.

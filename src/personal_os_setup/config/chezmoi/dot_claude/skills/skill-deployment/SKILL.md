---
name: skill-deployment
description: Use when deploying the shared agent skills via chezmoi, or fixing "not managed" errors.
---

# Skill Deployment via chezmoi

Shared skills: repo `src/personal_os_setup/config/chezmoi/dot_claude/skills/` → `~/.claude/skills`
(Claude Code + Hermes external_dirs). Desktops: TUI dotfiles tab. Container/CLI:

> Scope: this deploys only the **general/shared** skills. Repo-specific skills are NOT part of it —
> they live in the repo itself under `.claude/skills/` (Claude Code reads those natively) with
> git-symlink mirrors in `.agents/skills/` for other agents, kept in sync by `skills.mk`
> (`make skills-link` / `make skills-check`; see the `skill-layout` skill).

**Two loading paths — don't confuse them:**

- **Shared (Track 1)** → `skills.external_dirs` in the Hermes config: always in the index, every
  session, any cwd. That one entry (`~/.claude/skills`) is what both agents load.
- **Repo-scoped** → `<repo>/.hermes/skills` + `.agents/skills` load *only* when the session's
  working dir resolves to the repo's git root **and** that root is in `skills.trusted_project_dirs`.
  A session rooted at HOME (global `terminal.cwd`) resolves no repo, so nothing loads — upstream
  Hermes bug #103423, fix in review as PR #103424. Never park repo skills in `external_dirs`
  (N repos × M skills doesn't scale): promote a repo's skills to Track 1 if they must be
  always-on, otherwise they're read on demand.

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude    # deploy ONLY the skills
```

**No chezmoi (HA container/CLI):** `cd <repo> && make skills-deploy` — copies the same source
to `~/.claude/skills`. The make target lives in `makefiles/skills.mk` (same file as
`skills-link`/`skills-check`).

Two gotchas (both previously caused "not managed"):
1. `--source` = repo **ROOT** (git-backed, `.chezmoiroot` points at the nested dir) — never the nested dir
2. Run from **HOME** — targets resolve against CWD

⚠️ The nested `config/chezmoi` dir must **never** contain its own `.chezmoiroot`: the app
(`src/personal_os_setup/tasks/system/chezmoi.py`) passes that dir directly as `--source`, so a
nested `.chezmoiroot` would double-redirect and break the app's deploy path.

Refresh after `git pull`. On the container deploy only `.claude` (full apply would dump desktop dotfiles).

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

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude    # deploy ONLY the skills
```

Two gotchas (both previously caused "not managed"):
1. `--source` = repo **ROOT** (git-backed, `.chezmoiroot` points at the nested dir) — never the nested dir
2. Run from **HOME** — targets resolve against CWD

⚠️ The nested `config/chezmoi` dir must **never** contain its own `.chezmoiroot`: the app
(`src/personal_os_setup/tasks/system/chezmoi.py`) passes that dir directly as `--source`, so a
nested `.chezmoiroot` would double-redirect and break the app's deploy path.

Refresh after `git pull`. On the container deploy only `.claude` (full apply would dump desktop dotfiles).

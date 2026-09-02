---
name: skill-deployment
description: Use when deploying the shared agent skills via chezmoi, or fixing "not managed" errors.
---

# Skill Deployment via chezmoi

Shared skills: repo `src/personal_os_setup/config/chezmoi/dot_claude/skills/` → `~/.claude/skills`
(Claude Code + Hermes external_dirs). Desktops: TUI dotfiles tab. Container/CLI:

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude    # deploy ONLY the skills
```

Two gotchas (both previously caused "not managed"):
1. `--source` = repo **ROOT** (git-backed, `.chezmoiroot` points at the nested dir) — never the nested dir
2. Run from **HOME** — targets resolve against CWD

Refresh after `git pull`. On the container deploy only `.claude` (full apply would dump desktop dotfiles).

# Community skills via the Vercel skills CLI (npx skills)

Verified from docs/GitHub (Aug 2026) — step 5 of the mission, NOT yet executed locally. Commands below are official; treat local behavior as unverified until run.

## What it is

- `npx skills` = package manager for the open agent skills ecosystem (vercel-labs/skills, ~21.7K★, skills.sh / agenticskills.io).
- Registry = GitHub: ANY public repo with a SKILL.md at root is installable. Works with 40-73+ agents (claude-code, codex, cursor, opencode…).
- Manifest: `.skills.json`; lock file: `skills-lock.json` (tracks sourceUrl + skillFolderHash).

## Commands

```
npx skills find [query]                         # search (interactive or keyword)
npx skills add <owner/repo> [--skill <name>] [--all] [-a claude-code] [-g] [-y] [--list] [--copy]
npx skills list / remove <name> / init <name>   # day-2 management
npx skills check                                # compare lock hashes vs server → what changed
npx skills update                               # reinstall ONLY out-of-date skills (lock-driven)
```

- `-g` = global (user-level), omit = project scope. `-a claude-code` targets Claude Code. `--copy` copies files instead of symlinking.
- Version pinning (supply chain): `npx skills add owner/repo@<commit-or-tag>` or `gh skill install <owner/repo> <skill> --pin <hash>`.
- Update model: pull-to-update, never auto — Matt Pocock's README: "Nothing updates behind your back; pull my latest changes when you want them with npx skills update."

## Known pitfalls

- Symlink bug: `npx skills add -a claude-code` installs to `~/.agents/skills/<name>/` and is SUPPOSED to symlink into `~/.claude/skills/<name>` — regressions tracked in vercel-labs/skills issues #851 (global) and #1355 (project). Claude Code only reads `.claude/skills/`, so VERIFY the skill is actually visible there (or use --copy).
- Installer may write into repo-relative paths when run from a project dir — run from a neutral cwd for global installs.

## This user's flow (decided architecture)

1. `npx skills add <owner/repo> --skill <name> -a claude-code -g -y` (or pinned @commit)
2. COPY the skill folder into the shared dir: `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/<name>/`
3. Commit (`feat(skills): vendor <name>`) → PR → merge → chezmoi deploys to /config/.claude/skills on all machines; Hermes reads the same dir via external_dirs.
4. Updates: `npx skills check` → `npx skills update` → diff → commit (`feat(skills): update <name>`) → PR.

Why vendor: npx skills installs only into agent dirs — Hermes would never see them unless they land in the shared dir.

## Example

- `grill-me` (interview-the-user-relentlessly about a plan): from `mattpocock/skills`, install `npx skills@latest add mattpocock/skills --skill grill-me`. Fits the user's plan-first philosophy.
- Anthropic's own examples: `anthropics/skills` (document-skills, etc.) — installable as a Claude Code plugin marketplace or via skills CLI.

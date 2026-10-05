# Community skills — two independent discovery paths

There are two unrelated ways to pull in a community skill. Pick by WHO should see it: the Vercel
`skills` CLI vendors into git (both agents, via the shared dir); the Hermes hub installs straight
into the own store (Hermes-only, tool-managed). Never treat them as the same pipeline.

## Path 1 — `npx skills` (git-vendor path, both agents)

Verified from docs/GitHub (Aug 2026) — step 5 of the mission, NOT yet executed locally. Commands below are official; treat local behavior as unverified until run.

### What it is

- `npx skills` = package manager for the open agent skills ecosystem (vercel-labs/skills, ~21.7K★, skills.sh / agenticskills.io).
- Registry = GitHub: ANY public repo with a SKILL.md at root is installable. Works with 40-73+ agents (claude-code, codex, cursor, opencode…).
- Manifest: `.skills.json`; lock file: `skills-lock.json` (tracks sourceUrl + skillFolderHash).

### Commands

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

### Known pitfalls

- Symlink bug: `npx skills add -a claude-code` installs to `~/.agents/skills/<name>/` and is SUPPOSED to symlink into `~/.claude/skills/<name>` — regressions tracked in vercel-labs/skills issues #851 (global) and #1355 (project). Claude Code only reads `.claude/skills/`, so VERIFY the skill is actually visible there (or use --copy).
- Installer may write into repo-relative paths when run from a project dir — run from a neutral cwd for global installs.

### This user's flow (decided architecture)

1. `npx skills add <owner/repo> --skill <name> -a claude-code -g -y` (or pinned @commit)
2. COPY the skill folder into the shared dir: `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/<name>/`
3. Commit (`feat(skills): vendor <name>`) → PR → merge → chezmoi deploys to /config/.claude/skills on all machines; Hermes reads the same dir via external_dirs.
4. Updates: `npx skills check` → `npx skills update` → diff → commit (`feat(skills): update <name>`) → PR.

Why vendor: npx skills installs only into agent dirs — Hermes would never see them unless they land in the shared dir.

### Example

- `grill-me` (interview-the-user-relentlessly about a plan): from `mattpocock/skills`, install `npx skills@latest add mattpocock/skills --skill grill-me`. Fits the user's plan-first philosophy.
- Anthropic's own examples: `anthropics/skills` (document-skills, etc.) — installable as a Claude Code plugin marketplace or via skills CLI.

## Path 2 — Hermes hub discovery (own-store install, Hermes-only)

### Where the community lives

- CLI: `hermes skills search <query> [--source <src>]`, `hermes skills inspect <id>`,
  `hermes skills install <id> [--force]` (also reachable in-chat as `/skills <subcommand>`).
- Sources: `official` (the shipped optional catalog), `skills-sh` (the skills.sh registry), `well-known:<site-url>`
  (a site publishing `/.well-known/skills/index.json`), `browse-sh`, and custom taps added with
  `hermes skills tap add <owner>/<repo>`.
- Hub state sits in `$HERMES_HOME/skills/.hub/` (`taps.json`, `index-cache/`, `lock.json`, `quarantine/`,
  `audit.log`). `{"taps": []}` means no custom tap is registered — the built-in sources still work, so an empty
  tap list is not "no community available".
- Installs land in the own store: Hermes-only, hub-owned, and a name that collides with a vendored Track-1 skill
  gives two copies of one name. Vendor into the shared dir instead when both agents should see it.

### Querying the registry when the CLI is absent

The webui container ships no CLI, so the registry gets queried over HTTP. skills.sh has no public API yet (a
browsable `/api/skills` endpoint is an open feature request, vercel-labs/skills#426) and its pages are a
client-side app, so fetching a search URL returns an empty shell. What works:

- `web_search` with `site:skills.sh <domain terms>` — result snippets carry the skill's own SKILL.md text, which is
  usually enough to judge it without opening the page.
- `web_extract https://www.skills.sh/<owner>/<repo>` — lists every skill in that repo with install counts.
- `web_extract` a single skill page for the full body plus its audit panel.

Run several domain searches in one batch (HA, containers, networking, media, the user's actual stack) rather than
paging a leaderboard.

## Vetting a candidate (applies to either path)

- Per skill page: installs, repo stars, first-seen date, and three independent security audits (Gen Agent Trust
  Hub / Socket / Snyk). `Pass` everywhere is the bar; a `Warn` on a skill that ships scripts is a real signal; any
  `Fail` means skip it.
- The all-time leaderboard is dominated by a few mega-suites (frontend design, vendor SDK packs, cloud vendors) and
  is not a shopping list for a homelab/infra library.
- Overlap first: bundled equivalent, vendored Track-1 name, or a Track-2 Claude plugin already covering it — drop
  those before ranking anything.

### Exclusion patterns

- **Machine-specific suites**: the body is "run `~/<repo>/skills/<x>/scripts/check.sh`" — it only works on the
  machine that authored it.
- **Maintainer-internal sets**: a repo whose skills are its OWN dev workflow (worktree helpers, issue analysis,
  PR checkers, eval harnesses) with ~1 install each — shipped for its contributors, not for users.
- **Mega-packs with a few gems**: 100+ entries that are mostly cloud/LLM filler; cherry-pick the handful that match
  and never recommend the suite as a whole.
- **Hype-only skills**: a title plus "generates production-ready code" and no procedure.

### Report shape

Ranked short list (5 max), one line each: `owner/repo/skill` — installs, audit verdict, and the concrete gap it
fills in THIS library. Then one "deliberately excluded" line naming the near-misses and why, so the user can see
what was considered and rejected. Give the exact install command, note where it lands, and if you could not run
it, say plainly that nothing was installed and the install path is unverified.

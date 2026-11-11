---
name: skill-deployment
description: Use when deploying the shared agent skills via chezmoi, or fixing "not managed" errors.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Skill Deployment via chezmoi

Authored skills (ONE tree): repo `src/personal_os_setup/config/chezmoi/dot_claude/skills/` → `~/.claude/skills`
(Claude Code + Hermes external_dirs), with per-skill Codex links in `~/.agents/skills`.
Desktops: select the whole `.claude` folder in the TUI so both after-scripts run. Container/CLI:

```bash
REPO=/config/workspace/personal-os-setup
cd ~ && chezmoi apply -v --force --source "$REPO" .claude    # deploy ONLY the skills
```

> Scope: repo-specific skills are NOT deployed here — they live in `.claude/skills/` + `.agents/skills/` (`make skills-link` / `make skills-check`; see `agent-skills-architecture` → "Repo-local skills").

Repo-scoped skills (`<repo>/.hermes/skills` + `.agents/skills`) load *only* when the session's
working dir resolves to the repo's git root **and** that root is in `skills.trusted_project_dirs`.
A session rooted at HOME (global `terminal.cwd`) resolves no repo, so nothing loads. Never park repo skills in `external_dirs`
(N repos × M skills doesn't scale): promote a repo's skills to the global tree if they must be
always-on, otherwise they're read on demand.

Loading internals: `agent-skills-architecture` → "What actually loads".

**No chezmoi (HA container/CLI):** `cd <repo> && make skills-personal-repo-to-live` — copies the same source
to `~/.claude/skills` and links each authored name into `~/.agents/skills`. Existing Codex
destinations that point elsewhere are conflicts; reconcile them manually. `make skills-status`
verifies the links. Python 3 is required for the shared helper. The make target lives in `makefiles/skills.mk` (same file as
`skills-link`/`skills-check`).

Rules: `--source` = repo **ROOT** (git-backed, `.chezmoiroot` points at the nested dir — never the nested dir); run from **HOME** (targets resolve against CWD).

⚠️ The nested `config/chezmoi` dir must **never** contain its own `.chezmoiroot`: the app
(`src/personal_os_setup/tasks/system/chezmoi.py`) passes that dir directly as `--source`, so a
nested `.chezmoiroot` would double-redirect and break the app's deploy path.

Refresh after `git pull`. On the container deploy only `.claude`: the package source also holds the desktop
config (`dot_config/hypr`, ghostty, mpv, OpenRGB, coolercontrol, mimeapps…), and `/config/.claude/` also holds
Claude Code's own credentials/sessions — deploy into the `skills/` subdir only.

**File-level fallback (source dir is not a git repo):** `--source-path` with ABSOLUTE source paths works on any dir.

```bash
S=/config/workspace/personal-os-setup/src/personal_os_setup/config/chezmoi
chezmoi --source "$S" apply -v --force --parent-dirs --refresh-externals=never \
  --source-path "$S/dot_claude/skills/<name>/SKILL.md"
```

- If it hangs mid-apply with `--parent-dirs`, retry the missing file alone without it (the dirs already exist).
- `chezmoi managed --source "$S"` lists entries (live scan); `chezmoi cat`/`apply <target>` use target resolution,
  which is what fails on a non-git source. Idempotent: re-run for the skills a `git pull` changed.
- The TUI (`tasks/system/chezmoi.py`) runs the same flags with `chezmoi_source_dir()` as `--source`.

Pin the deployed names against the Curator per machine after each deploy: `hermes curator pin <skill>` (`unpin`/`status`/`run`/`pause`/`list-unmanaged` also exist).

Then make running sessions see the edit **without `/new`**: `hermes sessions refresh-prompts` (all continuing
sessions) or `--session <id> --json` for one. Each refreshed session pays one prompt-cache miss; history and
session ids are kept.

⚠️ **A `hermes curator lock`ed skill cannot be deployed by the agent.** Lock refuses `skill_manage`,
`write_file`, `patch` *and* terminal writes, so `make skills-personal-repo-to-live` aborts on that file — and
`hermes curator unlock` is also refused to the agent ("Only the user can unlock a skill"). Ask the user to run
the unlock, then deploy. Lock is the right tool for a skill he curates by hand; pin (above) only keeps the
curator away and still allows edits.

Prefer `lock` over `pin` when the goal is "the agent must not rewrite this skill": pin is curator-only,
lock is enforced against every writer including a deploy run from a session.

**Sync direction — repo → live, one way.** The repo copy is the truth; `make skills-personal-repo-to-live` is
copy-only: it overwrites whatever is live and deletes nothing.

- Never deploy a skill that already lives elsewhere in the repo and is symlinked into the store
  (e.g. a `docs/...`-hosted one): `cp -R` follows the symlink and writes through it into the
  tracked source. Keep the symlink, don't duplicate the directory.

**Drift:** `make skills-status` (one read-only report: per-skill OK/DIFFERS/MISSING, Codex links, Hermes name clashes, unlisted skills, third-party content; non-zero on any problem). `skills-personal-repo-to-live` runs the same scan as its gate: only a DIFFERS aborts. Override with `make skills-personal-repo-to-live FORCE=1` only after porting the live edit into the repo — see `references/deploy-drift-and-reconciliation.md`. Save a live skill: `make skills-personal-live-to-repo NAME=<name>`.

## Third-party skills — `npx skills` (skills-only packs)

**Who deploys what (one split, no overlap):**

- **Authored tree** → chezmoi. `dot_claude/skills/` is ordinary managed files, so `chezmoi apply` writes
  them; there is deliberately **no `run_` script for the copy** (`make skills-personal-repo-to-live` is the no-chezmoi twin).
  `run_after_zz-link-authored-skills.sh` only creates Codex links using the same helper as Make.
- **npx replay** → the one thing chezmoi cannot do. Script:
  `src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh`
  (plain shell, no template vars). It replays every entry of `third-party-skills.lock.json` with
  `npx -y skills add <source> -s <name> -a claude-code -a codex -g -y` (ONE call per skill naming every selected agent — that is what makes npx link the Claude entry to the canonical copy; a single-agent call writes a copy and replaces a link), only for entries that are missing, broken, unlinked or stale.
- **make** → `make skills-thirdparty-repo-to-live` installs for both agents. `AGENT=codex` selects only
  Codex; `AGENTS="claude-code codex"` selects both explicitly. It sets `STRICT=1` (`FORCE=1` reinstalls
  everything and skips the edit gate) and fails if Python 3 or npx is missing. Optional chezmoi replay logs `SKIPPED` and writes no success stamp.
- **Verification** → `make skills-status` checks lock identities and each agent's manifest, and reports `DIFFERS` for installed files
  newer than the lock's `updatedAt` (a hand edit). No receipts or stamp files exist.
- **Idempotent** → a plain apply or make run installs only what is missing, broken, unlinked or stale, and
  checks each result (`npx` exits 0 on cancel).
- **Updates** → replay fetches current upstream. If a folder ID changed, review it, save the new live
  lock with `make skills-thirdparty-live-to-repo`, and replay again. The lock is a drift reference, not a pin.
- **Packaged source** → the shared helper ships with `dot_claude`, so authored links work without
  a checkout. Optional third-party replay reports `SKIPPED` if no lock is reachable; set `LOCK`
  explicitly to enable it. A strict replay fails instead.
- **Windows Git Bash** → the replay attempts the same installation and surfaces errors; no silent no-op.

**Lock carve-out:** `claude-code` and `hermes-agent` come from
`NousResearch/hermes-agent` and also ship with Hermes. Installing them in Claude/Codex is intentional;
if Hermes also has a bundled copy under `~/.hermes/skills`, run `make skills-status` and reconcile the
duplicate. Never add Hermes as a separate npx target.

For the `npx skills` install recipe (targeting, symlink layout, lock location, updating, name checks, plugin-pack
exception) see `agent-skills-architecture` → `references/installing-and-vetting-skills.md` § "npx skills recipe".

## Bundled (addon-shipped) skills are read-only

Never edit a bundled skill (a modified copy is skipped by the sync forever). Local additions go in a skill we own; the
`hermes skills diff/reset/repair-official` workflow and its two traps (backup dir inside the scanned tree, interactive
prompt) are in `hermes-instance-audit` → `references/skills-sync-and-bundling.md` § "Bundled skills are read-only".

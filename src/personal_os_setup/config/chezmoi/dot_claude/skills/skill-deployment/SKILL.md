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

> Scope: repo-specific skills are NOT deployed here — they live in `.claude/skills/` + `.agents/skills/` (`make skills-link` / `make skills-check`; see the `skill-layout` skill).

Repo-scoped skills (`<repo>/.hermes/skills` + `.agents/skills`) load *only* when the session's
working dir resolves to the repo's git root **and** that root is in `skills.trusted_project_dirs`.
A session rooted at HOME (global `terminal.cwd`) resolves no repo, so nothing loads — upstream
Hermes bug #103423, fix in review as PR #103424. Never park repo skills in `external_dirs`
(N repos × M skills doesn't scale): promote a repo's skills to the global tree if they must be
always-on, otherwise they're read on demand.

Loading internals: `agent-skills-architecture` → "What actually loads".

**No chezmoi (HA container/CLI):** `cd <repo> && make skills-repo-to-live` — copies the same source
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

**Sync direction — repo → live, one way.** The repo copy is the truth; `make skills-repo-to-live` is
copy-only: it overwrites whatever is live and deletes nothing.

- Never deploy a skill that already lives elsewhere in the repo and is symlinked into the store
  (e.g. a `docs/...`-hosted one): `cp -R` follows the symlink and writes through it into the
  tracked source. Keep the symlink, don't duplicate the directory.

**Drift:** `make skills-status` (one read-only report: per-skill OK/DIFFERS/MISSING, Codex links, Hermes name clashes, unlisted skills, third-party content; non-zero on any problem). `skills-repo-to-live` runs the same scan as its gate: only a DIFFERS aborts. Override with `make skills-repo-to-live SKILLS_FORCE=1` only after porting the live edit into the repo — see `references/deploy-drift-and-reconciliation.md`. Save a live skill: `make skills-live-to-repo NAME=<name>`.

## Third-party skills — `npx skills` (skills-only packs)

**Who deploys what (one split, no overlap):**

- **Authored tree** → chezmoi. `dot_claude/skills/` is ordinary managed files, so `chezmoi apply` writes
  them; there is deliberately **no `run_` script for the copy** (`make skills-repo-to-live` is the no-chezmoi twin).
  `run_after_zz-link-authored-skills.sh` only creates Codex links using the same helper as Make.
- **npx replay** → the one thing chezmoi cannot do. Script:
  `src/personal_os_setup/config/chezmoi/dot_claude/run_after_replay-third-party-skills.sh`
  (plain shell, no template vars). It replays every entry of `third-party-skills.lock.json` with
  `npx -y skills add <source> -s <name> -a <agent> -g -y --copy` for Claude Code and Codex by default.
- **make** → `make skills-thirdparty-repo-to-live` installs for both agents. `AGENT=codex` selects only
  Codex; `AGENTS="claude-code codex"` selects both explicitly. It sets `FORCE=1 STRICT=1` and fails
  if Python 3, npx or jq is missing. Optional chezmoi replay logs `SKIPPED` and writes no success stamp.
- **Verification** → `make skills-status` checks lock identities, each agent's manifest, and local
  content receipts (SHA-256 over installed paths, executable flags and bytes). The receipts live at
  `$XDG_STATE_HOME/personal-os-setup/skills-installed.json`, defaulting to `~/.local/state`.
  They are not the npx lock and must never be committed. Existing installs need one explicit replay.
- **Stamp** → plain apply skips only when the lock, selected agents and installed content still verify.
  Deleted/edited files trigger replay. Failed installs, missing metadata and lock drift never stamp.
- **Updates** → replay fetches current upstream. If a folder ID changed, review it, save the new live
  lock with `make skills-thirdparty-live-to-repo`, and replay again. The lock is a drift reference, not a pin.
- **Packaged source** → the shared helper ships with `dot_claude`, so authored links work without
  a checkout. Optional third-party replay reports `SKIPPED` if no lock is reachable; set `LOCK`
  explicitly to enable it. A strict replay fails instead.
- **Windows Git Bash** → the replay attempts the same installation and surfaces errors; no silent no-op.

**Lock carve-out:** `claude-code`, `hermes-agent` and `hermes-agent-skill-authoring` come from
`NousResearch/hermes-agent` and also ship with Hermes. Installing them in Claude/Codex is intentional;
if Hermes also has a bundled copy under `~/.hermes/skills`, run `make skills-status` and reconcile the
duplicate. Never add Hermes as a separate npx target.

For a third-party repo that ships **only** a `skills/` tree (no plugin manifest per harness). Packs
that ship their own per-harness plugins (hooks, slash commands) are a different case — see the end
of this section.

```bash
npx skills add <owner>/<repo> -s <skill> -a claude-code -a codex -g -y --copy   # one skill
npx skills add <owner>/<repo> -a claude-code -a codex -g -y --copy                             # whole pack
```

- **Target `-a claude-code -a codex` — the Claude copy already reaches Hermes.** Hermes reads `~/.claude/skills` via
  `skills.external_dirs`, so the Claude installation serves Hermes too. Adding `-a hermes-agent` puts the same
  name in `~/.hermes/skills` AND under `~/.claude/skills` → two roots, one name, and Hermes refuses
  that name (`Ambiguous skill name … across your local skills dir and external_dirs`).
- **Lands as a real directory** in each selected agent’s skill directory (we pass `--copy` on every install, incl. `make skills-thirdparty-repo-to-live`); check the filesystem, not the CLI's success message. Flat placement, so the entry shows a blank category in `hermes skills list`.
- **The lock is OUTSIDE any repo:** `$XDG_STATE_HOME/skills/.skill-lock.json` (older CLIs: `~/.agents/.skill-lock.json`; the Makefile checks both) (v3: `source`, `sourceType`,
  `sourceUrl`, `skillPath`, `skillFolderHash`). Portability = commit a COPY plus a replay command;
  the live lock is never the record we ship. Replay/drift: `make skills-thirdparty-repo-to-live` / `make skills-status` in
  `makefiles/skills.mk`.
- **Updating:** `npx skills update` is broken (vercel-labs/skills#484 — reports "up to date" while
  upstream moved). Re-add is the update path: `-s <name> -y` refetches and bumps the hash; diff the
  lock to see what moved. Renovate has no skills.sh manager yet (discussion #41841), so automation =
  a scheduled workflow that re-adds and opens a lock-bump PR.
- **Before installing, check the names.** Hermes has no namespacing, so a third-party name that
  collides with a shipped or deployed skill breaks that name for both. Compare against
  `<install>/skills/`, `optional-skills/` and the deployed sets; install a `-s` subset if needed.
- **Symlink regressions exist** → verify the entry actually resolves in
  each agent dir (`find -L … -name SKILL.md`), or fall back to `--copy`. A symlink that exists is not
  proof the agent listed it.
- **Supply-chain panel runs pre-install** (Gen / Socket / Snyk). Record the verdict with the lock —
  a replay cannot re-prove it.
- **Node is only in the agent container.** The webui container ships no Node by design, so `npx`
  does not exist there.

**Packs that ship their own per-harness plugins are NOT this flow.** Install them per harness through
that harness's native channel, one canal per agent — never plugin *and* npx for the same agent.
Worked example, `obra/superpowers` (ships `.claude-plugin/`, `.codex-plugin/`, `.hermes-plugin/`,
`.cursor-plugin/`, … plus a SessionStart hook and a `pre_llm_call` bootstrap):

- Claude Code: `/plugin install superpowers@claude-plugins-official`
- Hermes: `hermes plugins install obra/superpowers` — registers every skill namespaced as
  `superpowers:<name>` (so no collision with shipped names) and injects the first-turn bootstrap
- Codex: its own plugin marketplace, `/plugins`
- `npx skills add obra/superpowers` on a harness that has the plugin = the same 15 skills twice, and
  it silently drops the bootstrap hook. Don't.

## Bundled (addon-shipped) skills are read-only

Bundled skills sync from the addon with a per-directory hash manifest, so a copy we edited is skipped
forever and upstream improvements never reach us. Never edit one. When we want a local addition:

1. `hermes skills diff <name>` — see exactly what our copy adds.
2. Move that content into a skill we own (a `*-ops` addendum, e.g. `claude-code-ops` for the container
   facts about the `claude-code` skill).
3. `hermes skills reset <name>` — clears the "user-modified" flag so updates work again; it does not
   touch the content. `hermes skills reset <name> --restore` also reverts to stock.
4. Confirm with `hermes skills list-modified`; the next addon update brings the stock version.

⚠️ **`hermes skills repair-official <name> --restore` writes its backup INSIDE the skills tree** —
to `~/.hermes/skills/.restore-backups/<ts>/<category>/<name>/`. That directory is *not* in Hermes'
excluded-scan list, so the backup is a second copy of the same name and the skill becomes
**unloadable**: `Ambiguous skill name … Refusing to guess`. Move the backup out of the
scanned root straight after any restore:
`mv ~/.hermes/skills/.restore-backups ~/.hermes/backups/restore-backups-<date>`.

⚠️ **`hermes skills reset` blocks on an interactive prompt — never call it from a non-interactive
surface.** A plain terminal call, `execute_code` or a delegated run hangs until the caller times out and **changes nothing**, because the prompt is never answered. Drive it from a
PTY, or skip it: to de-fork, refresh the live copy from the stock tree with a plain copy —
`cp -R /config/skills/<category>/<name>/. ~/.hermes/skills/<category>/<name>/` — which leaves the live
copy byte-identical to stock with no prompt. **Refresh, don't delete**: deleting the own-store copy
drops that name out of Hermes' index (the add-on's shipped tree is not indexed on its own, and a name
absent from `.bundled_manifest` has no reseed path) — so a skill with real usage disappears.
`hermes skills diff <name>` is the read-only way to see what a reset would change.

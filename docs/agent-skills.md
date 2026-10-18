# Agent skills

Skills are small `SKILL.md` instruction folders that coding agents (Claude Code, Hermes, ...) load on demand.
This repo manages them in three layers. You can drive all of them from the TUI or from `make`.

| Layer | What it is | Source of truth | Lands in |
|---|---|---|---|
| **Authored skills** | Skills you write and keep | `src/personal_os_setup/config/chezmoi/dot_claude/skills/` | `~/.claude/skills` |
| **Third-party skills** | Skills from other repos, installed with `npx skills` | `third-party-skills.lock.json` (repo root) | `~/.claude/skills` |
| **Repo-local skills** | Runbooks for this repo only | `.claude/skills/` (+ `.agents/skills/` symlinks) | read in place |

Hermes reads `~/.claude/skills` too, so one deploy serves both agents. Never put the same skill name in
`~/.hermes/skills` as well: the name becomes ambiguous and Hermes refuses to load it.

`skills.keep` (repo root) lists the authored skills you deliberately keep in the repo, one name per line.

## Using the TUI

Open the **Sync dotfiles** tab, expand `.claude`, and select the **whole `.claude` folder** (not single files).

| Button | What it does |
|---|---|
| diff selected | Shows what would change in `~/.claude` |
| apply selected | Copies the authored skills to `~/.claude/skills` and runs the third-party replay script |
| re-add selected | Pulls a skill you edited live back into the repo's source tree |
| chezmoi: clean backups | (action button above the list) Deletes the `<name>_<timestamp>_backup` copies that earlier applies left next to managed files, including those in `~/.claude/skills` |

Things to know:

- **Select the folder.** The replay script (`run_after_replay-third-party-skills.sh`) only runs when its own
  entry is selected. Selecting a single file applies that file and silently skips the script.
- **It never deletes.** A skill removed from the repo stays in `~/.claude/skills` until you delete it by hand.
- **Each apply leaves backups.** Before overwriting, it copies every selected file to
  `<name>_<timestamp>_backup<ext>` in the same folder, and `make skills-diff` then reports `DIFFERS`. Use
  **chezmoi: clean backups** to remove them.
- **It does not check for drift.** Apply overwrites a live skill that was edited and not yet pulled back with
  re-add. Run `make skills-diff` first if an agent may have edited a live skill.
- **Re-add only handles files already tracked.** For a brand-new live-only skill, use `make skills-keep`.

## Using make

| Command | Purpose |
|---|---|
| `make skills-diff` | Compare each authored skill with its live copy (`OK` / `DIFFERS` / `MISSING`); read-only |
| `make skills-drift` | Like `skills-diff` but only `DIFFERS` fails; this is the deploy gate |
| `make skills-deploy` | Copy the authored skills to `~/.claude/skills` without chezmoi; refuses if a live copy differs (`SKILLS_FORCE=1` overrides) |
| `make skills-status` | Flag names present in both `~/.claude/skills` and `~/.hermes/skills`, and repo skills missing from `skills.keep` |
| `make skills-keep NAME=<name>` | Save a live skill into the repo and add it to `skills.keep` |
| `make skills-thirdparty` | Report drift between the committed lock and the live `npx skills` lock; read-only |
| `make skills-thirdparty-save` | Copy the live `npx skills` lock into the repo as `third-party-skills.lock.json` |
| `make skills-thirdparty-replay` | Reinstall every third-party skill listed in the committed lock (`AGENT=codex` for another agent) |
| `make skills-link` / `make skills-check` | Create / verify the `.agents/skills` symlinks for repo-local skills |

### Typical flows

- **Edit an authored skill:** change it in the source tree, then apply from the TUI (or `make skills-deploy`),
  then `make skills-diff` to confirm every skill reports `OK`.
- **Add a third-party skill:** `npx skills add <owner>/<repo> -s <skill> -a claude-code -g -y --copy`, then
  `make skills-thirdparty-save`, then commit the updated lock.
- **Set up a new machine:** clone the repo, then apply `.claude` from the TUI. The lock is replayed for you. Use
  `make skills-thirdparty-replay` to force it.
- **Check for upstream changes:** `make skills-thirdparty`. It reports `CHANGED` when the installed version
  differs from the committed lock.

### What `skills-thirdparty-replay` does

The committed lock records which skills were installed and from which repo. The replay runs
`npx skills add <source> -s <skill> -a <agent> -g -y --copy` once per entry, so every listed skill is
(re)installed from its upstream repo, as a real directory under `~/.claude/skills`. It needs Node (`npx`) and
`jq`, fetches the **latest** upstream version rather than a pinned one, and ends with `make skills-thirdparty` to
show any drift against the lock. Press Ctrl-C only after it finishes: it installs the entries one at a time.

A plain `chezmoi apply` runs the same script but skips it when the lock hasn't changed since the last fully
successful run. The make target always replays.

## Where the `npx skills` lock lives

The CLI keeps its own live lock outside the repo: `$XDG_STATE_HOME/skills/.skill-lock.json` on current versions
(`~/.local/state/skills/` by default), `~/.agents/.skill-lock.json` on older ones. The Makefile checks both. The
repo never shares that file with chezmoi, so a sync can't overwrite the CLI's live lock with a stale one.

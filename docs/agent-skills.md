# Agent skills

Skills are small `SKILL.md` folders that coding agents (Claude Code, Hermes, ...) load on demand. Each skill's
short description is loaded into every session; the body is read only when the task matches. This page covers
what skills this repo provides, how they get onto a machine, and how to add or change them.

- [Skill catalog](#skill-catalog): every skill, grouped by layer
- [How skills are installed](#how-skills-are-installed): TUI and `make`
- [Adding skills](#adding-skills): your own, third-party, repo-local
- [Reference](#reference): `make` targets and internals

## The three layers

| Layer           | What it is                                           | Source of truth                                                                     | Lands in           | Reaches                 |
|-----------------|------------------------------------------------------|-------------------------------------------------------------------------------------|--------------------|-------------------------|
| **Authored**    | Skills you write and keep                            | `src/personal_os_setup/config/chezmoi/dot_claude/skills/` (listed in `skills.keep`) | `~/.claude/skills` | Claude Code and Hermes  |
| **Third-party** | Skills from other repos, installed with `npx skills` | `third-party-skills.lock.json` (repo root)                                          | `~/.claude/skills` | Claude Code and Hermes  |
| **Repo-local**  | Runbooks for working on this repo only               | `.claude/skills/` (+ `.agents/skills/` symlinks)                                    | read in place      | whoever opens this repo |

Hermes reads `~/.claude/skills` too, so one deploy serves both agents. Never put the same skill name in
`~/.hermes/skills` as well: the name becomes ambiguous and Hermes refuses to load it (`make skills-status` flags it).

## Skill catalog

### Authored skills (16)

General workflow:

| Skill               | Use it for                                                                                                                         |
|---------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `coding-workflow`   | Any coding task: plan, confirm, implement, verify, open a PR. Also the pre-push checklist and how to find a repo's own conventions |
| `template-adoption` | Starting a new project from a house template, or aligning an existing repo with one                                                |
| `git-line-endings`  | CRLF/LF churn breaking git diffs                                                                                                   |

GitHub:

| Skill                            | Use it for                                                                           |
|----------------------------------|--------------------------------------------------------------------------------------|
| `github-auth`                    | Setting up GitHub access: `gh` login, or a PAT/SSH key as a last resort              |
| `github-pr-workflow`             | Issues and the PR lifecycle: file and triage issues, branch, commit, open, CI, merge |
| `github-code-review`             | Reviewing a local diff or a PR, with inline comments via `gh` or REST                |
| `github-repo-management`         | Clone, create, fork; remotes and releases; adding missing community health files     |
| `github-actions-trigger-gotchas` | Workflows that fire wrong or not at all                                              |

Skills and the Hermes box:

| Skill                           | Use it for                                                                 |
|---------------------------------|----------------------------------------------------------------------------|
| `agent-skills-architecture`     | Organizing, deploying, installing, auditing and retiring skills            |
| `skill-deployment`              | Deploying the shared skills with chezmoi, and fixing "not managed" errors  |
| `claude-code-ops`               | Install, auth and model defaults for the Claude Code CLI on the Hermes box |
| `hermes-instance-audit`         | Auditing a live Hermes install: skills, plugins, config                    |
| `hermes-session-recall`         | Recalling past or continued Hermes sessions                                |
| `hermes-cron-automations`       | Building a recurring automation on the Hermes box                          |
| `debugging-hermes-tui-commands` | Debugging Hermes TUI slash commands (Python, gateway, Ink UI)              |

Media:

| Skill                         | Use it for                                                                                                                                          |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| `youtube-download-automation` | Ingesting a YouTube link or playlist into the music library: what's new, genre sourcing, yt-dlp download. Plans first, then asks before downloading |

### Third-party skills (11)

Installed with `npx skills`, tracked in `third-party-skills.lock.json`.

| Skill                          | Source                      | Use it for                                                                       |
|--------------------------------|-----------------------------|----------------------------------------------------------------------------------|
| `grill-me`                     | `mattpocock/skills`         | Being interviewed about a plan or design until every branch is resolved          |
| `grill-with-docs`              | `mattpocock/skills`         | The same interview, plus building a `GLOSSARY.md` and decision records as you go |
| `grilling`                     | `mattpocock/skills`         | The reusable interview primitive the two skills above call                       |
| `tdd`                          | `mattpocock/skills`         | Test-first development, one red-green-refactor slice at a time                   |
| `diagnosing-bugs`              | `mattpocock/skills`         | A gated loop for hard bugs and performance regressions                           |
| `handoff`                      | `mattpocock/skills`         | Compacting a conversation into a document another agent can continue from        |
| `differential-review`          | `trailofbits/skills`        | Security-focused review of a PR, commit or diff                                  |
| `find-skills`                  | `vercel-labs/skills`        | Discovering and installing skills                                                |
| `claude-code`                  | `NousResearch/hermes-agent` | Delegating coding work to the Claude Code CLI                                    |
| `hermes-agent`                 | `NousResearch/hermes-agent` | Using, configuring and extending Hermes Agent                                    |
| `hermes-agent-skill-authoring` | `NousResearch/hermes-agent` | Writing in-repo `SKILL.md` files                                                 |

### Repo-local skills (9)

Runbooks for working on this repo. They are not deployed to `~/.claude/skills`.

| Skill                | Use it for                                                                      |
|----------------------|---------------------------------------------------------------------------------|
| `add-system-action`  | Adding a TUI button or action, or a new package-manager backend                 |
| `chezmoi-scripts`    | Writing and debugging chezmoi `run_` scripts, and why they sometimes don't fire |
| `docs-site`          | Adding doc pages and building, previewing or deploying the properdocs site      |
| `run-tests`          | Running and writing tests; why integration tests must not run locally           |
| `ship-feature`       | Branching, conventional commits and the PR / squash-merge flow                  |
| `vm-lab`             | The local KVM/QEMU VM lab (`make vm-*`): CachyOS, Ubuntu, Windows, macOS guests |
| `fork-and-customize` | Forking and rebranding this repo for your own setup                             |
| `repo-gotchas`       | Known drift between the docs and what the repo really does                      |
| `skill-layout`       | How skills are organized in this repo                                           |

## How skills are installed

### Using the TUI

Open the **Sync dotfiles** tab, expand `.claude`, and select the **whole `.claude` folder** (not single files).

| Button                 | What it does                                                                                                                                                         |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| diff selected          | Shows what would change in `~/.claude`                                                                                                                               |
| apply selected         | Copies the authored skills to `~/.claude/skills` and runs the third-party replay script                                                                              |
| re-add selected        | Pulls a skill you edited live back into the repo's source tree                                                                                                       |
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

### Setting up a new machine

Clone the repo, then apply `.claude` from the TUI. The third-party lock is replayed for you. Without the TUI:
`make skills-deploy` (authored skills) and `make skills-thirdparty-replay` (third-party skills).

## Adding skills

### Your own (authored)

1. Create `src/personal_os_setup/config/chezmoi/dot_claude/skills/<name>/SKILL.md`.
2. Add `<name>` to `skills.keep`.
3. Deploy from the TUI or with `make skills-deploy`, then run `make skills-diff` to confirm every skill reports `OK`.

To keep a skill that already exists live (for example one an agent created), run `make skills-keep NAME=<name>`.

### From another repo (third-party)

```bash
npx skills add <owner>/<repo> -s <skill> -a claude-code -g -y --copy
make skills-thirdparty-save     # copy the live lock into third-party-skills.lock.json
```

Then commit the updated lock. Rules:

- **Use `-a claude-code` only.** Hermes already reads that directory, so adding `-a hermes-agent` makes names
  ambiguous. Never use `-a '*'`.
- **Use npx, not a Claude plugin, for plain skills.** One install channel per pack per agent; a plugin and npx copy
  of the same pack would show every skill twice. Plugins reach Claude only and are not tracked in this repo, while
  npx reaches both agents and is restored from the lock on a new machine.
- **Keep names unique.** A third-party name must not match an authored, repo-local or built-in skill. npx cannot
  rename a skill on install.
- **Install only what you use.** Every installed skill adds its description to every session.
- **Updates are manual.** Replays fetch the latest upstream version, not a pinned one. `make skills-thirdparty`
  reports `CHANGED` when upstream differs from the committed lock.

### For this repo only (repo-local)

Create `.claude/skills/<name>/SKILL.md`, run `make skills-link`, then `make skills-check`. Procedures that only
matter inside this repo belong here as skills, not under `docs/`: a skill loads itself at task time and a doc does
not.

## Reference

### `make` targets

| Command                                  | Purpose                                                                                                                     |
|------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `make skills-diff`                       | Compare each authored skill with its live copy (`OK` / `DIFFERS` / `MISSING`); read-only                                    |
| `make skills-drift`                      | Like `skills-diff` but only `DIFFERS` fails; this is the deploy gate                                                        |
| `make skills-deploy`                     | Copy the authored skills to `~/.claude/skills` without chezmoi; refuses if a live copy differs (`SKILLS_FORCE=1` overrides) |
| `make skills-status`                     | Flag names present in both `~/.claude/skills` and `~/.hermes/skills`, and repo skills missing from `skills.keep`            |
| `make skills-keep NAME=<name>`           | Save a live skill into the repo and add it to `skills.keep`                                                                 |
| `make skills-thirdparty`                 | Report drift between the committed lock and the live `npx skills` lock; read-only                                           |
| `make skills-thirdparty-save`            | Copy the live `npx skills` lock into the repo as `third-party-skills.lock.json`                                             |
| `make skills-thirdparty-replay`          | Reinstall every third-party skill listed in the committed lock (`AGENT=codex` for another agent)                            |
| `make skills-link` / `make skills-check` | Create / verify the `.agents/skills` symlinks for repo-local skills                                                         |

### What `skills-thirdparty-replay` does

The committed lock records which skills were installed and from which repo. The replay runs
`npx skills add <source> -s <skill> -a <agent> -g -y --copy` once per entry, so every listed skill is
(re)installed from its upstream repo, as a real directory under `~/.claude/skills`. It needs Node (`npx`) and
`jq`, fetches the **latest** upstream version rather than a pinned one, and ends with `make skills-thirdparty` to
show any drift against the lock. Press Ctrl-C only after it finishes: it installs the entries one at a time.

A plain `chezmoi apply` runs the same script but skips it when the lock hasn't changed since the last fully
successful run. The make target always replays.

### Where the `npx skills` lock lives

The CLI keeps its own live lock outside the repo: `$XDG_STATE_HOME/skills/.skill-lock.json` on current versions
(`~/.local/state/skills/` by default), `~/.agents/.skill-lock.json` on older ones. The Makefile checks both. The
repo never shares that file with chezmoi, so a sync can't overwrite the CLI's live lock with a stale one.

### Governance

The full rules (private skills, never vendoring third-party packs, bundled skills being read-only) are in
`AGENTS.md` under "Skills & plugins". Deeper material lives in the `agent-skills-architecture`, `skill-deployment`
and `skill-layout` skills.

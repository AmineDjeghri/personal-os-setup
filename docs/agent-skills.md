# Agent skills

Skills are small `SKILL.md` folders that coding agents (Claude Code, Hermes, ...) load on demand. Each skill's
short description is loaded into every session; the body is read only when the task matches. This page covers
what skills this repo provides, how they get onto a machine, and how to add or change them.

- [Skill catalog](#skill-catalog): every skill, grouped by layer
- [How skills are installed](#how-skills-are-installed): TUI and `make`
- [Adding skills](#adding-skills): your own, third-party, repo-local
- [Reference](#reference): `make` targets and internals

## The three layers

| Layer           | What it is                                           | Source of truth                                                                     | Lands in                                | Reaches                       |
|-----------------|------------------------------------------------------|-------------------------------------------------------------------------------------|-----------------------------------------|-------------------------------|
| **Authored**    | Skills you write and keep                            | `src/personal_os_setup/config/chezmoi/dot_claude/skills/` (listed in `skills.keep`) | `~/.claude/skills` + `~/.agents/skills` | Claude Code, Codex and Hermes |
| **Third-party** | Skills from other repos, installed with `npx skills` | `third-party-skills.lock.json` (repo root)                                          | `~/.claude/skills` + `~/.agents/skills` | Claude Code, Codex and Hermes |
| **Repo-local**  | Runbooks for working on this repo only               | `.claude/skills/` (+ `.agents/skills/` symlinks)                                    | read in place                           | whoever opens this repo       |

Authored skills deploy once into `~/.claude/skills`; per-skill links in `~/.agents/skills` expose
them to Codex. Hermes reads `~/.claude/skills` too, so no extra Hermes copy is needed. Never put the same skill name in
`~/.hermes/skills` as well: the name becomes ambiguous and Hermes refuses to load it (`make skills-status` flags it).

## Skill catalog

### Authored skills (17)

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
| `report-pdf`                  | Creating PDF reports with the shared report workflow                                                                                                |
| `youtube-download-automation` | Ingesting a YouTube link or playlist into the music library: what's new, genre sourcing, yt-dlp download. Plans first, then asks before downloading |

### Third-party skills (16)

Installed with `npx skills`, tracked in `third-party-skills.lock.json`.

| Skill                           | Source                       | Use it for                                                                       |
|---------------------------------|------------------------------|----------------------------------------------------------------------------------|
| `grill-me`                      | `mattpocock/skills`          | Being interviewed about a plan or design until every branch is resolved          |
| `grill-with-docs`               | `mattpocock/skills`          | The same interview, plus building a `GLOSSARY.md` and decision records as you go |
| `grilling`                      | `mattpocock/skills`          | The reusable interview primitive the two skills above call                       |
| `tdd`                           | `mattpocock/skills`          | Test-first development, one red-green-refactor slice at a time                   |
| `diagnosing-bugs`               | `mattpocock/skills`          | A gated loop for hard bugs and performance regressions                           |
| `handoff`                       | `mattpocock/skills`          | Compacting a conversation into a document another agent can continue from        |
| `differential-review`           | `trailofbits/skills`         | Security-focused review of a PR, commit or diff                                  |
| `find-skills`                   | `vercel-labs/skills`         | Discovering and installing skills                                                |
| `claude-code`                   | `NousResearch/hermes-agent`  | Delegating coding work to the Claude Code CLI                                    |
| `hermes-agent`                  | `NousResearch/hermes-agent`  | Using, configuring and extending Hermes Agent                                    |
| `hermes-agent-skill-authoring`  | `NousResearch/hermes-agent`  | Writing in-repo `SKILL.md` files                                                 |
| `home-assistant-best-practices` | `homeassistant-ai/skills`    | Home Assistant configuration practices                                           |
| `modern-python`                 | `trailofbits/skills`         | Modern Python project tooling                                                    |
| `bash-script-validator`         | `akin-ozer/cc-devops-skills` | Validating Bash scripts                                                          |
| `github-actions-validator`      | `akin-ozer/cc-devops-skills` | Validating GitHub Actions workflows                                              |
| `makefile-validator`            | `akin-ozer/cc-devops-skills` | Validating Makefiles                                                             |

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
| apply selected         | Copies authored skills, links them for Codex, and replays third-party skills for Claude Code and Codex                                                               |
| re-add selected        | Pulls a skill you edited live back into the repo's source tree                                                                                                       |
| chezmoi: clean backups | (action button above the list) Deletes the `<name>_<timestamp>_backup` copies that earlier applies left next to managed files, including those in `~/.claude/skills` |

Things to know:

- **Select the folder.** The authored link script (`run_after_zz-link-authored-skills.sh`) and replay script
  (`run_after_replay-third-party-skills.sh`) only run when their own entries are selected. Selecting a
  single file applies that file and skips both scripts. Linking uses Python 3; replay also needs Node
  (`npx`) and `jq`. Optional replay logs `SKIPPED` if tooling is missing and records no successful install.
- **It never deletes.** A skill removed from the repo stays in `~/.claude/skills` until you delete it by hand.
- **Each apply leaves backups.** Before overwriting, it copies every selected file to
  `<name>_<timestamp>_backup<ext>` in the same folder, and `make skills-status` then reports `DIFFERS`. Use
  **chezmoi: clean backups** to remove them.
- **It does not check for drift.** Apply overwrites a live skill that was edited and not yet pulled back with
  re-add. Run `make skills-status` first if an agent may have edited a live skill.
- **Re-add only handles files already tracked.** For a brand-new live-only skill, use `make skills-live-to-repo`.

### Setting up a new machine

Clone the repo, then apply `.claude` from the TUI. The third-party lock is replayed for you. Without the TUI:
`make skills-repo-to-live` (authored skills) and `make skills-thirdparty-repo-to-live` (third-party skills).

## Adding skills

### Your own (authored)

1. Create `src/personal_os_setup/config/chezmoi/dot_claude/skills/<name>/SKILL.md`.
2. Add `<name>` to `skills.keep`.
3. Deploy from the TUI or with `make skills-repo-to-live`, then run `make skills-status` to confirm every skill reports `OK`.

To keep a skill that already exists live (for example one an agent created), run `make skills-live-to-repo NAME=<name>`.

### From another repo (third-party)

```bash
npx skills add <owner>/<repo> -s <skill> -a claude-code -a codex -g -y --copy
make skills-thirdparty-live-to-repo     # copy the live lock into third-party-skills.lock.json
```

Then run `make skills-thirdparty-repo-to-live` to verify both agents and record local content receipts.
Commit the updated lock after review. Rules:

- **Use `-a claude-code -a codex`.** Hermes already reads the Claude directory, so adding
  `-a hermes-agent` makes names ambiguous. Never use `-a '*'`.
- **Use npx, not a Claude plugin, for plain skills.** One install channel per pack per agent; a plugin and npx copy
  of the same pack would show every skill twice. Plugins reach Claude only and are not tracked in this repo, while
  npx targets Claude Code and Codex, with Hermes reading the Claude copy. Replay restores these
  installations from the lock on a new machine.
- **Keep names unique.** A third-party name must not match an authored, repo-local or built-in skill. npx cannot
  rename a skill on install.
- **Install only what you use.** Every installed skill adds its description to every session.
- **Updates are manual.** Replays fetch the latest upstream version, not a pinned one. `make skills-status`
  reports `DRIFT` when the live lock differs from the committed lock.

### For this repo only (repo-local)

Create `.claude/skills/<name>/SKILL.md`, run `make skills-link`, then `make skills-check`. Procedures that only
matter inside this repo belong here as skills, not under `docs/`: a skill loads itself at task time and a doc does
not.

## Reference

### `make` targets

| Command                                  | Purpose                                                                                                                                                                                                                              |
|------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make skills-status`                     | One read-only report: repo vs live copy per skill (`OK` / `DIFFERS` / `MISSING`), Codex links, names present in both `~/.claude/skills` and `~/.hermes/skills`, repo skills missing from `skills.keep`, third-party lock and content |
| `make skills-repo-to-live`               | Copy authored skills repo → `~/.claude/skills` and link them into `~/.agents/skills`; refuses drift or link conflicts (`SKILLS_FORCE=1` overrides)                                                                                   |
| `make skills-live-to-repo NAME=<name>`   | Save a live skill into the repo and add it to `skills.keep`                                                                                                                                                                          |
| `make skills-thirdparty-live-to-repo`    | Copy the live `npx skills` lock into the repo as `third-party-skills.lock.json`                                                                                                                                                      |
| `make skills-thirdparty-repo-to-live`    | Reinstall and verify for Claude Code and Codex (`AGENT=codex` selects only Codex)                                                                                                                                                    |
| `make skills-link` / `make skills-check` | Create / verify the `.agents/skills` symlinks for repo-local skills                                                                                                                                                                  |

### What `skills-thirdparty-repo-to-live` does

The replay installs each locked skill for `claude-code` and `codex` using `npx skills add … --copy`.
Use `AGENT=codex` or `AGENTS="claude-code codex"` to select the agents explicitly. Hermes is never a
separate target. Python 3, Node (`npx`) and `jq` are required; explicit Make replay fails when a tool
is missing. A packaged chezmoi source without the repository lock still links authored skills,
and optional third-party replay reports `SKIPPED`; set `LOCK` to a reviewed lock to enable replay.
Windows Git Bash follows the same path and reports failures instead of silently succeeding.

Verification checks both the live lock identities and each agent's actual `SKILL.md` and supporting files.
A successful replay writes SHA-256 content receipts into
`$XDG_STATE_HOME/personal-os-setup/skills-installed.json` (`~/.local/state` by default). These local
receipts are separate from the upstream Git tree IDs in the npx lock. Missing receipts, missing files,
local edits, broken links and lock drift fail verification. Existing installations need one explicit
replay to establish receipts; the checker never creates a baseline from unverified existing files.

A plain chezmoi apply checks the lock, selected agents and installed content before skipping an
unchanged replay. A deleted or edited skill is replayed. A stamp is written only after installation
and verification succeed. Optional replay reports `SKIPPED` when tooling is unavailable; this is not
installation success. The Make target always replays and treats missing tooling as an error.

Replay fetches current upstream versions. If an upstream folder ID changed, verification fails:
review the update, run `make skills-thirdparty-live-to-repo`, then replay again to establish matching receipts.
The committed lock remains an inventory and drift reference, not an immutable source pin.

### Where the `npx skills` lock lives

The CLI keeps its own live lock outside the repo: `$XDG_STATE_HOME/skills/.skill-lock.json` on current versions
(`~/.local/state/skills/` by default), `~/.agents/.skill-lock.json` on older ones. The Makefile checks both. The
repo never shares that file with chezmoi, so a sync can't overwrite the CLI's live lock with a stale one.

### Deployment regression tests

`make test` includes `tests/skills/`: isolated Make and chezmoi applies with a fixture `npx`,
plus the unit checks for links, manifests, conflicts and content receipts. These never install
real skills or packages. The chezmoi case skips if chezmoi is unavailable.

### Governance

The full rules (private skills, never vendoring third-party packs, bundled skills being read-only) are in
`AGENTS.md` under "Skills & plugins". Deeper material lives in the `agent-skills-architecture`, `skill-deployment`
and `skill-layout` skills.

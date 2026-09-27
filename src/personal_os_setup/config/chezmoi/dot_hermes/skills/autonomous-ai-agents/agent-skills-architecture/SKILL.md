---
name: agent-skills-architecture
description: Use when organizing, deploying, or installing agent skills.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [skills, plugins, architecture, deployment, chezmoi, claude-code, vendor, mcp, external-dirs]
    related_skills: [hermes-instance-audit, skill-deployment, claude-code]
---

# Agent skills & plugins — architecture, deployment, installation

How this user's agent skills and plugins are organized across Hermes and Claude Code, and how to deploy,
vendor or install them. Canonical governance text: personal-os-setup `AGENTS.md` § "Skills & plugins —
2-track governance". Verifying what a configured dir actually LOADS → `hermes-instance-audit`.

## When to use
- Deploying, vendoring, promoting or installing a skill; "where does this skill belong?"
- Installing a Claude Code plugin, or a vendor bundle that ships skills (and MCP) for one or both agents
- "Why doesn't the agent see skill X" — the wiring side (diagnose with `hermes-instance-audit`)
- Repo-local runbooks, AGENTS.md vs CLAUDE.md layout questions
- Not for: auditing an install, merging duplicate skills, or a repo's own `skills-link`/`skills-check` flow (the repo's `skill-layout` skill).

## The zones
| Zone | Path | Read by |
|---|---|---|
| Hermes own store | `/config/.hermes/skills/` | Hermes only |
| Hermes-only — SOURCE (repo = truth) | `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_hermes/skills/<category>/<skill>/` | Hermes only, via `make skills-deploy` |
| Shared general — SOURCE (repo = truth) | `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/` | both agents, via deployment |
| Shared general — DEPLOYED | `/config/.claude/skills/` (chezmoi target; HOME=/config) | Claude Code (global) + Hermes `external_dirs` |
| Repo-specific | `<repo>/.claude/skills/` + `.agents/skills/` git symlinks | Claude Code in that repo; Hermes only from a session rooted there or via `external_dirs` |
| Track 2 (not skill files) | `~/.claude/plugins/`, `$HERMES_HOME/mcp-tokens/` | Claude plugins; Hermes MCP servers |

- One Hermes brain runs in two HA addon containers (agent + webui) over ONE persistent home, mounted
  `/config` in both (the webui symlinks it at start). Always write `/config/...`; `/addon_configs/<repo>_<slug>`
  is the host spelling and does not exist inside the agent container.
- NEVER copy bundled Hermes skills into the shared dir: they are tool-coupled (`ha_*`/Hermes tools), auto-updated,
  and duplicate names collide. Extract the user's customizations into shared skills instead.
- Shared-dir skills must stay agent-agnostic: terminal/git/gh + stdlib, no Hermes tool references, no single
  repo's workflow, no personal identifiers (names, emails, numeric IDs, home paths). Public
  `github.com/<owner>/<repo>` reference URLs are the deliberate exception and stay as full links.

## 2-track governance (decision Sep 2026)
- **Track 1 — Curated (repo = truth):** skills the user authors, customizes or pins. Canonical copy in the
  chezmoi source `dot_claude/skills/<name>/` → deployed to `/config/.claude/skills/<name>/`; Hermes loads it
  via `skills.external_dirs`, Claude Code via its global skills dir — one copy, both agents. Changes go
  through PRs. The authoritative "Currently:" enumeration is the one in that AGENTS.md section — read it there
  rather than trusting a copy here (any list duplicated in this skill goes stale the moment a Track-1 name gets
  re-homed). Durable fact: `skill-creator` is vendored from `anthropics/skills` (Apache-2.0 — keep its
  `LICENSE.txt`).
- **Track 2 — Managed (tool = truth):** fast-moving third-party suites via Claude Code's native plugin
  marketplace → `~/.claude/plugins/`, self-updating (`/plugin update`). NOT committed to the repo; re-register
  per machine. Hermes never loads plugins. Currently: `superpowers` (obra/superpowers; registers under
  marketplace `superpowers-dev`) and `cloudflare/skills` (Cloudflare skills + MCP).
- **Decision rule:** want to control / customize / pin a version → Track 1; want upstream's latest
  automatically → Track 2. Never hand-copy a Track-2 suite into Track 1 — it fights its own updater.

## Track 1 — vendor a skill into the shared dir (procedure)
1. Branch off `main` in personal-os-setup (`feature/*`), PR → `main`; a `docs(...)` commit triggers no release.
2. Fetch small: `git clone --depth 1 --filter=blob:none --sparse <owner/repo> /tmp/src && git -C /tmp/src sparse-checkout set <path>`.
3. Copy the whole skill folder — including its `LICENSE` — into the chezmoi source dir above.
4. Deploy live in the same step: copy the folder to `/config/.claude/skills/<name>/` so both agents pick it up
   immediately; keep live == repo.
5. Update the AGENTS.md § 2-track "Currently:" Track-1 list (skills are enumerated there). That file is
   agent-protected: the edit approval often times out unattended → the write comes back BLOCKED. Stop and have
   the user say "prompt me again" to re-fire the exact patch; never retry it via another path.
6. Pre-commit rejects vendored content in up to three rounds — fix all before committing: ruff-format rewrites
   the foreign Python (fail-by-design → re-add + recommit); ruff lint then flags D415 (vendored docstrings lack
   a terminal `.`; no auto-fix); detect-secrets flags SRI/base64 attributes such as `integrity="sha384-…"` on
   vendored HTML → inline `<!-- pragma: allowlist secret -->` on the flagged line (never whole-file excludes).
   A hook-aborted commit leaves HEAD unchanged with changes still staged — confirm with `git log --oneline -1` +
   `git status`, never trust the truncated hook tail.

## Track 2 — install a Claude Code plugin (procedure)
Claude reads `.claude.json`, credentials and plugins from `$HOME` — always run it with the persistent home as
HOME and by absolute path (the gateway PATH omits `~/.local/bin`):

```bash
export P=/addon_configs/<repo>_<slug>          # the addon's persistent home (== /config)
HOME=$P $P/.local/bin/claude plugin marketplace add <owner>/<repo>
HOME=$P $P/.local/bin/claude plugin marketplace list   # registered name may differ from the repo name
HOME=$P $P/.local/bin/claude plugin install <name>@<marketplace> -y
HOME=$P $P/.local/bin/claude plugin list
```

- Installs land in `~/.claude/plugins/` and do NOT touch `~/.claude/skills` — the Hermes `external_dirs` index
  stays clean (verified with superpowers: no symlinks leaked into skills).
- **Never point Hermes at a Claude plugin's cached subtree**
  (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills`) — the version segment changes on every
  plugin update and old versions are swept.
- Invoke claude WITHOUT `--bare` when plugins must load — bare mode skips plugins and skills.
- Never commit Track-2 state (marketplace registrations, `~/.claude/plugins/`, `known_marketplaces.json`) —
  machine-local, re-registered per machine.

## Track 2 — a vendor bundle that ships BOTH skills and MCP servers
Some vendors publish one bundle for several agents (e.g. `cloudflare/skills` is simultaneously a Claude plugin
marketplace and a plain `skills/<name>/SKILL.md` tree). Give each agent its NATIVE mechanism — two sources of
the same skill name confuse the model:
- **Claude Code** → the plugin (`plugin marketplace add` + `plugin install`). The vendor's plugin manifest can
  carry its MCP server too (`.claude-plugin/plugin.json` → `mcpServers`), so nothing else is needed that side.
- **Hermes** → the skills CLI (`vercel-labs/skills`, npm package `skills`):
  `npx -y skills add <owner>/<repo> --skill '*' --yes --global --agent hermes-agent`. It keeps ONE canonical
  copy in `~/.agents/skills` and symlinks per selected agent, so pass ONLY `--agent hermes-agent` when Claude is
  served by the plugin, or you get duplicate skills. Destination is chosen by agent + scope alone — no `--dir` flag.
- **Hermes MCP servers** → `hermes mcp add <name> --url <url> --auth oauth`, the `trust: untrusted` write gate,
  and scoped tokens over account-wide OAuth.

## Deploying the shared dir (chezmoi / container)

Deploy mechanics — the chezmoi `--source` = repo-root and run-from-HOME rules, `make skills-deploy` and its
`SKILLS_FORCE=1` escape hatch, and the Deploying-from-a-container variant — live in the `skill-deployment` skill;
don't restate them here. The container-specific debugging trail (a nested `.chezmoiroot` breaking the TUI's
`--source`, the file-level `--source-path` fallback) is in `references/chezmoi-dot-claude-deployment.md`.

## Reconciling the two trees (do this BEFORE any cleanup)
`make skills-status` is the authoritative duplicate list (live own-store copies that duplicate a git-managed name);
`make skills-diff` reports per skill `OK` / `DIFFERS` / `MISSING`; `make skills-drift` is the deploy's gate.

- **`MISSING` means "the deploy has not landed", never "redundant".** The own-store copy of a shared name can be the
  only copy the index has — the CLI dedupes by name, so deleting it first makes the skill vanish from the index.
  Order: deploy → confirm `skills-diff` prints no `MISSING`/`DIFFERS` → only then delete the own-store duplicate.
- `make skills-deploy` ABORTS on any `DIFFERS` (by design: it never silently reverts an in-place edit).
  `SKILLS_FORCE=1 make skills-deploy` is the escape hatch and is safe ONLY once the newer live content has been ported
  into the source tree — otherwise it overwrites that content for good.
- **`DIFFERS` never says which side is newer — check per FILE** with `stat -c '%s %y'` on both copies (the drifted set
  is usually mixed). Live strictly newer → port live→source (sanitized). Source strictly newer → port nothing, the
  deploy is the fix. A blanket "reconcile live→git" DELETES the newer source content; a blanket deploy reverts the
  newer live content.
- Re-run `skills-diff` after the deploy — a clean report is the proof, not the deploy's own output.

## Repo-local skills + AGENTS.md ↔ CLAUDE.md
- Canonical file `<repo>/.claude/skills/<name>/SKILL.md`; `make skills-link` creates/refreshes the git-tracked
  `.agents/skills/<name>` symlink; `make skills-check` must print `OK <name>` for every skill in `.claude/skills`.
- **A destination repo with NO skill tooling yet** gets the layout created by hand: `.claude/skills/<name>/` as the
  canonical copy plus a RELATIVE `.agents/skills/<name>` → `../../.claude/skills/<name>` symlink, file modes
  normalized (a copy out of the own store arrives `700`, git wants `644`), and a `## Skills` section in that repo's
  `AGENTS.md` naming the skills plus the placement rule. Without that AGENTS.md line the next session invents a
  second layout. Repos that already ship the tooling get the same result through `make skills-link` /
  `make skills-check` instead of by hand.
- Keep repo-bound runbooks OUT of `docs/`: `properdocs.yml` uses `docs_dir: .` and excludes only what its glob
  lists, so a new `docs/<topic>/` page is PUBLISHED on the public site — skills sit outside `docs/` and stay private.
- AGENTS.md = canonical rules for ALL agents and is sent with EVERY prompt → keep <150 lines, index-shaped
  (orientation table + pointers), silent invariants and gotchas only. CLAUDE.md starts with `@AGENTS.md` +
  Claude-only depth; never duplicate rules across the two (divergence is the #1 documented failure mode) and
  avoid header names that collide.
- Pick the tier before writing: repo-bound procedure → that repo's `.claude/skills/`; cross-machine curated →
  the chezmoi `dot_claude/skills` source + `make skills-deploy`; fast-moving upstream → Track 2, never
  hand-copied into Track 1.

## What actually loads (summary — probes and internals in the audit skill)
Resolution order: own store → `external_dirs` → project skills. Project skills need BOTH a candidate dir at the
repo root AND that root in `skills.trusted_project_dirs` (exact resolved path — no globs, no parent rules) — and
the session must resolve that root at all: with a global `terminal.cwd` (HOME, no `.git` above it) NO root
resolves, so trust stays silently inert for chat sessions (upstream defect, fix in review). Consequence: for a
repo runbook both agents must see from a `/config`-rooted session, list its `.agents/skills` in `external_dirs`
(one index line per skill) or promote it to Track 1. `config.yaml` is not writable through the file tools (the
refusal is explicit: "Refusing to write to Hermes config file … use 'hermes config' instead") — register the dir
with the CLI, which does take a JSON list:
`hermes config set skills.external_dirs '["/config/.claude/skills","<repo>/.agents/skills"]'`, read it back with
`hermes config get skills.external_dirs`, same for `skills.trusted_project_dirs`; any of it takes effect only in the
NEXT session. Hand the user the fenced block instead when the change is HIS to make (a path he has not approved). Full chain, decisive probes,
upstream issue/PR handles: `hermes-instance-audit` → `references/skill-loading-resolution.md`.

## Hermes own store — three writers, and keeping a skill Hermes-only

`~/.hermes/skills/<category>/<skill>/SKILL.md` (= `/config/.hermes/skills/…`; per-profile under
`~/.hermes/profiles/<name>/`) is fed by three owners mixed into ONE flat `category/skill` namespace, with nothing on
the file saying who owns it. Establish provenance before touching anything:

- **Addon bundled sync** — names listed in `.bundled_manifest`; re-synced and updated by the add-on. Never build work
  on top of one of these (an edited copy is skipped by the sync forever — see the section below).
- **Hub / dashboard installs** — land in the SAME store (there is no separate install dir; `skills:` in `config.yaml`
  defines no install path), with the hub's bookkeeping in `.hub/` (taps, lock, audit, quarantine, catalog cache).
  Often identifiable from the frontmatter (`author: community`). Tool-managed → never vendor them into git.
- **Agent-authored** (`author: Hermes Agent`) — nothing manages them: no git, no history, no backup, no update path.
  These are the only ones worth versioning.

**Hermes-only is a placement property, not a naming one.** `dot_claude/skills` → `/config/.claude/skills` is read by
BOTH agents, so renaming a skill or rewording its description does NOT hide it from Claude Code — it stays in
Claude's skill index and can still be loaded. A skill only Hermes should see has to live in the own store: version it
as `chezmoi/dot_hermes/skills/<category>/<skill>/` and have `make skills-deploy` copy it into `~/.hermes/skills/…`
beside the shared deploy. Keep the curated set disjoint from bundled/hub names — one namespace, so a collision
silently overwrites — and keep the promoted names distinct enough to be recognisable as curated.

**The Curator edits this store in place** (`curator:` in `config.yaml` — interval, `stale_after_days`,
`archive_after_days`, `prune_builtins`, backups in `.curator_backups/`). Anything you deploy into the store from git
is therefore in a two-writer situation: the Curator — and the autonomous background-review pass — rewrites or
archives it, and the next `make skills-deploy` overwrites it. **The deploy is one-way and copy-only**: it replaces
files and DELETES NOTHING, so an in-place edit to a live skill is silently reverted by the next deploy (copy it back
into the source tree first) and a skill dropped in the repo keeps living in the store (rm the deployed dir by hand).
Re-homing a skill between the two trees needs BOTH sides: deploy the new location AND delete the old live directory,
or one name ends up indexed from two sources with no way to tell which copy the agent reads.
The protection mechanism is the curator CLI, per machine, after the deploy:

```bash
hermes curator status                  # what it manages + activity per skill
hermes curator pin <skill>             # hands off: never rewritten, pruned or archived (unpin to release)
hermes curator usage                   # activity telemetry for ALL skills, with provenance
hermes curator {run,pause,resume,list-unmanaged,adopt,restore,ledger,backup,rollback}
```
- Bundled and hub-installed skills are **never touched** by the Curator — it only reviews agent-created ones, which is
exactly the promoted set, so pin every promoted name.
- A pin blocks CONTENT edits, not just lifecycle transitions: the Curator skips pinned names, and the autonomous
  background-review pass treats them as protected ("only the user, in a foreground session, can change a pinned
  skill"). Unpinned, a promoted skill gets rewritten in place and the next deploy silently wins the round.
- Promoted names need no defence against `hermes update`: the bundled sync only touches names in `.bundled_manifest`,
  and when a bundled name collides with an existing local skill it keeps YOUR copy and warns — swapping in the
  bundled version takes a deliberate `hermes skills reset <name>`.
- `hermes skills opt-out` is a DIFFERENT switch: it writes the `.no-bundled-skills` marker so the installer and
`hermes update` stop seeding bundled skills (optionally `--remove` unmodified ones). It is not a Curator pin.
- Say plainly which writer owns which file: git owns the promoted names, the hub owns its installs, the addon image
owns bundled ones.

### A skill's category is its path, not its frontmatter

`tools/skills_tool.py::_get_category_from_path` derives category from the first path component:
`<root>/<category>/<skill>/SKILL.md` → that category; a flat `<root>/<skill>/SKILL.md` → blank
category. Re-filing a skill between categories in the own store is a plain `mv`; for a git-managed
skill the repo path IS the category, so it's `git mv` in the source tree followed by a redeploy
(moving only the live copy comes back as `MISSING`/`DIFFERS` on the next diff). Category also forms
part of the address used in some config references (`category/skill`), so a rename can invalidate a
config entry pointing at the old address — check for that before renaming a promoted skill.

### Two skills on one topic are not automatically a duplicate to merge

Diff them before pitching a merge. The common legitimate case: one copy carries the runbook
(trigger → steps → verification) and the other carries library/API depth the runbook itself points
at (internals, a script, its own `references/`) — that's a deliberate split, not a duplication, and
proposing to merge it without having diffed first reads as not having done the homework. When it
really is the same content in two homes, pick the survivor by which one is actually MANAGED (git/
chezmoi-deployed and drift-checked beats a hand-symlinked or docs-hosted copy that a fresh machine
won't have), fold any delta the loser has that the survivor lacks, then delete the loser and verify
with a fresh `skills-diff`/`skills-check` pass.

### Deciding delete vs port (an inventory pass)
Classify from bookkeeping, never from the category directory a skill sits in: `hermes skills list` prints the Source
(`local` = own store, `builtin` = shipped in the addon tree) plus a Status column; `.usage.json` carries
`created_by` / `use_count` / `state` / `pinned`; the addon's read-only `skills/` tree is ground truth for "shipped";
`.curator_backups/` holds pre-run snapshots for rollback.

- Agent-authored + box-specific → the only promotable kind; port it into git (next section) if it must survive a
  reinstall.
- Shipped / hub-installed → NEVER vendor into a Track-1 tree; keep while used, otherwise delete the own-store copy
  (a deleted bundled skill is not re-seeded; `hermes skills reset <name> --restore` brings stock back).
- Live-only with 0 uses, superseded by a newer skill, or `state: stale` → delete.
- A skill dir that is a symlink into a repo → keep the symlink, never add a second copy.
- A DISABLED skill leaves the index AND is unreadable/unpatchable through the skill tools (`skill_view` refuses) —
  re-enable it before trying to edit it.
- Deleting files inside a skill dir leaves dangling `references/`/`scripts/` pointers in its SKILL.md: grep the live
  skills for the removed filenames afterwards (the deploy clears them when the source version does not reference them).
- Inventory pitfalls: `find -name SKILL.md` does not descend into symlinked skill dirs (use `ls -la`, `find -L`);
  `hermes skills list` truncates long names with `…`, so never diff name lists off that table; `.curator_ledger.jsonl`
  records curator/agent mutations only — a user-side deletion or disable leaves no entry, so an unexplained drop in the
  count means ask the user before suspecting the tooling.

### Promoting agent-authored skills into git (publishing gate)
The git home for promoted skills is a repo that may be **public**, so publishing is a review step, not a copy step:

1. **Prioritise with telemetry, not intuition:** `hermes curator usage` prints use/view/patches counts and last
   activity per skill. Skip promoting skills at 0 activity, and read the Curator's `patches` count as the quantified
   two-writer risk on the ones it actively rewrites.
2. **Check the destination's visibility:** `gh repo view <owner>/<repo> --json visibility` — a public repo publishes
   every promoted file the moment it is pushed.
3. **Scan each skill for personal identifiers before copying** (the shared-dir rule already forbids them, but only a
   scan catches what hides inside `references/` and worked examples): real name, personal email, the numeric GitHub
   noreply ID (`<id>+<username>@users.noreply.github.com`), LAN/global IPs, MACs, SSIDs, host paths, add-on slugs,
   tunnel hostnames, live exposure findings. If a skill fails, sanitize its examples to placeholders first or leave it
   in the own store — never publish it as-is to make the promotion set look complete. Sanitize the REPO copy and leave
   the live store copy untouched (it is private and keeps the real values); placeholder mapping, the pre/post scans and
   the diff-based proof: `references/sanitizing-skills-for-public-repos.md`. Real values in the own store are only
   temporary: the next `make skills-deploy` replaces that copy with the sanitized one, so drive the canonical text
   from the source tree rather than from what the live copy shows.
4. **Watch for skill dirs that are symlinks** into a repo path — that content already lives (and may already be
   published) elsewhere; resolve the single source of truth instead of creating a second copy. Keep the symlink and
   drop the duplicate from the deploy source: `make skills-deploy` copies with `cp -R`, which FOLLOWS a symlinked
   destination directory and writes through it into the tracked source file.
5. Report per skill what was copied and what was refused with the reason — the refusals are the interesting part.

## Hermes bundled-skill sync (protect your own edits)
Bundled skills sync from the repo with a per-directory hash manifest: a user-edited copy is skipped forever,
deletions are respected, and `hermes skills list-modified` / `hermes skills reset <name>` manage it. Don't park
your own work inside a bundled skill dir if you want upstream updates — audit with `hermes-instance-audit`.

## Pitfalls
- Approval gates: `AGENTS.md`/`CLAUDE.md` and `config.yaml` writes come back BLOCKED on timeout → STOP, report,
  and let the user say "prompt me again" to re-fire the exact patch; never retry it and never route the same edit
  through terminal or another file. `git commit`/`git push` need per-action approval every time (a plan, a task
  description or a previous yes is NOT permission); commit email must match existing commits, never invented.
- Destructive cleanup (`rm -rf`, `git clean -f`, a `tar` into a protected path) raises its OWN approval prompt, and a
  timed-out prompt is not consent either → stop, report, re-fire only when the user says so. Keep the backup and the
  delete in ONE command with the backup first, so a timeout at the prompt leaves nothing half-applied, and state the
  exact file/dir list before each step — this user approves deletions per step, not per plan.
- The webui container has NO Node.js by design — `npx skills` and node CLIs do not exist there (the AGENT
  container does). Vendor via git clone (Track 1) or `claude plugin` (Track 2); do not install Node for this.
- Python/npx-style third-party skill managers were evaluated and REJECTED (Sep 2026): `agent-skill-manager`
  (PyPI, 2 stars, beta) and `xingkongliang/skills-manager` (Tauri app with its own library + SQLite + git sync).
  Both add a second source of truth parallel to the repo → `.claude/skills` flow — the user rejects that duplication.
- Community sources worth knowing: the skills.sh marketplace leaderboard; `anthropics/skills` (official — source
  of `skill-creator`); `obra/superpowers` (methodology suite — Hermes already bundles the equivalents, so its
  value is Claude-side).
- personal-os-setup: branch/PR from `main` (the `dev` branch is retired).

## References
- `references/chezmoi-dot-claude-deployment.md` — the working container invocation, why dir-level and target-path
  applies fail, the file-level fallback, and the desktop-config trap.
- `references/community-skills-npx.md` — the Vercel `skills` CLI (find/add/check/update), its symlink pitfalls,
  the vendor-into-Track-1 flow, and the community sources considered.
- `references/sanitizing-skills-for-public-repos.md` — the placeholder mapping, the identifier scan, and the rules
  that keep a sanitized skill reviewable when it is promoted into the public shared dir.

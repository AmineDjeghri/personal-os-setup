---
name: agent-skills-architecture
description: Use when organizing, deploying or installing agent skills — or auditing, porting and retiring one.
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [skills, plugins, architecture, deployment, chezmoi, claude-code, vendor, mcp, external-dirs]
    related_skills: [hermes-instance-audit, skill-deployment, skill-layout]
---

# Agent skills & plugins — architecture, deployment, installation, audit, port, retire

How this user's agent skills and plugins are organized across Hermes and Claude Code: how to deploy,
vendor or install them, and how to audit, port live-only skills into git, or retire them. Canonical
governance text: personal-os-setup `AGENTS.md` § "Skills & plugins — 2-track governance". Verifying
what a configured dir actually LOADS → `hermes-instance-audit`.

## When to use
- Deploying, vendoring, promoting or installing a skill; "where does this skill belong?"
- Installing a Claude Code plugin, or a vendor bundle that ships skills (and MCP) for one or both agents
- "Why doesn't the agent see skill X" — the wiring side (diagnose with `hermes-instance-audit`)
- "Too many skills — which can I delete?" · "list my skills with their origin" · "find me skills I'm missing"
- Porting a live-only skill into git, or reviewing a rewrite the user pushed
- Repo-local runbooks, AGENTS.md vs CLAUDE.md layout questions
- Not for: auditing an install's config/plugins/curator behaviour, or a repo's own `skills-link`/`skills-check`
  flow (`hermes-instance-audit`, `skill-layout`).

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

## Provenance metadata — who owns a skill

Every skill we own records its origin in its own frontmatter, so a reader can tell a repo skill from an
agent-authored one without reading the box:

```yaml
metadata:
  hermes:
    origin: repo:personal-os-setup   # agent | repo:<name> | vendored | hub
    exposure: private                # ONLY when the skill must never be published
```

- `agent` — created in the own store, no git backing (the only promotable kind).
- `repo:<name>` — the canonical copy lives in that repo and is deployed from it.
- `vendored` + `source: <owner>/<repo>` — a whole-folder third-party copy.
- `hub` — installed from the skills hub; tool-managed, never vendored into git.
- `exposure: private` — never promote or publish as-is; absent = publishable (the default).
- Bundled (addon-shipped) skills carry **no** marker: editing one freezes its sync forever, and
  `.bundled_manifest` already records them.

The loader passes unknown frontmatter keys through verbatim, and the marker travels with the file — a
deploy or a copy never adds or strips it. The inventories below still classify from BOOKKEEPING
(`created_by`, `.bundled_manifest`); the marker makes the same answer visible in the file itself.

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
- **Deleting a deployed name locally is a no-op** — the next `make skills-deploy` restores it. Tracks 1/2 are
  deleted by repo PR; say that instead of deleting.
- `make skills-deploy` ABORTS on any `DIFFERS` (by design: it never silently reverts an in-place edit).
  `SKILLS_FORCE=1 make skills-deploy` is the escape hatch and is safe ONLY once the newer live content has been ported
  into the source tree — otherwise it overwrites that content for good.
- **`DIFFERS` never says which side is newer — check per FILE** with `stat -c '%s %y'` on both copies (the drifted set
  is usually mixed). Live strictly newer → port live→source (sanitized). Source strictly newer → port nothing, the
  deploy is the fix. A blanket "reconcile live→git" DELETES the newer source content; a blanket deploy reverts the
  newer live content.
- **When the gate ABORTS, attribute the drift and SHOW the delta before acting on it.** `hermes curator ledger` names
  the pass that patched the live copy and when — a curator/background-review patch minutes after your own deploy is
  the signature, and it means that live content is knowledge, not noise. Then render the delta per drifted skill with
  `scripts/review-drift.py <source-root> <live-root> <skill-dir>…` (writes `drift-<skill>.diff`, classifies the change,
  scrubs the added lines), hand the user the diff files plus what the added lines actually SAY, state which side is
  strictly newer, and recommend — do not force-deploy or port on their behalf. This user reads the delta before
  agreeing to keep it, and a forced deploy discards the passed lesson for good.
- **Classify additions vs a rewrite before copying either way.** Live-only lines with zero source-only lines = pure
  addition, so live→source is lossless. Source-only lines present = the live side rewrote something: read those lines
  before discarding either side — they are often a rule the live version CORRECTED, and restoring a superseded claim
  from the source is worse than the drift you set out to fix.
- **An autonomous rewrite is a PROPOSAL, not a fact — verify its claims against the implementation before publishing
  them into git.** Such a pass writes plausible, well-phrased assertions; run the decisive check (read the guard or
  function it names, or drive the code in a scratch script) and port only what holds, restating it with the scope the
  code actually has. A claim can be directionally right and still wrong in scope — a refusal list that omits
  `external_dirs` and an actor gate both send the next session to the wrong place. Report anything you could not
  verify as unverified instead of merging it on tone.
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

**Check order for "is this mine?"**: the addon's active tree `<install>/skills/<cat>/<name>/` → its optional tree
`optional-skills/` (shipped, NOT active — checking only the active tree yields a false "it's ours") →
`.bundled_manifest` → `created_by` in `.usage.json` (`agent` = ours, `null`/absent = shipped or hub-installed).
Counters come from `hermes curator usage`; where no CLI exists (the webui container ships none), read
`.usage.json` directly for `created_by`/`pinned`/`state` and say which path was used — never hand-reconstruct a
counter the CLI would print. A name in the optional tree exists on the box but is not in the index: state both
facts rather than guessing ownership.

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
into the source tree first) and a skill dropped in the repo keeps living in the store (rm the deployed dir by hand —
the audit is not finished while an orphan is still indexed).
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

Diff them before pitching a merge — this is the single most common audit finding, and often a deliberate split
(workflow vs internals) rather than duplication. The common legitimate case: one copy carries the runbook
(trigger → steps → verification) and the other carries library/API depth the runbook itself points
at (internals, a script, its own `references/`) — proposing to merge without having diffed first reads as not
having done the homework. When it really is the same content in two homes, pick the survivor by which one is
actually MANAGED (git/chezmoi-deployed and drift-checked beats a hand-symlinked or docs-hosted copy that a fresh
machine won't have), fold any delta the loser has that the survivor lacks, then delete the loser and verify with a
fresh `skills-diff`/`skills-check` pass.

**Verify the FOLD against the loser, never by re-reading the survivor.** A folded body reads fine even when rules
were dropped — the gaps are invisible from the inside, and a delegated merge loses whole sections silently. Before
deleting the loser, walk its body and its `references/` item by item:

- every section heading and pitfall bullet, grepped in the survivor by a distinctive phrase of each
  (`grep -c "<phrase>" <survivor>/SKILL.md`): a 0 means dropped, not reworded — restore it into the section it
  belongs to rather than appending a catch-all at the end;
- the `references/` mapping is 1:1 — each loser file is either copied in or merged into a surviving file on the same
  topic, and both the References list and every in-body pointer name the surviving filename (a stale pointer is a
  dead end for the next session);
- the frontmatter `description`/trigger now covers the loser's trigger words, or the merged half never loads for the
  tasks it was written for.

**File-level and content-level are different proofs, and you need both.** `skills-diff`/`skills-check` after a
merge show that the two trees agree — nothing about whether the merge lost anything; the phrase sweep above is the
only check for that. Never report a merge as lossless on the strength of a clean diff.

### Audit — "too many skills, which can I delete?" (an inventory pass)

- **Telemetry covers only what Hermes loaded.** `hermes curator usage` carries no counters for Track 1 or
  repo-scoped skills, so their demand reads `unverified` — never downgrade that absence into "0 uses" or a delete
  signal, and never quote a count the CLI did not print.
- **Real usage outranks size**: demand + no repo backing = *port* candidate, not a delete candidate.
- **Mid-move state**: while a live copy and a repo copy co-exist, `hermes skills list` shows one row per name and
  the total drops by one per collision — a falling count is NOT a missing skill.
- **Sweep the platform's own mutations before reporting** (seeding on update, origin-hash freezing, curator
  archiving, the unreviewed `pending/` backlog): one read-only pass over `hermes skills list-modified`, the
  manifest count, `.no-bundled-skills`, `pending/` counts and the relevant `hermes config get` keys — semantics in
  `references/platform-lifecycle-and-gates.md`.

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

### Origin inventory — "list my skills with their origin"

Answer in TIERS with the arithmetic reconciled (every indexed name lands in exactly one tier); a flat list is the
wrong shape and a single total for the whole box is always wrong, because the tiers overlap in name only.

One read-only pass over the sources: repo `dot_claude/skills` + `dot_hermes/skills/<cat>/`; the live shared dir
`/config/.claude/skills`; the own store `$HERMES_HOME/skills/**` (via `find -L`, so symlinked skills count); the
addon's shipped trees (`skills/` active, `optional-skills/` inactive); `.bundled_manifest`; `.usage.json`
(`created_by`, `pinned`); and every repo's `.claude/skills` + `.agents/skills`.

Tiers: **shared curated** (repo → deployed, both agents) · **repo-scoped** (that repo's sessions only) ·
**Hermes-only** (repo → own store) · **live-only agent-authored** (no repo backing — the deletable class) ·
**addon-shipped with a live copy**. Answer from the FILESYSTEM: `.usage.json` keeps rows for skills already deleted
from disk, so report those dead rows in one line and never let them inflate the count. A live name ABSENT from
`.bundled_manifest` is a copy that differs from the shipped one — state that as a fact, never as "broken". Columns
that worked: skill(s) | origin (repo → path) | tier/owner, grouped by tier, with the reconciliation stated once. Each
row's `metadata.hermes.origin` (above) must agree with the tier the bookkeeping puts it in — a disagreement means one
of the two moved without the other.

### Promoting agent-authored skills into git (publishing gate)
The git home for promoted skills is a repo that may be **public**, so publishing is a review step, not a copy step:

1. **Prioritise with telemetry, not intuition:** `hermes curator usage` prints use/view/patches counts and last
   activity per skill. Skip promoting skills at 0 activity, and read the Curator's `patches` count as the quantified
   two-writer risk on the ones it actively rewrites.
2. **Check the destination's visibility:** `gh repo view <owner>/<repo> --json visibility` — a public repo publishes
   every promoted file the moment it is pushed.
3. **Scrub and stage the copy OUTSIDE the repo first** — nothing is written to a repo before the scan comes back
   clean. Scan for personal identifiers (the shared-dir rule already forbids them, but only a scan catches what
   hides inside `references/` and worked examples): real name, personal email, the numeric GitHub noreply ID,
   LAN/global IPs, MACs, SSIDs, host paths, add-on slugs, tunnel hostnames, live exposure findings. Placeholder
   mapping, the pre/post scans and the diff-based proof: `references/sanitizing-skills-for-public-repos.md`.
4. **Place it in the tier matching its audience** — `dot_claude/skills/` (shared) or `dot_hermes/skills/<category>/`
   (Hermes-only); modes 644 for files, 755 for dirs. Repo-scoped placement is the symlink flow in "Repo-local
   skills" above.
5. **Verify by resolving the NAME, not the listing** — see the ambiguity-window pitfall below.
6. **Delete the live copy in the SAME pass** — that is what closes the ambiguity window.
7. **Content that fails the scrub stays live-only** and gets `hermes curator pin <name>` — never publish it as-is
   to make the promotion set look complete. Sanitize the REPO copy and leave the live store copy untouched (it is
   private and keeps the real values); real values there are only temporary since the next `make skills-deploy`
   replaces that copy with the sanitized one, so drive the canonical text from the source tree.
8. **Watch for skill dirs that are symlinks** into a repo path — that content already lives (and may already be
   published) elsewhere; resolve the single source of truth instead of creating a second copy. Keep the symlink and
   drop the duplicate from the deploy source: `make skills-deploy` copies with `cp -R`, which FOLLOWS a symlinked
   destination directory and writes through it into the tracked source file.
9. **Report per skill** what was copied, deleted and refused, with the reason — the refusals are the interesting part.

## Hermes bundled-skill sync (protect your own edits)
Bundled skills sync from the repo with a per-directory hash manifest: a user-edited copy is skipped forever,
deletions are respected, and `hermes skills list-modified` / `hermes skills reset <name>` manage it. Don't park
your own work inside a bundled skill dir if you want upstream updates — audit with `hermes-instance-audit`.

## Reviewing a rewrite the user pushed
Audit the DIFF, not the result: the old side is where the lost knowledge is, and a rewrite can only be called
lossless against its baseline. **The pushed work may not be on `main`** — this user pushes follow-ups onto the
open PR's branch, so review `git log --oneline HEAD..origin/<branch>` / `git diff --stat HEAD origin/<branch>`
from the existing worktree, not `origin/main`. Find the ref that carries it, sweep every surface for each removed
or renamed NAME, run the structural + live-vs-source inventory checks, privacy-scan only the touched files, and
report file:line + fix + severity with anything unconfirmed marked unverified. **Diff before committing a skill
file you edited earlier** — the user works in the same worktrees concurrently, so a file can gain changes between
your edit and your commit, and `git add <dir>` sweeps them in under your message; read `git diff --cached` and
disclose anything you did not author. Full sequence, checks and delegation rules: `references/reviewing-a-rewrite.md`.

## Community discovery — "find me skills I'm missing"
Never answer from the leaderboard: it is dominated by a handful of mega-suites and says nothing about THIS
library. Search by DOMAIN across either discovery path, vet each hit on installs + security audits, drop whatever
the library already covers (an equivalent bundled skill, a vendored Track-1 name, a Track-2 plugin), and return a
short ranked list plus an explicit "deliberately excluded" line. Installing is a separate, user-gated step, and a
hub install lands in the own store (Hermes-only, hub-owned) — vendor into Track 1 instead when it should serve
both agents or carry history. Both discovery mechanisms (`npx skills` git-vendor vs the Hermes hub), vetting
signals, the no-CLI query path, and exclusion patterns: `references/community-skills-npx.md`.

## Verification checklist
- [ ] exactly one path serves each ported name (`find -L <every root> -path "*<name>/SKILL.md"` == 1 hit)
- [ ] the target repo's hooks pass on the staged files, and the commit is only made after a green pass
- [ ] the scrub scan on the STAGED copy returns 0 identity/secret hits — report the count, an adjective is not evidence
- [ ] every skill's frontmatter `name` equals its directory name, and no surviving file names a dead skill (body, `related_skills`, `AGENTS.md` index row, help block)
- [ ] no live store name is left over from a source-tree deletion, and no report claims a count the CLI did not print
- [ ] a ported/deployed name resolves to the repo path, not the agent store, and private skills carry `pinned: true`
- [ ] a community recommendation names installs + audit verdict + the overlap check, and says plainly if nothing was installed

## Pitfalls
- Approval gates: `AGENTS.md`/`CLAUDE.md` and `config.yaml` writes come back BLOCKED on timeout → STOP, report,
  and let the user say "prompt me again" to re-fire the exact patch; never retry it and never route the same edit
  through terminal or another file. `git commit`/`git push` need per-action approval every time (a plan, a task
  description or a previous yes is NOT permission); commit email must match existing commits, never invented. Keep
  read-only bookkeeping to single-purpose shell one-liners — a compound call embedding an interpreter
  (`python3 -c …`) alongside other commands stalls at the gate and returns BLOCKED, while a one-liner or
  `read_file` on the JSON returns at once; name any blocked call in the report instead of quietly substituting.
- Destructive cleanup (`rm -rf`, `git clean -f`, a `tar` into a protected path) raises its OWN approval prompt, and a
  timed-out prompt is not consent either → stop, report, re-fire only when the user says so. Keep the backup and the
  delete in ONE command with the backup first, so a timeout at the prompt leaves nothing half-applied, and state the
  exact file/dir list before each step — this user approves deletions per step, not per plan.
- **Ambiguity window breaks loads.** While a live copy and the repo copy co-exist, name-based loading FAILS
  (`Ambiguous skill name '<n>': 2 skills match across your local skills dir and external_dirs`) and the listing
  hides it — verify with `find -L <every root> -path "*<name>/SKILL.md"` (exactly one hit; plain `find` misses a
  skill reached through a `.agents/skills` symlink).
- **Copied scripts and templates must pass the target repo's hooks before the commit** — a verbatim copy routinely
  fails lint/format/YAML hooks; running the gate and the recurring fixes: `references/repo-hook-gate.md`.
- **The staged copy is a snapshot.** An edit made to the live skill after staging is not in the port; re-copy if the
  live file moved on.
- **Check BOTH path bases before calling a supporting-file reference broken.** `references/…`/`scripts/…` written
  with a slash are skill-relative; a bare `scripts/<name>.py` in prose is usually the REPO root's own directory —
  test both `<skill-dir>/<rel>` and `<repo-root>/<rel>` before calling one broken.
- The webui container has NO Node.js by design — `npx skills` and node CLIs do not exist there (the AGENT
  container does). Vendor via git clone (Track 1) or `claude plugin` (Track 2); do not install Node for this.
- Python/npx-style third-party skill managers were evaluated and REJECTED (Sep 2026): `agent-skill-manager`
  (PyPI, 2 stars, beta) and `xingkongliang/skills-manager` (Tauri app with its own library + SQLite + git sync).
  Both add a second source of truth parallel to the repo → `.claude/skills` flow — the user rejects that duplication.
- **A skill that documents its own PII grep re-trips that gate forever.** Describe the check ("the owner's name,
  handle, numeric ID, a personal email domain") instead of embedding the literal tokens, so a later scan reports the
  real hit count instead of matching the instructions themselves.
- **The refusal list IS the drift set, and it is scoped to one ACTOR.** `_background_review_write_guard`
  (`tools/skill_manager_guards.py`) returns immediately unless the write origin is `background_review`
  (`tools/skill_provenance.py` — a ContextVar), so the autonomous pass is refused on: pinned names, bundled and
  protected built-ins, hub installs, anything under `skills.external_dirs` (EVERY Track-1 shared skill), and any
  name with no curator record (`created_by` absent or `None` — "not curator-managed … run `hermes curator adopt
  <name>`"). What it CAN write is therefore exactly the own-store `created_by: agent` unpinned names — the same set
  that drifts against the chezmoi source. Foreground actors (CLI, gateway, cron, subagent) are subject to none of
  it: a pinned skill can be edited there, and `_pinned_guard` blocks only its DELETION. Never describe "the
  curator" as one actor with one rulebook.
- **Test such a guard without touching a skill.** In a scratch script set
  `tools.skill_provenance.set_current_write_origin("background_review")`, call
  `skill_manager_guards._background_review_preflight(action, name)` for each name of interest, reset the token, then
  repeat in the default origin to prove the scope. It reads usage records and resolves paths and writes nothing —
  never test a write guard by attempting a real write to a live skill.
- Repo-*deployed* names that an autonomous pass promoted DO carry `created_by: agent` and its write goes through,
  so the lesson then differs from the chezmoi source: the next `make skills-deploy` either ABORTS on the fresh
  `DIFFERS` or a `SKILLS_FORCE=1` run overwrites the lesson you just saved. Either way the lesson is now repo work:
  the write path for a deployed skill is the source tree (an in-repo change on the open branch), never the live copy,
  and never a new overlapping curator skill. If every skill that needs the lesson is genuinely protected, the pass
  output is "Nothing to save" PLUS the exact edits the repo still needs — and name any drift you caused, with the
  file, so it gets ported instead of force-overwritten.
- **A file the source tree no longer has is not automatically stale live content to port back.** Compare size and
  mtime per FILE and ask whether the source-side edit was deliberate: a deleted install snapshot or context dump must
  be dropped (force-deploy), while a live-only reference the source never had is the one to port in.
- **`find` without `-L` cannot see a skill reached through a `.agents/skills` symlink** — an empty result reads as
  "the skill vanished"; pair it with `find -name SKILL.md` caveats above.
- personal-os-setup: branch/PR from `main` (the `dev` branch is retired).

## References
- `references/chezmoi-dot-claude-deployment.md` — the working container invocation, why dir-level and target-path
  applies fail, the file-level fallback, and the desktop-config trap.
- `references/community-skills-npx.md` — the Vercel `skills` CLI (find/add/check/update) AND the Hermes hub
  discovery path, their symlink/no-CLI pitfalls, the vendor-into-Track-1 flow, vetting signals and exclusion
  patterns, and the community sources considered.
- `references/sanitizing-skills-for-public-repos.md` — the scan-for list, the placeholder mapping, and the rules
  that keep a sanitized skill reviewable when it is promoted into the public shared dir.
- `references/repo-hook-gate.md` — running a target repo's hooks on copied skill files, and the lint/YAML fixes
  that recur.
- `references/platform-lifecycle-and-gates.md` — what Hermes itself does to the library between sessions (bundled
  seeding, origin-hash freezing, hub updates, curator archiving, `create_dir`, write-time lints), the memory
  semantics, and the gates/knobs that make all of it reviewable.
- `references/reviewing-a-rewrite.md` — the diff-first review of a pushed rewrite, its structural/inventory checks,
  and the rules for delegating it.
- `scripts/review-drift.py` — source-vs-live drift review for one skill or a whole tree: per-skill unified diffs,
  addition-vs-rewrite classification, and a scrub of the added lines before anything is ported or force-deployed.

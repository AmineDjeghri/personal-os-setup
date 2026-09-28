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

## Track 1 / Track 2 — the installation procedures (detail moved out)

- **Track 1 (vendor into the shared dir):** shallow sparse clone → copy the whole folder incl. its `LICENSE`
  into the chezmoi source → deploy live in the same step → update the AGENTS.md "Currently:" list (that write
  often comes back BLOCKED on an approval timeout; the user re-fires it) → the repo's pre-commit rejects
  vendored content in up to three rounds (ruff-format rewrites foreign Python; ruff D415; detect-secrets on
  vendored SRI attributes → inline pragma, never a whole-file exclude).
- **Track 2 (Claude plugin):** `HOME=<persistent home> <home>/.local/bin/claude plugin marketplace add
  <owner>/<repo>` → `plugin install <name>@<marketplace> -y`. Installs land in `~/.claude/plugins/` and never
  touch `~/.claude/skills`; never `--bare` when plugins must load; never point Hermes at a plugin's versioned
  cache subtree; never commit the marketplace state.
- **Track 2 (a bundle that is BOTH a plugin marketplace and a skill tree, e.g. `cloudflare/skills`):** give each
  agent its native mechanism — Claude the plugin, Hermes `npx -y skills add <owner>/<repo> --skill '*' --yes
  --global --agent hermes-agent` (pass ONLY `--agent hermes-agent` when the plugin serves Claude), MCP servers
  via `hermes mcp add`.
- Exact commands, the `sparse-checkout` incantation and the three-round hook fix:
  `references/install-and-track-procedures.md`.

## Deploying the shared dir (chezmoi / container)

Deploy mechanics — the chezmoi `--source` = repo-root and run-from-HOME rules, `make skills-deploy` and its
`SKILLS_FORCE=1` escape hatch, and the Deploying-from-a-container variant — live in the `skill-deployment` skill;
don't restate them here. The container-specific debugging trail (a nested `.chezmoiroot` breaking the TUI's
`--source`, the file-level `--source-path` fallback) is in `references/chezmoi-dot-claude-deployment.md`.

## Reconciling the two trees — the deploy gate

`make skills-status` lists live copies duplicating a git-managed name; `make skills-diff` prints `OK`/`DIFFERS`/
`MISSING`; `make skills-drift` is the deploy's gate (MISSING tolerated, DIFFERS aborts). **`MISSING` means "the
deploy has not landed", never "redundant".** `DIFFERS` never says which side is newer — check per FILE: live newer
→ port live→source; source newer → the deploy is the fix. `SKILLS_FORCE=1` is safe only after the newer live
content has been ported. Re-run `skills-diff` after the deploy; a clean report is the proof, not the deploy's own
output. Decision tree, per-file checks and the mixed-drift case: `references/deploy-drift-and-reconciliation.md`.

## Repo-local skills + AGENTS.md ↔ CLAUDE.md
- Canonical file `<repo>/.claude/skills/<name>/SKILL.md`; `make skills-link` refreshes the git-tracked
  `.agents/skills/<name>` symlink and `make skills-check` must print `OK <name>` for each one. A repo with no skill
  tooling yet gets that layout by hand — relative symlink, modes normalized (a copy out of the own store arrives
  `700`, git wants `644`), plus a `## Skills` section in its `AGENTS.md` naming the skills and the placement rule,
  else the next session invents a second layout.
- Keep repo-bound runbooks OUT of `docs/`: `properdocs.yml` uses `docs_dir: .` and excludes only what its glob
  lists, so a new `docs/<topic>/` page is PUBLISHED publicly. Skills sit outside `docs/`.
- `AGENTS.md` = canonical rules for ALL agents, sent with EVERY prompt → <150 lines, index-shaped (orientation
  table + pointers), invariants and gotchas only. `CLAUDE.md` = `@AGENTS.md` + Claude-only depth; never duplicate a
  rule across the two (divergence is the #1 documented failure mode).
- Pick the tier first: repo-bound → that repo's `.claude/skills/`; cross-machine curated → the chezmoi
  `dot_claude/skills` source + deploy; fast-moving upstream → Track 2, never hand-copied into Track 1.

## What actually loads (summary — probes and internals in the audit skill)
Resolution order: own store → `external_dirs` → project skills. Project skills need a candidate dir at the repo root
AND that root in `skills.trusted_project_dirs` (exact resolved path, no globs, no parent rules) — and the session
must resolve that root at all, which a global `terminal.cwd` (HOME, no `.git` above it) prevents, so trust stays
silently inert for chat sessions (upstream defect, fix in review). For a repo runbook both agents must see from a
`/config`-rooted session, list its `.agents/skills` in `external_dirs` or promote it to Track 1. `config.yaml`
refuses file-tool writes ("use 'hermes config' instead") → `hermes config set skills.external_dirs '["/config/.claude/skills","<repo>/.agents/skills"]'`
(read it back with `hermes config get`; effective only in the NEXT session), or hand the user the fenced block when
the path is his to approve. Full chain and decisive probes: `hermes-instance-audit` → `references/skill-loading-resolution.md`.

## Hermes own store — three writers

`~/.hermes/skills/<category>/<skill>/` is fed by three owners in ONE flat namespace, with nothing on the file
saying who owns it. Establish provenance before touching anything: the addon's ACTIVE tree → its `optional-skills/`
tree (shipped, NOT active — checking only the active tree yields a false "it's ours") → `.bundled_manifest` →
`created_by` in `.usage.json` (`agent` = ours). Counters come from `hermes curator usage`; where no CLI exists
(the webui container), read `.usage.json` and say which path you used.

- **Hermes-only is a PLACEMENT property, not a naming one:** `dot_claude/skills` → `/config/.claude/skills` is
  read by BOTH agents, so only a `dot_hermes/skills/<category>/` copy is Hermes-only.
- The store has TWO unattended writers (the Curator and the background-review pass) against git's one-way deploy:
  an in-place live edit is reverted by the next deploy unless it is ported into the source tree first, and a skill
  dropped from the repo keeps living live until its deployed dir is removed by hand. `hermes curator pin <name>` is
  the per-name opt-out; which names are actually writable, and by which actor, is in the Pitfalls below.
- Full writer matrix, the curator CLI, pin semantics, `hermes skills opt-out` vs a pin, and the re-homing rules:
  `references/store-writers-curator-and-pins.md`.

### A skill's category is its path, not its frontmatter

`tools/skills_tool.py::_get_category_from_path` derives category from the first path component:
`<root>/<category>/<skill>/SKILL.md` → that category; a flat `<root>/<skill>/SKILL.md` → blank
category. Re-filing a skill between categories in the own store is a plain `mv`; for a git-managed
skill the repo path IS the category, so it's `git mv` in the source tree followed by a redeploy
(moving only the live copy comes back as `MISSING`/`DIFFERS` on the next diff). Category also forms
part of the address used in some config references (`category/skill`), so a rename can invalidate a
config entry pointing at the old address — check for that before renaming a promoted skill.

### Merging a duplicate: pick the survivor, then prove the fold

Diff before pitching a merge — a workflow-vs-internals split is common and deliberate. Pick the survivor by which
copy is actually MANAGED (git/chezmoi-deployed and drift-checked), fold the loser's delta, delete the loser, then
re-run `skills-diff`/`skills-check`. **Verify the fold against the LOSER, item by item: a folded body reads fine
with rules missing and a delegated merge drops whole sections silently, so a clean diff proves nothing about lost
content.** Method and the phrase sweep: `references/reviewing-a-rewrite.md`.

### Audit — "too many skills, which can I delete?" (an inventory pass)

The inventory pass — telemetry caveats, the classification order, and the pitfalls that make a proposal wrong:
`references/audit-and-origin-inventory.md`. Findings are proposals: deletions are approved per step.

### Origin inventory — "list my skills with their origin"

The origin inventory query and the shape of the answer it must produce:
`references/audit-and-origin-inventory.md`.

### Promoting agent-authored skills into git (publishing gate)

Publishing is a review step, not a copy step: prioritise with `hermes curator usage`, check the destination's
visibility (`gh repo view <owner>/<repo> --json visibility`), scrub and stage the copy OUTSIDE the repo, place it
in the tier matching its audience (modes 644 files / 755 dirs), verify by resolving the NAME, and delete the live
copy in the SAME pass. Content that fails the scrub stays live-only and gets `hermes curator pin`. The nine steps,
the scan list and the placeholder mapping: `references/sanitizing-skills-for-public-repos.md`.

## Hermes bundled-skill sync (protect your own edits)
Bundled skills sync from the repo with a per-directory hash manifest: a user-edited copy is skipped forever,
deletions are respected, and `hermes skills list-modified` / `hermes skills reset <name>` manage it. Don't park
your own work inside a bundled skill dir if you want upstream updates — audit with `hermes-instance-audit`.

## Reviewing a rewrite the user pushed
Audit the DIFF, not the result — the old side is where the lost knowledge is, and a rewrite can only be called
lossless against its baseline. **The pushed work may not be on `main`**: this user pushes follow-ups onto the open
PR's branch, so review `git log --oneline HEAD..origin/<branch>` / `git diff --stat HEAD origin/<branch>` from the
existing worktree. Find the ref that carries it, sweep every surface for each removed or renamed NAME, run the
structural + live-vs-source inventory checks, privacy-scan only the touched files, and report file:line + fix +
severity with anything unconfirmed marked unverified. **Diff before committing a skill file you edited earlier** —
the user works in the same worktrees concurrently, so `git add <dir>` sweeps in changes you did not author; read
`git diff --cached` and disclose them. Full sequence and delegation rules: `references/reviewing-a-rewrite.md`.

## Community discovery — "find me skills I'm missing"
Never answer from the leaderboard (mega-suites dominate it and it says nothing about THIS library). Search by
DOMAIN, vet each hit on installs + security audits, drop whatever the library already covers (a bundled equivalent,
a vendored Track-1 name, a Track-2 plugin), and return a short ranked list plus an explicit "deliberately excluded"
line. Installing is a separate, user-gated step, and a hub install lands in the own store (Hermes-only, hub-owned) —
vendor into Track 1 instead when it must serve both agents or carry history. Both mechanisms, vetting signals, the
no-CLI path and exclusion patterns: `references/community-skills-npx.md`.

## Verification checklist
- [ ] exactly one path serves each ported name (`find -L <every root> -path "*<name>/SKILL.md"` == 1 hit)
- [ ] the target repo's hooks pass on the staged files, and the commit is only made after a green pass
- [ ] the scrub scan on the STAGED copy returns 0 identity/secret hits — report the count, an adjective is not evidence
- [ ] every skill's frontmatter `name` equals its directory name, and no surviving file names a dead skill (body, `related_skills`, `AGENTS.md` index row, help block)
- [ ] no live store name is left over from a source-tree deletion, and no report claims a count the CLI did not print
- [ ] a ported/deployed name resolves to the repo path, not the agent store, and private skills carry `pinned: true`
- [ ] a community recommendation names installs + audit verdict + the overlap check, and says plainly if nothing was installed

## Pitfalls
- Approval gates: `AGENTS.md`/`CLAUDE.md` and `config.yaml` writes come back BLOCKED on timeout → STOP, report, and
  let the user say "prompt me again" to re-fire the exact patch; never retry it and never route the same edit
  through terminal or another file. `git commit`/`git push` need per-action approval every time (a plan, a task
  description or a previous yes is NOT permission); commit email must match existing commits, never invented. Keep
  read-only bookkeeping to single-purpose shell one-liners — a compound call embedding an interpreter
  (`python3 -c …`) alongside other commands stalls at the gate and returns BLOCKED, while a one-liner or `read_file`
  on the JSON returns at once; name any blocked call in the report instead of quietly substituting.
- Destructive cleanup (`rm -rf`, `git clean -f`, a `tar` into a protected path) raises its OWN approval prompt, and a
  timed-out prompt is not consent either → stop, report, re-fire only when the user says so. Keep the backup and the
  delete in ONE command with the backup first, so a timeout leaves nothing half-applied, and state the exact
  file/dir list before each step — deletions are approved per step, not per plan.
- **Ambiguity window breaks loads.** While a live copy and the repo copy co-exist, name-based loading FAILS
  (`Ambiguous skill name '<n>': 2 skills match across your local skills dir and external_dirs`) and the listing
  hides it — verify with `find -L <every root> -path "*<name>/SKILL.md"` (exactly one hit; plain `find` misses a
  skill reached through a `.agents/skills` symlink, so an empty result is not "the skill vanished").
- **Copied scripts and templates must pass the target repo's hooks before the commit** — a verbatim copy routinely
  fails lint/format/YAML hooks (`references/repo-hook-gate.md`), and the staged copy is a SNAPSHOT: an edit made to
  the live skill after staging is not in the port, so re-copy if the live file moved on.
- **Check BOTH path bases before calling a supporting-file reference broken.** `references/…`/`scripts/…` written
  with a slash are skill-relative; a bare `scripts/<name>.py` in prose is usually the REPO root's own directory —
  test `<skill-dir>/<rel>` and `<repo-root>/<rel>` before calling one broken.
- The webui container has NO Node.js by design — `npx skills` and node CLIs do not exist there (the AGENT container
  does). Vendor via git clone (Track 1) or `claude plugin` (Track 2); do not install Node for this.
- Python/npx-style third-party skill managers were evaluated and REJECTED (Sep 2026): `agent-skill-manager` (PyPI, 2
  stars, beta) and `xingkongliang/skills-manager` (Tauri app with its own library + SQLite + git sync). Both add a
  second source of truth parallel to the repo → `.claude/skills` flow; that duplication is rejected here.
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
- **A lesson such a pass produces for a deployed skill is SOURCE work.** Repo-deployed names carry `created_by:
  agent`, so its write to the live copy goes through — and then the next deploy either ABORTS on the fresh
  `DIFFERS` or a `SKILLS_FORCE=1` run overwrites the lesson. Write it in the source tree instead, name any drift you
  caused with its file, and if every relevant skill is genuinely protected, report "Nothing to save" PLUS the exact
  edits the repo still needs — never a new overlapping curator skill.
- **A file the source tree no longer has is not automatically stale live content to port back.** Compare size and
  mtime per FILE and ask whether the source-side edit was deliberate: a deleted install snapshot or context dump must
  be dropped (force-deploy), while a live-only reference the source never had is the one to port in.
- personal-os-setup: branch/PR from `main` (the `dev` branch is retired).

## References
- `references/store-writers-curator-and-pins.md` — the three writers of the own store, the curator CLI, pin
  semantics, `hermes skills opt-out` vs a pin, and the re-homing rules.
- `references/install-and-track-procedures.md` — the Track-1 vendor steps, the Track-2 plugin commands and the
  bundle-that-is-both case, with the three-round hook fix.
- `references/audit-and-origin-inventory.md` — the "which can I delete?" inventory pass and the origin inventory.
- `references/deploy-drift-and-reconciliation.md` — the two-tree reconciliation decision tree, per-file checks and
  the mixed-drift case.
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

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
governance text: personal-os-setup `AGENTS.md` § "Skills & plugins — one rule". Verifying
what a configured dir actually LOADS → `hermes-instance-audit`.

## When to use
- "Why doesn't the agent see skill X" — the wiring side (diagnose with `hermes-instance-audit`)
- "Too many skills — which can I delete?" · porting a live-only skill into git · reviewing a rewrite the user pushed
- Repo-local runbooks, AGENTS.md vs CLAUDE.md layout questions
- Not for: auditing an install's config/plugins/curator behaviour, or a repo's own `skills-link`/`skills-check`
  flow (`hermes-instance-audit`, `skill-layout`).

## The zones
| Zone | Path | Read by |
|---|---|---|
| Hermes own store | `/config/.hermes/skills/` | Hermes only |
| Authored — SOURCE, the ONE tree (repo = truth) | `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/` | both agents, via deployment |
| Authored — DEPLOYED | `/config/.claude/skills/` (chezmoi target; HOME=/config) | Claude Code (global) + Hermes `external_dirs` |
| Repo-specific | `<repo>/.claude/skills/` + `.agents/skills/` git symlinks | Claude Code in that repo; Hermes only from a session rooted there or via `external_dirs` |
| Plugins / MCP (not skill files) | `~/.claude/plugins/`, `$HERMES_HOME/mcp-tokens/` | Claude plugins; Hermes MCP servers |

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
- `vendored` + `source: <owner>/<repo>` — a third-party copy.
- `hub` — installed from the skills hub; tool-managed.
- `exposure: private` — never promote or publish as-is; absent = publishable (the default).
- Bundled (addon-shipped) skills carry **no** marker: editing one freezes its sync forever, and
  `.bundled_manifest` already records them.

## Governance — one rule (`AGENTS.md`)
- Authored skills → chezmoi source `dot_claude/skills/<name>/`, deployed to `/config/.claude/skills/`; the saved set is `skills.keep`.
- Third-party skills → `npx skills add <owner>/<repo> -s <skill> -a claude-code -g -y --copy` (never `-a hermes-agent`, never `-a '*'`); never vendored as a copy.
- Plugin packs (`superpowers`, `cloudflare/skills`) → that harness's own channel, one canal per pack per agent.
- Plugin install commands and the bundle-that-is-both case: `references/install-and-track-procedures.md`.

## Deploying the shared dir (chezmoi / container)

Deploy mechanics — the chezmoi `--source` = repo-root and run-from-HOME rules, `make skills-deploy` and its
`SKILLS_FORCE=1` escape hatch, and the Deploying-from-a-container variant — live in the `skill-deployment` skill;
don't restate them here. The container-specific debugging trail (a nested `.chezmoiroot` breaking the TUI's
`--source`, the file-level `--source-path` fallback) is in `references/chezmoi-dot-claude-deployment.md`.

## Reconciling the two trees — the deploy gate

`MISSING` = the deploy has not landed, never "redundant"; `DIFFERS` → check per FILE which side is newer; re-run
`make skills-diff` after the deploy. Decision tree and per-file checks: `references/deploy-drift-and-reconciliation.md`.

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
  `dot_claude/skills` source + deploy; fast-moving upstream → plugin pack or `npx`, never hand-copied into the authored tree.

## What actually loads (summary — probes and internals in the audit skill)
Resolution order: own store → `external_dirs` → project skills. Project skills need a candidate dir at the repo root
AND that root in `skills.trusted_project_dirs` (exact resolved path, no globs, no parent rules) — and the session
must resolve that root at all, which a global `terminal.cwd` (HOME, no `.git` above it) prevents, so trust stays
silently inert for chat sessions (upstream defect, fix in review). For a repo runbook both agents must see from a
`/config`-rooted session, list its `.agents/skills` in `external_dirs` or promote it to the authored tree. `config.yaml`
refuses file-tool writes ("use 'hermes config' instead") → `hermes config set skills.external_dirs '["/config/.claude/skills","<repo>/.agents/skills"]'`
(read it back with `hermes config get`; effective only in the NEXT session), or hand the user the fenced block when
the path is the user's to approve. Full chain and decisive probes: `hermes-instance-audit` → `references/skill-loading-resolution.md`.

## Hermes own store — three writers

`~/.hermes/skills/<category>/<skill>/` is fed by three owners in ONE flat namespace. Establish provenance before
touching anything: the addon's ACTIVE tree → its `optional-skills/` tree (shipped, NOT active) → `.bundled_manifest` →
`created_by` in `.usage.json` (`agent` = ours). Writer matrix, curator CLI, pins and re-homing rules:
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

**Verify the fold against the LOSER, item by item: a folded body reads fine
with rules missing and a delegated merge drops whole sections silently, so a clean diff proves nothing about lost
content.** Method and the phrase sweep: `references/reviewing-a-rewrite.md`.

### Shortening a skill that has grown verbose

Skills carry a size norm — **~200 lines for a complex SKILL.md, ~100 for a simple one** — so a 400+-line file is a
compliance failure, not thoroughness, and this user will ask for it to be shortened. Shrink by MOVING, never by
deleting: cut whole sections at their headings, append them verbatim to `references/<topic>.md`, leave a 3-6 line
pointer naming what the reference covers and its path, and register it in the References list. A pointer that
paraphrases a rule instead of pointing at it silently rewrites the skill — keep pointers to coverage + filename,
and carry over only the one hard rule a caller must not miss. Prove the trim with the same phrase sweep as a merge,
run against the PRE-trim text (`git show HEAD:<path>`), and report the line/byte before-and-after with the miss
count.

**Audit / origin inventory** ("which can I delete?", "list my skills with their origin"): `references/audit-and-origin-inventory.md`. Findings are proposals: deletions are approved per step.

### Promoting agent-authored skills into git (publishing gate)

Publishing is a review step: scrub → place in `dot_claude/skills/<name>/` → delete the live copy in the same pass; failing content stays live-only + `hermes curator pin`. Steps: `references/sanitizing-skills-for-public-repos.md`.

## Reviewing a rewrite the user pushed
Audit the DIFF, not the result; the pushed work may not be on `main`. Diff before committing a skill file you edited earlier — `git add <dir>` sweeps in changes you did not author. Sequence and delegation rules: `references/reviewing-a-rewrite.md`.

## Community discovery — "find me skills I'm missing"
Never answer from the leaderboard. Vetting, exclusion patterns and the pre-flight rules: `references/community-skills-npx.md`.

## Verification checklist
- [ ] exactly one path serves each ported name (`find -L <every root> -path "*<name>/SKILL.md"` == 1 hit)
- [ ] the target repo's hooks pass on the staged files, and the commit is only made after a green pass
- [ ] the scrub scan on the STAGED copy returns 0 identity/secret hits — report the count, an adjective is not evidence
- [ ] every skill's frontmatter `name` equals its directory name, and no surviving file names a dead skill (body, `related_skills`, `AGENTS.md` index row, help block)
- [ ] a ported/deployed name resolves to the repo path, not the agent store, and private skills carry `pinned: true`; no live store name is left over from a source-tree deletion, and no report claims a count the CLI did not print
- [ ] a community recommendation names installs + audit verdict + the overlap check, and says plainly if nothing was installed

## Pitfalls
- Approval gates: `AGENTS.md`/`CLAUDE.md` and `config.yaml` writes come back BLOCKED on timeout → STOP, report, and
  let the user say "prompt me again" to re-fire the exact patch; never retry it and never route the same edit
  through terminal or another file. Name any blocked call instead of quietly substituting.
- `git commit`/`git push` need per-action approval every time (also in `AGENTS.md`); commit email must match existing commits, never invented.
- Keep shell calls single-purpose — no `$(…)`, `for`, `;`/`&&` chains or `python3 -c …` bundles: one gated link takes the
  whole sequence down, so split a verification bundle into separate calls UP FRONT. Run multi-source research as direct
  `web_extract`/`terminal` calls, not a batch through `execute_code`.
- Destructive cleanup (`rm -rf`, `git clean -f`, a `tar` into a protected path) raises its OWN approval prompt, and a
  timed-out prompt is not consent either → stop, report, re-fire only when the user says so. Keep the backup and the
  delete in ONE command with the backup first, so a timeout leaves nothing half-applied, and state the exact
  file/dir list before each step — deletions are approved per step, not per plan.
- **Ambiguity window breaks loads.** While a live copy and the repo copy co-exist, name-based loading FAILS
  (`Ambiguous skill name '<n>': 2 skills match across your local skills dir and external_dirs`) and the listing
  hides it — verify with `find -L <every root> -path "*<name>/SKILL.md"` (exactly one hit; plain `find` misses a
  skill reached through a `.agents/skills` symlink, so an empty result is not "the skill vanished").
- **Copied scripts and templates must pass the target repo's hooks before the commit** — a verbatim copy routinely
  fails lint/format/YAML hooks (`references/repo-hook-gate.md`), and the staged copy is a SNAPSHOT, and live moves while you port: an edit after staging is not in the port,
  so re-copy if the live file moved on and re-run `make skills-diff` immediately before committing.
- **Check BOTH path bases before calling a supporting-file reference broken.** `references/…`/`scripts/…` written
  with a slash are skill-relative; a bare `scripts/<name>.py` in prose is usually the REPO root's own directory —
  test `<skill-dir>/<rel>` and `<repo-root>/<rel>` before calling one broken.
- The webui container has NO Node.js by design — `npx skills` and node CLIs do not exist there (the AGENT container
  does). Deploy authored skills via chezmoi/`make skills-deploy` or install plugin packs with `claude plugin`; do not install Node for this.
- Python/npx-style third-party skill managers were evaluated and REJECTED (Sep 2026): `agent-skill-manager` (PyPI, 2
  stars, beta) and `xingkongliang/skills-manager` (Tauri app with its own library + SQLite + git sync). Both add a
  second source of truth parallel to the repo → `.claude/skills` flow; that duplication is rejected here.
- **A lesson such a pass produces for a deployed skill is SOURCE work.** Repo-deployed names carry `created_by:
  agent`, so its write to the live copy goes through — and then the next deploy either ABORTS on the fresh
  `DIFFERS` or a `SKILLS_FORCE=1` run overwrites the lesson. Write it in the source tree instead, name any drift you
  caused with its file, and if every relevant skill is genuinely protected, report "Nothing to save" PLUS the exact
  edits the repo still needs — never a new overlapping curator skill.
- **A file the source tree no longer has is not automatically stale live content to port back.** Compare size and
  mtime per FILE and ask whether the source-side edit was deliberate: a deleted install snapshot or context dump must
  be dropped (force-deploy), while a live-only reference the source never had is the one to port in.

## References
- `references/store-writers-curator-and-pins.md` — own-store writers, curator, pins
- `references/install-and-track-procedures.md` — plugin and bundle install commands
- `references/audit-and-origin-inventory.md` — deletion audit, origin inventory
- `references/deploy-drift-and-reconciliation.md` — two-tree drift decision tree
- `references/chezmoi-dot-claude-deployment.md` — container deploy invocation, file-level fallback
- `references/community-skills-npx.md` — community discovery, vetting, install rules
- `references/sanitizing-skills-for-public-repos.md` — scrub list, placeholders, review rules
- `references/repo-hook-gate.md` — running target repo hooks on copies
- `references/platform-lifecycle-and-gates.md` — Hermes library lifecycle, gates, knobs
- `references/reviewing-a-rewrite.md` — diff-first review of pushed rewrites
- `scripts/review-drift.py` — source-vs-live drift review

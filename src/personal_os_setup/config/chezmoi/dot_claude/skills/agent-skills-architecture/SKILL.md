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
    related_skills: [hermes-instance-audit, skill-deployment]
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
  flow (`hermes-instance-audit`).

## The zones
| Zone              | Path                                                         | Read by                          |
|-------------------|--------------------------------------------------------------|----------------------------------|
| Hermes own store  | `/config/.hermes/skills/`                                    | Hermes only                      |
| Authored SOURCE   | `<repo>/src/.../chezmoi/dot_claude/skills/`                  | all agents, via deployment       |
| Authored DEPLOYED | `/config/.claude/skills/` (chezmoi target; HOME=/config)     | Claude Code, Codex, Hermes       |
| Repo-specific     | `<repo>/.claude/skills/` + `.agents/skills/` git symlinks    | that repo's sessions             |
| Plugins / MCP     | `~/.claude/plugins/`, `$HERMES_HOME/mcp-tokens/`             | Claude plugins; Hermes MCP       |

- SOURCE is the ONE tree (repo = truth). DEPLOYED is read by Claude Code (global), Codex per-skill links in
  `~/.agents/skills`, and Hermes `external_dirs`. Repo-specific skills reach Hermes only from a session rooted
  there or via `external_dirs`.

Zone rules, verbatim in `references/zones-and-provenance.md`: always write `/config/...` (never the host
`/addon_configs/...` spelling); NEVER copy bundled Hermes skills into the shared dir (tool-coupled, auto-updated);
shared-dir skills stay agent-agnostic with no personal identifiers (public `github.com/<owner>/<repo>` URLs excepted).

## Provenance metadata — who owns a skill

Every owned skill records `metadata.hermes.origin` (`agent` | `repo:<name>` | `vendored` | `hub`), plus
`exposure: private` ONLY when it must never be published. Bundled skills carry **no** marker (editing one freezes its
sync). Meaning of each value: `references/zones-and-provenance.md`.

## Governance — one rule (`AGENTS.md`)
- Authored skills → chezmoi source `dot_claude/skills/<name>/`, deployed to `/config/.claude/skills/`; the saved set is `skills.keep`.
- Third-party skills → `npx skills add <owner>/<repo> -s <skill> -a claude-code -g -y` (never `-a hermes-agent`, never `-a '*'`); never vendored as a copy.
- Plugin packs (`superpowers`, `cloudflare/skills`) → that harness's own channel, one canal per pack per agent.
- Plugin install commands and the bundle-that-is-both case: `references/installing-and-vetting-skills.md`.

## Deploying the shared dir (chezmoi / container)

Deploy mechanics — the chezmoi `--source` = repo-root and run-from-HOME rules, `make skills-personal-repo-to-live` and its
`FORCE=1` escape hatch, and the Deploying-from-a-container variant — live in the `skill-deployment` skill;
don't restate them here. The container-specific debugging trail (a nested `.chezmoiroot` breaking the TUI's
`--source`) and the file-level `--source-path` fallback are in `skill-deployment`.

## Reconciling the two trees — the deploy gate

`MISSING` = the deploy has not landed, never "redundant"; `DIFFERS` → check per FILE which side is newer; re-run
`make skills-status` after the deploy. Decision tree and per-file checks: `skill-deployment` → `references/deploy-drift-and-reconciliation.md`.

## Repo-local skills + AGENTS.md ↔ CLAUDE.md

Layout (`.claude/skills` canonical, `.agents/skills` git symlinks, `make skills-link` / `skills-check`), keeping runbooks out of `docs/`, AGENTS.md/CLAUDE.md split, tier choice: `references/repo-local-skills-and-agents-md.md`. Rules not to miss: never edit through a symlink; a repo-bound runbook is a skill, not a `docs/` page (docs are published publicly).

## What actually loads

Precedence, project-trust and root-resolution caveats and the `external_dirs` config command: `references/what-actually-loads.md`; probes in `hermes-instance-audit` → `references/skill-loading-resolution.md`. `config.yaml` refuses file-tool writes; effects start in the NEXT session.

## Hermes own store — three writers

`~/.hermes/skills/<category>/<skill>/` is fed by three owners in ONE flat namespace. Establish provenance before
touching anything: the addon's ACTIVE tree → its `optional-skills/` tree (shipped, NOT active) → `.bundled_manifest` →
`created_by` in `.usage.json` (`agent` = ours). Writer matrix, curator CLI, pins and re-homing rules:
`references/store-writers-curator-and-pins.md`.

### Category, merging, shortening

Category = path, not frontmatter (re-file with `mv`, or `git mv` + redeploy for git skills); merging a duplicate (**verify the fold against the LOSER, item by item** — a clean diff proves nothing about lost content); shortening a verbose skill (norm ~200 lines; MOVE sections to `references/`, never delete; phrase-sweep against the pre-trim text): `references/store-maintenance-recipes.md`.

**Audit / origin inventory** ("which can I delete?", "list my skills with their origin"): `references/audit-and-origin-inventory.md`. Findings are proposals: deletions are approved per step.

### Promoting agent-authored skills into git (publishing gate)

Publishing is a review step: scrub → place in `dot_claude/skills/<name>/` → delete the live copy in the same pass; failing content stays live-only + `hermes curator pin`. Steps: `references/sanitizing-skills-for-public-repos.md`.

## Reviewing a rewrite the user pushed
Audit the DIFF, not the result; the pushed work may not be on `main`. Diff before committing a skill file you edited earlier — `git add <dir>` sweeps in changes you did not author. Sequence and delegation rules: `references/reviewing-a-rewrite.md`.

## Community discovery — "find me skills I'm missing"
Never answer from the leaderboard. Vetting, exclusion patterns and the pre-flight rules: `references/installing-and-vetting-skills.md`.

## Verification checklist
- [ ] exactly one path serves each ported name (`find -L <every root> -path "*<name>/SKILL.md"` == 1 hit)
- [ ] the target repo's hooks pass on the staged files, and the commit is only made after a green pass
- [ ] the scrub scan on the STAGED copy returns 0 identity/secret hits — report the count, an adjective is not evidence
- [ ] every skill's frontmatter `name` equals its directory name, and no surviving file names a dead skill (body, `related_skills`, `AGENTS.md` index row, help block)
- [ ] a ported/deployed name resolves to the repo path, not the agent store, and private skills carry `pinned: true`; no live store name is left over from a source-tree deletion, and no report claims a count the CLI did not print
- [ ] a community recommendation names installs + audit verdict + the overlap check, and says plainly if nothing was installed

## Pitfalls

- Approval gates: a timed-out prompt is not consent → STOP and report; never retry or re-route the same edit. `git commit`/`git push` need per-action approval every time.
- **Name collisions:** keep every skill name in exactly one root. Check with `find -L <every root> -path "*<name>/SKILL.md"` (exactly one hit).
- Copied scripts/templates must pass the target repo's hooks before commit; a staged copy is a snapshot — re-copy if live moved.
- Everything else (shell-call hygiene, destructive cleanup, container facts, source-vs-live lessons): `references/pitfalls.md`.

## References
- `references/zones-and-provenance.md` — zone rules, provenance values
- `references/repo-local-skills-and-agents-md.md` — repo-local layout, AGENTS.md/CLAUDE.md
- `references/what-actually-loads.md` — precedence, trust, external_dirs command
- `references/store-maintenance-recipes.md` — category, merge, shorten recipes
- `references/store-writers-curator-and-pins.md` — own-store writers, curator, pins
- `references/audit-and-origin-inventory.md` — deletion audit, origin inventory
- `references/installing-and-vetting-skills.md` — npx / plugin / hub installs, community vetting
- `references/sanitizing-skills-for-public-repos.md` — scrub list, placeholders, review rules
- `references/repo-hook-gate.md` — running target repo hooks on copies
- `references/platform-lifecycle-and-gates.md` — Hermes library lifecycle, gates, knobs
- `references/reviewing-a-rewrite.md` — diff-first review of pushed rewrites
- `references/pitfalls.md` — shell hygiene, destructive cleanup, container facts
- `scripts/review-drift.py` — source-vs-live drift review

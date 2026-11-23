---
name: hermes-instance-audit
description: "Audit a live Hermes install: skills, plugins, config."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [hermes, audit, skills, plugins, platforms, channels, config, versions, curator, sync, read-only]
    related_skills: [hermes-agent, agent-skills-architecture]
---

# Hermes Instance Audit (read-only)

Answer "what do we have / is anything wrong / how does it compare upstream" about a live Hermes
Agent installation without changing it. Read-only unless the user explicitly asks for a change.

## When to use
- "Where did skill X go / why is it disabled / can I get deleted skills back" · "did they remove the default installed stuff" · "compare it with the latest version / release"
- "Why does the dashboard say X" · "why is context at X% / do these tools eat too much"
- A pasted add-on/gateway BOOT LOG — "why is /dashboard/ dead" → boot-log triage below, depth in `references/addon-boot-log-triage.md` · "analyse the storage of this add-on" → `references/storage-and-cache-map.md`
- "hermes update" · "is an update already running" · "the update looks stuck / the version didn't change" → depth in `references/update-lifecycle.md`
- Not for installing, vendoring, merging or wiring skills → `agent-skills-architecture`.

## Hard rules
- **Read-only**: `read_file`, `search_files`, `web_extract`. Never edit `config.yaml` (only `hermes config set`), never run a sync by hand, never restore a skill without an explicit go-ahead. The deliverable of an audit is the EXPLANATION — what exists, what it does, what (if anything) needs doing — and **"nothing needs doing" is a valid, expected answer**. Do not close with install/enable/cleanup pitches or a menu of optional upgrades: the user reads an unrequested proposal as a defect in the answer, and only wants options when asked.
- **Approval gate**: with `approvals.mode: manual`, `terminal`/`execute_code` calls can sit at the consent gate and time out (BLOCKED). An audit is doable on file tools + read-only plain-shell one-liners: single `mkdir`/`cp`/`tar`/`find`/`diff`/`md5sum`/`grep` lines pass, while `execute_code`, `python -c`, heredocs and multi-line loops/scripts time out even when read-only. Keep shell work to one-liners; do the rest with file tools. **Never retry a blocked call** — report it and let the user say "prompt me again"; when the user does, re-issue the SAME call, which then runs (the gate was the problem, not the call). Never reach the same outcome through a substitute tool in the meantime.
- `.env` is access-denied to `read_file` (credential store) — audit keys from memory/session context instead.
- web_extract caches of big GitHub API JSON are ONE giant line: `read_file` cannot page them (no `next_offset`). Use `search_files` with context, or fetch a single release/tag endpoint (~60KB, fits one read).

## Inventory — key paths

`~/.hermes` = `$HERMES_HOME`. Path table (manifest, usage, curator files, `config.yaml`, `.update_check`, gateway state, `plugins/`, checkout) and the two skill zones (bundled vs optional; upstream "debloats" by relocation, not deletion): `references/inventory-and-paths.md`.

## Version & release comparison

Local first (`.update_check` `behind`, `pyproject.toml` version), then git (`rev-list --count HEAD..origin/main`, tags). **A new version on disk does NOT mean the new code is live**: `hermes update` never restarts the gateway/dashboard — compare `ps -o lstart` of the gateway pid against the install mtime. Recipes: `references/version-comparison.md`, `references/release-verification.md`.

## Commands to advise, never run unasked
- `hermes skills reset <name>` = un-mark user-modified so updates apply again; `hermes skills reset <name> --restore` = ALSO deletes the local copy and re-seeds current stock (the fix for STALE stock — it destroys user content if there was any). Reset is per-skill: there is no global reset.
- Restore a deleted bundled skill: `hermes skills reset <name>` + `hermes update`, or copy the dir from `<install>/skills/`. Optional skills: `hermes skills repair-official <name> --restore` (backs up first). Nothing blocks re-seeding unless `.curator_suppressed` exists.

## Skills: what's on disk vs what actually loads

Tiers (builtin/local/hub/external), reliable probes, the config-write limitation and root resolution: `references/skills-on-disk-vs-loaded.md` (chain internals: `references/skill-loading-resolution.md`). Rules a caller must not miss: **`hermes skills inspect` does not resolve `external_dirs`** (never read its "not found" as absence), and **the agent cannot write `config.yaml`** — hand the user a bare fenced YAML block; a corrected dir takes effect in the NEXT session.

## Skills sync rules (manifest-based; restore is always safe)
- Missing bundled skills are NOT corruption → report "removed on your side". User deletions and curator prunes look identical on disk: disambiguate with `.curator_suppressed` + `.curator_backups/<ts>/manifest.json` (curator `prune_builtins: true` CAN prune bundled skills after `stale_after_days`) and by asking the user.
- **Never compare `md5sum SKILL.md`** — manifest hashes are DIRECTORY hashes and it reports EVERY bundled skill as user-modified. Run `scripts/check_bundled_manifest.py`.
- **DIFFERS ≠ user-modified**: read the direction (`hermes skills diff <name>`) — STALE stock (older baked copy, no custom content → `reset --restore`) vs USER-MODIFIED (keep; sync protects it).
- NEW/EXISTING/DELETED/REMOVED matrix, content sweep one-liner, delete vs disable: `references/skills-sync-and-bundling.md`.

## Curator behaviour
- Prunes stale skills by default (`stale_after_days`, `archive_after_days`), weekly (`interval_hours: 168`); LLM consolidation OFF unless `curator.consolidate: true` (= no aux-model spend).
- Bundled + hub-installed skills are OFF-LIMITS to the LLM pass (`tools/skill_usage.py`: `off_limits = bundled | hub_installed`) — it only marks them stale/reactivates; only agent-created skills get consolidated.
- **Pinned = off-limits to BOTH writers.** `hermes curator pin <name>` skips lifecycle transitions and the autonomous background-review pass; only a foreground user edit can change a pinned skill. Details: `agent-skills-architecture/references/store-writers-curator-and-pins.md`.

## Config checklist, log triage, library hygiene

Details: `references/config-log-hygiene.md`. Must-not-miss: split agent-created vs bundled BEFORE opining on cleanup (never propose touching bundled skills); an explicit old `agent.max_turns` silently caps runs; **attribute a pasted log to a surface (name the add-on slug in the FIRST line) and lead with the defect**; `SystemExit` 75 is a normal update restart; Telegram "polling conflict" = two gateways at once. Boot-log depth: `references/addon-boot-log-triage.md`.

## Plugins / platforms / channels + dashboard toggles

Allow/deny-list semantics, platform toolsets, web backend, bundled-vs-catalog and removal rules: `references/plugins-and-dashboard-toggles.md` (taxonomy: `references/plugins-platforms-channels.md`). Key rule: `plugins.disabled` is the real deny-list; bundled plugins cannot be removed, so never propose a cleanup pass over them.

## Pitfalls

Full list: `references/audit-pitfalls.md`. Most-missed: `skills_list` is not the on-disk inventory (count per tier, exclude `.archive/`); "not found" from a probe is not absence (prove against a CONTROL); a missing `make`/`hermes`/`npx` is the container, not a broken install (check `hostname`); `reset --restore` destroys user content — read the diff first.

## References
- `references/inventory-and-paths.md` — key-path table, skill zones
- `references/version-comparison.md` — local/git version checks, live-code caveat
- `references/skills-on-disk-vs-loaded.md` — tiers, probes, config-write limitation
- `references/plugins-and-dashboard-toggles.md` — allow/deny lists, toolsets, removal rules
- `references/audit-pitfalls.md` — full pitfall list
- `references/config-log-hygiene.md` — config checklist, log triage, library hygiene
- `references/storage-and-cache-map.md` — where add-on space goes, probe recipe
- `references/release-verification.md` — after-upgrade checklist, probe recipes, per-feature evidence
- `references/update-lifecycle.md` — `hermes update` phases, markers, checks
- `references/addon-boot-log-triage.md` — boot-log attribution and failure signatures
- `references/skill-loading-resolution.md` — loading chain, root resolution, probes
- `references/plugins-platforms-channels.md` — plugin/platform/channel taxonomy and rules
- `references/skills-sync-and-bundling.md` — sync semantics, sweep one-liner, delete vs disable
- `scripts/check_bundled_manifest.py` — read-only manifest probe

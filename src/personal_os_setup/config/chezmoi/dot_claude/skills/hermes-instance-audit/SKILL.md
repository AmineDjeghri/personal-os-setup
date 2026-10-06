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

## Inventory — key paths (`~/.hermes` = `$HERMES_HOME`)
| Path | Meaning |
|---|---|
| `skills/.bundled_manifest` | `name:hash` of every bundled skill synced from `<install>/skills/` (v2) |
| `skills/.usage.json` | per-skill `use_count`, `state` (active/stale), `created_by` ("agent" = agent-created) |
| `skills/.curator_state` / `.curator_ledger.jsonl` | last curator run summary / per-patch audit trail (actor, action, skill, evidence session) |
| `skills/.curator_backups/<ts>/` | weekly pre-run snapshots (`manifest.json` + `skills.tar.gz`) |
| `skills/.curator_suppressed` | curator-banned builtins — sync will NOT re-seed these (absent = nothing blocked) |
| `.no-bundled-skills` | opt-out marker (installer `--no-skills`); absent = seeding active |
| `config.yaml` | protected: `skills.disabled`, `plugins.enabled/disabled`, `platform_toolsets`, `approvals`, `curator`, `agent.max_turns` |
| `.update_check` | `{ver, behind}` — `behind: 0` = up to date |
| `channel_directory.json` / `gateway_state.json` | registered channels / live platform states + gateway pid |
| `plugins/` | USER plugins only — bundled plugin code lives in `<install>/plugins/` (state-only leftovers are cleanable) |
| `hermes-agent/` | the git checkout: version in `pyproject.toml`, tags under `.git/refs/tags/` |

- The repo ships TWO skill zones: `<install>/skills/` (bundled, manifest-synced on install/update) and `<install>/optional-skills/` (100+, on demand, never synced). Bundled plugins load from `<install>/plugins/` and are ADDED, not removed, by upgrades.
- Upstream "debloats" by MOVING skills bundled → optional-skills, never by silently deleting → "they removed the default stuff" is usually relocation.

## Version & release comparison
- Local first: `.update_check` (`behind`) + `<install>/pyproject.toml` `version =` — the install is often already current.
- git install (cheapest "latest vs mine"): `git fetch origin && git rev-list --count HEAD..origin/main` (`0` = the checkout IS main tip), `git tag --sort=-creatordate | head -5`, `git rev-list --count <tag>..HEAD`. HEAD can be AHEAD of the newest tag (main tip) — report both.
- Tag ↔ version: tags are calendar `v2026.M.D` while the package version is `0.x.y` (`v2026.8.3` = 0.20.0). Patch tags' notes are rolled into the next minor's body.
- Manifest vs repo: `.bundled_manifest` should equal `<install>/skills/**/SKILL.md` 1:1.
- Release bodies: working URLs, the escaped-JSON pitfall and the keywords to grep → `references/release-history.md`.

## Commands to advise, never run unasked
- `hermes skills reset <name>` = un-mark user-modified so updates apply again; `hermes skills reset <name> --restore` = ALSO deletes the local copy and re-seeds current stock (the fix for STALE stock — it destroys user content if there was any). Reset is per-skill: there is no global reset.
- Restore a deleted bundled skill: `hermes skills reset <name>` + `hermes update`, or copy the dir from `<install>/skills/`. Optional skills: `hermes skills repair-official <name> --restore` (backs up first). Nothing blocks re-seeding unless `.curator_suppressed` exists.

## Skills: what's on disk vs what actually loads
- Four tiers: builtin + local (`~/.hermes/skills/**`) + hub are the only ones `hermes skills list` shows; `external_dirs` and `trusted_project_dirs` are **never listed** — absence from that output proves nothing about them.
- Decisive probe: `hermes skills inspect <name>` ("No skill named 'x' found in any source" = out of scope); run it from the repo root to test repo-local loading. `hermes config check` validates NOTHING about skill dirs (a non-existent entry is skipped SILENTLY): `ls -d <every entry>`.
- A trusted repo that still loads nothing is ROOT RESOLUTION, not trust: root = nearest `.git` ancestor of the *surface* cwd (`TERMINAL_CWD` / `terminal.cwd` — a global value overrides the session's own cwd: upstream defect, fix in review), one root per session, fixed at session start, exact-path match, no globs.
- **The agent cannot write `config.yaml`** (the write tool refuses: "use 'hermes config'") and `hermes config set` takes ONE key + value with unverified list semantics → hand the user the exact copy-paste block: **only the fenced YAML, no preamble and no per-line explanation** (the user interrogates the reasoning afterwards if they want it), plus the post-edit proof (`hermes skills list --source local | grep -c '<known-shared-skill>'`, `hermes skills inspect <name>` from the repo). Skills load at session start — a corrected dir takes effect in the NEXT session; never claim immediate effect.
- Full chain, root-resolution internals, upstream issue/PR handles, probes and the working config block: `references/skill-loading-resolution.md`.

## Skills sync rules (manifest-based; restore is always safe)
- Missing bundled skills are NOT corruption → report "removed on your side". User deletions and curator prunes look identical on disk: disambiguate with `.curator_suppressed` + `.curator_backups/<ts>/manifest.json` (curator `prune_builtins: true` CAN prune bundled skills after `stale_after_days`) and by asking the user.
- **Never compare `md5sum SKILL.md`** — manifest hashes are DIRECTORY hashes and it reports EVERY bundled skill as user-modified. Run `scripts/check_bundled_manifest.py`.
- **DIFFERS ≠ user-modified**: read the direction (`hermes skills diff <name>`) — STALE stock (older baked copy, no custom content → `reset --restore`) vs USER-MODIFIED (keep; sync protects it).
- NEW/EXISTING/DELETED/REMOVED matrix, content sweep one-liner, delete vs disable: `references/skills-sync-and-bundling.md`.

## Curator behaviour (changed by version!)
- v0.16+: prunes stale skills by default (`stale_after_days`, `archive_after_days`), weekly (`interval_hours: 168`); LLM consolidation OFF unless `curator.consolidate: true` (= no aux-model spend).
- Bundled + hub-installed skills are OFF-LIMITS to the LLM pass (`tools/skill_usage.py`: `off_limits = bundled | hub_installed`) — it only marks them stale/reactivates; only agent-created skills get consolidated.
- **Pinned = off-limits to BOTH writers.** `hermes curator pin <name>` skips lifecycle transitions and the autonomous background-review pass; only a foreground user edit can change a pinned skill. Details: `agent-skills-architecture/references/store-writers-curator-and-pins.md`.

## Skill-library & memory hygiene (agent-created skills only)
- Split agent-created vs bundled BEFORE opining on cleanup: agent-created = on disk under `$HERMES_HOME/skills` minus `<install>/skills/` (join the two glob lists). Bundled skills are re-seeded by sync — never propose touching them.
- `.usage.json` and `skills.disabled` can both name skills that no longer exist — harmless dead state (check frontmatter `name:` before calling a config entry stale).

## Plugins / platforms / channels + dashboard toggles
- `plugins.enabled` = opt-in allow-list, **`plugins.disabled` = the REAL deny-list** ("never load, even if in enabled"). Bundled `platform`/`backend` plugins auto-load regardless, so a dashboard "enable" only appends a name (cosmetic for bundled) while "disable" is real. Confirm runtime truth in `gateway_state.json`, never the dashboard.
- Disabling `telegram-platform` stops the bot polling — flag that before advising it. Restricting what a platform may do is a different lever: `platform_toolsets.<platform>` (absent = implicit fallback to the platform default composite = ALL standard tools; clicking enable FREEZES an explicit list).
- Home Assistant is BOTH a platform adapter (WebSocket event bus in, persistent notifications out) AND the `ha_*` toolset (core, gated on `HASS_TOKEN`).
- Web search backend is separate from the plugin toggle: `web.search_backend: ''` = auto → the provider whose key is in `.env` wins; change with `hermes config set web.search_backend <name>`.
- **Bundled ≠ catalog, and there is usually nothing to clean up.** Everything shipped reports `Source: bundled`; `hermes plugins list` has THREE statuses: `enabled`, `disabled` (explicit deny, wins over enabled) and `not enabled` (inert, no weight). Never propose a cleanup pass over bundled plugins.
- **Bundled plugins cannot be removed** (`hermes plugins remove` resolves names under `$HERMES_HOME/plugins/` only). Hand-deleting from `<install>/plugins/` is undone by `hermes update` and can strip LIVE capability: several kinds (e.g. `plugins/model-providers/*`) are found by directory scan and are NOT gated by `plugins.enabled`.
- Code quotes, plugin kinds, per-platform toolset internals, web backends, the bundled-vs-catalog boundary, the three statuses, removal rules and the documented way to digest the docs catalog page: `references/plugins-platforms-channels.md`.

## Config audit checklist (what goes stale across upgrades)
- `agent.max_turns`: an explicit old value silently caps runs (default moved 90 → 500 in v0.20.0) — compare against `hermes_cli/config_defaults.py`, the source of truth for current defaults.
- `approvals.mode: manual` = the user opted OUT of v0.19+'s smart-approvals default.
- `dashboard.basic_auth` / `oauth` empty = dashboard open if exposed (fine behind HA Supervisor).
- `config.yaml.bak.*` / `config.yaml.corrupt.*.bak` = historical corruption events; report, no action.

## Log triage
- **Attribute the log to a surface before diagnosing, and lead with the defect.** A pasted log is not necessarily from the install you are running in: two add-ons can share one `HERMES_HOME` with different run scripts, ports and banners. Name the add-on (and its slug) in the FIRST line, then the chain with each link marked verified (log / code / disk) vs inferred, then the remedy — and name any probe that approval-blocked instead of dropping it from the answer.
- `logs/gateway-exit-diag.log`: `SystemExit` code 75 = NORMAL scheduled restart (update), not a crash.
- `logs/gateway.log*`: Telegram "polling conflict … only one bot instance" = TWO gateways ran at once → "ensure only one gateway runs". DNS / `httpx.ReadError` with "fallback IP" is transient/self-healing — mention, no action.
- `plugins/<name>/` holding only state files is normal for a bundled dashboard plugin (code lives in `<install>/plugins/`).
- Source-update failures, the `/dev/null` patched-home class and a dead `/dashboard/` (`connection refused`): `references/addon-boot-log-triage.md`.

## Pitfalls
- `skills_list` ≠ on-disk inventory: a session shows only ACTIVE skills. Glob `**/SKILL.md` for the real set — EXCLUDING `.archive/`, whose archived skills still match and inflate the count — then subtract `skills.disabled` and frontmatter `platforms:` gating (`platforms: [macos]` is excluded on Linux). For a "how many skills do I have" question, count per tier (`find <dir> -name SKILL.md` per tier, plus the `.bundled_manifest` line count) and report the tiers separately; a single number for the whole box is always wrong because bundled, agent-authored, `external_dirs` and repo-local sets overlap.
- A stale `.bundled_manifest` (older addon build) makes `hermes skills list-modified` OVER-REPORT — harmless when installed content matches the latest repo; prove it with the recursive diff sweep.
- Missing bundled skills are NOT corruption (see sync rules) — never report "broken" for a respected deletion.
- `reset --restore` on a skill that DOES carry user content destroys that content — read the diff first.
- `hermes plugins info <name>` → "not found" does NOT prove absence: kind-specific discovery (`plugins/model-providers/*`, `dashboard_auth/*`) is invisible to the general plugin scanner, so a live, active plugin reads as missing. Open the kind directory's `plugin.yaml` before calling an entry in `plugins.enabled` stale or dead.
- **Prove absence against a CONTROL, never from one probe's silence.** Put a known-good input in every multi-item absence check (dir entries, hostnames, skills before declaring one missing) and name the control in the report.
- **A missing `make` / `hermes` / `npx` is the CONTAINER, not a broken install.** One Hermes brain runs in two HA add-on containers over the same `/config`, and a session can be served by EITHER. Check `hostname` first — `<slug>-hermes-agent` is the agent container; the webui side has no Node.js and no `make` by design, and its Hermes CLI fails the dependency preflight (`no dependency environment is committed for this install; run hermes pm repair`).

## References
- `references/storage-and-cache-map.md` — where add-on space goes, probe recipe
- `references/update-lifecycle.md` — `hermes update` phases, markers, checks
- `references/addon-boot-log-triage.md` — boot-log attribution and failure signatures
- `references/skill-loading-resolution.md` — loading chain, root resolution, probes
- `references/release-history.md` — release-body recipe, working URLs
- `references/plugins-platforms-channels.md` — plugin/platform/channel taxonomy and rules
- `references/skills-sync-and-bundling.md` — sync semantics, sweep one-liner, delete vs disable
- `scripts/check_bundled_manifest.py` — read-only manifest probe

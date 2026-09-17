---
name: hermes-instance-audit
description: "Audit a live Hermes install: skills, plugins, config."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, audit, skills, plugins, platforms, channels, config, versions, curator, sync, read-only]
    related_skills: [hermes-agent, hermes-addon-troubleshooting, agent-skills-architecture]
---

# Hermes Instance Audit (read-only)

Answer "what do we have / is anything wrong / how does it compare upstream" about a live Hermes
Agent installation without changing it. Read-only unless the user explicitly asks for a change.

## When to use
- "Check what we have in terms of skills, plugins and more" · "is anything wrong with my Hermes"
- "Compare it with the latest version / release" · "did they remove the default installed stuff"
- "Where did skill X go / why is it disabled / can I get deleted skills back"
- "Why does the dashboard say X" · "why is context at X% / do these tools eat too much"
- Not for installing, vendoring, merging or wiring skills → `agent-skills-architecture`.

## Hard rules
- **Read-only**: `read_file`, `search_files`, `web_extract`. Never edit `config.yaml` (only `hermes config set`), never run a sync by hand, never restore a skill without an explicit go-ahead. The deliverable of an audit is the EXPLANATION — what exists, what it does, what (if anything) needs doing — and **"nothing needs doing" is a valid, expected answer**. Do not close with install/enable/cleanup pitches or a menu of optional upgrades: he reads an unrequested proposal as a defect in the answer, and only wants options when he asks for them.
- **Approval gate**: with `approvals.mode: manual`, `terminal`/`execute_code` calls can sit at the consent gate and time out (BLOCKED). An audit is doable on file tools + read-only plain-shell one-liners: single `mkdir`/`cp`/`tar`/`find`/`diff`/`md5sum`/`grep` lines pass, while `execute_code`, `python -c`, heredocs and multi-line loops/scripts time out even when read-only (verified 2026-08). Keep shell work to one-liners; do the rest with file tools. **Never retry a blocked call** — report it and let the user say "prompt me again"; when he does, re-issue the SAME call, which then runs (the gate was the problem, not the call). Never reach the same outcome through a substitute tool in the meantime.
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
- Release bodies: working URLs, the escaped-JSON pitfall, the version↔tag↔date map and the keywords to grep → `references/release-history.md`.

## Commands to advise, never run unasked
- `hermes skills list [--enabled-only|--source all|--source local]` · `hermes skills inspect <name>` · `hermes skills diff <name>` · `hermes skills config` · `hermes skills uninstall <name>` (hub) · `hermes skills snapshot export <file>` · `hermes skills opt-out [--remove]` · `hermes skills trust [path]` · `hermes config set <key> <value>` · `hermes mcp list` · `claude plugin list`.
- `hermes skills reset <name>` = un-mark user-modified so updates apply again; `hermes skills reset <name> --restore` = ALSO deletes the local copy and re-seeds current stock (the fix for STALE stock — it destroys user content if there was any). Reset is per-skill: there is no global reset.
- Restore a deleted bundled skill: `hermes skills reset <name>` + `hermes update`, or copy the dir from `<install>/skills/`. Optional skills: `hermes skills repair-official <name> --restore` (backs up first). Nothing blocks re-seeding unless `.curator_suppressed` exists.

## Skills: what's on disk vs what actually loads
- Four tiers: builtin + local (`~/.hermes/skills/**`) + hub are the only ones `hermes skills list` shows. `external_dirs` and `trusted_project_dirs` are **never listed** — absence from that output proves nothing about them.
- Decisive probe: `hermes skills inspect <name>` ("No skill named 'x' found in any source" = out of scope). `hermes skills list --source local` checks a shared dir; run `inspect` from the repo root to test repo-local loading.
- `hermes config check` validates NOTHING about skill dirs: a non-existent entry is skipped SILENTLY, forever. Audit form: `ls -d <every entry>`, then re-point at the container-valid `/config/...` form.
- `external_dirs` = global load list (every session's index, name+description lines only); `trusted_project_dirs` = a per-repo permission, one exact path per repo, enumerating only the current root, so N repos cost nothing until a session is rooted in one. Always-on → the one shared deployed dir; repo-scoped → trust. Never accumulate per-repo `external_dirs` lines.
- A trusted repo that still loads nothing is ROOT RESOLUTION, not trust: root = nearest `.git` ancestor of the *surface* cwd (`TERMINAL_CWD` / `terminal.cwd` — a global value overrides the session's own cwd: upstream defect, fix in review), one root per session, fixed at session start, exact-path match, no globs.
- **The agent cannot write `config.yaml`** (the write tool refuses: "use 'hermes config'") and `hermes config set` takes ONE key + value with unverified list semantics → hand the user the exact copy-paste block: **only the fenced YAML, no preamble and no per-line explanation** (he interrogates the reasoning afterwards if he wants it), plus the post-edit proof (`hermes skills list --source local | grep -c '<known-shared-skill>'`, `hermes skills inspect <name>` from the repo). Skills load at session start — a corrected dir takes effect in the NEXT session; never claim immediate effect.
- Full chain, root-resolution internals, upstream issue/PR handles, probes and the working config block: `references/skill-loading-resolution.md`.

## Skills sync rules (manifest-based; restore is always safe)
- **NEW** (not in manifest) → copied, hash recorded — but a skill shipped for the first time is NEVER written over a
  same-named local skill: the sync keeps yours, warns "bundled version shipped but you already have a local skill by
  this name", and baselines the manifest only when the two are byte-identical (otherwise the local copy reads as
  user-modified forever). Adopting the bundled version takes a deliberate `hermes skills reset <name>`. **EXISTING** → bundled unchanged: skip; bundled changed + user copy untouched: safe update; bundled changed + user copy differs: **user customized → SKIP** (forever, so upstream improvements never arrive — refresh deliberately). **DELETED by user** (in manifest, absent on disk) → respected, never re-added. **REMOVED from bundled** → cleaned from the manifest.
- Missing bundled skills are therefore NOT corruption → report "removed on your side". User deletions and curator prunes look identical on disk: disambiguate with `.curator_suppressed` + `.curator_backups/<ts>/manifest.json` (curator `prune_builtins: true` CAN prune bundled skills after `stale_after_days`) and by asking the user.
- **Manifest hashes are DIRECTORY hashes** (rel-path + bytes over every file; sync prefers the sha256 `_content_digest` over the md5 `_dir_hash`). Never compare `md5sum SKILL.md` — it reports EVERY bundled skill as user-modified. Run `scripts/check_bundled_manifest.py` (tries both algorithms, classifies CURRENT / USER-MODIFIED / USER-DELETED / UPSTREAM-CHANGED).
- **DIFFERS ≠ user-modified**: read the direction (`hermes skills diff <name>`) — STALE stock (older baked copy, no custom content → `reset --restore`) vs USER-MODIFIED (keep; sync protects it).
- Content sweep one-liner (the truth for stale-vs-modified), `_dir_hash` semantics and the verified 2026-08 baseline: `references/skills-sync-and-bundling.md` + `references/2026-08-28-install-snapshot.md`.
- Delete vs disable: both cost ~0 at runtime. Disable is reversible, keeps edits and stays visible to the agent; delete is invisible (nothing proposes reinstalling a skill it cannot see) and needs a manual restore — and a restored bundled skill comes back ACTIVE (prompt weight) unless also in `skills.disabled`. Recommend disable unless the goal is prompt-size reduction.

## Curator behaviour (changed by version!)
- v0.16+: prunes stale skills by default (`stale_after_days`, `archive_after_days`), weekly (`interval_hours: 168`); LLM consolidation OFF unless `curator.consolidate: true` (= no aux-model spend).
- Bundled + hub-installed skills are OFF-LIMITS to the LLM pass (`tools/skill_usage.py`: `off_limits = bundled | hub_installed`) — it only marks them stale/reactivates; only agent-created skills get consolidated.
- **Pinned = off-limits to BOTH writers.** `hermes curator pin <name>` (state in `.usage.json`) also skips lifecycle
  transitions (`if row.get("pinned") … continue` in `agent/curator.py`) and the autonomous background-review pass,
  whose protected list names pinned skills with content updates included — only a foreground user edit can change one.
  That is the answer to "what if Hermes edits skills I deploy from git?": pin the deployed names, and pair it with the
  copy-only deploy rule (one-way, deletes nothing) in `agent-skills-architecture`.
- `prune_builtins: true` → the curator CAN delete bundled skills → the prime suspect for "missing bundled skills".

## Skill-library & memory hygiene (agent-created skills only)
- Split agent-created vs bundled BEFORE opining on cleanup: agent-created = on disk under `$HERMES_HOME/skills` minus `<install>/skills/` (join the two glob lists). Bundled skills are re-seeded by sync — never propose touching them.
- **The same topic living in two skills is a defect, not redundancy**: duplicates mean neither triggers reliably and the next patch lands in only one. Sweep by comparing descriptions + line counts across the tree, then MERGE into one skill and keep the depth in that skill's `references/`.
- A self-improvement round can CREATE the duplication it was meant to fix (one topic landing in two skills' `references/` in a single run) — after any auto-patch round, re-check the patched topics for a second home before adding more.
- Which survivor a merged topic belongs to is decided by the JOB, not by history (diagnostics/probes → the audit skill; organization/installation → the architecture skill). Then repoint every inbound reference (`grep -rn '<old-name>'`) so nothing dangles, and archive the losers before deleting them (`.curator_backups` is weekly; a manual tarball is immediate).
- **Merge procedure (verified end-to-end).** (1) Read both skills in full and pick the survivor by JOB, not by which one is newer. (2) `tar czf ~/.hermes/archive/skills-<topic>.tar.gz -C $HERMES_HOME/skills <loser dirs, plus any file you will drop>` — the archive goes OUTSIDE the skills tree, where nothing indexes it. (3) Copy the loser's `references/` + `scripts/` files that are pure content across with a `cp` one-liner; rewrite only the files whose CONTENT actually merges. (4) Rewrite the survivor's SKILL.md in ONE `skill_manage` patch (content alone replaces the file, so it must carry the full frontmatter) and fold every unique rule in — nothing may be dropped, and a rule that belongs to a DIFFERENT skill moves there and leaves a pointer behind. (5) Dedupe references by TOPIC: when both skills carried the same topic, merge the text into ONE file and `remove_file` the other — and sweep the files you are MOVING for near-duplicates too (two release-history files, two loading-recipe files): the pairs the user flags are only the ones he noticed, and a moved-in file that duplicates one already in the survivor leaves the original defect in place. (6) Delete each loser with `skill_manage(action='delete')` — a sole op, one call per skill. (7) Verify with `search_files` for the old names across every skill root: 0 hits in visible files is a pass, and `.curator_ledger.jsonl` still matching is CORRECT (history, not a live pointer). Never verify skill edits with a shell loop — multi-line scripts time out at the approval gate.
- Memory has a hard character budget checked on the FINAL result → consolidate as ONE batch (removes + replaces + adds together always fit) and merge rules stated twice. Report the delta in chars, not a promise to clean up.
- `.usage.json` and `skills.disabled` can both name skills that no longer exist — harmless dead state (check frontmatter `name:` before calling a config entry stale).

## Plugins / platforms / channels + dashboard toggles
- **Plugin** = extension unit (`hermes_cli/plugins.py`; kinds `standalone`, `backend`, `exclusive`, `platform`, `model-provider`). **Platform** = messaging adapter (`plugins/platforms/<name>/plugin.yaml`; 22 shipped incl. telegram, homeassistant). **Channel** = a destination on a platform (`channel_directory.json`).
- `plugins.enabled` = opt-in allow-list, **`plugins.disabled` = the REAL deny-list** ("never load, even if in enabled"). Bundled `platform`/`backend` plugins auto-load regardless, so a dashboard "enable" only appends a name (cosmetic for bundled) while "disable" is real. Confirm runtime truth in `gateway_state.json`, never the dashboard.
- Disabling `telegram-platform` stops the bot polling — flag that before advising it. Restricting what a platform may do is a different lever: `platform_toolsets.<platform>` (absent = implicit fallback to the platform default composite = ALL standard tools; clicking enable FREEZES an explicit list).
- Home Assistant is BOTH a platform adapter (WebSocket event bus in, persistent notifications out) AND the `ha_*` toolset (core, gated on `HASS_TOKEN`).
- Web search backend is separate from the plugin toggle: `web.search_backend: ''` = auto → the provider whose key is in `.env` wins; change with `hermes config set web.search_backend <name>`.
- **Bundled ≠ catalog, and there is usually nothing to clean up.** Everything shipped reports `Source: bundled`; the curated catalog is the install-only channel for OUT-OF-TREE plugins (`hermes plugins install`, SHA-pinned, landing in `$HERMES_HOME/plugins/`) and contains none of them — name overlap with a bundled plugin is coincidence, never identity. `hermes plugins list` has THREE statuses: `enabled`, `disabled` (explicit deny, wins over enabled) and `not enabled` (opt-in default = off, i.e. inert: no tools registered, no hooks fired, no context/schema weight). "What do I do with the plugins I don't use?" → nothing; never propose deleting bundled plugin files or a cleanup pass over them.
- **Bundled plugins cannot be removed.** `hermes plugins remove` resolves names under `$HERMES_HOME/plugins/` only and says so in its own error text ("bundled ones can only be enabled or disabled"). Hand-deleting files from `<install>/plugins/` is undone by `hermes update` and can strip LIVE capability, because several kinds are found by directory scan and are NOT gated by `plugins.enabled` — `plugins/model-providers/*` among them, so `hermes plugins info deepseek-provider` answers "not found" while that provider is active and real.
- Code quotes, plugin kinds, per-platform toolset internals, web backends, the bundled-vs-catalog boundary, the three statuses, removal rules and the documented way to digest the docs catalog page: `references/plugins-platforms-channels.md`.

## Context-usage & token diagnostics
- Point the user at `/context` (alias `/ctx`, sub `all`) and `/usage` BEFORE source archaeology — both are gateway-side and the agent cannot run them itself.
- The gauge is context_used/context_max, NOT % of the model window; a short session is relatively dominated by tool_definitions, which is normal. `/usage`'s `Total: N` is CUMULATIVE — read the `Context: X / Y (Z%)` line.
- Reduction levers (take effect on `/reset`, never mid-conversation — prompt-cache invariant): `agent.disabled_toolsets`, an explicit `platform_toolsets.<platform>` list, `tools.tool_search`. Enabled plugins ≈ zero schema weight unless their `plugin.yaml` kind registers tools (`ctx.register_tool`).
- Detail: `references/context-usage-diagnostics.md`.

## Config audit checklist (what goes stale across upgrades)
- `agent.max_turns`: an explicit old value silently caps runs (default moved 90 → 500 in v0.20.0) — compare against `hermes_cli/config_defaults.py`, the source of truth for current defaults.
- `approvals.mode: manual` = the user opted OUT of v0.19+'s smart-approvals default.
- `dashboard.basic_auth` / `oauth` empty = dashboard open if exposed (fine behind HA Supervisor).
- `config.yaml.bak.*` / `config.yaml.corrupt.*.bak` = historical corruption events; report, no action.
- Missing bundled skills + `prune_builtins: true` → deletion or curator (restore path above).

## Log triage
- `logs/gateway-exit-diag.log`: `SystemExit` code 75 = NORMAL scheduled restart (update), not a crash.
- `logs/gateway.log*`: Telegram "polling conflict … only one bot instance" = TWO gateways ran at once → "ensure only one gateway runs". DNS / `httpx.ReadError` with "fallback IP" is transient/self-healing — mention, no action.
- `plugins/<name>/` holding only state files is normal for a bundled dashboard plugin (code lives in `<install>/plugins/`).

## Pitfalls
- `skills_list` ≠ on-disk inventory: a session shows only ACTIVE skills (an audited install: 53 listed vs 90 on disk). Glob `**/SKILL.md` for the real set — EXCLUDING `.archive/`, whose archived skills still match and inflate the count (52 live vs 63 with archives on an audited install) — then subtract `skills.disabled` and frontmatter `platforms:` gating (`platforms: [macos]` is excluded on Linux). For a "how many skills do I have" question, count per tier (`find <dir> -name SKILL.md` per tier, plus the `.bundled_manifest` line count) and report the tiers separately; a single number for the whole box is always wrong because bundled, agent-authored, `external_dirs` and repo-local sets overlap.
- A stale `.bundled_manifest` (older addon build) makes `hermes skills list-modified` OVER-REPORT — harmless when installed content matches the latest repo; prove it with the recursive diff sweep.
- Missing bundled skills are NOT corruption (see sync rules) — never report "broken" for a respected deletion.
- `reset --restore` on a skill that DOES carry user content destroys that content — read the diff first.
- `hermes plugins info <name>` → "not found" does NOT prove absence: kind-specific discovery (`plugins/model-providers/*`, `dashboard_auth/*`) is invisible to the general plugin scanner, so a live, active plugin reads as missing. Open the kind directory's `plugin.yaml` before calling an entry in `plugins.enabled` stale or dead.
- **Prove absence against a CONTROL, never from one probe's silence.** A check that returns the same negative for items known to work is a broken probe, not a finding: a `dig`/`getent` sweep returned nothing for EVERY hostname including the live ones, while the same sweep using `curl -s -o /dev/null -m 10 -w '%{http_code} %{exitcode}'` with one known-good entry as the control answered properly (a routing error for the dead entry, normal responses for the live ones). Put a known-good input in every multi-item absence check — dir entries, hostnames, skills before declaring one missing — and name the control in the report.

## References
- `references/skill-loading-resolution.md` — the full loading chain (own store → `external_dirs` → project), root resolution + exact-path trust semantics, decisive probes, upstream issue/PR handles, the working config block, and the `/config` vs `/addon_configs` path duality.
- `references/release-history.md` — version↔tag↔date map, skills/plugin debloat, default-behaviour changes per release, plus the recipe and pitfalls for pulling release bodies.
- `references/context-usage-diagnostics.md` — context breakdown internals, slash commands, tool-schema composition and reduction levers.
- `references/plugins-platforms-channels.md` — plugin/platform/channel taxonomy, `plugins.enabled` vs `disabled` with code quotes, bundled-vs-catalog boundary, the three list statuses, removal rules, kind-specific discovery, web backends, per-platform toolsets, audited snapshot.
- `references/skills-sync-and-bundling.md` — `skills_sync` manifest semantics, repo layout, curator off-limits rule.
- `references/2026-08-28-install-snapshot.md` — verified baseline of THIS install (v0.20.6): 82 bundled → 70 identical / 10 user-deleted / 2 differing, 37 extras, curator + usage counts, the content-sweep one-liner, delete-vs-disable guidance, Claude Code CLI state.
- `scripts/check_bundled_manifest.py` — read-only probe reproducing the real hash algorithms and classifying every bundled skill.

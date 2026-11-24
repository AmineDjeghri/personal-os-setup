# Inventory — key paths (`~/.hermes` = `$HERMES_HOME`)

| Path                                              | Meaning                                                                                                                  |
|---------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `skills/.bundled_manifest`                        | `name:hash` of every bundled skill synced from `<install>/skills/` (v2)                                                  |
| `skills/.usage.json`                              | per-skill `use_count`, `state` (active/stale), `created_by` ("agent" = agent-created)                                    |
| `skills/.curator_state` / `.curator_ledger.jsonl` | last curator run summary / per-patch audit trail (actor, action, skill, evidence session)                                |
| `skills/.curator_backups/<ts>/`                   | weekly pre-run snapshots (`manifest.json` + `skills.tar.gz`)                                                             |
| `skills/.curator_suppressed`                      | curator-banned builtins — sync will NOT re-seed these (absent = nothing blocked)                                         |
| `.no-bundled-skills`                              | opt-out marker (installer `--no-skills`); absent = seeding active                                                        |
| `config.yaml`                                     | protected: `skills.disabled`, `plugins.enabled/disabled`, `platform_toolsets`, `approvals`, `curator`, `agent.max_turns` |
| `.update_check`                                   | `{ver, behind}` — `behind: 0` = up to date                                                                               |
| `channel_directory.json` / `gateway_state.json`   | registered channels / live platform states + gateway pid                                                                 |
| `plugins/`                                        | USER plugins only — bundled plugin code lives in `<install>/plugins/` (state-only leftovers are cleanable)               |
| `hermes-agent/`                                   | the git checkout: version in `pyproject.toml`, tags under `.git/refs/tags/`                                              |

- The repo ships TWO skill zones: `<install>/skills/` (bundled, manifest-synced on install/update) and `<install>/optional-skills/` (100+, on demand, never synced). Bundled plugins load from `<install>/plugins/` and are ADDED, not removed, by upgrades.
- Upstream "debloats" by MOVING skills bundled → optional-skills, never by silently deleting → "they removed the default stuff" is usually relocation.

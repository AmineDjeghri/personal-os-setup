# Config audit checklist, log triage and library hygiene

## Skill-library & memory hygiene (agent-created skills only)
- Split agent-created vs bundled BEFORE opining on cleanup: agent-created = on disk under `$HERMES_HOME/skills` minus `<install>/skills/` (join the two glob lists). Bundled skills are re-seeded by sync — never propose touching them.
- `.usage.json` and `skills.disabled` can both name skills that no longer exist — harmless dead state (check frontmatter `name:` before calling a config entry stale).

## Config audit checklist (what goes stale across upgrades)
- `agent.max_turns`: an explicit old value silently caps runs — compare against `hermes_cli/config_defaults.py`, the source of truth for current defaults.
- `approvals.mode: manual` = the user opted OUT of the smart-approvals default.
- `dashboard.basic_auth` / `oauth` empty = dashboard open if exposed (fine behind HA Supervisor).
- `config.yaml.bak.*` / `config.yaml.corrupt.*.bak` = historical corruption events; report, no action.

## Log triage
- **Attribute the log to a surface before diagnosing, and lead with the defect.** A pasted log is not necessarily from the install you are running in: two add-ons can share one `HERMES_HOME` with different run scripts, ports and banners. Name the add-on (and its slug) in the FIRST line, then the chain with each link marked verified (log / code / disk) vs inferred, then the remedy — and name any probe that approval-blocked instead of dropping it from the answer.
- `logs/gateway-exit-diag.log`: `SystemExit` code 75 = NORMAL scheduled restart (update), not a crash.
- `logs/gateway.log*`: Telegram "polling conflict … only one bot instance" = TWO gateways ran at once → "ensure only one gateway runs". DNS / `httpx.ReadError` with "fallback IP" is transient/self-healing — mention, no action.
- `plugins/<name>/` holding only state files is normal for a bundled dashboard plugin (code lives in `<install>/plugins/`).
- Source-update failures, the `/dev/null` patched-home class and a dead `/dashboard/` (`connection refused`): `addon-boot-log-triage.md`.

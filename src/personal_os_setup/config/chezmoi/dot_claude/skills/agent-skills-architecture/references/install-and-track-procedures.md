# Installing skills and plugins — the Track 1 and Track 2 procedures

Detail for the 2-track decision rule in `SKILL.md` (which tier something belongs in, and never hand-copy a
Track-2 suite into Track 1 — it fights its own updater).

## Track 1 — vendor a skill into the shared dir

1. Branch off `main` in personal-os-setup (`feature/*`), PR → `main`; a `docs(...)` commit triggers no release.
2. Fetch small: `git clone --depth 1 --filter=blob:none --sparse <owner/repo> /tmp/src && git -C /tmp/src sparse-checkout set <path>`.
3. Copy the whole skill folder — including its `LICENSE` — into the chezmoi source dir above.
4. Deploy live in the same step: copy the folder to `/config/.claude/skills/<name>/` so both agents pick it up
   immediately; keep live == repo.
5. Add the name to `skills.keep` (`make skills-keep NAME=<name>` does copy + list). AGENTS.md no longer enumerates skills; it is
   agent-protected: the edit approval often times out unattended → the write comes back BLOCKED. Stop and have
   the user say "prompt me again" to re-fire the exact patch; never retry it via another path.
6. Pre-commit rejects vendored content in up to three rounds — fix all before committing: ruff-format rewrites
   the foreign Python (fail-by-design → re-add + recommit); ruff lint then flags D415 (vendored docstrings lack
   a terminal `.`; no auto-fix); detect-secrets flags SRI/base64 attributes such as `integrity="sha384-…"` on
   vendored HTML → inline `<!-- pragma: allowlist secret -->` on the flagged line (never whole-file excludes).
   A hook-aborted commit leaves HEAD unchanged with changes still staged — confirm with `git log --oneline -1` +
   `git status`, never trust the truncated hook tail.

## Track 2 — install a Claude Code plugin

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

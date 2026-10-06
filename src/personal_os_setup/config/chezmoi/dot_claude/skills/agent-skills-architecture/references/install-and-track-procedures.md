# Installing plugins and plugin-skill bundles

Detail for the plugin-install lines in `SKILL.md` § Governance: plugin packs use that harness's own channel,
one canal per pack per agent.

## Install a Claude Code plugin

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
  stays clean.
- **Never point Hermes at a Claude plugin's cached subtree**
  (`~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/skills`) — the version segment changes on every
  plugin update and old versions are swept.
- Invoke claude WITHOUT `--bare` when plugins must load — bare mode skips plugins and skills.
- Never commit plugin-install state (marketplace registrations, `~/.claude/plugins/`, `known_marketplaces.json`) —
  machine-local, re-registered per machine.

## A vendor bundle that ships BOTH skills and MCP servers

Some vendors publish one bundle for several agents (e.g. `cloudflare/skills` is simultaneously a Claude plugin
marketplace and a plain `skills/<name>/SKILL.md` tree). Give each agent its NATIVE mechanism — two sources of
the same skill name confuse the model:

- **Claude Code** → the plugin (`plugin marketplace add` + `plugin install`). The vendor's plugin manifest can
  carry its MCP server too (`.claude-plugin/plugin.json` → `mcpServers`), so nothing else is needed that side.
- **Hermes** → the skills CLI (`vercel-labs/skills`, npm package `skills`):
  `npx -y skills add <owner>/<repo> -s <skill> -a claude-code -g -y --copy`. `-a claude-code` already reaches Hermes
  (it reads `~/.claude/skills`); never add `-a hermes-agent` (two roots Hermes reads → ambiguous names);
  `-a claude-code -a codex` is safe, never `-a '*'`. If the plugin already serves Claude, expect the skills twice —
  one canal per pack per agent. Destination is chosen by agent + scope alone — no `--dir` flag.
- **Hermes MCP servers** → `hermes mcp add <name> --url <url> --auth oauth`, the `trust: untrusted` write gate,
  and scoped tokens over account-wide OAuth.

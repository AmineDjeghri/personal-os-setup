---
name: cloudflare-agents
description: Use when installing, updating, or troubleshooting the Cloudflare agent integration (skills + the remote MCP server) for Claude Code and Hermes — "wire cloudflare for the agents", "why is cloudflare prompting for approval", "scoped token instead of OAuth".
---

# Cloudflare agent integration (Track 2 — tool = truth)

`make agents-cloudflare` wires the Cloudflare skills and the remote Cloudflare MCP server for
whichever agents are installed. Nothing here is vendored into Track 1 (`dot_claude/skills`), and
`make skills-deploy` never touches it.

```bash
make agents-cloudflare           # both agents; skips any CLI that is not on PATH
make agents-cloudflare-claude    # Claude Code only
make agents-cloudflare-hermes    # Hermes only
make agents-cloudflare-update    # refresh skills + plugin
```

Override binaries when they are off `PATH`: `make agents-cloudflare CLAUDE=/path/claude HERMES=/path/hermes`.

## Where each piece comes from

| Agent | Skills | MCP server |
|---|---|---|
| Claude Code | the `cloudflare` marketplace plugin | bundled in that plugin's manifest |
| Hermes | `npx skills add cloudflare/skills` → one canonical copy in `~/.agents/skills`, symlinked into `$HERMES_HOME/skills` | `hermes mcp add cloudflare --url https://mcp.cloudflare.com/mcp --auth oauth` |

Claude deliberately gets **no** CLI symlinks: two sources of the same skill name confuse it.

## The approval gate (the point of the whole setup)

Nobody mutates a Cloudflare zone without an explicit yes.

- **Hermes:** the entry must carry `trust: untrusted`; every tool without a `readOnlyHint: true`
  annotation then routes through the approval surface. Check the generated entry after `hermes mcp add`.
- **Claude Code:** prompts per call by default; pin it with `permissions` rules on `mcp__cloudflare__*`
  in `~/.claude/settings.json`.
- See what is wired: `claude plugin list`, `hermes mcp list`.

## Prefer a scoped token over OAuth

OAuth grants the whole account. For least privilege, replace `auth: oauth` with a bearer header:

```yaml
mcp_servers:
  cloudflare:
    url: "https://mcp.cloudflare.com/mcp"
    headers:
      Authorization: "Bearer <account-scoped-token>"
    trust: untrusted
```

Cloudflare requires `Account Resources : Read` on that token (so the server can auto-detect the
account ID) and rejects tokens with "Client IP Address Filtering" enabled. **Never commit a token file.**

## Traps

- Re-running `hermes mcp add cloudflare` prompts `Overwrite? [y/N]` and changes nothing — the target
  leaves an existing entry alone on purpose.
- Hermes builds MCP connections at **startup**: after an update run `hermes gateway restart`. Claude
  Code needs `/reload-plugins`. Skills are read at session start.
- Only skills/plugin need updating — the MCP server is remote, so its tool list is re-read on every
  connect (`make agents-cloudflare-update` is a no-op for it).

Upstream: <https://developers.cloudflare.com/agent-setup/> · <https://github.com/cloudflare/skills>

# Agent integrations (Track 2 — tool-managed)

Shared, version-controlled *recipes* for wiring third-party agent integrations. These install
upstream-owned, fast-moving content with the vendor's own tool — nothing here is vendored into
`dot_claude/skills` (Track 1), and `make skills-deploy` never touches it.

```bash
make agents-cloudflare            # whichever agents are installed on this machine
make agents-cloudflare-claude     # Claude Code only
make agents-cloudflare-hermes     # Hermes only
```

Nothing requires both agents: each target is independent, idempotent and **skips itself** when
its CLI isn't on `PATH` (a machine with only Claude Code installs only the plugin). Re-running
changes nothing — an already-registered MCP server is left untouched rather than re-added.
Override the binaries when they aren't on `PATH`: `make agents-cloudflare CLAUDE=/path/claude HERMES=/path/hermes`.

To see what is wired without the makefile: `claude plugin list`, `hermes mcp list`, and that
`mcp_servers.cloudflare` carries `trust: untrusted`.

## What `agents-cloudflare` installs

| Agent | Skills come from | MCP server comes from |
|---|---|---|
| Claude Code | the `cloudflare` plugin (marketplace `cloudflare/skills`) | the same plugin — its manifest bundles `cloudflare` → `https://mcp.cloudflare.com/mcp` |
| Hermes Agent | `npx skills add cloudflare/skills -g --agent hermes-agent` → symlinks in `$HERMES_HOME/skills` | `hermes mcp add cloudflare --url https://mcp.cloudflare.com/mcp --auth oauth` |

`npx skills` keeps one canonical copy in `~/.agents/skills` and symlinks it per agent
(`~/.claude/skills/…`, `~/.hermes/skills/…`). Claude is served by the plugin instead, so it is
deliberately **not** given the CLI symlinks — two sources of the same skill name confuse it.

Upstream reference: <https://developers.cloudflare.com/agent-setup/> · <https://github.com/cloudflare/skills>

## Approval model

Nobody may mutate a Cloudflare zone without an explicit yes:

- **Hermes** — the entry must carry `trust: untrusted`: every tool without a `readOnlyHint: true`
  annotation then goes through the approval surface. Verify the generated entry after
  `hermes mcp add`; the least-privilege block below shows its shape (swap `headers:` for
  `auth: oauth`).

- **Claude Code** — MCP tools prompt per call by default. To pin it, add the server to the
  `permissions` rules in `~/.claude/settings.json` (`mcp__cloudflare__*`) with `ask`/`deny`
  semantics for your Claude version.

The main server is **Code Mode**: 3 tools (`docs`, `search`, `execute`) rather than ~2,500
individual ones, so the context cost is negligible. Write capability rides inside `execute`.

## Updates & credentials

- **MCP server: nothing to update** — it's remote (`mcp.cloudflare.com`) and the tool list is
  re-read on every connect. Tokens refresh themselves (`hermes mcp reauth cloudflare` when one
  goes stale); they persist in `$HERMES_HOME/mcp-tokens/cloudflare.json` (Claude: `~/.claude/`, on
  first tool use) — **never commit either file**, they are full-account grants unless you use a
  scoped token.
- **Skills + plugin:** `make agents-cloudflare-update` (Hermes skills via `npx skills update -g -y`;
  Claude via `claude plugin marketplace update cloudflare` + `plugin install cloudflare@cloudflare`).
- **After updating:** Hermes builds MCP connections at **startup**, so `hermes gateway restart`;
  Claude Code needs `/reload-plugins`. Skills are read at session start.

## Least-privilege alternative

The main server also accepts an API token instead of OAuth — pass it as a bearer header and the
OAuth flow is skipped:

```yaml
mcp_servers:
  cloudflare:
    url: "https://mcp.cloudflare.com/mcp"
    headers:
      Authorization: "Bearer <account-scoped-token>"
    trust: untrusted
```

Requirements (Cloudflare docs): the account token needs `Account Resources : Read` so the server
can auto-detect the account ID, and tokens with "Client IP Address Filtering" enabled are not
supported. Prefer this when the agent should only touch DNS/WAF/Zero Trust and nothing else —
OAuth grants the whole account.

`docs.mcp.cloudflare.com/mcp` is a no-auth, read-only doc lookup if you ever want it; `bindings` /
`builds` / `observability` are Workers-only. To remove everything:
`claude plugin uninstall cloudflare@cloudflare`, `hermes mcp remove cloudflare`,
`npx -y skills remove --global --agent hermes-agent cloudflare`.

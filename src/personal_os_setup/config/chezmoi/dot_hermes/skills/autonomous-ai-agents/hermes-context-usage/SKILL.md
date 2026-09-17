---
name: hermes-context-usage
description: Use when explaining Hermes /ctx or /usage context reports.
---

# Hermes Context & Token Usage Interpretation

Use when the user asks "why is X% of my context used?", "are all these tools necessary?", or pastes `/usage` / `/ctx` output and wants it explained. Companion to the bundled `hermes-agent` skill (which owns slash-command registry).

## The two commands (both work in CLI and gateway/Telegram)

| Command | Shows |
|---|---|
| `/usage` | Token usage + rate limits (billing-oriented) |
| `/ctx` (alias `/context`, sub `all`) | Per-category breakdown + usage gauge: system prompt / tool definitions / subagent defs / memory / conversation |

**Both are gateway-side commands — the user must type them; the agent cannot invoke slash commands itself.** If the user can't run them, answer from code: `get_model_context_length(model, provider=...)` in `agent/model_metadata.py`, payload shape in `agent/context_breakdown.py`.

## Reading the numbers (verified on deepseek-v4-flash, 2026-08)

- **Breakdown percentages are shares of the CURRENTLY LOADED context** (they sum to ~100%), NOT shares of the context window. At session start conversation ≈ 0, so tool definitions dominate (~68–72%): normal, not a leak. As the conversation grows, the share dilutes (observed 20% at 51K used).
- The gauge line `Context: X / MAX (Y%)` is the true window fullness. Default compression threshold: 50%.
- **`/usage` "Total" is CUMULATIVE across all API calls** (≈ input-tokens × call count), not live context. Live usage is the `Context:` line above it.
- Tool schemas are a fixed block (~35 core tools ≈ 13K tokens ≈ **1.3% of a 1M window**). Every core tool ships on every API call by design ("narrow waist").
- Models with 1M context (deepseek-v4-flash, qwen3.x-max, minimax-m3, gemini) make tool overhead negligible; it only matters on small windows.

## Why the tool count is already trimmed

- Gated tools (`check_fn`) are stripped BEFORE the schema is sent: `kanban_*` (worker-only), `computer_use` (macOS), `bfl_flux3_*` (BFL creds), `browser_cdp`/`browser_dialog` (desktop). The visible ~35 tools are what you could actually use.
- **Plugins ≠ tools**: plugins CAN register tools (`ctx.register_tool`, e.g. spotify adds 7), but providers/platforms/backends (deepseek-provider, telegram-platform, web-tavily, disk-cleanup) add zero schema weight.
- **MCP tools** (`mcp_<server>_<tool>`) are discovered at gateway startup and registered for NEW sessions only — a session that started before the server connected won't see them until `/reset`. Toolset/schema changes NEVER apply mid-conversation (prompt-caching invariant).

## Levers to shrink the schema (if ever needed)

- `agent.disabled_toolsets` in config.yaml — disable whole toolsets (browser, image_gen, kanban…).
- `platform_toolsets` — per-platform tool lists.
- MCP `tools.include` allowlist — keep a curated subset (see `home-assistant-mcp` skill for the HA example: 87 → ~17 tools).
- All take effect on `/reset`, never mid-conversation.

## Pitfalls

- Don't claim "tools eat 68% of my window" — verify against `context_max` first; the breakdown % is share-of-loaded, and deepseek-v4-flash has a 1M window.
- For Hermes-behavior questions, check the `hermes-agent` skill's `references/slash-commands.md` BEFORE grepping source — the registry of record lives there.
- `/usage` ≠ `/ctx`: billing vs breakdown. Don't send the user to the wrong one.

## Related

- `home-assistant-mcp` — MCP server allowlist (context-bloat lever for HA).
- `hermes-addon-troubleshooting` — dashboard false "gateway not running" liveness diagnostics.

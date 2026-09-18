# Context-Usage Diagnostics (Hermes runtime)

Answers to "why is context at X%", "tools eat too much context", "can I shrink the tool schema".

## The user-facing answer: slash commands FIRST
The agent CANNOT run slash commands itself (gateway-side, user-triggered). When the user
asks about context/token usage, tell them to type one of these, or verify via source:

| Command | Shows | Availability |
|---|---|---|
| `/context` (alias `/ctx`, sub `all`) | Usage gauge + **category breakdown**: system_prompt, tool_definitions, conversation, mcp, subagent_definitions; compression stats; throughput | CLI + gateway (Telegram included) |
| `/usage` | Token usage + rate limits (billing/limits, NOT the breakdown); `reset` redeems banked Codex limit reset | CLI + gateway |
| `/status` | Session, model, token, context info | CLI + gateway |

Source of truth for command existence/scope: `hermes_cli/commands.py` `COMMAND_REGISTRY`
(flags: `cli_only=True`, `gateway_only=True`, aliases, subcommands). `/help` in-session is
always authoritative and derives from the same registry.

## How the breakdown is computed
- `agent/context_breakdown.py` → `compute_session_context_breakdown(agent)`.
- Categories built from `build_system_prompt_parts()` + agent.tools split into
  builtin / mcp / subagent (`delegate_task` is the only subagent tool name).
- Token estimates: `_json_tokens(tools)` (JSON dump / 4 heuristic); system prompt
  `_chars_to_tokens` (char/4).
- **`context_percent` = context_used / context_max**, where context_used =
  compressor `last_prompt_tokens` (measured) if > 0 else estimated_total, and
  context_max = compressor `context_length`. In a SHORT session the percent is
  dominated by the fixed overhead (system prompt + tool schema) — a 68% reading
  there is "tools+system are most of what's loaded", NOT 68% of the model window.
- Model window sizes live in `agent/model_metadata.py`: deepseek-v4-pro /
  deepseek-v4-flash = **1,000,000**; the `deepseek` substring fallback entry stays
  at 128K for older/unknown DeepSeek models. Honored: explicit `model.context_length`
  in config.yaml short-circuits probing (`model_tools.py::_resolve_active_context_length`).

## Tool schema composition (why it's big)
- `toolsets.py` `_HERMES_CORE_TOOLS` = the default bundle shared by CLI AND every
  messaging platform: web_search/extract, terminal+process, read_file/write_file/
  patch/search_files, vision+image_gen, bfl video gen (6 tools), skills_*,
  browser_* (12 tools incl. cdp/dialog/vision), tts, todo/memory/session_search/
  clarify, execute_code/delegate_task, cronjob, ha_* (4), kanban_* (9), computer_use.
- Platform composites (`hermes-telegram`, `hermes-homeassistant`, …) =
  `_HERMES_CORE_TOOLS + [platform extras]`. The `hermes-messaging` mega-composite
  includes ~22 platform bundles but each platform gets its own.
- Every core tool is sent on EVERY API call by design — the "narrow waist" rule in
  AGENTS.md: new core tools are the expensive exception; capability should land at
  the edges (service-gated check_fn, plugins, MCP).

## Reduction levers (all take effect on `/reset` — NEVER mid-conversation)
Prompt-caching invariant: changing toolsets/system prompt mid-conversation invalidates
the cached prefix. Tool changes land on the next session.
- `agent.disabled_toolsets` (was `[]` in this install) — disable whole toolsets.
- `platform_toolsets.<platform>` in config.yaml — explicit per-platform list. Absent
  entry = implicit fallback to the platform's default composite (ALL standard tools
  work). Adding an explicit list FREEZES it → future toolsets need manual opt-in.
  Use to RESTRICT a platform (e.g. drop browser/image_gen/kanban from telegram).
- `tools.tool_search` — `enabled: auto`, `threshold_pct: 10` — dynamic tool
  discovery settings.
- Tools themselves (gated via check_fn) can be hidden without config when their
  dependency is missing (e.g. computer_use needs cua-driver, ha_* needs HASS_TOKEN).

## This install (verified session values)
- config.yaml: `platform_toolsets` only defines `cli:`; `agent.disabled_toolsets: []`;
  model `deepseek-v4-flash` / provider deepseek; `toolsets: [hermes-cli]`.
- Config sections: `platform_toolsets.cli` = browser, clarify, code_execution,
  computer_use, cronjob, delegation, file, homeassistant, image_gen, kanban, memory,
  session_search, skills, terminal, todo, tts, vision, web; known_plugin_toolsets
  cli = spotify.

## Verified `/ctx` output (real session, deepseek-v4-flash)
Early-session reading: Context **51,308 / 1,000,000 (5%)**. Breakdown (estimated):
system prompt ~3,909 (6%), tool definitions ~12,778 (20%), subagent defs ~964 (2%),
memory ~878 (1%), conversation ~45,087 (71%). Percentages are shares of the 51K
LOADED, not of the 1M window (tool defs = 1.3% of window).

**The "68% at session start" phenomenon, proven:** with conversation ≈ 0, tool defs
share = 12,778 / (12,778 + 3,909 + 878 + 964) ≈ **69%** — matches what users report
seeing. As conversation grows, the share dilutes (20% at 45K conversation). It is
normal, not a leak.

**`/usage` Total trap:** `Total: 947,948` with 27 API calls is the CUMULATIVE token
sum across calls (~35K input × 27 ≈ 945K), NOT the current context. The real current
usage is the `Context: X / Y (Z%)` line. Don't alarm the user over the Total.

## Plugins vs tools (do plugins add schema weight?)
- Plugins CAN register tools via `ctx.register_tool(name, toolset=, schema=, handler=,
  check_fn=, emoji=)` — example: `plugins/spotify/__init__.py` registers 7 tools
  (spotify_playlists, spotify_albums, spotify_library, …) into the `spotify` toolset,
  gated on credentials via check_fn.
- BUT most plugins add ZERO tool definitions: model providers (deepseek-provider),
  platform adapters (telegram-platform, homeassistant-platform), web backends
  (web-tavily, `kind: backend` / provides_web_providers), and hook/command plugins
  (disk-cleanup registers hooks + a slash command, no tools).
- This install's 5 enabled plugins (deepseek-provider, disk-cleanup,
  homeassistant-platform, telegram-platform, web-tavily) register NO tools — verified
  by grepping each for `register_tool`. The `ha_*` tools in the schema come from
  `_HERMES_CORE_TOOLS` gated on HASS_TOKEN via check_fn, NOT from the
  homeassistant-platform plugin. So: enabled plugins add ~zero schema weight.
- Check a plugin's kind + registrations: `plugins/<name>/plugin.yaml` (`kind:`) and
  grep for `register_tool|register_hook|register_command` in its `__init__.py`.

## The schema you see is already pre-filtered
`_HERMES_CORE_TOOLS` lists ~60 tools, but the LIVE schema (what the model actually
receives, ~35 tools ≈ 12.8K tokens) is stripped by check_fn gates BEFORE sending:
kanban_* (10 tools, kanban workers only), computer_use (macOS cua-driver),
bfl_flux3_* (6 video tools, BFL creds), browser_cdp/browser_dialog (desktop-only).
So "35 tools in schema" vs "60+ in core list" is normal — the fat is already trimmed;
`agent.disabled_toolsets` would save only ~1% of a 1M window. When a user asks "are
all these tools necessary", show them what's already been gated out.

## Live context-window verification
`cd <install> && ./venv/bin/python -c "from agent.model_metadata import
get_model_context_length; print(get_model_context_length('<model>',
provider='<provider>'))"` → returns the resolved window (e.g. deepseek-v4-flash
via deepseek = 1,000,000, exact-match entry; `deepseek` substring fallback = 128K).
NOTE: `python -c` triggers the approval prompt — user must approve. Prefer asking
the user to run `/ctx` instead; source path alone (model_metadata.py exact-match
entry) is usually sufficient evidence.

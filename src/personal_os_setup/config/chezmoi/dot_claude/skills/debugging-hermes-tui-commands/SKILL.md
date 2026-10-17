---
name: debugging-hermes-tui-commands
description: "Debug Hermes TUI slash commands: Python, gateway, Ink UI."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    origin: repo:personal-os-setup
    tags: [debugging, hermes-agent, tui, slash-commands, typescript, python]
    related_skills: [python-debugpy, node-inspect-debugger, systematic-debugging]
---

# Debugging Hermes TUI Slash Commands

## Overview

Hermes slash commands span three layers — Python command registry, tui_gateway JSON-RPC bridge, and the Ink/TypeScript frontend. When a command misbehaves (missing from autocomplete, works in CLI but not TUI, config persists but UI doesn't update), the bug is almost always one layer being out of sync with another.

## When to Use

- A slash command exists in one part of the codebase but doesn't work fully
- A command needs to be added to both backend and frontend
- Command autocomplete isn't working for specific commands
- Command behavior is inconsistent between CLI and TUI
- A command persists config but doesn't apply live in the TUI

## Architecture Overview

```
Python backend (hermes_cli/commands.py)     <- canonical COMMAND_REGISTRY
       │
       ▼
TUI gateway (tui_gateway/server.py)         <- slash.exec / command.dispatch
       │
       ▼
TUI frontend (ui-tui/src/app/slash/)        <- local handlers + fallthrough
```

Command definitions must be registered consistently across Python and TypeScript to work properly. The Python `COMMAND_REGISTRY` is the source of truth for: CLI dispatch, gateway help, Telegram BotCommand menu, Slack subcommand map, and autocomplete data shipped to Ink.

## Investigation Steps

1. **TUI frontend:** search for `/commandname` under `ui-tui/` (`*.ts`, `*.tsx`).
2. **TUI command definitions:** `ui-tui/src/app/slash/commands/core.ts`.
3. **Python backend:** `hermes_cli/commands.py` (`COMMAND_REGISTRY`, `CommandDef`).
4. **Gateway:** `tui_gateway/server.py` (`slash.exec` / `complete.slash`).

## Fix: Missing Command Autocomplete

If a command exists in the TUI but doesn't show in autocomplete:

1. Add a `CommandDef` entry to `COMMAND_REGISTRY` in `hermes_cli/commands.py`:
   ```python
   CommandDef("commandname", "Description of the command", "Session",
              cli_only=True, aliases=("alias",),
              args_hint="[arg1|arg2|arg3]",
              subcommands=("arg1", "arg2", "arg3")),
   ```

2. Pick `cli_only` vs gateway availability carefully:
   - `cli_only=True` — only in the interactive CLI/TUI
   - `gateway_only=True` — only in messaging platforms
   - neither — available everywhere
   - `gateway_config_gate="display.foo"` — config-gated availability in the gateway

3. Ensure `subcommands` matches the expected tab-completion options shown by the TUI.

4. If the command runs server-side, add a handler in `HermesCLI.process_command()` in `cli.py`.

5. For gateway-available commands, add an `if canonical == "commandname":` handler in `gateway/run.py`.

## Common Issues

1. **Command shows in TUI but not in autocomplete.** The command is defined in the TUI codebase but missing from `COMMAND_REGISTRY` in `hermes_cli/commands.py`. Autocomplete data ships from Python.

2. **Command shows in autocomplete but doesn't work.** Check the command handler in `tui_gateway/server.py` and the frontend handler in `ui-tui/src/app/createSlashHandler.ts`. If the command is local-only in Ink, it must be handled in `app.tsx` built-in branch; otherwise it falls through to `slash.exec` and must have a Python handler.

3. **Command behavior differs between CLI and TUI.** The command might have different implementations. Check both `cli.py::process_command` and the TUI's local handler. Local TUI handlers take precedence over gateway dispatch.

4. **Command persists config but doesn't apply live.** For TUI-local commands, `config.set` is not enough — also `patchUiState(...)` and thread the new state through every render path: live `StreamingAssistant`/`ToolTrail` and transcript/pending `MessageLine` rows (a `/clean` pass should check both).

5. **Gateway dispatch silently ignores the command.** The gateway only dispatches commands it knows about. Check `GATEWAY_KNOWN_COMMANDS` (derived from `COMMAND_REGISTRY` automatically) includes the canonical name. If the command is `cli_only` with a `gateway_config_gate`, verify the gated config value is truthy.

## Debugging Tactics

When surface-level inspection doesn't reveal the bug:

- **Python side hangs or misbehaves:** use the `python-debugpy` skill to break inside `_SlashWorker.exec` or the command handler. `remote-pdb` set at the handler entry is the fastest path.
- **Ink side not reacting:** use the `node-inspect-debugger` skill to break in `app.tsx`'s slash dispatch or the local command branch. `sb('dist/app.js', <line>)` after `npm run build`.
- **Registry mismatch / unclear which side is wrong:** compare the canonical `COMMAND_REGISTRY` entry against the TUI's local command list side-by-side.

## Verification

After fixing (run in the hermes-agent checkout):

- Rebuild and launch: `npm --prefix ui-tui run build`, then `hermes --tui`.
- Type `/` and verify the command appears in autocomplete with the expected description and args hint; execute it and confirm the behavior fires, any persisted config updates (`~/.hermes/config.yaml`) and live UI state changes immediately (not just after restart).
- If the command is also gateway-available, test it from at least one messaging platform (or run the gateway tests: `scripts/run_tests.sh tests/gateway/`).

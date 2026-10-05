# Plugins, Platforms, Channels — taxonomy & dashboard semantics (verified v0.20.0)

## Taxonomy
- **Plugin** = generic extension unit. Registry: `hermes_cli/plugins.py`. Kinds (`_VALID_PLUGIN_KINDS`):
  `standalone` (own hooks/tools, opt-in via `plugins.enabled`), `backend` (pluggable backend for a core tool, e.g. image_gen / web search), `exclusive` (category with one active provider, e.g. memory), `platform` (gateway messaging adapter), `model-provider`.
- **Platform** = gateway messaging adapter — `plugin.yaml` with `kind: platform` under `<repo>/plugins/platforms/<name>/`. 22 shipped: telegram, discord, slack, whatsapp, teams, sms, simplex, raft, photon, ntfy, mattermost, matrix, line, irc, homeassistant, google_chat, feishu, email, dingtalk, buzz, wecom, a2a.
- **Channel** = a conversation destination ON a platform. `~/.hermes/channel_directory.json`:
  `{"platforms": {"telegram": [{"id": "<chat-id>", "name": "<user>", "type": "dm", "thread_id": null}], "homeassistant": []}}`.
  Home channels = default delivery targets for cron/scheduled messages.
- **Runtime truth**: `~/.hermes/gateway_state.json` → `{"platforms": {"telegram": {"state": "connected"}, "homeassistant": {"state": "connected"}, "api_server": {"state": "disconnected"}}}`. Never trust the dashboard's enable state — read this file.

## Home Assistant dual role
- Platform adapter `plugins/platforms/homeassistant/plugin.yaml`: requires `HASS_TOKEN`, optional `HASS_URL` (default `http://homeassistant.local:8123`). Subscribes to HA's WebSocket event bus, forwards state-change events (per-entity cooldowns, domain/entity filtering) to the agent; outbound messages delivered as HA persistent notifications via REST; out-of-process cron delivery via `notify.notify`.
- Toolset: `ha_call_service`, `ha_get_state`, `ha_list_entities`, `ha_list_services` — the agent controls HA independently of the messaging channel (e.g. from Telegram).

## `plugins.enabled` vs `plugins.disabled` (hermes_cli/plugins.py docstrings)
- `enabled`: "Plugins are opt-in by default — only plugins whose name appears in this set are loaded." Key missing/malformed → `None` = "nothing enabled yet"; first `migrate_config` populates it with a grandfathered set of currently-installed USER plugins.
- `disabled`: "A plugin name in this set will never load, even if it appears in `plugins.enabled`." → the REAL off switch.
- Bundled platform/backend plugins: "Bundled platform plugins auto-load so every shipped platform is available out of the box; user-installed platform plugins in `~/.hermes/plugins/` still gated by `plugins.enabled` (untrusted code)." Same rule for `backend` kind.
- Observed dashboard behavior: "enable" appends the plugin name to `plugins.enabled` ONLY (config diff = +1 line; `platform_toolsets` and `web.search_backend` untouched). For bundled plugins this is cosmetic — they were already loading. "disable" either removes from `enabled` (no-op for bundled) or writes `plugins.disabled` (real off). After a user clicks, read `config.yaml` `plugins:` blocks to say which happened.
- Real-world consequence: disable `telegram-platform` via `plugins.disabled` → adapter never loads → no polling → user loses the bot. Flag this before advising.

## Web search backends (tavily, etc.)
- `plugins/web/<name>/plugin.yaml`, `kind: backend`, `provides_web_providers: [tavily]` etc. Seven providers in the "Web Search & Extract" picker (`hermes_cli/tools_config.py`): tavily, brave-free, ddgs, exa, firecrawl, parallel, searxng.
- `web.search_backend: ''` = auto → the provider whose API key is present in `.env` wins (e.g. `TAVILY_API_KEY` → tavily active). Change via `hermes config set web.search_backend <name>` or the picker — not the plugin toggle.
- Tavily is the only bundled provider with crawl (search + extract + crawl per its description).

## Per-platform toolsets
- `platform_toolsets.<platform>` absent from config → fallback to the platform default composite: `_get_platform_tools()` in `hermes_cli/tools_config.py` → `toolset_names = [default_ts]` (`hermes-<platform>`), i.e. ALL standard tools active.
- An explicit saved list (from `hermes tools` or one dashboard toggle) FREEZES the platform's set — toolsets shipped later are not inherited except `_RECENTLY_SHIPPED_TOOLSETS` (comment in tools_config.py: "everyone still on [hermes-cli] inherits it on upgrade").
- This is the lever to restrict what the bot can do on a platform (e.g. no terminal on Telegram) — distinct from the plugin toggle.

## Audit snapshot (2026-08-05, v0.20.0, HA-addon install)
- `plugins.enabled` after user's dashboard clicks: `[deepseek-provider, disk-cleanup, homeassistant-platform, telegram-platform, web-tavily]`; `plugins.disabled`: `[fal, google_meet, openai]`.
- `gateway_state.json`: telegram + homeassistant connected; api_server disconnected (normal for the HA-addon layout).
- `channel_directory.json`: telegram = 1 DM ("<user>", <chat-id>); homeassistant = [] (adapter connected, no channel registered yet).
- `web.search_backend` left `''` by the tavily "enable" click (auto-selection unchanged).

## Bundled vs catalog — two unrelated universes
- **Bundled** = shipped with the install, code in `<install>/plugins/`, `Source: bundled` in `hermes plugins list`. Enable/disable only; they are ADDED, never removed, by upgrades.
- **Catalog** = the only out-of-tree distribution channel: one YAML per entry under `plugin-catalog/` in the repo, 40-hex commit SHA pin mandatory, published by the docs build as `/docs/api/plugin-catalog.json` and browsable at `<docs>/docs/plugins`. It is INSTALL-ONLY — not a source of anything already on the box, and not an uninstall list. `removed.yaml` is the kill list (every install path refuses a match; only the CLI's loud `--allow-removed` overrides).
- `hermes plugins install <name|owner/repo|git-url>` lands the repo in `$HERMES_HOME/plugins/`; portable Agent Plugins v1 packages install DISABLED (a deliberate second step is required to activate). `update` re-pins to the entry's current SHA, so it is not a branch track.
- Catalog CLI: `list|ls`, `search <kw>`, `browse`, `show|info <name>` (incl. emits/listens), `install`, `update`, `remove|rm|uninstall`, `enable|disable`, `capabilities`, `doctor`, `compat`, `pack` (declarative, shareable plugin sets via `hermes-pack.yaml`).
- Answering "do I already have this?": read `Source` per row. A catalog entry never replaces, conflicts with or shadows a bundled plugin of a similar name — different directory, different key.

## Status model in `hermes plugins list`
- `enabled` = named in `plugins.enabled`. `disabled` = named in `plugins.disabled` (explicit deny, wins over enabled). `not enabled` = in neither list — the opt-in default, i.e. OFF.
- A `not enabled` plugin is genuinely inert: no `ctx.register_tool`, no hooks, no tool-schema/context weight, no token cost. ~50 bundled plugins sitting in that state are NORMAL, not a backlog to resolve. `disable` on an already-off bundled plugin only pins the intent; it changes no behavior.
- Only plugins that register tools cost schema weight; `backend`/`exclusive`/provider kinds cost load time at most.

## Removal rules ("can I delete the ones I don't use?")
- `hermes plugins remove <name>` resolves only inside `$HERMES_HOME/plugins/` (downloaded plugins). A bundled name returns the CLI's own answer: *"This command only works on downloaded plugins; bundled ones can only be enabled or disabled."*
- Never hand-delete directories under `<install>/plugins/`: `hermes update` restores them, and the delete can remove live capability (next section).
- There is nothing to reclaim: a default-off bundled plugin occupies disk only. Deleting bundled plugin code buys zero runtime/context gains.

## Kind-specific discovery — NOT gated by the allow-list
- `plugins/model-providers/<name>/plugin.yaml` (`kind: model-provider`) is discovered by a directory scan (`providers/__init__.py._discover_providers()`, lazy, last-writer-wins) rather than by `plugins.enabled`; `dashboard_auth/*` and the other kind directories each have their own loader. Directory present = capability live.
- Consequently `hermes plugins info deepseek-provider` → "Plugin 'deepseek-provider' not found" even though `plugins/model-providers/deepseek/plugin.yaml` declares `name: deepseek-provider` and the provider is active and selectable. Before calling any `plugins.enabled` entry stale, check the kind directories (`model-providers/`, `platforms/`, `web/`, `image_gen/`, `video_gen/`, `memory/`, `context_engine/`, `cron_providers/`, `dashboard_auth/`) for its manifest.
- Verified on this install: `plugins.enabled` = `[deepseek-provider, disk-cleanup, homeassistant-platform, telegram-platform, web-tavily]` — the first is a model-provider manifest, invisible to the general scanner and unaffected by the config list.

## Digesting the docs catalog page
- `web_extract` on `<docs>/docs/plugins` returns the entire catalog as markdown (category `##` → entry `### <name>` → tier badge `✓ Official` / `❖ Community` → `★ N` → description → `N tools` / `N hooks`). The rendered page paginates and hides the middle; extraction does not. `hermes plugins search|browse` remains the authoritative local view.
- Parse each entry from its OWN heading block and take the FIRST `★ N` after it. A windowed regex (e.g. `lines[i:i+12]`) that keeps the LAST match attributes the NEXT entry's star count to the current one — that produced a 215★ reading for a 5★ plugin, quoted to the user as fact before the error was caught. Cross-check any figure you intend to repeat, and say so plainly when a number already given turns out wrong.

# Hermes Agent releases — comparison recipe

Cadence: ~weekly minors + infra patch tags whose notes roll into the next minor's body. Tags are calendar `vYYYY.M.D`; the release NAME carries the semver ("Hermes Agent v0.19.0 (2026.7.20)"). Local checkout tags: `<install>/.git/refs/tags/*`.

## Working URLs
- Latest release: `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest` (tag_name, name, published_at, body).
- One release by tag: `.../releases/tags/<tag>` — single JSON (~60-100KB); the `body` starts ~2KB in (after author/assets blobs), so web_extract's head slice covers the highlights.
- Full history: `.../releases?per_page=100` — ~900KB escaped JSON, last resort only.
- Human list: `https://github.com/NousResearch/hermes-agent/releases` — page 1 = 10 newest with `#release-<tag>` anchors and full bodies, `?page=N` for older; multi-line HTML → `search_files` with context works well.

## Pitfalls
- The web_extract-cached API JSON is ESCAPED (`\"`, `\_`, `\n`) → `json.loads` fails with "Invalid \escape". Treat it as text, never JSON.
- The `?per_page=100` cache file is ONE giant line: `read_file` cannot page it (`total_lines: 0`, no next_offset) and `search_files` returns the whole line as a single match. Do not try to page or grep it.

## What to grep in release bodies
The "important stuff" usually hides in the middle of the body: `optional-skills`, `debloat`, `bundled plugin`, `removed`, `deprecat`, `breaking`, `migration`, and `default` (silent behavior changes live there).

## Cross-check against the local install
- Always read the local tag/version FIRST (`.update_check`, `<install>/pyproject.toml`) — the install may already be current, and HEAD can be ahead of the newest tag.
- `hermes_cli/config_defaults.py` in the local checkout is the source of truth for CURRENT defaults (e.g. `agent.max_turns: 500`) — explicit old values in `config.yaml` override new defaults silently.

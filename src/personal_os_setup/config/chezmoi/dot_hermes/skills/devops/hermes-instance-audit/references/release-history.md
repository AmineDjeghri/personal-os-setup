# Hermes Agent releases — history + comparison recipe

Compiled from the GitHub releases API (Aug 2026; v0.20.0 = v2026.8.3 was the newest release then) and kept
current by re-running the recipe below. Cadence: ~weekly minors + infra patch tags whose notes roll into the
next minor's body. **This install has moved past the table's last row** (v0.20.6, checkout at tag
`v2026.8.27`+ at the 2026-08-28 audit) — extend the table from the recipe instead of trusting its end.

## Version ↔ tag ↔ date map
| Version | Tag | Date | Theme |
|---|---|---|---|
| 0.2.0 | v2026.3.12 | 2026-03-12 | — |
| 0.3.0 | v2026.3.17 | 2026-03-17 | — |
| 0.4.0 | v2026.3.23 | 2026-03-23 | — |
| 0.5.0 | v2026.3.28 | 2026-03-28 | — |
| 0.6.0 | v2026.3.30 | 2026-03-30 | — |
| 0.7.0 | v2026.4.3 | 2026-04-03 | — |
| 0.8.0 | v2026.4.8 | 2026-04-08 | — |
| 0.9.0 | v2026.4.13 | 2026-04-13 | — |
| 0.10.0 | v2026.4.16 | 2026-04-16 | — |
| 0.11.0 | v2026.4.23 | 2026-04-23 | — |
| 0.12.0 | v2026.4.30 | 2026-04-30 | — |
| 0.15.1 | v2026.5.29 | 2026-05-29 | Patch |
| 0.15.2 | v2026.5.29.2 | 2026-05-29 | Patch |
| 0.16.0 | v2026.6.5 | 2026-06-05 | The Surface Release |
| 0.17.0 | v2026.6.19 | 2026-06-19 | — |
| 0.18.0 | v2026.7.1 | 2026-07-01 | The Judgment Release |
| 0.18.1 | v2026.7.7 | 2026-07-07 | Patch (infra) |
| 0.18.2 | v2026.7.7.2 | 2026-07-07 | Patch (infra) |
| 0.19.0 | v2026.7.20 | 2026-07-20 | The Quicksilver Release |
| 0.19.1 | v2026.7.30 | 2026-07-30 | Patch (dashboard 401 fix etc.) |
| 0.20.0 | v2026.8.3 | 2026-08-03 | The Herald Release |

Tags are calendar `vYYYY.M.D`; the release NAME carries the semver ("Hermes Agent v0.19.0 (2026.7.20)").
Local checkout tags: `<install>/.git/refs/tags/*`. ~30 releases in 5 months.

## Working URLs
- Latest release: `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest` (tag_name, name, published_at, body).
- One release by tag: `.../releases/tags/<tag>` — single JSON (~60-100KB); the `body` starts ~2KB in (after author/assets blobs), so web_extract's head slice covers the highlights.
- Full history: `.../releases?per_page=100` — ~900KB escaped JSON, last resort only.
- Human list: `https://github.com/NousResearch/hermes-agent/releases` — page 1 = 10 newest with `#release-<tag>` anchors and full bodies, `?page=N` for older; multi-line HTML → `search_files` with context works well.

## Pitfalls (learned the hard way)
- The web_extract-cached API JSON is ESCAPED (`\"`, `\_`, `\n`) → `json.loads` fails with "Invalid \escape". Treat it as text, never JSON.
- The `?per_page=100` cache file is ONE giant line: `read_file` cannot page it (`total_lines: 0`, no next_offset) and `search_files` returns the whole line as a single match. Do not try to page or grep it.
- `execute_code` may be blocked by the approval gate mid-audit — the per-tag API and HTML-page paths need no code at all.

## What to grep in release bodies
The "important stuff" usually hides in the middle of the body: `optional-skills`, `debloat`, `bundled plugin`, `removed`, `deprecat`, `breaking`, `migration`, and `default` (silent behavior changes live there — see the two sections below).
- `optional-skills` / `debloat` — v0.20.0 moved yuanbao, segment-anything, jupyter, heartmula, audiocraft to optional-skills, removed the claude-marketplace source and restructured the hub.
- `bundled plugin` — bundled plugins are ADDED, not removed (v0.20.0: A2A v1.0).

## Skills/plugins changes across versions (the "debloat")
- **v0.15.1**: hub catalog 858 → 19,932 entries (skills.sh full sitemap).
- **v0.16.0 (Surface)**: curator cost optimization — prunes stale skills by default, LLM consolidation OFF unless `curator.consolidate: true`. Telegram rich text via Bot API 10.1 (on by default, opt-out).
- **v0.20.0 (Herald)**: official skills bundled (docx, xlsx, pdf + refreshed powerpoint) + debloat by relocation (yuanbao, segment-anything, jupyter, heartmula, audiocraft → optional-skills; claude-marketplace source removed; hub restructure absorbing themes/desktop-plugins/tui-widgets). New bundled plugin: A2A v1.0. New bundled skill: grounded-citations.
- Repo state at v0.20.0: `skills/` = 71 bundled (manifest-synced), `optional-skills/` = 111 on demand. So "they removed the default stuff" = debloat by relocation; the core bundle still ships and syncs.

## Default-behaviour changes that silently affect existing installs
- **v0.16.0**: curator prunes stale skills by default; Telegram rich messages (Bot API 10.1) on by default.
- **v0.19.0**: "smart approvals are now the default" — an LLM reviewer judges flagged commands instead of asking the user; user-defined deny rules + `/deny`; `approvals.mode: manual` opts out.
- **v0.19.0**: delivery-obligation ledger — finished replies survive gateway crashes (redelivered on next boot; closed a P1 silent-loss path for Telegram/Discord/Slack).
- **v0.20.0**: default tool-calling iteration limit 90 → 500 (`agent.max_turns`); an explicit old value in config.yaml silently keeps the old cap.

## Other notable per-version features
- **v0.18.0 (Judgment)**: verification evidence + completion contracts (`/goal`); `/learn` (turn a workflow into a skill); MoA ensemble reasoning display; desktop Projects (project → repo → lane); gateway scale-to-zero/drain.
- **v0.19.0 (Quicksilver)**: cold start ~4.3s → ~0.9s; reasoning streams live; `/subscription` + `/topup`; Bitwarden/1Password SecretSource; live subagent transcripts + durable background delegation; profile-based message routing (one bot token → several profiles).
- **v0.20.0 (Herald)**: streaming voice with barge-in + wake words; outbound signed webhooks (HMAC); desktop artifacts + plugin SDK; CLI `!command`, `/init`, `/diff`, `/context`, `/focus`; redirects (mid-turn correction); self-recovering tools.

## Cross-check against the local install
- Always read the local tag/version FIRST (`.update_check`, `<install>/pyproject.toml`) — the install may already be current, and HEAD can be ahead of the newest tag.
- `hermes_cli/config_defaults.py` in the local checkout is the source of truth for CURRENT defaults (e.g. `agent.max_turns: 500`) — explicit old values in `config.yaml` override new defaults silently.

# Skills sync semantics + audit snapshot (2026-08-05)

## skills_sync.py — manifest-based bundling (from tools/skills_sync.py docstring, v0.20.0)

Manifest: `~/.hermes/skills/.bundled_manifest`, format `skill_name:origin_hash` (MD5 of the bundled skill at last sync). v1 manifests (plain names) auto-migrate to v2.

Update logic:
- **NEW** (not in manifest): copied to user dir, hash recorded.
- **EXISTING** (in manifest, present): bundled still matches hash → skip; bundled changed + user copy untouched → safe update; bundled changed + user copy differs → **user customized, SKIP**.
- **DELETED by user** (in manifest, absent from user dir): **respected, never re-added**. ← explains "missing bundled skills"
- **REMOVED from bundled** (in manifest, gone from repo): cleaned from manifest.

Opt-out marker: `~/.hermes/.no-bundled-skills` (written by installer `--no-skills` or `hermes profile create --no-skills`). When present, sync is a no-op — delete the file to opt back in.

Bundled dir resolution: `HERMES_BUNDLED_SKILLS` env var first, else `<repo>/skills/` relative to the source file.

Curator interplay: bundled + hub-installed skills are off-limits to the curator (`tools/skill_usage.py` `off_limits = bundled | hub_installed`); it only marks stale/reactivates. User-deleted bundled skills are NOT re-added by sync.

## Repo layout (v0.20.0 = v2026.8.3, published 2026-08-03)

| Zone | Content | Synced to user dir? |
|---|---|---|
| `<repo>/skills/` | 71 bundled skills | Yes (manifest-based) |
| `<repo>/optional-skills/` | 111 optional skills | No (installed on demand) |
| `<repo>/plugins/` | ~17 bundled plugins (browser, context_engine, cron_providers, dashboard_auth, disk-cleanup, google_meet, hermes-achievements, image_gen, kanban, memory/*8 backends, model-providers, observability, platforms/*17, security-guidance, spotify, teams_pipeline, video_gen, web/*8 backends) | Loaded from repo; `~/.hermes/plugins/` is for user plugins |

## Audit snapshot — this user's instance (2026-08-05, before v2026.8.3 was known)

- Version: 0.20.0, `.update_check` `{"ver": "0.20.0", "behind": 0}` → up to date. Install is a git checkout at `~/.hermes/hermes-agent` (editable venv install, `__editable___hermes_agent_0_20_0_finder.py`).
- `.bundled_manifest`: 71 entries = repo `skills/` 71 SKILL.md → 1:1.
- On disk: 90 SKILL.md dirs; session `skills_list` showed only 53 active.
- 10 bundled but absent locally (user deletions, respected by sync): airtable, codex, huggingface-hub, llama-cpp, notion, openhue, powerpoint, teams-meeting-pipeline, touchdesigner-mcp, weights-and-biases.
- 32 skills disabled in `config.yaml` `skills.disabled` (incl. many bundled: architecture-diagram, ascii-*, blogwatcher, codex, comfyui, computer-use, design-md, evaluating-llms-harness, excalidraw, himalaya, humanizer, manim-video, opencode, p5js, polymarket, popular-web-designs, pretext, research-paper-writing, serving-llms-vllm, sketch, songsee, songwriting-and-ai-music, ...).
- ~29 on-disk skills NOT in manifest: optional-skills imports (godmode, obliteratus, subagent-driven-development, hermes-s6-container-supervision, pixel-art, heartmula, baoyu-*, creative-ideation, audiocraft...), hub/user-created (home-assistant-*, web-scraping, advanced-web-scraping, writing-plans, native-mcp, petdex, web-research, messaging-integration, webhook-subscriptions...).
- Plugins: `~/.hermes/plugins/` = only `hermes-achievements` (state files only — scan_checkpoint.json, scan_snapshot.json, state.json; code lives in repo plugins/hermes-achievements as a dashboard plugin). `config.yaml` `plugins.enabled: [deepseek-provider, disk-cleanup]`, `disabled: [fal, google_meet, openai]`.
- Platform gating: `apple-notes` etc. frontmatter `platforms: [macos]` → excluded on Linux.

## Upstream debloat evidence (release v0.20.0 body)

> "skills bundled: docx, xlsx, pdf + refreshed powerpoint; skills-tree debloat continues (yuanbao, segment-anything, jupyter, heartmula, audiocraft → optional-skills; claude-marketplace source removed; hub restructure absorbing themes/desktop-plugins/tui-widgets)"

Also new in v0.20.0: A2A v1.0 bundled plugin, Kanban plugin SDK, grounded-citations skill, signed outbound webhooks. So "they removed the default stuff" = debloat by relocation, not removal; the 71-skill core bundle still ships and syncs.

## Release-note grepping tip

GitHub release JSON via web_extract lands as ONE giant line in the cache file — `read_file`/grep by line fails. Use execute_code with `re.finditer` over the raw text and slice `[i-150:i+220]` for context.

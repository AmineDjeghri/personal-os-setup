---
name: youtube-download-automation
description: Use when downloading YouTube audio into the music library or driving yt-dlp. Plan first, confirm with the user, then download.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# YouTube Download Automation (yt-dlp)

## Trigger
Any task that drives **yt-dlp** — the YouTube → `/media/music` → Navidrome/beets pipeline below, playlist or single-link downloads, per-video metadata, chapter splitting, debugging the downloader script — and any change to the downloader script itself.

## 0. Gate — ask before you touch anything (MANDATORY)

This pipeline writes into the user's music library, and its script is a file in a repo. **Nothing downloads and nothing gets edited until the user has seen the proposal and answered.**

- **Check for an existing import BEFORE you plan.** Grep the video ID in `.archive.txt` and `overrides.json`, then look for the file under `/media/music/YouTube/`. Already imported → the reply is its verified state (library path + `ffprobe` tags), **not** a metadata proposal; only propose when something is genuinely missing or wrong. The plan's status column is not an archive check.
- **Say what governed the run, in one line.** Name this skill and what you did not do (no download / no edit / no git). The user asks "did you read the skill first?" whenever that isn't visible in the first reply to a dropped link.
- **Before a download — a single link included.** `--plan` first, then show the proposed metadata (`artist | title | album | year | genre | folder`) and ask for the go-ahead. There is no "small enough to skip the gate" case: a one-video link is exactly where a wrong `folder` or a guessed artist is cheapest to prevent and most annoying to undo.
- **Before editing `yt_dl.py`, the README or the overrides format.** Say what changes, why, and what it affects, then wait. A link that exposes a gap in the pipeline ("genre: rai" when nothing can write a genre) is a **proposal**, not a mandate to patch the pipeline.
- **Before deleting state.** `.archive.txt` and the library folder are what decide whether a re-run downloads or no-ops — warn explicitly, then confirm.
- **Before git.** commit / push / PR need explicit per-action approval (repo `AGENTS.md`); a download run never commits.
- **A timed-out approval prompt is not consent.** Stop; the user re-triggers it.

Asking costs one short message. Guessing wrong costs a re-download, a wrong tag in a 200-file library, or a repo change that has to be unwound.

## 1. The pipeline (concrete instance)

Project: `<personal-os-setup>/docs/home-server/music/youtube_ai_download/`.

- `yt_dl.py` carries a PEP 723 header → run it as **`uv run --no-project yt_dl.py …`** from that folder. `--no-project` is load-bearing: the folder sits inside a uv project, and bare `uv run` would bind to that project's env instead of the script's own deps.
- State lives next to the script: `.archive.txt` (downloaded video IDs), `.staging/` (download target, OUTSIDE the watched root), `overrides.json` (the metadata decisions), `downloads.log`. That folder's `README.md` is the **published** doc for the format and naming rules — no live/private specifics in it (no real add-on slugs, host paths, hostnames).
- Flow: ⓪ duplicate check — ID in `.archive.txt` / `overrides.json` / a file already under `/media/music/YouTube/` (a hit ends the task: report state, or propose only the specific defect) → ① `yt_dl.py --plan <url>` → ② the agent reads the plan and writes `overrides.json` (full map on first run, delta for new videos — the script parses nothing, the LLM is 100 % of the metadata decisions) → ③ **confirm with the user (§0)** → ④ `yt_dl.py <url> --overrides overrides.json [--max N] [--log downloads.log]` → ⑤ verify.
- Downloads land in `/media/music/YouTube/<folder>/NN - Artist - Title.m4a` with tags embedded by the script; the finished staging folder is moved into the library with one rename so the beets watcher imports it whole.
- Rate limits: ~1 s/request — a 50-video playlist takes minutes. Launch those with `background=true` + `notify_on_complete=true`, then report.

## 2. The metadata decisions (all of them are the agent's)

| Field | Rule |
|---|---|
| `artist` | The performer, not the channel — live-title channels are uploaders, not artists. |
| `title` | The original video title **minus channel noise only** (`[4K]`, `[Audio HQ]`, `HD`, `(Best Quality)`, `\| Channel`, a leading `Artist - `, a stray year). Never rewrite, never translate; keep `(Live …)` and venue info. |
| `album` | Typically `Live at <Venue> (<City>, <Year>)`. Navidrome's smart playlist collects `Album contains "Live"` — an album without "Live" silently drops out of it. |
| `year` | Concert year when it differs from the upload year. |
| `genre` | From the `"genre"` field in `overrides.json` (e.g. `"rai"`). With **no** genre override, **no genre tag is written at all** — the script neutralises the metadata PP's fallback chain, so YouTube's *category* ("People & Blogs", "Sports" — the values 211 files in the library used to carry) can never land in the tag again. Never hand-tag a file the pipeline owns. |
| `folder` | **Set it explicitly for a single-video link** — `playlist_title` defaults to the video's own title, so the documented `Singles` default rarely fires and you get a folder named after the video. Playlists: folder = playlist title. Non-music clips: `Other`. |
| `split` | `true` only for videos with YouTube chapters that should become tracks. |

- **Non-music clips (entrances, chants, interviews, fireworks…) are NEVER classified alone**: list them with a proposed handling and wait for the confirmation before setting `album`/`folder` to `Other`.
- A video the user labels by genre or occasion is a metadata hint, not permission to change the code that writes it.

## 3. Verify before reporting

- Files are under `/media/music/YouTube/…`, **not** left in `.staging/`; spot-check the embedded tags of one file (`ffprobe -v quiet -show_entries format_tags -of default=nw=1 <file>`), genre included when a genre was requested.
- The beets add-on log shows the import (`ha_get_logs` source=supervisor slug=`<beets add-on>`); without beets the files still reach Navidrome on its own scan.
- Report downloads and failures: failed/unavailable videos grouped by reason with counts + video IDs, never silently dropped, never invented.
- Archive file present after success; a re-run downloads only new videos.

## 4. References

- `references/yt-dlp-api-facts.md` — verified yt-dlp internals: PP key names, runtime `outtmpl` dict, `ignoreerrors`, chapter splitting, and which info-dict field feeds which tag.
- `references/pipeline-quirks.md` — archive/resume/re-download, filename collisions, plan-index quirks, override coverage checks.
- `references/chapter-split-duration-quirk.md` — the one cosmetic defect worth accepting as-is.
- `scripts/validate_overrides.py` — overrides-vs-plan coverage check (usage in the script docstring).

## 5. Where this skill lives

Canonical copy: `personal-os-setup/src/personal_os_setup/config/chezmoi/dot_claude/skills/youtube-download-automation/` (the one authored tree; deployed to `~/.claude/skills`, which Hermes also reads). Deploy with `make skills-deploy` in that repo, then `hermes curator pin <name>` — see the `skill-deployment` skill. Edits go through the repo's normal flow (delegate the file change; §0 git gate).

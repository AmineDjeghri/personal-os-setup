---
name: youtube-download-automation
description: Use when ingesting a music/YouTube link or playlist into the music library — what is new in it, genre sourcing, yt-dlp download. Plan first, confirm with the user, then download.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Music ingest & YouTube download (yt-dlp)

Drives the YouTube → music library → Navidrome/beets pipeline: playlist or single-link
downloads, per-video metadata, chapter splitting, and changes to the downloader script.
Also answers "what is new in this playlist?" (§4) and "which genre is this track?" (§2).

## 0. Gate — ask before you touch anything (MANDATORY)

This pipeline writes into the user's music library and its script is a repo file.
**Nothing downloads and nothing is edited until the user has seen the proposal and answered.**

1. **Check for an existing import first.** Grep the video ID in `.archive.txt` and `overrides.json`, then look for the file under the library. Already imported → reply with its verified state (path + `ffprobe` tags), not a metadata proposal. Propose only what is genuinely missing or wrong.
2. **Before any download — a single link included** — run `--plan`, show `artist | title | album | year | genre | folder`, and wait for the go-ahead. No "small enough to skip" case: a one-video link is where a wrong `folder` or guessed artist is cheapest to prevent.
3. **Before editing `yt_dl.py`, its README or the overrides format**, say what changes, why and what it affects, then wait. A link that exposes a pipeline gap is a proposal, not a mandate to patch it.
4. **Before deleting state** (`.archive.txt`, a library folder), warn that it decides whether a re-run downloads or no-ops, then confirm.
5. **Git:** commit/push/PR need explicit per-action approval (repo `AGENTS.md`). A download run never commits.
6. A timed-out prompt is not consent. Stop; the user re-triggers.

Close every reply with one line naming what governed the run and what you did *not* do (no download / no edit / no git).

## 1. The pipeline

Project: `<personal-os-setup>/docs/home-server/music/youtube_ai_download/`. Its `README.md` is the **published** format doc — no private specifics in it (host paths, hostnames, add-on slugs).

**Run it with `uv run --no-project yt_dl.py …` from that folder.** `--no-project` is load-bearing: the folder sits inside a uv project, and bare `uv run` would bind to that project's env instead of the script's PEP 723 deps.

| Path | Role |
|---|---|
| `.archive.txt` | downloaded video IDs; decides whether a re-run downloads or no-ops |
| `overrides.json` | the metadata decisions, keyed by video ID |
| `.staging/` | download target, gitignored, outside the watched library |
| `downloads.log` | optional `--log` output |
| `LIBRARY_ROOT` | **hard-coded `/media/music` in `yt_dl.py`** (no flag, no env var). Finished files land in `<LIBRARY_ROOT>/YouTube/<folder>/NN - Artist - Title.m4a`, tags embedded by the script, moved in with one rename so beets imports the folder whole |

**Where it runs matters.** `/media/music` exists on the media server / add-on container, not on a
dev workstation. Before any download run `ls -ld /media/music`. If it is missing the script still
downloads into `.staging/`, then fails at the final move (`PermissionError`) and leaves the files
staged — surface this at the gate and let the user choose (create the path, or a `--library-root`
change to `yt_dl.py`, itself a §0.3 proposal). Never `sudo mkdir` on your own.

**Flow:**

1. Duplicate check (§0.1).
2. `yt_dl.py --plan <url>` (read-only).
3. Write `overrides.json` (full map on first run, delta afterwards). The script parses nothing; the agent makes 100 % of the metadata decisions (§2).
4. `scripts/plan_tools.py coverage plan.txt overrides.json` must report no MISSING.
5. **Confirm with the user (§0.2).**
6. `yt_dl.py <url> --overrides overrides.json [--max N] [--log downloads.log]`. Smoke-test with `--max 1` first.
7. Verify (§5).

Rate limit is ~1 s/request, so a 50-video playlist takes minutes — run it in the background and report on completion.

## 2. Metadata decisions

| Field | Rule |
|---|---|
| `artist` | The performer, not the channel. Live-title channels are uploaders, not artists. |
| `title` | Original video title **minus channel noise only** (`[4K]`, `[Audio HQ]`, `HD`, `(Best Quality)`, `\| Channel`, a leading `Artist - `, a stray year). Never rewrite or translate; keep `(Live …)` and venue info. |
| `album` | Typically `Live at <Venue> (<City>, <Year>)`. Navidrome's smart playlist matches `Album contains "Live"` — an album without "Live" silently drops out of it. |
| `year` | Concert year when it differs from the upload year. |
| `genre` | Optional. Title Case, `;` separator with no space (`Rock;Pop`), mapped onto `references/genre-vocabulary.md`. **No override → no genre tag at all** (the script neutralises yt-dlp's category fallback). Never hand-tag a file the pipeline owns. Sourcing: `references/genre-sourcing.md`. |
| `folder` | Set it **explicitly for a single-video link** — `playlist_title` defaults to the video's own title, so the `Singles` default rarely fires. Playlists: folder = playlist title. Non-music clips: `Other`. |
| `split` | `true` only for videos with YouTube chapters that should become tracks. |

- **Non-music clips** (entrances, chants, interviews, fireworks…) are never classified alone: list them with a proposed handling and wait for confirmation before using `Other`.
- A video the user labels by genre or occasion is a metadata hint, not permission to change the code that writes it.

## 3. Genre

Propose a genre in the §0.2 table as a short choice (broad / precise / none). Source it with
`references/genre-sourcing.md`; format and allowed tokens are in `references/genre-vocabulary.md`.
Fixing genres on files *already in the library* is a different, bulk task: `references/genre-retag.md`.

## 4. What is new in this playlist (no download)

```bash
# from the pipeline folder
uv run --no-project yt_dl.py --plan <playlist-url> > plan.txt
python3 <skill>/scripts/plan_tools.py delta plan.txt .
```

Report only the delta and stop (§0 still applies). Treat an ID in `.archive.txt` **or** `overrides.json` as already handled — report its state, don't re-propose it. The script handles the traps below; treat a "0 new" on a non-trivial playlist as suspect.

- The plan index is right-aligned and space-padded (`[  1]`, `[  ?]` for a single video), so `^\[(\d+)\]` matches nothing and falsely reports "0 new".
- A hand-curated playlist can list one video twice: report duplicates apart, never as new.
- Unavailable/private videos are not items; the declared count exceeds the listed count by that number. Never count them as new or invent a replacement.
- If the library mount is absent, `.archive.txt` + `overrides.json` still decide the delta.
- When only some items are new, ingest by re-running the **same playlist URL** (the archive makes it incremental and keeps the playlist folder); a bare video URL makes `folder` default to the video's title.

## 5. Verify before reporting

- Files are under `<LIBRARY_ROOT>/YouTube/…`, **not** left in `.staging/`. Spot-check one file: `ffprobe -v quiet -show_entries format_tags -of default=nw=1 <file>` (genre included when one was requested).
- `.archive.txt` is updated; a re-run downloads only new videos.
- With beets installed, its log shows the import; without it, Navidrome picks the files up on its own scan.
- Report failed/unavailable videos grouped by reason, with counts and IDs — never silently dropped, never invented.

## 6. References

| File | Content |
|---|---|
| `references/pipeline-quirks.md` | archive/resume/re-download, filename collisions, plan-index quirks, ffmpeg passes |
| `references/yt-dlp-api-facts.md` | yt-dlp internals the script relies on: PP keys, runtime `outtmpl`, chapter splitting, info-dict → tag map |
| `references/genre-sourcing.md` | choosing a genre at ingest: sources, limits, matching guard |
| `references/genre-retag.md` | bulk genre fixes on existing files: writer ownership, `©gen` atoms, recount |
| `references/genre-vocabulary.md` | canonical token set, merge map, never-write list, 4-value cap |
| `references/genre-whitelist.txt`, `genre-whitelist-extra.txt` | lowercase whitelists (beets' list; regional/Spotify supplement). The skill owns them |
| `scripts/plan_tools.py` | `delta` (what is new) and `coverage` (overrides vs plan); shared parser, exits 2 on empty parse |

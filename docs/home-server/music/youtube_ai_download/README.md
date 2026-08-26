# youtube_ai_download

AI-assisted YouTube → music library pipeline. Downloads YouTube playlists (or single videos) as **audio-only m4a** into `/media/music/YouTube/<folder>/` with clean embedded metadata (tags are written by the script itself). An optional **beets addon** (if installed) adds last.fm genres, cover art and refreshes Navidrome. **No new addons, no extra containers.**

---

## The AI pipeline (why this is not a plain yt-dlp wrapper)

**Every metadata decision is made by the LLM agent, not by parsing rules.** Live YouTube titles are messy — `Artist - Song (Live at X)`, no-artist titles, artists mentioned only in the description, Arabic/French/English mixes. Regex heuristics get maybe 60–80% right; the LLM reads the actual title, uploader and description of every video and decides. The script is pure plumbing:

```
you paste a link
      │
      ▼
① PLAN      yt_dl.py --plan <url>      →  per-video: id, title, uploader,
      │                                    chapter count, description snippet.
      │                                    NO download.
      ▼
② LLM PASS  the agent reads the plan   →  writes overrides.json — the FULL
      │                                    metadata map (artist/title/album,
      │                                    folder for non-music clips)
      ▼
③ DOWNLOAD  yt_dl.py <url> --overrides →  audio-only m4a → staging dir → tags
      │     overrides.json                 embedded → folder atomically moved
      │                                    into /media/music/YouTube/
      ▼
④ BEETS     (optional) the addon's      →  last.fm genres, cover art, Navidrome
            watcher auto-imports           refresh; without it, files still appear
                                           on Navidrome's own scan schedule
```

**Why this shape:** the script stays simple (it's plumbing), the intelligence is explicit and reviewable (plan + overrides are visible *before* anything downloads), and every decision is versioned in the overrides file.

---

## Folder layout

```
youtube_ai_download/
├── yt_dl.py                  # the downloader — deps in its PEP 723 header
├── README.md                 # this file
├── overrides.json            # per-video LLM decisions (the "brain")
├── overrides.example.json    # template
├── skill/
│   └── yt-dlp-music-downloads/
│       └── SKILL.md          # Hermes runbook — symlinked into ~/.hermes/skills
├── .staging/                 # downloads land here first (created at run time)
├── .archive.txt              # downloaded video IDs — incremental state (not in git)
└── downloads.log             # tee'd run log (--log) — progress/resume debugging
```

## Install (nothing to install)

Dependencies live in the script itself (PEP 723 inline metadata — `# /// script` header with `requires-python = ">=3.11"` and `dependencies = ["yt-dlp", "mutagen"]`). `uv` builds a cached environment on first run (~1 min the first time, instant after). No `requirements.txt`, no manual venv.

Requires: a container/host with `/media` rw (the Hermes agent addon qualifies), `ffmpeg`, `uv`.

## Usage

```bash
cd /config/workspace/personal-os-setup/docs/home-server/music/youtube_ai_download

# 1. PLAN — review before downloading (id, title, uploader, description)
uv run --no-project yt_dl.py --plan "https://youtube.com/playlist?list=..."

# 2. LLM PASS — the agent reads the plan and writes overrides.json
#    (full map on first run, delta for new videos on updates)

# 3. DOWNLOAD (archive-driven: re-running a URL only fetches NEW videos;
#    --log tees all output to a file for progress/resume debugging)
uv run --no-project yt_dl.py "https://youtube.com/playlist?list=..." --overrides overrides.json --log downloads.log

# 4. (optional) Beets takes over automatically (~300s watch debounce); without
#    it, Navidrome picks the files up on its own scan schedule.
```

> **`--no-project` is important**: this folder may sit inside a uv project (personal-os-setup has its own `pyproject.toml`) — bare `uv run` would bind to that project's environment instead of the script's own deps.

Helpers: `--max N` (limit downloads, testing), `--urls-file file.txt` (many URLs, one per line), `--log FILE` (tee output to a log file). Interrupted runs resume: leftover `.staging/` files are moved into the library on the next start, and the archive skips already-done videos.

## Overrides — the whole decision layer

```json
{"VIDEO_ID": {
    "artist": "...",    // default: uploader
    "title":  "...",    // default: video title — original MINUS noise only
                        // ([4K]/HD/(Best Quality)/| Channel + artist prefix dropped;
                        // (Live…) and venue info kept, never rewritten)
    "album":  "...",    // default: playlist title
    "year":   "2018",   // optional: concert year (default: upload year)
    "folder": "Other",  // optional: download into YouTube/Other instead of the playlist folder
    "split":  true      // optional: video has YouTube chapters → split into per-chapter
                        // tracks (title = chapter name, track = section number)
}}
```

- Only the fields you set are applied; missing fields fall back to neutral defaults.
- **Non-music clips** (sport entrances, walkouts, chants) — always **validated with the user first**, then `"folder": "Other"` with the clip's subject as artist, so they stay out of the playlist folder and are easy to spot/delete.

## Naming rules (agreed)

| What | Rule |
|---|---|
| Folder | playlist title → `YouTube/<playlist>/`; single links → `YouTube/Singles/`; non-music → `YouTube/Other/` |
| File | `NN - Artist - Title.m4a` (NN = playlist position) |
| Chapter split | `"split": true` → `NN - Artist - Title - SS - <chapter>.m4a` per YouTube chapter (SS = section number = track number; title = chapter name); the full file is discarded |
| Artist / Title / Album | **decided by the LLM** in overrides.json |
| Title | original video title, **noise removed only** (no rewrites): `[4K]`/`[Audio HQ]`/`HD`/`(Best Quality)`/`| Channel` stripped, leading `Artist - ` dropped, `(Live…)` + venue info kept |
| Album | typically `Live at <Venue> (<City>, <Year>)` from the description |
| Format | audio-only, native m4a (AAC, YouTube's ceiling) — **never** re-encoded to "lossless" |

## Incremental playlist updates

`.archive.txt` remembers every downloaded video ID (persisted after **each** video, so an interrupted run never re-downloads). When you add videos to a playlist: add their overrides, re-run the same URL — only the new videos download, beets imports only those. **Never delete `.archive.txt`** (it's gitignored, but deleting it forces a full re-download — which is exactly what you want when starting over: delete the `YouTube/` folder AND `.archive.txt` together).

## Run output

The script ends with a readable summary: per-video `Artist - Title [Album] (folder/)`, then **the videos that couldn't be downloaded with the reason and count** (unavailable/private/age-restricted grouped by reason, with video IDs), and download-time failures.

## Known quirks

- **Chapter files carry the source's duration in the container header (moov)** — cosmetic: players use the stream duration (correct), only beets' internal DB length is off. Remuxing does **NOT** fix it (timestamps are preserved) — don't try. Re-encoding would, but at quality cost for zero benefit.
- **Sign-in-only videos** (private/age-restricted) can't download without YouTube cookies — they're skipped and reported. A `--cookies` option is a possible future addition.

## Navidrome

Downloads appear under **Artists** and as **"Live at …" albums** (album tag) — folders are invisible to Navidrome, no playlists are created. One smart playlist — rule **`Album contains "Live"`** — collects every live download automatically, including future ones. Non-music clips have album `Other` (excluded from that rule).

## The skill

The Hermes runbook (`skill/yt-dlp-music-downloads/SKILL.md`) is symlinked into the agent's skills folder, so it's the live procedure while the source of truth stays here, versioned with the code.

## Prerequisites / assumptions

- **(optional, recommended)** Beets addon watching `/media/music` — adds last.fm genres, cover art, and triggers Navidrome's rescan right after import. Without it the pipeline still works: tags are embedded by the script, and Navidrome picks up new files on its own scan schedule (and at startup).
- Downloads run where `/media` is reachable — this machine: the Hermes agent addon (mounts `/media` rw, has `ffmpeg` + `uv`)
- Live bootlegs won't match MusicBrainz — by design they keep the embedded tags; beets (if installed) adds last.fm genres

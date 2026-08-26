---
name: yt-dlp-music-downloads
description: Download YouTube playlists into the Navidrome music library.
---

# YouTube → Music Library (yt-dlp → Navidrome)

## Trigger
User pastes a YouTube playlist or video link (often live performances) and wants it in the music library, tagged.

## Environment (verified Aug 2026)
- Agent container mounts **/media rw** — the real music library (`/media/music` FLACs visible from inside the agent). `ffmpeg` at `/usr/bin/ffmpeg`, `uv` at `/usr/local/bin/uv`.
- Project: `/config/workspace/personal-os-setup/docs/home-server/music/youtube_ai_download/` — script `yt_dl.py` with a **PEP 723 `# /// script` header** (yt-dlp, mutagen; `requires-python >=3.11`; uv fetches a managed Python if needed). Run via **`uv run --no-project yt_dl.py`** from that folder. Archive `.archive.txt` and staging `.staging` (outside `/media/music` so beets never imports half-finished folders) live next to the script itself — overrides `overrides.json`. README.md explains the pipeline.
- Home: **personal-os-setup `docs/home-server/music/youtube_ai_download/`**; the skill file is symlinked into `~/.hermes/skills/media/` — edit the project file, not the symlink. NOTE: `skill_manage` refuses symlinked skills — patch the project file with the patch tool.
- **Metadata decisions are 100% LLM-made**: the script does NO title/description parsing — it is plumbing only. The plan output + overrides file are the entire decision layer.
- **(optional, recommended) beets addon** watches `/media/music` (inotify, 300s debounce): adds last.fm genres + cover art and triggers Navidrome's rescan. The script embeds all tags itself, so without beets the files still reach Navidrome on its own scan schedule. If beets IS used: live bootlegs don't match MusicBrainz → `quiet_fallback: asis` keeps the embedded tags; `import.copy/move: no` → **the download location IS the final location**.
- **Navidrome**: songs appear under Artists + "Live at …" albums (tag-driven; folders invisible). Offer the one-time smart playlist **`Album contains "Live"`** — it collects every live download automatically. `Other`-folder clips have album `Other` (excluded).

## Workflow
1. Clarify scope: whole playlist vs specific links.
2. **PLAN FIRST** (never download blind):
   `cd /config/workspace/personal-os-setup/docs/home-server/music/youtube_ai_download && uv run --no-project yt_dl.py --plan <url>`
   → per-video: index, id, title, **uploader**, **chapter count** (for split decisions), description snippet + a count of unavailable videos. No download.
3. **LLM PASS (100% of the decisions)**: read titles/descriptions/uploaders and write the overrides JSON — every video that should not use neutral defaults (artist=uploader, album=playlist title) gets an entry. First run = full map; playlist updates = delta (new videos only).
   **Titles: remove noise ONLY, never rewrite.** Strip: quality/source tags (`[4K]`, `[Audio HQ]`, `HD`, `(Best Quality)`, `4K`), trailing `| <Channel>` segments, and a leading `"Artist - "` segment when artist is set separately. Keep everything else verbatim — including `(Live…)` markers, venues, `feat.` info, `| Festival 2019`-style context. Non-music clips keep their descriptive title (noise rule only — no rewrites).
   **Non-music clips (sport entrances, walkouts, chants, fireworks, interviews…): NEVER classify them alone — present them to the user for validation first** (list titles + proposed handling). Only after the user confirms do you set `{"artist": "<subject of the clip>", "album": "Other", "folder": "Other"}` — artist = the SUBJECT (e.g. WWE, PSG, Lil Yachty), never the uploader; never skip outright.
4. **DOWNLOAD** (archive-driven — re-runs fetch only NEW videos):
   `uv run --no-project yt_dl.py <url> --overrides overrides.json [--max N] [--log downloads.log]`
   → m4a into `/media/music/YouTube/<folder>/NN - Artist - Title.m4a`, tags embedded (artist/title/album/track/year/thumbnail), mutagen pass verifies. Interrupted runs resume safely: leftover `.staging/` files are moved into the library at the next start (archive skips already-done videos).
5. **VERIFY**: files exist under `/media/music/YouTube/<folder>/` (NOT `.staging`); if the beets addon is installed, its log (`ha_get_logs` source=supervisor slug=ffaaaf16_beets) shows the import; report a readable per-video summary AND **the failed/unavailable videos with reasons + counts** (the script prints these); flag anything that fell to defaults.
6. **Playlist updates** (user added videos): add overrides for the new IDs, re-run step 4 with the same URL — archive skips existing, beets imports the new files only.

## Overrides format
```json
{"VIDEO_ID": {
    "artist": "...",    // default: uploader
    "title":  "...",    // default: video title — LLM sets it as original MINUS noise
                        // ([4K]/HD/(Best Quality)/| Channel + artist prefix dropped;
                        // (Live…) and venue info kept, never rewritten)
    "album":  "...",    // default: playlist title — typically "Live at <Venue> (<City>, <Year>)"
    "year":   "2018",   // optional: concert year (default: upload year)
    "folder": "Other",  // optional: download into YouTube/Other instead of the playlist folder
    "split":  true      // optional: video has YouTube chapters (plan shows the count) →
                        // split into per-chapter tracks (title = chapter name,
                        // track = section number); the full file is discarded
}}
```
Only provided fields are applied.

## Pitfalls
- **Always `uv run --no-project`** — once this folder lives inside personal-os-setup (a uv project with its own pyproject.toml), bare `uv run` binds to THAT project's env, not the script's PEP 723 deps.
- **Non-music classification requires user validation** — never decide alone to move a video to `Other`; the user's default expectation is that everything in the playlist is wanted. Propose, wait for confirmation, then apply.
- **100% LLM = full overrides on first run** — do not rely on neutral defaults for album quality ("Live at <venue>" albums require explicit overrides).
- **Rate limits**: script sleeps ~1s/request; 50-video playlists take minutes — run with `background=true` + `notify_on_complete=true`.
- **Mid-playlist insertions** shift `playlist_index` → new file gets the current index, existing files keep theirs (cosmetic duplicate track numbers; accepted).
- **No re-encoding**: native m4a (AAC ~128–160 kbps — YouTube ceiling). Never transcode to "lossless".
- **Staging is outside the watch root**; the final folder rename into `/media/music/YouTube/` triggers ONE clean import (single event burst, debounce batches).
- User's beets option `incremental: false` → re-imports may re-process folders on later events; harmless (same tags), do not "fix" without asking.
- **Chapter splits**: flag `"split": true` only when the plan shows chapters. Chapter files are named `NN - Artist - Title - SS - <chapter>.m4a` (SS = section number, becomes the track number; title = chapter name). The 2h full file is discarded after splitting.
- **Chapter moov quirk**: split files keep the SOURCE duration in the container header — cosmetic (players use the stream duration, which is correct). Remuxing does NOT fix it; do not try (re-encoding would, at quality cost — not worth it).
- **Sign-in-only videos** (private/age-restricted) are skipped; they'd need a yt-dlp cookies file (`--cookies`) — not implemented.
- **429s**: retries built in; archive prevents duplicates — never delete `.archive.txt`. **Fresh start** (user deleted `/media/music/YouTube` to re-download everything): the archive must ALSO be deleted, or the re-run skips all videos as "already downloaded".
- Same artist+title twice in a playlist (e.g. two live versions): yt-dlp's no-overwrites silently skips the second — the script detects it ("no file produced") and does NOT archive it, so the next run retries with a corrected title.

## Verification checklist
- [ ] plan output reviewed (agent + user)
- [ ] overrides written for all non-default videos
- [ ] **non-music clips validated with the user BEFORE download** → set to `Other` with subject-based artist
- [ ] downloads under `/media/music/YouTube/<folder>/` (not `.staging`)
- [ ] failed/unavailable videos reported with reasons + counts
- [ ] (if beets installed) its log shows the import completed
- [ ] readable summary reported to user

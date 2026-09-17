---
name: youtube-download-automation
description: Automate YouTube downloads via the yt-dlp library.
---

# YouTube Download Automation (yt-dlp library)

## Trigger
Building or debugging any script that drives **yt-dlp programmatically** (playlist downloads, per-video metadata overrides, custom naming/tagging, plan-then-download workflows). Concrete instance: the `yt-dlp-music-downloads` skill (music pipeline: YouTube → `/media/music` → beets) — see it for the full workflow; this skill carries the library-level facts.

## Verified API facts (yt-dlp, Aug 2026, Python 3.14, uv-managed)
- **Postprocessor keys have NO `PP` suffix.** `{"key": "FFmpegMetadataPP"}` crashes at `YoutubeDL.__init__` with `KeyError: 'FFmpegMetadataPPPP'` (get_postprocessor appends `PP`). Correct: `{"key": "FFmpegMetadata", "add_metadata": True}` and `{"key": "EmbedThumbnail"}`.
- **Mutating `ydl.params["outtmpl"]` at runtime requires a DICT, not a string.** yt-dlp normalizes a string outtmpl into `{'default': …}` only inside `__init__`. Assigning a raw string later makes `_prepare_filename` crash on EVERY entry with `AttributeError: 'str' object has no attribute 'get'` → 0 downloads, all entries reported failed. Fix: `ydl.params["outtmpl"] = {"default": str(path)}` per entry.
- **`ignoreerrors: True` is needed in BOTH metadata-only (plan) and download modes.** Without it, a single unavailable/private video aborts the ENTIRE playlist fetch (`ERROR: [youtube] <id>: Video unavailable`). With it, failed entries come through as `None` — skip them.
- **Per-video metadata before download**: mutate the extracted entry dict (`e["artist"]`, `e["title"]`, `e["album"]`, `e["track"]`, `e["album_artist"]`, `e["date"]`) then `ydl.process_ie_result(e, download=True)` — the outtmpl template and FFmpegMetadata PP pick up the overridden values. Archive keyed by video ID (`--download-archive` or a manual file) makes re-runs incremental.
- **Chapter splitting (`FFmpegSplitChapters`)** — verified against `yt_dlp/postprocessor/ffmpeg.py`:
  - The PP splits whenever `chapters` exists in the entry dict → include the PP globally and `e.pop("chapters", None)` for entries that must NOT split (one PP list is global; there is no per-entry gate).
  - Chapter file names come from `prepare_filename(info, 'chapter')` → the runtime outtmpl dict needs a `"chapter"` key: `{"default": …, "chapter": str(dir / "%(section_number)02d - %(section_title)s.%(ext)s")}` (fields `section_number`/`section_title`/`section_start`/`section_end` are set by the PP on a copy of the info dict).
  - The PP does **NOT** delete the original full file (`run()` returns `[], info`), and metadata PPs (FFmpegMetadata/EmbedThumbnail) run on `info['filepath']` — the ORIGINAL. So chapter files come out **untagged** and the full file lingers. Pattern: route the default outtmpl to a throwaway `_full/` subdir, delete it after processing, and tag each chapter file yourself (title = chapter name, track = section number parsed from the filename).
  - **Registering the PP is mandatory**: add `{"key": "FFmpegSplitChapters"}` FIRST in `opts["postprocessors"]`. Building only the `"chapter"` outtmpl key does nothing — the video downloads as ONE file into the default path and the entry reports "no file produced" (nothing matches the chapter pattern). This exact miss cost a full 2h-video re-download.
  - A `"split"` flag on a video WITHOUT chapters → PP no-ops; fall back to single-file download (don't treat as failure).
  - **Duration quirk (cosmetic — accept it, don't chase it)**: split chapter files keep the SOURCE's duration in the container header — ffprobe `format.duration` reports the whole concert while `streams[0].duration` is the correct chapter length. Players (Navidrome, VLC) use the stream duration → playback correct; only mutagen/beets' stored length field is wrong. Remuxing does NOT fix it: `-c copy` preserves the original timestamps/edit list, and `-copyts -start_at_zero` leaves the moov duration unchanged too. Re-encoding would fix the label but costs quality — never do it for this. See `references/chapter-split-duration-quirk.md`.

## Pattern: plan-then-download (LLM-driven metadata)
1. `extract_info(url, download=False)` → print per-video id/title/uploader/description (the plan). No download.
2. A human/LLM reviews the plan and writes a per-video override map (artist/title/album/year/folder).
3. Download: for each entry, resolve metadata (override wins, neutral default otherwise), set entry fields, `ydl.params["outtmpl"] = {"default": …}`, `process_ie_result(e, download=True)`.
4. **Stage downloads OUTSIDE any watched directory**; move the finished folder into place with one rename so a watcher (e.g. beets inotify) imports it once, whole.

## Pitfalls
- `sleep_requests`/`sleep_interval` ~1s per request avoids 429 bursts on big playlists.
- `writethumbnail` + `EmbedThumbnail` can fail on opus/webm AFTER a good download — keep the file if it exists (check for the audio file before declaring the entry failed; a postprocessor exception after download ≠ failed download).
- yt-dlp's default no-overwrites silently SKIPS a second video that would produce the same filename (e.g. two live versions of the same song) — detect "no file produced" and do NOT archive it, so the next run retries.
- **Debugging per-entry failures**: when exceptions are caught and reduced to one line, temporarily add `traceback.print_exc()` in the except branch — one run shows the real stack (this is how the outtmpl-dict bug was found).
- ffmpeg with an unknown output extension (e.g. `file.m4a.tmp`) fails with `Unable to find a suitable output format` — force the muxer: `-f ipod` for m4a output. (This also bit a scripted `remux_m4a()` that built `.tmp` names; a remux that only repackages won't fix the split duration quirk above, so skip the pass entirely.)
- **Before running ffmpeg passes (remux/convert) on the user's music library, explain what the pass does and why first** — the user asks "what are you doing?"; remuxing = repackaging the same audio into a new container, no re-encode, no quality change. Explain from first principles, then run.
- Playlist `playlist_index` shifts on mid-playlist insertions → new files get the current index, existing files keep theirs (cosmetic duplicate track numbers; accepted).
- `playlist_index` is `None` for single-video URLs (key present with a None value) — `f"{e.get('playlist_index'):>3}"` raises `TypeError`; the `.get(key, default)` default does NOT apply to None values, use `e.get('playlist_index') or '?'`.
- **Resume safety for interrupted runs**: persist the archive after EACH video, and at the start of a run move leftover `.staging/` audio files into the final library folder. A killed run leaves finished files staged-but-unmoved; the archive skips them on re-run, so without the recovery move they'd be orphaned in staging forever. Tee output to a log file (a `_Tee` stream class wrapping `sys.stdout`/`sys.stderr`, `--log` style) so progress/resume is debuggable outside the terminal.
- **Re-downloading a video after changing its overrides** (new artist/title, enabling `split`): the archive blocks it. Remove that video's ID from the archive file, delete the old file from the library, re-run — everything else is skipped, so it doubles as a cheap archive test.
- **Full fresh start** (library folder deleted to re-download everything): the ENTIRE archive must be deleted too — keeping it while the files are gone makes the re-run skip every video as "already downloaded" and move nothing. Warn the user explicitly; the archive is the only thing standing between a re-download and a no-op.
- **Parsing plan output / coverage-checking overrides**: YouTube video IDs are `[A-Za-z0-9_-]{11}` — hyphens AND underscores. A `\w{11}` regex silently misses IDs like `-ZvsGmYKhcU` or `_eTBcHE-xPQ`, producing false "extra override" alarms (and false "missing" results). This bit a coverage check on a 158-entry playlist; the overrides file was actually complete.
- **Plan index gaps = unavailable videos**: with `ignoreerrors`, failed entries are OMITTED from the plan listing (indices skip, e.g. [9], [34], [79] missing), not printed inline. Don't treat gaps as parse bugs; count unique IDs from the plan itself (dedupe), don't subtract from the playlist total.
- **Duplicate IDs in a playlist** (same video listed twice): the archive is keyed by ID → downloaded once, second occurrence skipped. Only ONE override entry is needed per unique ID — a coverage checker must dedupe before reporting "missing". `scripts/validate_overrides.py` automates the whole check (usage in the script docstring).

## Verification checklist
- [ ] overrides coverage verified against the plan (`scripts/validate_overrides.py <plan.txt> <overrides.json>` → MISSING must be empty)
- [ ] `--max 1` smoke test before a full playlist run (catches init/PP/outtmpl bugs in seconds)
- [ ] failed/unavailable videos reported grouped by reason with counts + video IDs
- [ ] archive file present after success; re-run downloads only new videos

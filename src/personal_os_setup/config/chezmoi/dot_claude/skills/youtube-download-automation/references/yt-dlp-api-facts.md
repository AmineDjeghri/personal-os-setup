# Verified yt-dlp API facts

All verified against the installed yt-dlp source / a real run (Python 3.14, uv-managed env). Cite the source line when re-checking after a yt-dlp upgrade.

## Postprocessor keys have NO `PP` suffix

`{"key": "FFmpegMetadataPP"}` crashes at `YoutubeDL.__init__` with `KeyError: 'FFmpegMetadataPPPP'` (the registry looks up `key + "PP"`).
Correct:

```python
"postprocessors": [
    {"key": "FFmpegSplitChapters"},                      # no-ops unless chapters are present
    {"key": "FFmpegMetadata", "add_metadata": True},
    {"key": "EmbedThumbnail"},
]
```

## Mutating `ydl.params["outtmpl"]` at runtime requires a DICT

yt-dlp normalizes a string `outtmpl` into `{"default": …}` only inside `__init__`. Assigning a raw string later makes `_prepare_filename` fail on **every** entry with `AttributeError: 'str' object has no attribute 'get'` → 0 downloads, every entry reported failed.

```python
ydl.params["outtmpl"] = {"default": str(path)}
```

## `ignoreerrors: True` is needed in BOTH modes

Metadata-only (`--plan`) and download. Without it a single unavailable/private video aborts the entire playlist fetch (`ERROR: [youtube] <id>: Video unavailable`). With it, failed entries arrive as `None` — skip them.

## Per-video metadata before download

Mutate the extracted entry dict, then hand it back:

```python
e["artist"], e["title"], e["album"] = artist, title, album
e["album_artist"], e["track"], e["date"] = artist, track, date
ydl.process_ie_result(e, download=True)
```

The `outtmpl` template and the metadata PP both read the mutated values. An archive keyed by video ID (`--download-archive` or a manual file) makes re-runs incremental.

## Which info-dict field becomes which tag

`FFmpegMetadataPP` builds its tag map from the entry dict (`yt_dlp/postprocessor/ffmpeg.py`, `_get_metadata_object`), taking the **first present** key of each group:

| Tag | Keys tried, in order |
|---|---|
| artist | `artist`, `artists`, `creator`, `creators`, `uploader`, `uploader_id` |
| genre | `genre`, `genres`, `categories`, `tags` |

**The genre fallback is a data-corruption trap.** With no `genre` key, `FFmpegMetadataPP` falls through `genres`/`categories`/`tags` and writes YouTube's *category* ("People & Blogs", "Sports"…) as the genre; beets does not clean it up. Set `e["genre"]` from an explicit decision, or pop `categories`/`tags`/`genres`/`genre` so nothing is written.

## Chapter splitting (`FFmpegSplitChapters`)

- The PP splits whenever `chapters` exists in the entry dict → one global PP list, no per-entry gate: `e.pop("chapters", None)` for entries that must NOT split.
- Chapter filenames come from `prepare_filename(info, 'chapter')` → the runtime outtmpl dict needs a `"chapter"` key:
  `{"default": …, "chapter": str(dir / "%(section_number)02d - %(section_title)s.%(ext)s")}`
  (`section_number`/`section_title`/`section_start`/`section_end` are set by the PP on a copy of the info dict).
- **Registering the PP is mandatory**: add `{"key": "FFmpegSplitChapters"}` **first** in `opts["postprocessors"]`. Building only the `"chapter"` outtmpl key does nothing — the video downloads as ONE file into the default path and the entry reports "no file produced" (nothing matches the chapter pattern).
- The PP does **NOT** delete the original full file (`run()` returns `[], info`), and the metadata PPs run on `info["filepath"]` — the ORIGINAL. So chapter files come out **untagged** and the full file lingers. Pattern: route the default outtmpl into a throwaway `_full/` subdir, delete it after processing, and tag each chapter file in the script (title = chapter name, track = section number parsed from the filename).
- `"split": true` on a video WITHOUT chapters → the PP no-ops; fall back to a single-file download (not a failure).
- **Cosmetic duration quirk — accept it, don't chase it**: split chapter files keep the SOURCE duration in the container header (ffprobe `format.duration` = whole concert, `streams[0].duration` = the chapter). Players use the stream duration, so playback is correct; only the stored length in mutagen/beets is wrong. Remuxing does not fix it (timestamps preserved; `-copyts -start_at_zero` leaves the moov duration unchanged). Re-encoding would, at a quality cost — never do it for this.

# Pipeline quirks — archive, resume, collisions, coverage

## Archive & re-download

- `.archive.txt` holds every downloaded video ID and is persisted **after each video** (crash-safe). It is what makes a re-run incremental: same URL again → only new videos download, beets imports only those.
- **Re-downloading one video after changing its overrides** (new artist/title, enabling `split`): delete that ID from the archive, delete the old file from the library, re-run. Everything else is skipped, so it doubles as a cheap archive test.
- **Full fresh start** (library folder deleted to re-download everything): delete the ENTIRE archive at the same time. Keeping it while the files are gone makes the re-run skip everything as "already downloaded" and move nothing. Warn the user explicitly — the archive is the only thing between a re-download and a no-op.
- **Duplicate IDs in a playlist** (same video listed twice): the archive is keyed by ID, so only ONE override entry is needed per unique ID; the second occurrence is skipped. A coverage checker must dedupe before reporting "missing".
- Never delete the archive (or a library folder) without the explicit warning + confirmation of §0.

## "No file produced" — the silent collision

yt-dlp's default no-overwrites behaviour silently **skips** a second video that would produce the same filename (two live versions of the same song, same artist/title). Detect the case (no matching audio file after `process_ie_result`) and do **not** archive that ID, so the next run retries it — otherwise a real video is lost with no error.

The warning also fires when a previous run already produced the file and moved it into the library: the re-run writes nothing new, so `Downloaded: 0  Failed: 0` printed next to it is **not** a missing video. Look the file up under `/media/music/YouTube/<folder>/` before telling the user anything was lost.

## Resume safety for interrupted runs

- Persist the archive after each video (above) and, at the start of a run, move leftover `.staging/` audio files into the final library folder. A killed run leaves finished files staged-but-unmoved; the archive then skips them on re-run, so without that recovery move they stay orphaned in staging forever.
- Tee output to a log file so progress and resume behaviour are debuggable outside the terminal.

## Postprocessor exceptions that are NOT download failures

`writethumbnail` + `EmbedThumbnail` can throw on opus/webm AFTER a good download. Check whether the audio file exists before declaring the entry failed — a PP exception after download ≠ failed download.

## Playlist indices

- `playlist_index` shifts when someone inserts a video mid-playlist → new files get the current index, existing files keep theirs (cosmetic duplicate track numbers; accepted).
- `playlist_index` is `None` for single-video URLs (key present, value `None`) — `.get(key, default)` does NOT cover that, use `e.get('playlist_index') or '?'`. A single-video download therefore lands with **no `NNN - ` prefix** beside numbered siblings — expected, not a partial run.
- For a single video, `playlist_title` is the video's own title (the plan header prints `## Playlist: <video title> (1 videos)`): set `folder` explicitly for single links (see SKILL.md §2).

## Plan parsing & overrides coverage

- YouTube video IDs match `[A-Za-z0-9_-]{11}` — hyphens AND underscores. A `\w{11}` regex silently misses IDs like `-ZvsGmYKhcU` or `_eTBcHE-xPQ`, producing false "extra override" alarms *and* false "missing" results. `scripts/validate_overrides.py` does the check properly.
- **Plan index gaps = unavailable videos.** With `ignoreerrors`, failed entries are OMITTED from the listing (indices skip, e.g. [9], [34], [79]) rather than printed inline. Count unique IDs from the plan itself (deduped) — don't subtract from the playlist total.

## Searching for a video ID

IDs can begin with `-` or `_`. A search pattern starting with `-` is parsed as an option and matches **nothing, silently** — drop the leading dash (`pattern="9Ad5NZLAHo"`), never trust a zero-match result for such an ID.

## ffmpeg passes on the user's library

- ffmpeg cannot infer the muxer from a `.tmp` output name (`Unable to find a suitable output format`) — force it: `-f ipod` for m4a output.
- **Before running any remux/convert pass on the library, explain what it does and why**, then run.

## Smoke test before a full run

`--max 1` first: it catches init/PP/outtmpl bugs in seconds instead of after a 150-video run.

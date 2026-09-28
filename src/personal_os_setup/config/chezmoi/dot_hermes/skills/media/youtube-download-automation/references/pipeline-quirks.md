# Pipeline quirks — archive, resume, collisions, coverage

Bugs and near-misses from real runs. Each one cost a re-download, an orphaned file or a false alarm.

## Archive & re-download

- `.archive.txt` holds every downloaded video ID and is persisted **after each video** (crash-safe). It is what makes a re-run incremental: same URL again → only new videos download, beets imports only those.
- **Re-downloading one video after changing its overrides** (new artist/title, enabling `split`): delete that ID from the archive, delete the old file from the library, re-run. Everything else is skipped, so it doubles as a cheap archive test.
- **Full fresh start** (library folder deleted to re-download everything): delete the ENTIRE archive at the same time. Keeping it while the files are gone makes the re-run skip everything as "already downloaded" and move nothing. Warn the user explicitly — the archive is the only thing between a re-download and a no-op.
- **Duplicate IDs in a playlist** (same video listed twice): the archive is keyed by ID, so only ONE override entry is needed per unique ID; the second occurrence is skipped. A coverage checker must dedupe before reporting "missing".
- Never delete the archive (or a library folder) without the explicit warning + confirmation of §0.

## "No file produced" — the silent collision

yt-dlp's default no-overwrites behaviour silently **skips** a second video that would produce the same filename (two live versions of the same song, same artist/title). Detect the case (no matching audio file after `process_ie_result`) and do **not** archive that ID, so the next run retries it — otherwise a real video is lost with no error.

## Resume safety for interrupted runs

- Persist the archive after each video (above) and, at the start of a run, move leftover `.staging/` audio files into the final library folder. A killed run leaves finished files staged-but-unmoved; the archive then skips them on re-run, so without that recovery move they stay orphaned in staging forever.
- Tee output to a log file (`--log`, a `_Tee` stream class wrapping `sys.stdout`/`sys.stderr`) so progress and resume behaviour are debuggable outside the terminal.
- Long runs: `background=true` + `notify_on_complete=true`, then read the log tail rather than polling.

## Postprocessor exceptions that are NOT download failures

`writethumbnail` + `EmbedThumbnail` can throw on opus/webm AFTER a good download. Check whether the audio file exists before declaring the entry failed — a PP exception after download ≠ failed download.

## Playlist indices

- `playlist_index` shifts when someone inserts a video mid-playlist → new files get the current index, existing files keep theirs (cosmetic duplicate track numbers; accepted).
- `playlist_index` is `None` for single-video URLs (key present, value `None`). `f"{e.get('playlist_index'):>3}"` raises `TypeError` — `.get(key, default)` does NOT cover a present-but-None value; use `e.get('playlist_index') or '?'`.
- For a single video, `playlist_title` is the video's own title: the plan header prints `## Playlist: <video title> (1 videos)` and the folder default becomes a folder named after the video. Set `folder` explicitly for single links (see SKILL.md §2).
- Index gaps in the plan are unavailable videos (see below), not a parse bug.

## Plan parsing & overrides coverage

- YouTube video IDs match `[A-Za-z0-9_-]{11}` — hyphens AND underscores. A `\w{11}` regex silently misses IDs like `-ZvsGmYKhcU` or `_eTBcHE-xPQ`, producing false "extra override" alarms *and* false "missing" results. This bit a coverage check on a 158-entry playlist; the overrides file was actually complete. `scripts/validate_overrides.py` does the check properly.
- **Plan index gaps = unavailable videos.** With `ignoreerrors`, failed entries are OMITTED from the listing (indices skip, e.g. [9], [34], [79]) rather than printed inline. Count unique IDs from the plan itself (deduped) — don't subtract from the playlist total.

## Debugging per-entry failures

When exceptions are caught and reduced to one line, temporarily add `traceback.print_exc()` in the except branch: one run shows the real stack (this is how the runtime-`outtmpl`-dict bug was found).

## ffmpeg passes on the user's library

- ffmpeg with an unknown output extension (e.g. `file.m4a.tmp`) fails with `Unable to find a suitable output format` — force the muxer: `-f ipod` for m4a output. (This bit a scripted `remux_m4a()` that built `.tmp` names.)
- **Before running any remux/convert pass on the library, explain what it does and why**, then run — the user asks "what are you doing?". Remuxing = repackaging the same audio into a new container: no re-encode, no quality change.
- A remux that only repackages does not fix the chapter-split duration quirk — skip the pass entirely (`chapter-split-duration-quirk.md`).

## Smoke test before a full run

`--max 1` first: it catches init/PP/outtmpl bugs in seconds instead of after a 150-video run. Rate limits are ~1 s/request, so a 50-video playlist is minutes, not seconds.

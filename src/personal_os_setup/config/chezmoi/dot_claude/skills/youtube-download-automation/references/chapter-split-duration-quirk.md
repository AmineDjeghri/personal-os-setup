# Chapter-split duration quirk (yt-dlp FFmpegSplitChapters)

Observed Aug 2026 on a 1h23m Travis Scott concert split into 30 m4a chapter
tracks by `FFmpegSplitChapters` + `bestaudio[ext=m4a]`.

## Symptom
- `ffprobe -show_format` → `duration=4996.000000` (the FULL source length,
  1h23m) on a 2.6-min chapter file.
- `ffprobe -show_streams` → `duration=229.016009` (the CORRECT chapter
  length; 229s = exact chapter window 0:47→4:36).
- File sizes are chapter-sized (4.6MB @ 128kbps ≈ 2.6min) → the audio IS cut
  correctly; only the container (moov/mvhd) duration is wrong.

## Why
yt-dlp's split runs ffmpeg with `-ss <start> -t <dur>` and stream copy into
the ipod muxer. The output keeps the SOURCE timestamps and an edit list, so
the movie header carries the source duration. Players honor the stream/edit
list → play correctly. mutagen/beets read the moov header → store the wrong
length (cosmetic; nothing user-visible in Navidrome).

## What was tried (all failed to fix the label)
1. `ffmpeg -i in.m4a -c copy -movflags +faststart out.m4a.tmp` →
   `Unable to find a suitable output format for 'out.m4a.tmp'` — ffmpeg can't
   infer the muxer from `.tmp`; need `-f ipod`.
2. Same with `-f ipod` → runs, duration still 4996 (timestamps preserved).
3. `-c copy -map 0:a -copyts -start_at_zero -movflags +faststart -f ipod` →
   still 4996.

## Conclusion
- Remuxing cannot fix it; re-encoding would, but violates the project's
  no-re-encode rule (native AAC, YouTube ceiling). Accept the quirk.
- Remove/replace any scripted `remux_m4a()` helper that was added hoping to
  fix it — it's a no-op for this problem (keep at most `-movflags +faststart`
  if file-serving matters, but don't claim duration is fixed).
- If the label ever matters (e.g. a player that reads moov only), the honest
  fix is a real cut with re-encode or a different splitter — out of scope.

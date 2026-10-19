---
name: music-library-ingest
description: Use when ingesting new songs into the music library.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Music library ingest — delta detection and metadata research

## When to Use

- The user drops a playlist (or video) link and asks what is new in it.
- A track is about to enter the library and its artist / title / album / year / genre / folder must be decided or
  verified; a genre is requested and must be sourced online rather than guessed.

Two halves: which playlist items are not yet ingested (§1), and sourcing/validating their tags (§2). The download,
the confirm-before-download gate (including how to present the proposal) and the folder/album/override conventions
belong to **`youtube-download-automation`** — authoritative; not restated here.

## 1. What is new in this playlist (no download)

1. Capture the pipeline's read-only plan to a file:
   `uv run --no-project yt_dl.py --plan <playlist-url> > plan.txt` (run from the pipeline folder).
2. Set-diff the plan's video IDs against the pipeline's `.archive.txt` **and** `overrides.json`.
   An ID present in either is already handled — report its state, don't re-propose it.
3. Report only the delta and stop; the download gate belongs to the pipeline skill.

Run `scripts/playlist_delta.py plan.txt <pipeline_dir>` rather than eyeballing the list — it implements the
pitfalls below and prints declared/listed/duplicate/unavailable/new counts.

Pitfalls:
- **The plan index is right-aligned and space-padded (`[  1]`)**, so `^\[(\d+)\]` matches
  nothing and you report "0 new" on a playlist that does have new items. Parse with
  `^\[\s*(\d+|\?)\]`. Treat a zero-new result as suspect until the regex is re-checked —
  a silent false negative is the most damaging answer this task can give. (A single-video plan
  prints its index as `[  ?]`, so the index pattern must allow a non-digit.)
- A hand-curated playlist can list the **same video twice**: compare unique IDs and report the
  duplicate count separately, never as new items.
- Unavailable/private videos are not list items — the plan prints them with IDs and reason in a
  trailing error block, and the declared count exceeds the listed count by exactly that number.
  Never count them as new and never invent a replacement.
- If the library path (`/media/music/...`) is not mounted in the container you are running in,
  `.archive.txt` + `overrides.json` still decide the delta; an empty mount does not mean nothing
  was downloaded.
- When only some items are new, the canonical ingest is a re-run of the **same playlist URL**
  (the archive makes it incremental, and it derives the playlist folder); a bare video URL makes
  `folder` default to the video's own title.

## 2. Sourcing the genre (and sanity-checking other tags)

Check these in order, prefer the earliest that answers:
1. **Apple/iTunes Search API** — `https://itunes.apple.com/search?term=<artist+title>&entity=song`
   → `primaryGenreName`. No key, and it is the value Apple Music shows.
2. **Shazam** song page → "Genres".
3. **SoundCloud** — the uploader's own free-text tag (e.g. "Electro", "Chanson électronique").
4. **Deezer** — `https://api.deezer.com/album/<id>` → `genres.data`.
5. **The artist's own press sheet / bio** for the *style* (e.g. "melodic techno and progressive house").

Pitfalls:
- **Apple's `primaryGenreName` can be the storefront country** (e.g. "France"), not a genre —
  it can appear on one track of a release while another returns the real genre. Never write a
  country name into a genre tag; corroborate with a second source.
- **Deezer's `genres` array is routinely empty** even for a properly released track — an empty
  list means "not labelled here", not "this release has no genre".
- Aggregator labels are broad (Electronic); the artist's own words are the style. Pick according
  to what the user asked for, and match the library's existing convention — short and lowercase
  (`rai`, `electronic`). Grep `overrides.json` for established values before inventing one.
- Some pipelines write a genre only when one is explicitly supplied, and otherwise write no genre
  tag at all. Confirm which behaviour applies before promising a genre.

## 3. Presenting the proposal

Field table and gate: `youtube-download-automation` § 0. Offer the genre as a short choice (broad label vs precise
style vs none) rather than silently picking one; nothing is written or downloaded until the user answers.

---
name: youtube-download-automation
description: Use when ingesting a music/YouTube link or playlist into the music library — what is new in it, genre sourcing, yt-dlp download. Plan first, confirm with the user, then download.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Music ingest & YouTube download automation (yt-dlp)

## Trigger
Any task that drives **yt-dlp** — the YouTube → `/media/music` → Navidrome/beets pipeline below, playlist or single-link downloads, per-video metadata, chapter splitting, debugging the downloader script — and any change to the downloader script itself. Also: "here's a playlist/video link, what is new in it?" (§3) and "which genre is this track?" (§4).

## 0. Gate — ask before you touch anything (MANDATORY)

This pipeline writes into the user's music library, and its script is a file in a repo. **Nothing downloads and nothing gets edited until the user has seen the proposal and answered.**

- **Check for an existing import BEFORE you plan.** Grep the video ID in `.archive.txt` and `overrides.json`, then look for the file under `/media/music/YouTube/`. Already imported → the reply is its verified state (library path + `ffprobe` tags), **not** a metadata proposal; only propose when something is genuinely missing or wrong. The plan's status column is not an archive check.
- **Say what governed the run, in one line.** Name this skill and what you did not do (no download / no edit / no git).
- **Before a download — a single link included.** `--plan` first, then show the proposed metadata (`artist | title | album | year | genre | folder`) and ask for the go-ahead. There is no "small enough to skip the gate" case: a one-video link is exactly where a wrong `folder` or a guessed artist is cheapest to prevent and most annoying to undo.
- **Before editing `yt_dl.py`, the README or the overrides format.** Say what changes, why, and what it affects, then wait. A link that exposes a gap in the pipeline ("genre: rai" when nothing can write a genre) is a **proposal**, not a mandate to patch the pipeline.
- **Before deleting state.** `.archive.txt` and the library folder are what decide whether a re-run downloads or no-ops — warn explicitly, then confirm.
- **Before git.** commit / push / PR need explicit per-action approval (repo `AGENTS.md`); a download run never commits.
- **A timed-out approval prompt is not consent.** Stop; the user re-triggers it.

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
| `genre` | From the `"genre"` field in `overrides.json` (e.g. `"rai"`), lowercase storefront labels, multi-value with `"; "` (`"rock; pop"`). With **no** genre override, **no genre tag is written at all** — the script neutralises the metadata PP's fallback chain, so YouTube's *category* ("People & Blogs", "Sports") can never land in the tag again. Never hand-tag a file the pipeline owns. |
| `folder` | **Set it explicitly for a single-video link** — `playlist_title` defaults to the video's own title, so the documented `Singles` default rarely fires and you get a folder named after the video. Playlists: folder = playlist title. Non-music clips: `Other`. |
| `split` | `true` only for videos with YouTube chapters that should become tracks. |

- **Non-music clips (entrances, chants, interviews, fireworks…) are NEVER classified alone**: list them with a proposed handling and wait for the confirmation before setting `album`/`folder` to `Other`.
- A video the user labels by genre or occasion is a metadata hint, not permission to change the code that writes it.

## 3. What is new in this playlist (no download)

1. Capture the read-only plan: `uv run --no-project yt_dl.py --plan <playlist-url> > plan.txt` (from the pipeline folder).
2. Set-diff the plan's video IDs against `.archive.txt` **and** `overrides.json`. An ID in either is already handled — report its state, don't re-propose it.
3. Report only the delta and stop; the §0 gate applies before any download.

Run `scripts/playlist_delta.py plan.txt <pipeline_dir>` rather than eyeballing — it implements the pitfalls below and prints declared/listed/duplicate/unavailable/new counts.

- **The plan index is right-aligned and space-padded (`[  1]`)**, so `^\[(\d+)\]` matches nothing and you report "0 new" on a playlist that has new items. Parse with `^\[\s*(\d+|\?)\]` (a single-video plan prints `[  ?]`). Treat a zero-new result as suspect until the regex is re-checked — a silent false negative is the most damaging answer here.
- A hand-curated playlist can list the **same video twice**: compare unique IDs and report the duplicate count separately, never as new.
- Unavailable/private videos are not list items — the plan prints them with ID and reason in a trailing error block, and the declared count exceeds the listed count by exactly that number. Never count them as new, never invent a replacement.
- If `/media/music/...` is not mounted in the container you run in, `.archive.txt` + `overrides.json` still decide the delta; an empty mount does not mean nothing was downloaded.
- When only some items are new, the canonical ingest is a re-run of the **same playlist URL** (the archive makes it incremental and derives the playlist folder); a bare video URL makes `folder` default to the video's own title.

## 4. Sourcing the genre (and sanity-checking other tags)

Order matters: **one source supplies many tags, the rest supply one.**

1. **last.fm — primary, and the only multi-value source.** `track.getTopTags` (→ `artist.getTopTags` when the track has none) returns weighted crowd tags; beets ships a working key (`beets.plugins.LASTFM_KEY`), the limit is ~4 req/s — and that shared key is rate-limited in practice (`error 29`), so expect to need a personal key. Filter by `min_weight`, map aliases, then intersect the bundled whitelist (`references/genre-whitelist.txt` = beets' list, `references/genre-whitelist-extra.txt` = the Spotify/EveryNoise + regional supplement): that intersection is what turns `['pop','love songs','1995','adult contemporary']` into `['Pop','Adult Contemporary']`. Keep up to the library's `genre_count`.
2. **iTunes — fallback for tracks last.fm has never tagged** (new releases, bootlegs, rai/Arabic). One `primaryGenreName` per release; anything above ~1 req/s gets 403.
3. **Deezer — corroboration only, never an override**: it calls French rap "Electro" and *Enter Sandman* "Pop".

Whichever source wins, map the value onto the canonical token set in
`references/genre-vocabulary.md` before writing: that file holds the additions (`Arabic`,
`Arabic Pop`, `World`, `Moroccan Pop`), the merge map that kills duplicate spellings, the
tokens that are never genres (`Maghreb`, `World Music`, `Eurovision`), and the 4-value cap.

- **Apple's `primaryGenreName` can be the storefront country** (e.g. "France"), not a genre — it can appear on one track of a release while another returns the real genre. Never write a country name into a genre tag; corroborate with a second source.
- **Deezer's `genres` array is routinely empty** even for a properly released track — "not labelled here", not "no genre".
- Aggregator labels are broad (Electronic); the artist's own words are the style. Pick per what the user asked for and match the library's convention — short and lowercase (`rai`, `electronic`); grep `overrides.json` for established values before inventing one.
- The pipeline writes a genre only when one is explicitly supplied (§2) — confirm before promising one.
- Present the genre as a short choice (broad label vs precise style vs none) in the §0 proposal; nothing is written or downloaded until the user answers.
- **Cache every fetch** on disk keyed `<kind>.<artist>-<title>` and give each host its own **token bucket** — last.fm 4 req/s, iTunes 1 req/s, Deezer 8 req/s. Parallel workers help last.fm and Deezer; they only make iTunes worse (its limit is per IP).
- **Matching guard**: accept a hit only when the credited artist equals the file's after normalisation (diacritics, `&`→`and`) **and** title similarity ≥ 0.60 — a prefix test matched *Travis – My Eyes* to Travis Scott and returned "Rock".
- **The LLM adjudicates, it does not invent**: whitelist survivors can still be wrong (`pop` on a metal track), and the library's own tokens win over storefront wording (`Rap`, not `hip-hop/rap`; Title Case; `;` with no space).

### 4a. Who writes the tag — this is where libraries get corrupted

- **beets owns `library.db`, never the genre tag.** Write with mutagen, then run `beet update` immediately after — it copies file tags into the DB. Tags edited behind beets' back make the next import write the stale row back or re-split a multi-value set.
- **Never run `beet lastgenre -A` (or `-A -f`) on this library.** The add-on no longer ships the plugin, but the CLI stays reachable in older images and it re-tags everything from last.fm — including the ingest folder, which sits in `library.db` even though beets skips re-importing it. Genre has one writer: this pipeline.
- **One decision per show, not per chapter.** Chapter-split live sets are matched by last.fm against each chapter title, so a 29-chapter concert ends up with 10 different sets and `Pop` in front. Resolve the show (artist prior, the release it comes from), then apply that set to every chapter.
- **The pipeline's own folder** (no MusicBrainz release): mutagen `©gen` **plus** the same string in `overrides.json` per video ID, so `.archive.txt` re-runs inherit it.
- **Never two writers on one file**, and never let a storefront's single label collapse a 2–8 value `lastgenre` set.
- **Multi-value format**: one string `Pop;Dance` — `;` with no space, and no token containing `/` (Navidrome splits on `;`, `/`, `,`).
- **M4A `©gen` is a list of atoms, not one string**: an m4a can hold `©gen: ['Pop', 'Dance', 'Trap']`. Reading `tags.get('©gen')[0]` silently sees only the first value and reports the file as already canonical while it carries five. Always iterate every atom and split each on `;` — this bit a 74-file pass that looked clean.
- **Storefront ≠ recording**: *Love Story* returns `Country` for the 2008 single while the file may be a pop live performance — keep a small manual override map.
- **Pipeline categories are not genres** (`Music`, `People & Blogs`, `Sports`): replace them; clear non-music `Other/` clips rather than inventing a genre for them.
- **A second value needs corroboration** — another source agrees, or one genre holds ≥35 % of the artist's catalogue: 208 files gave **11** duals, not 200. Don't pad.
- **Verify by recount**: `ffprobe` histogram before/after, reporting gained / changed / would-lose-a-value counts.
- **Dead ends**: MusicBrainz (`genres` empty, single-vote tags), RateYourMusic (no API, Cloudflare, ToS), Shazam (no public API), SoundCloud (client-id scraping). Discogs `styles` is the token-gated upgrade.

## 5. Verify before reporting

- Files are under `/media/music/YouTube/…`, **not** left in `.staging/`; spot-check the embedded tags of one file (`ffprobe -v quiet -show_entries format_tags -of default=nw=1 <file>`), genre included when a genre was requested.
- The beets add-on log shows the import (`ha_get_logs` source=supervisor slug=`<beets add-on>`); without beets the files still reach Navidrome on its own scan.
- Report downloads and failures: failed/unavailable videos grouped by reason with counts + video IDs, never silently dropped, never invented.
- Archive file present after success; a re-run downloads only new videos.

## 6. References

- `references/yt-dlp-api-facts.md` — verified yt-dlp internals: PP key names, runtime `outtmpl` dict, `ignoreerrors`, chapter splitting, and which info-dict field feeds which tag.
- `references/pipeline-quirks.md` — archive/resume/re-download, filename collisions, plan-index quirks, override coverage checks.
- `scripts/validate_overrides.py` — overrides-vs-plan coverage check (usage in the script docstring).
- `references/genre-whitelist.txt` — beets' genre whitelist (1,568 entries, lowercase). The skill owns it; nothing depends on the beets add-on any more.
- `references/genre-whitelist-extra.txt` — the supplement the add-on used to ship (Spotify/EveryNoise catalogue + regional descriptors like `chaabi`, `rai`), 1,019 entries, no overlap with the base list.
- `references/genre-vocabulary.md` — the canonical token set: additions, merge map, never-write list, 4-value cap. Every genre write is mapped onto it.
- `scripts/playlist_delta.py` — plan-vs-archive delta (§3).

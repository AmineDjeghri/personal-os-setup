# Genre sourcing — choosing a genre at ingest time

Used when proposing the `genre` field for a new video (SKILL.md §2). The pipeline writes a
genre **only** when `overrides.json` carries one, so every value here is a proposal the user
confirms. Output format and allowed tokens: `genre-vocabulary.md`.

**One source supplies many tags, the rest supply one.** Try in this order.

## Sources

| # | Source                                                                       | Role                                                                          | Limits                                                                                                                                        |
|---|------------------------------------------------------------------------------|-------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | **last.fm** `track.getTopTags` → `artist.getTopTags` when the track has none | Primary, the only multi-value source                                          | ~4 req/s. beets' bundled key (`beets.plugins.LASTFM_KEY`) is shared and rate-limited in practice (`error 29`) — expect to need a personal key |
| 2 | **iTunes Search** `primaryGenreName`                                         | Fallback for tracks last.fm never tagged (new releases, bootlegs, rai/Arabic) | One genre per release; > ~1 req/s gets 403 (limit is per IP)                                                                                  |
| 3 | **Deezer**                                                                   | Corroboration only, never an override                                         | ~8 req/s; it calls French rap "Electro" and *Enter Sandman* "Pop"                                                                             |

last.fm pipeline: filter by `min_weight`, map aliases, then intersect the whitelist
(`genre-whitelist.txt` = beets' list, `genre-whitelist-extra.txt` = Spotify/EveryNoise +
regional supplement). That intersection turns `['pop','love songs','1995','adult contemporary']`
into `Pop;Adult Contemporary`. Then map onto `genre-vocabulary.md` and apply its cap.

## Source pitfalls

- Apple's `primaryGenreName` can be the **storefront country** ("France"). Never write a country into a genre tag; corroborate with a second source.
- Deezer's `genres` array is routinely empty even for a released track — "not labelled here", not "no genre".
- Storefront ≠ recording: *Love Story* returns `Country` for the 2008 single while the file may be a live pop performance. Keep a small manual override map.
- YouTube categories (`Music`, `People & Blogs`, `Sports`) are not genres. Non-music clips (`Other/`) get no genre at all.
- Aggregator labels are broad (`Electronic`); the artist's own words are the style. Offer the user the choice (broad / precise / none) in the §0 proposal.
- Before inventing a value, grep `overrides.json` for ones already in use.

## Matching guard

Accept a lookup hit only when the credited artist equals the file's after normalisation
(diacritics, `&` → `and`) **and** title similarity ≥ 0.60. A prefix test once matched
*Travis – My Eyes* to Travis Scott and returned "Rock".

For a whole library use `scripts/genre_tag.py` (`references/genre-retag.md`); this page is for
choosing a genre by hand for a new video.

## Fetch hygiene

- Cache every response on disk, keyed `<kind>.<artist>-<title>`.
- One token bucket per host (last.fm 4/s, iTunes 1/s, Deezer 8/s). Parallel workers help last.fm and Deezer; they only hurt iTunes.

## The LLM adjudicates, it does not invent

Whitelist survivors can still be wrong (`pop` on a metal track). The library's own tokens win
over storefront wording (`Rap`, not `hip-hop/rap`). With last.fm as the source, its weights are
the corroboration: keep tags at or above the weight cutoff, up to the 4-value cap. Single-label
sources (iTunes, Deezer) supply one value and need a second source before adding a second.

## Dead ends (don't retry)

MusicBrainz (empty `genres`, single-vote tags) · RateYourMusic (no API, Cloudflare, ToS) ·
Shazam (no public API) · SoundCloud (client-id scraping). Discogs `styles` is the token-gated upgrade.

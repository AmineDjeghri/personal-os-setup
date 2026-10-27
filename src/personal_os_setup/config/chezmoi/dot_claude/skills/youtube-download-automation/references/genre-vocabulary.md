# Genre vocabulary — the canonical token set

Every genre written to a file must map onto this set. It exists because three separate
writers (beets' `lastgenre`, storefront lookups, last.fm) each produced their own spelling
of the same genre, and a duplicated token splits every filter and every client facet.

## Format rules

- Title Case, `;` as separator with **no space** (`Pop;Dance-Pop`).
- Never emit a token containing `/` — Navidrome splits on `/`, so `R&B/Soul` becomes two wrong genres.
- **Max 4 values per file** (the single cap — sourcing and re-tag docs defer to it). The first value — the primary genre — always survives. A generic
  parent (`Pop`, `Rock`, `Electronic`, `World`) is dropped only when a more specific token in the
  same file covers it (`Pop` goes when `Dance-Pop` is present, stays when it is not).
- Specific before generic: `Rai;Algerian Pop;World` is fine, `World;Rai` is not.
- **A drop must never leave only a marker.** When a region token was the file's only genre
  (`Maghrebi`), dropping it leaves `Arabic` alone — a language tag pretending to be a genre.
  Restore the real genre from the artist's own catalogue or a duplicate copy; 33 files needed
  this after the `Maghreb`/`Maghrebi` drop.

## Library tokens

Canonical tokens that are not in the stock lists (`Arabic`, `Arabic Pop`, `Moroccan Pop`,
`Algerian Pop`, `Rai`, `World`, `French Pop`, `French Rap`, `French R&B`, `Quran Recitation`)
live in `genre-whitelist-extra.txt` / `genre-whitelist.txt`, lowercase like every entry — add
a new one there, not here. Any write is rendered Title Case from the whitelist entry.

### Marker rules

A language/region marker is added *beside* the genre, never instead of it:

- **Arabic**: the file already carries `Rai`, `Arabic Pop`, `Moroccan Pop`, `Algerian Pop` or `Arabic`, or the artist is Arabic-language. Add `Arabic`, plus `Arabic Pop` when the file is pop-family.
- **Rai**: an artist of the rai scene carries `Rai` even if last.fm never said it. `Rai` is a genre, not a subset of `World`; `Algerian Pop` is the national flavour beside it.
- **French**: French-language artists get exactly one marker — `French Rap` for rap/hip-hop (absorbs `French Hip Hop`), `French R&B` for R&B/soul (spelled with `&`, never `Rnb`), `French Pop` otherwise.
- **`Quran Recitation`** is the only value for tilāwa; it is not a music genre, so no marker or parent applies.
- **`World`** replaces the shelf label `World Music`.

Do **not** add whitelist tokens the catalogue does not use (`chaabi`, `taarab`, `sawt`,
`arabesk`, `deep rai`, `oriental metal`). Precision nobody listens to is noise.

## Aliases and never-write tokens

Same-genre spellings (`Heavy Metal` → `Metal`, `Rnb` → `R&B`…), non-genres (regions, shelf
labels, moods, events, YouTube categories) and troll-tag patterns are rules in
`genre-aliases.txt`, which `scripts/genre_tag.py` reads — edit that file, not this page.

## Keep — sub-genres are legitimate

`Industrial Metal`, `Underground Rap`, `Algerian Pop`, `Funk Rock`, `Blue-Eyed Soul`,
`Moombahton`, `Italo Disco`, `Experimental Pop`, `Afrobeats`, `Nu Metal`, `Hyperpop`, `Bitpop`,
`Dance-Rock`, `Experimental Rock`, `Queercore`, `Riot Grrrl`, `Europop`, `Country Rock`,
`Progressive Pop`, `J-Pop`, `Spanish Rap`, `Merseybeat`, `Afropop`, `Emo`, `Progressive Metal`,
`Progressive Death Metal`, `Thrash Metal`, `Industrial Hip Hop`, `Christian Hip Hop`.

A 1,590-file library does not need to pretend it has no sub-genres. Flattening these to `Metal`
or `Rock` is a loss, not a cleanup.

## Enforcement

- A new value needs **corroboration**: last.fm against a storefront, or the artist's own
  catalogue. One source alone can be a troll tag or a remixer credit.
- The pipeline folder (`YouTube/`) follows the same set; `overrides.json` carries the values.
- Writer: mutagen, then exactly one `beet update`. beets must never own the genre field.

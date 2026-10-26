# Genre vocabulary — the canonical token set

Every genre written to a file must map onto this set. It exists because three separate
writers (beets' `lastgenre`, storefront lookups, last.fm) each produced their own spelling
of the same genre, and a duplicated token splits every filter and every client facet.

## Format rules

- Title Case, `;` as separator with **no space** (`Pop;Dance-Pop`).
- Never emit a token containing `/` — Navidrome splits on `/`, so `R&B/Soul` becomes two wrong genres.
- **Max 4 values per file.** When a file would exceed it, drop the generic parent first
  (`Pop` loses to `Dance-Pop`; `Electronic` loses to `House`).
- Specific before generic: `Rai;Algerian Pop;World` is fine, `World;Rai` is not.

## Additions (canonical, in use)

| Token | Meaning |
|---|---|
| `Arabic` | language/region marker for the Arabic-language catalogue — pairs with a genre |
| `Arabic Pop` | the genre of Arabic-language pop (Saad Lamjarred, Amr Diab, Nancy Ajram) |
| `World` | the bucket; replaces the industry shelf label `World Music` |
| `Moroccan Pop` | regional flavour, sits beside `Arabic Pop` |
| `Rai` | genre for Khaled, cheb bello, Bilel Tacchini — not a subset of `World` |
| `Algerian Pop` | national flavour for rai-adjacent pop; keeps `Rai` as the genre |

Do **not** add whitelist tokens the catalogue does not use (`chaabi`, `taarab`, `sawt`,
`arabesk`, `deep rai`, `oriental metal`). Precision nobody listens to is noise.

## Merge map — same genre under two names

| From | To |
|---|---|
| `Industrial`, `Industrial Rock` | `Industrial Metal` |
| `Heavy Metal` | `Metal` |
| `French Rnb`, `Contemporary R&B`, `Chillout R&B` | `R&B` |
| `Euro Disco`, `Hi Nrg` | `Disco` |
| `Diva House`, `Uk Funky` | `House` |
| `Electro Pop` | `Electropop` |
| `Dance Pop` | `Dance-Pop` |
| `Neo Soul` | `Neo-Soul` |
| `Boyband` | `Boy Band` |
| `Pop Edm` | `Electronic` |
| `Arabic Music` | `Arabic Pop` |

## Never write (not genres)

`Maghreb`, `Maghreb Pop`, `Maghrebi`, `North African` (regions) · `World Music` (shelf label) ·
`Eurovision` (event) · `Chillout` (mood) · `Sophisti Pop`, `Sophisti-Pop` (artefact) ·
`Pop In Spanish` (language) · last.fm troll tags (`National Socialist Black Metal` and friends —
filter by regex, they are not corner cases).

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

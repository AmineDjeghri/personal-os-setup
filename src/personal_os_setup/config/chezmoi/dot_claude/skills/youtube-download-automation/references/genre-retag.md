# Genre re-tag — adding genres to files already in the library

Not part of a normal ingest. Use when the user asks to fill, fix or normalise genres across
existing files. It is a bulk write to the library: show the dry-run report and get approval
before `--apply` (SKILL.md §0). The tool is `scripts/genre_tag.py`.

## Run it

```bash
export LASTFM_API_KEY=...                       # personal key; beets' shared one hits error 29
uv run --no-project scripts/genre_tag.py <music_dir> --limit 50   # smoke test, dry run
uv run --no-project scripts/genre_tag.py <music_dir> --report r.tsv   # whole library, dry run
uv run --no-project scripts/genre_tag.py <music_dir> --apply          # write (+ backup)
beet update                                                           # then, once
uv run --no-project scripts/genre_tag.py --restore <backup.jsonl>     # undo an --apply
```

First run: the whole library. Later runs: the same command — processed files are remembered by
`(mtime, size)` and lookups are cached (`~/.cache/genre_tag/`), so only new or changed files
cost anything. `--force` re-checks everything (use it after editing the whitelist or aliases).
Throughput is bounded by last.fm's ~4 req/s: budget about an hour per 10 000 *unique* tracks
on a cold cache; a crashed run resumes from the cache.

## Additions-only run (the safe default for a library that already has genres)

The default policy *removes* a generic parent (`Pop` beside `Dance-Pop`) and renames spellings.
On a curated library that is a loss, not a fix. Three flags turn the pass into additions only:

```bash
uv run --no-project scripts/genre_tag.py /media/music --force --keep-existing --cap 5 \
    --block "black metal,death metal,screamo,national socialist black metal,synthpop,edm" \
    --exclude-dir Other --report filtered.tsv            # then --apply
```

- `--keep-existing` — no value the file already has is ever dropped; the status can then only be
  unchanged / extended / gained / review.
- `--block` — comma-separated tokens that are never *added*. Two uses: brigade tags (last.fm
  returns `Black Metal` for Justin Bieber's whole catalogue) and duplicate spellings
  (`Synthpop` beside the library's `Synth-Pop`, `EDM` beside `Edm`).
- `--exclude-dir NAME` — skip a folder by name (the ingest folder's `Other/` clips must stay
  genre-less; without it the artist fallback invents `Hip Hop` for stadium chants).
- `--cap 5` — a file at 4 values has no room otherwise, and existing 4-value files are common.

Verify after the write: re-read every file and assert **no token disappeared** (compare against a
pre-pass inventory, case-insensitively — the tool's acronym rule legitimately renames `Edm`→`EDM`),
and that the value count stayed ≤ cap. A verifier that reads `tags.get("genre")` sees **nothing**
for m4a: the atoms are `©gen`, so read both keys or every m4a looks empty and the pass looks
catastrophic.

## Removing junk that is already in the files

`--block` stops new junk but never removes what an older pass wrote (`--keep-existing` keeps it by
definition). That needs a one-off spec keyed on the file, not the scanner: read each file's genres at
write time, drop the junk tokens, and give a file whose only value was junk a real replacement.
Some tokens are junk only in context — `Metal` is right for Gojira and wrong on a Taylor Swift
track — so the drop list has to be per file, not global.

## The merge policy

- **Every track is looked up on its own** (artist + cleaned title). Chapters of a live set can
  legitimately get different genres. When a track has no confident match, the artist's tags are
  the fallback, then iTunes (`--no-itunes` to skip).
- **last.fm tags are filtered**, not trusted blindly: weight ≥ `--min-weight` (30, relative to
  the top tag), then `genre-aliases.txt`, then the whitelist. `seen live`, years and
  `love songs` die there.
- **Existing values are kept** and normalised; new ones are appended up to `--cap` (4). An
  existing value is removed only if it is never-write (YouTube categories, regions…) or a
  generic parent covered by a specific token (`Pop` next to `Dance-Pop`). Nothing is overwritten.
- **`review` files are not written**: a result that would be only a language marker (`Arabic`),
  a tag containing `/`, or a file whose only genre was a never-write token with nothing to
  replace it. Decide those by hand.
- Language markers (`Arabic`, `French Rap`…) are **not** added automatically — the script can't
  know a language. Add them by hand per `genre-vocabulary.md`.

## Who writes the tag

- **Genre has exactly one writer: `genre_tag.py` (and the pipeline for new downloads).** beets owns `library.db`, never the genre tag; `beet update` afterwards copies file tags into it.
- **Never run `beet lastgenre -A` (or `-A -f`)**: it re-tags everything from last.fm with its own spelling and separator.
- The pipeline's own folder (`YouTube/`): `overrides.json` also carries the genre per video ID, so `.archive.txt` re-runs inherit it. After a re-tag of that folder, mirror the values into `overrides.json` (not automated).
- M4A `©gen` can be a list of atoms; the script reads every atom, splits on `;`, and writes one string `A;B;C`.
- Multi-value format and caps: `genre-vocabulary.md`.

## Verify by recount

The dry run prints gained / extended / normalized / unchanged / nodata / review / failed counts.
After `--apply`, re-run the same command: it must report 0 files to process (or only new
ones). Spot-check a few with `ffprobe -v quiet -show_entries format_tags=genre -of default=nw=1 <file>`.

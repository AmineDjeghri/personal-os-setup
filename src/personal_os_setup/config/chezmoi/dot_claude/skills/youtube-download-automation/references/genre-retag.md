# Genre re-tag — fixing genres on files already in the library

Not part of a normal ingest. Use only when the user asks to fix or normalise genres on
existing files. It is a bulk write to the library: explain the plan and get approval first
(SKILL.md §0).

## Who writes the tag

- **Genre has exactly one writer: this pipeline.** beets owns `library.db`, never the genre tag.
- **Never run `beet lastgenre -A` (or `-A -f`)** on this library. Older add-on images still expose the CLI, and it re-tags everything from last.fm, including the ingest folder.
- Write with mutagen, then run `beet update` once, immediately after — it copies file tags into the DB. Tags edited behind beets' back get written back stale (or re-split) by the next import.
- The pipeline's own folder (`YouTube/`, no MusicBrainz release): write mutagen `©gen` **and** the same string in `overrides.json` under the video ID, so `.archive.txt` re-runs inherit it.
- Never two writers on one file; never let a storefront's single label collapse an existing multi-value set.

## Rules while re-tagging

- **One decision per show, not per chapter.** last.fm matches each chapter title separately, so a 29-chapter concert ends up with many different sets. Resolve the show (artist prior, source release), then apply that set to every chapter.
- **M4A `©gen` is a list of atoms.** `tags.get('©gen')[0]` sees only the first value and calls a five-value file canonical. Iterate every atom and split each on `;`.
- **Pipeline categories are not genres** (`Music`, `People & Blogs`, `Sports`): replace them, or clear non-music `Other/` clips instead of inventing a genre.
- Multi-value format and caps: `genre-vocabulary.md`.

## Verify by recount

Take an `ffprobe` genre histogram before and after
(`ffprobe -v quiet -show_entries format_tags=genre -of default=nw=1 <file>`) and report
**gained / changed / would-lose-a-value** counts. A pass is not done until the recount matches
the plan.

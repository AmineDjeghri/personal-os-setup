#!/usr/bin/env -S uv run --no-project --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["mutagen>=1.47"]
# ///
"""Merge last.fm genres into the genre tag of every audio file under a folder.

Usage:
    export LASTFM_API_KEY=...            # a personal key; beets' shared one is rate-limited
    uv run --no-project genre_tag.py <music_dir>                 # dry run: report only
    uv run --no-project genre_tag.py <music_dir> --apply         # write tags (+ backup)
    uv run --no-project genre_tag.py --restore <backup.jsonl>    # undo an --apply

Behaviour (the "merge" policy, see references/genre-retag.md):
  * Every track is looked up on its own: last.fm track tags, then the artist's tags when the
    track has none, then iTunes when last.fm knows neither. Chapters of one live set can
    therefore get different genres.
  * A tag is kept when its weight >= --min-weight (last.fm weights are relative to the top
    tag), it survives references/genre-aliases.txt, and it is on the whitelist.
  * Existing values are kept (normalised) and never removed, except tokens that are
    never-write (YouTube categories, regions...) or generic parents covered by a specific
    token (Pop next to Dance-Pop). New values are appended up to --cap (default 4).
  * Files whose result would be only a language marker, or whose tag holds a "/", are left
    alone and reported as "review".
  * Dry run is the default. --apply writes after saving the old values to a backup file.
    Run `beet update` afterwards: beets copies file tags into its DB, it must not write them.

Resumable: lookups are cached in sqlite and processed files are remembered by (mtime, size),
so a crashed or later run only does the remaining / new work. --force ignores that memory.
"""

import argparse
import concurrent.futures as cf
import difflib
import json
import os
import re
import sqlite3
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"
AUDIO_EXT = {".m4a", ".mp3", ".flac", ".opus", ".ogg"}
GENERIC = {"pop", "rock", "electronic", "world"}  # dropped when a specific token covers them
MARKERS = {"arabic"}  # language markers: never a genre on their own
ACRONYMS = {"r&b", "edm", "idm", "uk", "us", "dj"}
LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
ITUNES_URL = "https://itunes.apple.com/search"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "genre_tag"


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


# ------------------------------------------------------------------ vocabulary ---
class Vocab:
    """Whitelist + alias/never-write rules loaded from references/."""

    def __init__(self, refs=REFS):
        self.allowed, self.alias, self.drop, self.drop_re = set(), {}, set(), []
        for name in ("genre-whitelist.txt", "genre-whitelist-extra.txt"):
            for line in (refs / name).read_text(encoding="utf-8").splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    self.allowed.add(line)
        for line in (refs / "genre-aliases.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("drop-re:"):
                self.drop_re.append(re.compile(line[8:].strip(), re.I))
            elif line.startswith("drop:"):
                self.drop.add(line[5:].strip().lower())
            else:
                src, _, dst = line.partition("->")
                self.alias[src.strip().lower()] = dst.strip().lower()
        self.allowed |= set(self.alias.values())

    def canon(self, raw, require_listed=True):
        """Return the lowercase canonical token, or None if it must not be written."""
        t = " ".join(raw.lower().split())
        for step in range(2):  # check the raw form, then the aliased form
            if not t or "/" in t or t in self.drop or any(r.search(t) for r in self.drop_re):
                return None
            if step == 0:
                t = self.alias.get(t, t)
        if require_listed and t not in self.allowed:
            return None
        return t


def render(token):
    """Title Case a canonical token (``dance-pop`` -> ``Dance-Pop``, ``r&b`` -> ``R&B``)."""

    def word(w):
        if w in ACRONYMS:
            return w.upper()
        return "-".join(p[:1].upper() + p[1:] for p in w.split("-"))

    return " ".join(word(w) for w in token.split(" "))


# --------------------------------------------------------------- merge decision ---
def split_values(atoms):
    """Split tag atoms (a list of strings) on ';' into individual values."""
    return [v.strip() for a in atoms for v in str(a).split(";") if v.strip()]


def _covered(generic, values):
    return any(
        v.lower() != generic and re.search(rf"[\s-]{re.escape(generic)}$", v.lower())
        for v in values
    )


def _drop_covered(values):
    return [v for v in values if not (v.lower() in GENERIC and _covered(v.lower(), values))]


def decide(existing_atoms, candidates, vocab, cap):
    """Merge ``candidates`` (rendered, best first) into the existing genre atoms.

    Returns ``(final_values, status)``; status is one of unchanged / gained / extended /
    normalized / review / nodata.
    """
    raw = split_values(existing_atoms)
    review = False
    existing = []
    for v in raw:
        if "/" in v:  # can't be normalised safely: keep and flag
            review = True
            existing.append(v)
            continue
        t = vocab.canon(v, require_listed=False)
        if t is None:
            continue
        existing.append(render(t) if (t in vocab.allowed or t != v.lower()) else v)
    final = []
    for v in existing:
        if v.lower() not in {f.lower() for f in final}:
            final.append(v)
    final = _drop_covered(final)

    taken = {f.lower() for f in final}
    fresh = [c for c in candidates if c.lower() not in taken]
    fresh = [c for c in fresh if c.lower() != "world"] + [c for c in fresh if c.lower() == "world"]
    for c in fresh:
        if len(final) >= cap:
            break
        if c.lower() in GENERIC and _covered(c.lower(), final + [c]):
            continue
        final = _drop_covered(final + [c])

    markers_only = bool(final) and all(f.lower() in MARKERS for f in final)
    if review or markers_only or (raw and not final):
        return final, "review"
    if not final:
        return final, "nodata"
    old = ";".join(raw)
    if ";".join(final) == old:
        return final, "unchanged"
    if not raw:
        return final, "gained"
    if {r.lower() for r in raw} <= {f.lower() for f in final}:
        return final, "extended"
    return final, "normalized"


# ------------------------------------------------------------ lookups & caching ---
def norm_name(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().replace("&", " and ")
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def clean_title(title):
    """Drop '(Live …)', '[4K]' and a '- live …' suffix: they hide the song from lookups."""
    t = re.sub(r"[\(\[].*?[\)\]]", "", title)
    t = re.sub(r"\s+-\s+(live|remaster|remastered|official).*$", "", t, flags=re.I)
    return " ".join(t.split())


def primary_artist(artist):
    return re.split(r"\s+(?:feat\.?|ft\.?|featuring)\s+|;", artist, maxsplit=1, flags=re.I)[
        0
    ].strip()


def same_song(artist, title, got_artist, got_title):
    """Matching guard: credited artist equal and title similarity >= 0.60."""
    if norm_name(artist) != norm_name(got_artist):
        return False
    return difflib.SequenceMatcher(None, norm_name(title), norm_name(got_title)).ratio() >= 0.60


class RateLimiter:
    def __init__(self, per_sec):
        self.gap, self.next, self.lock = 1.0 / per_sec, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            slot = max(now, self.next)
            self.next = slot + self.gap
        time.sleep(max(0.0, slot - now))


class Cache:
    """Tiny thread-safe sqlite key/value store; also caches 'not found' answers."""

    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)")
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            row = self.db.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?, ?)", (key, json.dumps(value)))
            self.db.commit()


def http_json(url, limiter, retries=5):
    """GET ``url`` as JSON with backoff on 429/5xx/network errors. Raises on final failure."""
    for attempt in range(retries):
        limiter.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "genre_tag/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == retries - 1:
                raise
        except urllib.error.URLError, TimeoutError:
            if attempt == retries - 1:
                raise
        time.sleep(2**attempt)
    raise RuntimeError("unreachable")


class Lookup:
    def __init__(self, api_key, cache, lastfm_rps, itunes=True):
        self.key, self.cache, self.itunes_on = api_key, cache, itunes
        self.lastfm = RateLimiter(lastfm_rps)
        self.itunes = RateLimiter(1.0)

    def _lastfm(self, method, **params):
        """Return (attr, [(tag, weight)]) or None when last.fm does not know the item."""
        q = urllib.parse.urlencode(
            {"method": method, "api_key": self.key, "format": "json", "autocorrect": 1, **params}
        )
        for attempt in range(5):
            data = http_json(f"{LASTFM_URL}?{q}", self.lastfm)
            code = data.get("error")
            if code == 29:  # rate limit exceeded
                time.sleep(2**attempt)
                continue
            if code in (6, 7):  # not found
                return None
            if code:
                raise RuntimeError(f"last.fm error {code}: {data.get('message')}")
            top = data.get("toptags", {})
            tags = top.get("tag", [])
            tags = tags if isinstance(tags, list) else [tags]
            return top.get("@attr", {}), [(t["name"], int(t.get("count", 0))) for t in tags]
        raise RuntimeError("last.fm rate limit (error 29) persisted; use a personal API key")

    def tags(self, kind, artist, title=None):
        """Cached last.fm tags for a track or artist; [] when unknown or guard fails."""
        key = f"lfm.{kind}.{norm_name(artist)}" + (f"-{norm_name(title)}" if title else "")
        hit = self.cache.get(key)
        if hit is not None:
            return [tuple(t) for t in hit]
        if kind == "track":
            res = self._lastfm("track.getTopTags", artist=artist, track=title)
        else:
            res = self._lastfm("artist.getTopTags", artist=artist)
        out = []
        if res:
            attr, tags = res
            got_artist = attr.get("artist", artist)
            if kind == "track":
                ok = same_song(artist, title, got_artist, attr.get("track", title))
            else:
                ok = norm_name(artist) == norm_name(got_artist)
            out = tags if ok else []
        self.cache.put(key, out)
        return out

    def itunes_genre(self, artist, title):
        key = f"itunes.{norm_name(artist)}-{norm_name(title)}"
        hit = self.cache.get(key)
        if hit is not None:
            return hit or None
        q = urllib.parse.urlencode(
            {"term": f"{artist} {title}", "entity": "song", "media": "music", "limit": 5}
        )
        genre = ""
        for r in http_json(f"{ITUNES_URL}?{q}", self.itunes).get("results", []):
            if same_song(artist, title, r.get("artistName", ""), r.get("trackName", "")):
                genre = r.get("primaryGenreName", "")
                break
        self.cache.put(key, genre)
        return genre or None


def candidates_from(tags, vocab, min_weight):
    out = []
    for name, weight in sorted(tags, key=lambda t: -t[1]):
        t = vocab.canon(name)
        if weight >= min_weight and t and render(t) not in out:
            out.append(render(t))
    return out


def lookup_candidates(lk, vocab, artist, title, min_weight):
    """Return (candidates, source). Raises on network/API failure."""
    artist = primary_artist(artist)
    title = clean_title(title)
    if title:
        found = candidates_from(lk.tags("track", artist, title), vocab, min_weight)
        if found:
            return found, "track"
    found = candidates_from(lk.tags("artist", artist), vocab, min_weight)
    return (found, "artist") if found else ([], "none")


# ------------------------------------------------------------------ files/state ---
def open_audio(path):
    import mutagen

    f = mutagen.File(path, easy=True)
    if f is None:
        return None
    if f.tags is None:
        f.add_tags()
    return f


def scan(root, state, force):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            p = Path(dirpath, name)
            if p.suffix.lower() not in AUDIO_EXT:
                continue
            st = p.stat()
            if not force and state.get(str(p)) == [st.st_mtime_ns, st.st_size]:
                continue
            yield p


def load_state(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state))
    tmp.replace(path)


def restore(backup):
    n = 0
    first = {}  # a file may appear in several runs of one backup: the first record is the original
    for line in Path(backup).read_text().splitlines():
        rec = json.loads(line)
        first.setdefault(rec["path"], rec)
    for rec in first.values():
        f = open_audio(rec["path"])
        if f is None:
            continue
        if rec["old"]:
            f.tags["genre"] = rec["old"]
        elif "genre" in f.tags:
            del f.tags["genre"]
        f.save()
        n += 1
    print(f"restored {n} file(s) from {backup}; run `beet update` to refresh beets' DB")


# ------------------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("path", nargs="?", help="music folder to scan recursively")
    ap.add_argument("--apply", action="store_true", help="write tags (default: dry run)")
    ap.add_argument("--restore", metavar="BACKUP", help="restore tags from a backup .jsonl")
    ap.add_argument("--cap", type=int, default=4, help="max genres per file (default 4)")
    ap.add_argument("--min-weight", type=int, default=30, help="last.fm tag weight 0-100")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--lastfm-rps", type=float, default=4.0)
    ap.add_argument("--no-itunes", action="store_true", help="skip the iTunes fallback")
    ap.add_argument("--limit", type=int, default=0, help="only the first N files (smoke test)")
    ap.add_argument("--force", action="store_true", help="ignore the processed-files memory")
    ap.add_argument("--report", metavar="TSV", help="write every decision to a TSV file")
    ap.add_argument("--show", type=int, default=10, help="example lines per status")
    args = ap.parse_args()

    if args.restore:
        return restore(args.restore)
    if not args.path or not Path(args.path).is_dir():
        die("Give an existing music folder (see --help).")
    key = os.environ.get("LASTFM_API_KEY")
    if not key:
        die("Set LASTFM_API_KEY (a personal key: https://www.last.fm/api/account/create).")

    vocab = Vocab()
    cache = Cache(CACHE_DIR / "lookups.sqlite")
    state_path = CACHE_DIR / "state.json"
    state = load_state(state_path)
    lk = Lookup(key, cache, args.lastfm_rps, itunes=not args.no_itunes)

    files = []
    for p in scan(args.path, state, args.force):
        files.append(p)
        if args.limit and len(files) >= args.limit:
            break
    print(f"{len(files)} file(s) to process", file=sys.stderr)

    # 1. read tags
    recs = []  # dicts: path, artist, title, atoms
    unreadable = []
    for p in files:
        try:
            f = open_audio(p)
            tags = f.tags
            recs.append(
                {
                    "path": p,
                    "artist": (tags.get("artist") or [""])[0],
                    "title": (tags.get("title") or [""])[0],
                    "atoms": list(tags.get("genre") or []),
                }
            )
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the run
            unreadable.append((p, exc))

    # 2. one lookup per unique (artist, title); a live set's chapters differ by title
    uniq = {(r["artist"], r["title"]) for r in recs if r["artist"]}
    results, failed = {}, {}
    done = 0

    def work(pair):
        return pair, lookup_candidates(lk, vocab, pair[0], pair[1], args.min_weight)

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(work, pair): pair for pair in uniq}
        for fut in cf.as_completed(futs):
            pair = futs[fut]
            try:
                results[pair] = fut.result()[1]
            except Exception as exc:  # noqa: BLE001
                failed[pair] = exc
            done += 1
            if done % 100 == 0:
                print(f"  looked up {done}/{len(uniq)}", file=sys.stderr)

    # 3. iTunes fallback for what last.fm does not know (sequential, 1 req/s)
    if lk.itunes_on:
        for pair, (cands, _) in list(results.items()):
            if cands:
                continue
            try:
                g = lk.itunes_genre(primary_artist(pair[0]), clean_title(pair[1]))
            except urllib.error.HTTPError as exc:
                print(f"iTunes fallback disabled ({exc}).", file=sys.stderr)
                lk.itunes_on = False
                break
            t = vocab.canon(g) if g else None
            if t:
                results[pair] = ([render(t)], "itunes")

    # 4. decide
    rows = []  # (status, path, old, new, source)
    for r in recs:
        pair = (r["artist"], r["title"])
        if pair in failed:
            rows.append(
                ("failed", r["path"], ";".join(split_values(r["atoms"])), "", str(failed[pair]))
            )
            continue
        cands, source = results.get(pair, ([], "none"))
        final, status = decide(r["atoms"], cands, vocab, args.cap)
        rows.append(
            (status, r["path"], ";".join(split_values(r["atoms"])), ";".join(final), source)
        )
    rows += [("unreadable", p, "", "", str(e)) for p, e in unreadable]

    # 5. apply
    written = 0
    if args.apply:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        backup = CACHE_DIR / f"backup-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
        try:
            with backup.open("a", encoding="utf-8") as bf:
                for status, path, old, new, _ in rows:
                    if status in ("gained", "extended", "normalized"):
                        f = open_audio(path)
                        bf.write(
                            json.dumps({"path": str(path), "old": list(f.tags.get("genre") or [])})
                            + "\n"
                        )
                        bf.flush()
                        f.tags["genre"] = [new]
                        f.save()
                        written += 1
                    if status in ("gained", "extended", "normalized", "unchanged", "nodata"):
                        st = Path(path).stat()
                        state[str(path)] = [st.st_mtime_ns, st.st_size]
        finally:
            save_state(state_path, state)
        print(f"\nbackup: {backup}")

    # 6. report
    by = {}
    for row in rows:
        by.setdefault(row[0], []).append(row)
    print(f"\n{'APPLIED' if args.apply else 'DRY RUN'} -- {len(rows)} file(s)")
    for status in (
        "gained",
        "extended",
        "normalized",
        "unchanged",
        "nodata",
        "review",
        "failed",
        "unreadable",
    ):
        print(f"  {status:<11}: {len(by.get(status, []))}")
        for _, path, old, new, source in by.get(status, [])[: args.show]:
            if status in ("gained", "extended", "normalized"):
                print(f"      {path}\n        {old or '(none)'}  ->  {new}   [{source}]")
            elif status in ("review", "failed", "unreadable"):
                print(f"      {path}  ({old or source})")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write("status\tpath\told\tnew\tsource\n")
            for row in rows:
                fh.write("\t".join(str(c) for c in row) + "\n")
        print(f"full report: {args.report}")
    if args.apply:
        print(f"\nwrote {written} file(s). Now run `beet update` so beets' DB picks up the tags.")
    elif by.get("gained") or by.get("extended") or by.get("normalized"):
        print("\nDry run only. Re-run with --apply to write.")


if __name__ == "__main__":
    main()

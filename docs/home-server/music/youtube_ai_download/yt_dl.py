#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "yt-dlp",
#     "mutagen",
# ]
# ///
"""yt_dl.py — YouTube playlist/video → music library downloader (LLM-driven).

Downloads YouTube playlists (or single videos) as audio-only m4a into
/media/music/YouTube/<folder>/ with metadata (artist, title, album, year)
decided 100% by the LLM agent via --overrides. The script is PURE PLUMBING:
no title/description parsing, no guessing.

Modes:
  --plan <url>              Fetch metadata only; print per-video: id, title,
                            uploader, description snippet. NO download.
                            This is the input for the LLM review.
  <url> [urls...]           Download. Archive-driven (incremental updates).
  --overrides file.json     Per-video metadata decisions (key = video ID).
  --urls-file file.txt      URLs from a file, one per line.
  --max N                   Limit downloads this run (testing).
  --log FILE                Tee all output to a log file (in addition to
                            stdout — resume/progress debugging).

Overrides JSON — the ONLY source of metadata decisions:
{
  "VIDEO_ID": {
    "artist": "...",      # default: uploader
    "title":  "...",      # default: video title
    "album":  "...",      # default: playlist title
    "year":   "2018",     # optional: concert year (default: upload year)
    "folder": "Other",    # optional: download into YouTube/Other instead of
                          # the playlist folder (e.g. non-music clips)
    "split":  true        # optional: split a video with YouTube chapters into
                          # per-chapter tracks (title = chapter name,
                          # track = section number); full file is discarded
  }
}
Only the fields you set are used; anything else falls back to neutral
defaults. Videos without an entry get the defaults.

Run with uv (deps declared in the PEP 723 header — no venv, no
requirements.txt):
    uv run --no-project yt_dl.py --plan <url>
    uv run --no-project yt_dl.py <url> --overrides overrides.json
    (--no-project: this folder may sit inside a uv project (personal-os-setup);
     without it uv would bind to that project's env instead of this script's.)

Config at the bottom of this block — adjust once.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

import yt_dlp
from yt_dlp.utils import sanitize_filename

try:
    import mutagen
    from mutagen.mp4 import MP4
except ImportError:
    mutagen = None

# ---------------------------------------------------------------- config ---
LIBRARY_ROOT = Path("/media/music")  # beets library root (watched)
YOUTUBE_DIR = "YouTube"  # subfolder for downloads
_SCRIPT_DIR = Path(__file__).resolve().parent
ARCHIVE_FILE = _SCRIPT_DIR / ".archive.txt"
STAGING_DIR = _SCRIPT_DIR / ".staging"  # OUTSIDE the watch root
SINGLES_NAME = "Singles"  # folder for single-video links
OTHER_NAME = "Other"  # folder for non-music clips


# ---------------------------------------------------------------- helpers ---
class _ErrLog:
    """Collects yt-dlp error lines so the summary can report what failed."""

    def __init__(self):
        self.lines = []

    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        self.lines.append(str(msg))


class _Tee:
    """Duplicate writes to several streams (real stdout + a log file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def resolve_meta(info: dict, overrides: dict) -> dict:
    """Metadata for an entry: overrides win, neutral defaults otherwise."""
    vid = info.get("id")
    ov = (overrides or {}).get(vid, {})
    return {
        "artist": ov.get("artist")
        or info.get("uploader")
        or info.get("channel")
        or "Unknown Artist",
        "title": ov.get("title") or info.get("title") or "Unknown",
        "album": ov.get("album")
        or info.get("playlist_title")
        or info.get("playlist")
        or YOUTUBE_DIR,
        "year": str(ov.get("year") or (info.get("upload_date") or "")[:4]),
        "folder": ov.get("folder")
        or (info.get("playlist_title") or info.get("playlist") or SINGLES_NAME),
        "split": bool(ov.get("split", False)),
    }


# ---------------------------------------------------------------- archive ---
def load_archive() -> set:
    if ARCHIVE_FILE.exists():
        return {ln.strip() for ln in ARCHIVE_FILE.read_text().splitlines() if ln.strip()}
    return set()


def save_archive(ids: set) -> None:
    ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_FILE.write_text("\n".join(sorted(ids)) + "\n")


# ---------------------------------------------------------------- tagging ---
def fix_tags(path: Path, meta: dict, track: str, date: str) -> None:
    """Belt-and-suspenders tag pass (guarantees the metadata yt-dlp embedded)."""
    if mutagen is None:
        return
    try:
        f = mutagen.File(path)
    except Exception:
        return
    if f is None:
        return
    try:
        if isinstance(f, MP4):
            f["\xa9ART"] = [meta["artist"]]
            f["\xa9nam"] = [meta["title"]]
            f["\xa9alb"] = [meta["album"]]
            f["aART"] = [meta["artist"]]
            if track:
                f["trkn"] = [(int(track), 0)]
            if date:
                f["\xa9day"] = [date]
        else:  # Vorbis (opus/webm); mp3 would land here too but we never produce it
            f["artist"] = meta["artist"]
            f["title"] = meta["title"]
            f["album"] = meta["album"]
            f["albumartist"] = meta["artist"]
            if track:
                f["tracknumber"] = str(track)
            if date:
                f["date"] = date
        f.save()
    except Exception:
        pass


# ------------------------------------------------------------------ modes ---
def iter_entries(info: dict):
    """Yield playlist entries (or the single video itself) skipping failures."""
    if info is None:
        return
    if "entries" in info:
        for e in info["entries"]:
            if e is not None:
                yield e
    else:
        yield info


def find_downloaded(staging_dir: Path, prefix: str) -> list:
    """Audio files actually produced for an entry (excludes thumbnails)."""
    if not staging_dir.exists():
        return []
    return [
        p
        for p in sorted(staging_dir.glob(f"{prefix}*"))
        if p.suffix.lower() in (".m4a", ".opus", ".webm", ".mp3")
    ]


def plan_mode(urls: list, max_items: int) -> int:
    errlog = _ErrLog()
    opts = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,  # skip unavailable/private videos, don't abort the playlist
        "logger": errlog,
        "sleep_requests": 1.0,
        "sleep_interval": 1.0,
        "max_sleep_interval": 2.0,
    }
    shown = 0
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:  # noqa: BLE001
                print(f"\n## ERROR: could not fetch {url}: {exc}")
                continue
            pl_title = (info or {}).get("title", url)
            n = len(info.get("entries") or [1]) if info and "entries" in info else 1
            print(f"\n## Playlist: {pl_title} ({n} videos) — {url}")
            for e in iter_entries(info):
                if max_items and shown >= max_items:
                    break
                desc = (e.get("description") or "").replace("\n", " ")[:400]
                idx = e.get("playlist_index") or "?"
                print(f"[{idx:>3}] {e.get('id')}  {e.get('title')}")
                print(f"     uploader: {e.get('uploader') or e.get('channel')}")
                ch = e.get("chapters") or []
                if ch:
                    print(f"     chapters: {len(ch)}")
                if desc:
                    print(f"     desc: {desc}")
                shown += 1
    if errlog.lines:
        print(f"\nUnavailable/errors seen during scan: {len(errlog.lines)}")
        for ln in dict.fromkeys(errlog.lines):
            print(f"  {ln}")
    return 0


def download_mode(urls: list, overrides: dict, max_items: int) -> int:
    archive = load_archive()
    downloaded, skipped, failed = [], [], []
    staging_dirs = set()
    errlog = _ErrLog()

    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio",
        "outtmpl": str(STAGING_DIR / "%(playlist_title|Singles)s" / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "logger": errlog,
        "retries": 5,
        "fragment_retries": 5,
        "sleep_requests": 1.0,
        "sleep_interval": 1.0,
        "max_sleep_interval": 2.0,
        "writethumbnail": True,
        "postprocessors": [
            {"key": "FFmpegSplitChapters"},  # no-ops unless chapters present (split:true)
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ],
    }

    # Resume-safety: move any leftovers from an interrupted previous run.
    # The archive is per-video, so already-downloaded entries get skipped —
    # but their staged files must still reach the library.
    if STAGING_DIR.exists():
        for sub in sorted(STAGING_DIR.iterdir()):
            if not sub.is_dir():
                continue
            if sub.name == "_full":  # split source dir, never a final artifact
                shutil.rmtree(sub, ignore_errors=True)
                continue
            files = [
                p for p in sub.iterdir() if p.suffix.lower() in (".m4a", ".opus", ".webm", ".mp3")
            ]
            if not files:
                continue
            dst = LIBRARY_ROOT / YOUTUBE_DIR / sub.name
            dst.mkdir(parents=True, exist_ok=True)
            for p in files:
                shutil.move(str(p), str(dst / p.name))
            print(
                f"  resumed: moved {len(files)} leftover file(s) from "
                f".staging/{sub.name}/ into the library"
            )
            try:
                sub.rmdir()
            except OSError:
                pass

    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: could not fetch {url}: {exc}")
                failed.append((url, "", str(exc)))
                continue
            for e in iter_entries(info):
                if max_items and len(downloaded) >= max_items:
                    break
                vid = e.get("id")
                if vid and vid in archive:
                    skipped.append((vid, e.get("title"), "in archive"))
                    continue
                meta = resolve_meta(e, overrides)
                folder = sanitize_filename(meta["folder"])
                staging_dir = STAGING_DIR / folder
                idx = e.get("playlist_index")
                track = str(idx) if idx else "1"
                date = meta["year"]
                prefix = f"{int(idx):03d} - " if idx else ""
                # Unique per entry even without a playlist index
                stem = f"{prefix}{sanitize_filename(meta['artist'])} - {sanitize_filename(meta['title'])}"
                fname = f"{stem}.%(ext)s"
                e["title"] = meta["title"]
                e["artist"] = meta["artist"]
                e["track"] = track
                e["album"] = meta["album"]
                e["album_artist"] = meta["artist"]
                e["date"] = date
                # Chapter split: only for videos flagged "split": true that
                # actually have chapters; the PP is otherwise kept inert by
                # removing the chapters key. The full source file is routed to
                # a _full/ subdir and discarded after splitting.
                chapters = e.get("chapters") or []
                want_split = meta["split"] and bool(chapters)
                if meta["split"] and not chapters:
                    print(f"  NOTE: {vid} has no chapters — keeping as one track")
                if not want_split:
                    e.pop("chapters", None)
                tmpl = {"default": str(staging_dir / fname)}
                if want_split:
                    tmpl["default"] = str(staging_dir / "_full" / fname)
                    tmpl["chapter"] = str(
                        staging_dir / f"{stem} - %(section_number)02d - %(section_title)s.%(ext)s"
                    )
                ydl.params["outtmpl"] = tmpl
                try:
                    ydl.process_ie_result(e, download=True)
                except Exception as exc:  # noqa: BLE001
                    # postprocessors (e.g. thumbnail embed on opus) can fail
                    # AFTER a good download — keep the file if it's there.
                    if not find_downloaded(staging_dir, stem):
                        print(f"  ERROR: {vid} {e.get('title')}: {str(exc).splitlines()[0]}")
                        failed.append((vid, e.get("title"), str(exc)))
                        continue
                    print(f"  WARN: {vid} {e.get('title')}: {str(exc).splitlines()[0]} (file kept)")
                found = find_downloaded(staging_dir, stem)
                if not found:
                    # yt-dlp default is no-overwrites: same artist+title twice
                    # silently skips — don't archive so the next run retries
                    print(f"  WARN: {vid} no file produced (name exists?) — not archived")
                    continue
                if vid:
                    archive.add(vid)
                    save_archive(archive)  # crash-safe: persisted per video
                if want_split:
                    # Each chapter file gets the chapter name + its section
                    # number; the full source file is discarded.
                    for p in found:
                        m = re.search(r"- (\d{2}) - ", p.stem)
                        n = int(m.group(1)) if m else None
                        ch = chapters[n - 1] if n and n <= len(chapters) else {}
                        fix_tags(
                            p,
                            {**meta, "title": ch.get("title") or p.stem},
                            str(n) if n else track,
                            date,
                        )
                    shutil.rmtree(staging_dir / "_full", ignore_errors=True)
                else:
                    for p in found:
                        fix_tags(p, meta, track, date)
                staging_dirs.add(staging_dir)
                downloaded.append((vid, meta["artist"], meta["title"], meta["album"], folder))
                extra = f" [{len(found)} chapters]" if want_split else ""
                print(
                    f"  + {meta['artist']} - {meta['title']}  →  {meta['album']}  ({folder}/){extra}"
                )

    # Move finished folders into the library (single rename → one beets import)
    moved = 0
    for src in sorted(staging_dirs):
        if not src.exists() or not any(src.iterdir()):
            continue
        dst = LIBRARY_ROOT / YOUTUBE_DIR / src.name
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            shutil.move(str(item), str(dst / item.name))
        moved += 1
        try:
            src.rmdir()
        except OSError:
            pass

    # Summary
    print("\n=== Summary ===")
    print(
        f"Downloaded: {len(downloaded)}   Already in archive: {len(skipped)}   "
        f"Failed: {len(failed)}"
    )
    for vid, artist, title, album, folder in downloaded:
        print(f"  {artist} - {title}  [{album}]  ({folder}/)")

    # Download-time failures, with reasons
    if failed:
        print(f"\nFailed ({len(failed)}):")
        for vid, title, exc in failed:
            print(f"  {vid}  {title}: {str(exc).splitlines()[0]}")

    # Extract-time failures (unavailable/private/age-restricted), grouped
    if errlog.lines:
        groups = {}
        for ln in errlog.lines:
            m = re.match(r"^\[([^\]]+)\]\s+([\w-]+):\s*(.+)$", ln)
            if m:
                groups.setdefault(m.group(3), []).append(m.group(2))
            else:
                groups.setdefault(ln, [])
        total = sum(len(v) for v in groups.values())
        print(f"\nCouldn't download ({total} videos):")
        for reason, vids in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            shown_ids = ", ".join(vids[:6]) + (" …" if len(vids) > 6 else "")
            print(f"  {len(vids):>3}×  {reason[:80]}  [{shown_ids}]")

    print(
        f"\nMoved {moved} folder(s) into {LIBRARY_ROOT / YOUTUBE_DIR}/ — beets "
        f"will import them automatically (watch debounce ~300s)."
    )
    return 0


# ------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("urls", nargs="*", help="YouTube playlist/video URL(s)")
    ap.add_argument("--plan", action="store_true", help="metadata review only, no download")
    ap.add_argument("--overrides", metavar="FILE", help="JSON per-video metadata decisions")
    ap.add_argument("--urls-file", metavar="FILE", help="file with URLs, one per line")
    ap.add_argument("--max", type=int, default=0, help="limit downloads this run")
    ap.add_argument("--log", metavar="FILE", help="tee output to a log file")
    args = ap.parse_args()

    if args.log:
        try:
            logf = open(args.log, "a", encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot open log file {args.log}: {exc}")
            return 2
        tee = _Tee(sys.__stdout__, logf)
        sys.stdout = tee
        sys.stderr = _Tee(sys.__stderr__, logf)

    urls = list(args.urls)
    if args.urls_file:
        p = Path(args.urls_file)
        if not p.exists():
            print(f"ERROR: {p} not found")
            return 2
        urls += [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
    if not urls:
        ap.print_help()
        return 2

    overrides = {}
    if args.overrides:
        op = Path(args.overrides)
        if not op.exists():
            print(f"ERROR: overrides file {op} not found")
            return 2
        overrides = json.loads(op.read_text())
        if not isinstance(overrides, dict):
            print("ERROR: overrides must be a JSON object {video_id: {...}}")
            return 2

    if args.plan:
        return plan_mode(urls, args.max)
    return download_mode(urls, overrides, args.max)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""watchtower — deterministic collector for "what changed on the internet" digests.

One script, one source list, one shared interest profile, one state file. No LLM
call in the hot path: every item is scored in code, so a run costs nothing and can
be audited by reading the output.

    watchtower.py                      # run every enabled source
    watchtower.py --due                # only sources whose `every:` slot has elapsed
    watchtower.py --source sports      # one source, ignore the clock
    watchtower.py --doctor             # probe sources + print schedule health
    watchtower.py --json               # machine-readable items, for other agents
    watchtower.py --explain <id|url>   # why one item scored what it scored
    watchtower.py --dry-run            # read only: no state, no ledger

Layout (see README.md):
    <repo>/docs/home-server/watchtower/   code + example configs  (committed)
    <home>/                               config + state (see resolve_home)
        sources.yaml  interests.yaml  state.json  ledger/

Exit codes: 0 ok or silent, 1 a source failed, 2 config error, 3 watchdog timeout.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import html as html_lib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

UA = "watchtower/0.2 (+https://github.com/AmineDjeghri/personal-os-setup)"
SCRIPT_VERSION = "0.2"
TICK = timedelta(minutes=5)  # the tick cron's period; also the smallest supported `every`
WATCHDOG_SECONDS = 300  # hard ceiling per run (enrich_github worst case is ~1050s)

_NOW: datetime | None = None  # set by --now (tests only)
HOME = Path(".")
HOME_KIND = "unresolved"


# --------------------------------------------------------------------------- clock


def now_dt() -> datetime:
    return _NOW if _NOW is not None else datetime.now(timezone.utc)


def now_iso() -> str:
    return now_dt().replace(microsecond=0).isoformat()


def iso_week(when: datetime | None = None) -> str:
    y, w, _ = (when or now_dt()).isocalendar()
    return f"{y}-W{w:02d}"


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def days_since(stamp: str | None) -> float:
    """Age in days of a stored ISO date/datetime, or a large number when unknown."""
    when = parse_iso(stamp)
    if when is None:
        return 9999.0
    return (now_dt() - when).total_seconds() / 86400


# --------------------------------------------------------------- home resolution


def resolve_home(cli_home: str | None) -> tuple[Path, str]:
    """First match wins. The legacy agent path stays last so a live install keeps working."""
    if cli_home:
        return Path(cli_home).expanduser(), "--home"
    env = os.environ.get("WATCHTOWER_HOME")
    if env:
        return Path(env).expanduser(), "$WATCHTOWER_HOME"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg and (Path(xdg) / "watchtower").is_dir():
        return Path(xdg) / "watchtower", "$XDG_CONFIG_HOME"
    config = Path.home() / ".config" / "watchtower"
    if config.is_dir():
        return config, "~/.config"
    legacy = Path.home() / ".hermes" / "watchtower"
    if (legacy / "sources.yaml").is_file():
        return legacy, "legacy ~/.hermes"
    return config, "default ~/.config"


# --------------------------------------------------------------------------- io


class FetchError(RuntimeError):
    """A source failed. Never silently degrade into 'no news'."""


class ConfigError(SystemExit):
    def __init__(self, message: str):
        print(f"watchtower: {message}", file=sys.stderr)
        super().__init__(2)


class WatchdogTimeout(BaseException):
    """Not an Exception on purpose: no retry loop or per-source handler may swallow it."""


def load_yaml(path: Path, *, required: bool = True) -> dict:
    if not path.exists():
        if required:
            raise ConfigError(f"missing config file {path}")
        return {}
    data = yaml.safe_load(path.read_text())
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must contain a YAML mapping")
    return data


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"sources": {}, "runs": []}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"corrupt state file {path}: {exc}")
    if not isinstance(data, dict):
        raise ConfigError(f"state file {path} must contain a JSON object")
    return data


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"state.json.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True))
    tmp.replace(path)


def append_ledger(home: Path, record: dict) -> None:
    ledger_dir = home / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    with (ledger_dir / f"{now_dt():%Y-%m}.jsonl").open("a") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class Lock:
    """flock on <home>/.lock. The kernel releases it on SIGKILL, so no stale-lock logic."""

    def __init__(self, home: Path):
        self.path = home / ".lock"
        self.fh = None
        self.holder: dict | None = None

    def __enter__(self):
        """Acquire the lock non-blocking; on contention `held` stays False and `holder` is filled in."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = self.path.open("a+")
        try:
            fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.fh.seek(0)
            try:
                self.holder = json.loads(self.fh.read() or "{}")
            except json.JSONDecodeError:
                self.holder = {}
            self.fh.close()
            self.fh = None
            return self
        self.fh.seek(0)
        self.fh.truncate()
        self.fh.write(
            json.dumps({"pid": os.getpid(), "started_at": now_iso(), "argv": sys.argv[1:][:4]})
        )
        self.fh.flush()
        return self

    @property
    def held(self) -> bool:
        return self.fh is not None

    def __exit__(self, *exc):
        """Release the lock. The kernel would also drop it on SIGKILL, so no stale handling is needed."""
        if self.fh:
            try:
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            finally:
                self.fh.close()
                self.fh = None
        return False


# --------------------------------------------------------------------------- http


def http_get(url: str, *, timeout: int = 30, retries: int = 1, headers: dict | None = None) -> str:
    req_headers = {"User-Agent": UA, "Accept": "*/*"}
    if headers:
        req_headers.update(headers)
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return resp.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 + attempt * 3)
                continue
            raise FetchError(f"{url} -> {last}") from exc
        except Exception as exc:  # noqa: BLE001 - network layer, keep the reason
            last = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(2)
                continue
            raise FetchError(f"{url} -> {last}") from exc
    raise FetchError(f"{url} -> {last}")


# ----------------------------------------------------------------------- schedule

_DUR_RE = re.compile(
    r"^(?:every\s+)?(\d+)?\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)$"
)
_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def parse_every(value) -> timedelta | None:
    """`15m`, `1h`, `every day`, `every week` -> timedelta. Cron expressions are refused."""
    if value is None:
        return None
    raw = str(value).strip().lower()
    if any(ch in raw for ch in "*/,"):
        raise ConfigError(
            f"every: {value!r} looks like a cron expression; use 15m / 1h / 1d / 1w "
            "(plus at: for daily and weekly alignment)"
        )
    match = _DUR_RE.match(raw)
    if not match:
        raise ConfigError(f"every: {value!r} is not understood (use 15m, 1h, 1d, 1w)")
    count = int(match.group(1) or 1)
    unit = match.group(2)[0]
    if unit in "dw" and count != 1:
        raise ConfigError(f"every: {value!r} — only 1{unit} is supported, not {count}{unit}")
    if unit == "d":
        every = timedelta(days=count)
    elif unit == "w":
        every = timedelta(weeks=count)
    elif unit == "h":
        every = timedelta(hours=count)
    else:
        every = timedelta(minutes=count)
    if every < TICK:
        raise ConfigError(f"every: {value!r} is below the {int(TICK.total_seconds() // 60)}m tick")
    if every > timedelta(weeks=4):
        raise ConfigError(f"every: {value!r} is above 4w")
    return every


def parse_duration(value) -> timedelta | None:
    """Lenient duration for window / close_after / remember / min_gap (no tick floor, no 4w cap)."""
    if value is None:
        return None
    raw = str(value).strip().lower()
    match = _DUR_RE.match(raw)
    if not match:
        raise ConfigError(f"duration {value!r} is not understood (use 30m, 6h, 90d, 1w)")
    count = int(match.group(1) or 1)
    unit = match.group(2)[0]
    if unit == "d":
        return timedelta(days=count)
    if unit == "w":
        return timedelta(weeks=count)
    if unit == "h":
        return timedelta(hours=count)
    return timedelta(minutes=count)


def parse_at(value) -> tuple[int, int]:
    if value is None:
        raise ConfigError("at: is required for 1d and 1w sources")
    if isinstance(value, int):
        raise ConfigError(f'at: {value!r} must be quoted ("07:30") — YAML reads 10:30 as a number')
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", str(value))
    if not match:
        raise ConfigError(f'at: {value!r} must look like "07:30"')
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise ConfigError(f"at: {value!r} is not a valid time")
    return hour, minute


def validate_schedule(source: dict) -> dict:
    """Normalise {every, at, on}. An absent `every` means legacy (never due)."""
    every = parse_every(source.get("every"))
    at = source.get("at")
    on = source.get("on")
    if every is None:
        if at or on:
            raise ConfigError(f"{source.get('id')}: at:/on: need an every:")
        return {"every": None, "at": None, "on": None}
    if every >= timedelta(days=1):
        at = parse_at(at)
    elif at is not None:
        raise ConfigError(f"{source.get('id')}: at: is only for 1d/1w sources")
    if on is not None:
        if every < timedelta(weeks=1):
            raise ConfigError(f"{source.get('id')}: on: is only for weekly sources")
        if str(on).lower()[:3] not in _DAYS:
            raise ConfigError(f"{source.get('id')}: on: {on!r} must be mon..sun")
    return {
        "every": every,
        "at": at,
        "on": str(on).lower()[:3] if on else ("mon" if every >= timedelta(weeks=1) else None),
    }


def slot_start(sched: dict, tz: ZoneInfo, when: datetime) -> datetime | None:
    """Start of the most recent slot, in UTC. A slot is a calendar/grid cell, never 'now - every'."""
    every = sched["every"]
    if every is None:
        return None
    if every < timedelta(days=1):
        # Sub-day grids are epoch-aligned, so they need no timezone at all (Paris offset is whole hours).
        step = every.total_seconds()
        return datetime.fromtimestamp((when.timestamp() // step) * step, tz=timezone.utc)
    hour, minute = sched["at"]
    local = when.astimezone(tz)
    # Build the wall time as NAIVE, then attach the zone with fold=0. Using replace() on an aware
    # datetime keeps the incoming fold, which fires twice at the autumn change and drifts in spring.
    naive = datetime(local.year, local.month, local.day, hour, minute)
    if every >= timedelta(weeks=1):
        target = _DAYS.index(sched["on"] or "mon")
        naive -= timedelta(days=(naive.weekday() - target) % 7)
    candidate = _resolve_local(naive, tz)
    if candidate > when:
        naive -= every
        candidate = _resolve_local(naive, tz)
    return candidate.astimezone(timezone.utc)


def _resolve_local(naive: datetime, tz: ZoneInfo) -> datetime:
    """Attach tz; a wall time that does not exist (spring-forward gap) moves to the first valid instant."""
    candidate = naive.replace(tzinfo=tz, fold=0)
    if candidate.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive:
        probe = naive
        for _ in range(180):  # at most a 3h gap in practice
            probe += timedelta(minutes=1)
            candidate = probe.replace(tzinfo=tz, fold=0)
            if candidate.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == probe:
                break
    return candidate


def next_due(sched: dict, tz: ZoneInfo, when: datetime) -> datetime | None:
    slot = slot_start(sched, tz, when)
    return None if slot is None else slot + sched["every"]


def is_due(sched: dict, snap: dict, tz: ZoneInfo, when: datetime) -> bool:
    """Due when the last attempt predates the current slot. Failures back off exponentially."""
    if sched["every"] is None:
        return False  # legacy source: only a plain (no --due) run picks it up
    last_attempt = parse_iso(snap.get("last_attempt"))
    if last_attempt is not None and last_attempt > when:
        last_attempt = when  # a clock that jumped forward must not freeze the schedule
    failures = int(snap.get("failures") or 0)
    if failures:
        wait = min(timedelta(hours=6), timedelta(minutes=15) * (2 ** min(failures - 1, 5)))
        return last_attempt is None or when >= last_attempt + wait
    slot = slot_start(sched, tz, when)
    if slot is None:
        return False
    return last_attempt is None or last_attempt < slot


def human_delta(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    for unit, size in (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size and seconds % size == 0:
            return f"{seconds // size}{unit}"
    return f"{seconds // 60}m"


# ------------------------------------------------------------------- normalising


def make_item(
    source_id: str,
    *,
    id_: str,
    title: str,
    url: str = "",
    summary: str = "",
    published: str = "",
    rank=None,
    tags: list[str] | None = None,
    author: str = "",
    **extra,
) -> dict:
    """Item schema v2 — the contract every source kind must produce."""
    return {
        "source": source_id,
        "id": id_,
        "title": title.strip(),
        "url": url,
        "summary": " ".join((summary or "").split()),
        "published": published,
        "rank": rank,
        "tags": [t for t in (tags or []) if t],
        "author": author,
        "extra": extra,
    }


def _text(node) -> str:
    return " ".join(html_lib.unescape(node.text or "").split()) if node is not None else ""


_MONTHS = {
    m: i
    for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"],
        start=1,
    )
}


def _parse_feed_offset(text: str) -> str:
    """RFC-822/ISO with an explicit offset -> UTC ISO. A dropped offset skews the alert window."""
    match = re.search(r"([+-])(\d{2}):?(\d{2})$", text)
    offset = timedelta(0)
    if match:
        sign = -1 if match.group(1) == "-" else 1
        offset = sign * timedelta(hours=int(match.group(2)), minutes=int(match.group(3)))
        text = text[: match.start()].strip()
    moment = None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    if moment is None:
        match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\w*\s+(\d{2,4})\s+(\d{2}):(\d{2})", text)
        month_no = _MONTHS.get(match.group(2).lower()) if match else None
        if not match or not month_no:
            return ""
        day, _, year, hour, minute = match.groups()
        try:
            moment = datetime(
                int(year) + (2000 if int(year) < 100 else 0),
                month_no,
                int(day),
                int(hour),
                int(minute),
            )
        except ValueError:
            return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone(offset))
    return moment.astimezone(timezone.utc).isoformat()[:19]


def fetch_rss(source: dict) -> list[dict]:
    """RSS 2.0 / Atom -> items. One `url:` or a `feeds:` list of {id, url, tier}."""
    feeds = source.get("feeds") or (
        [{"id": source["id"], "url": source["url"], "tier": 2}] if source.get("url") else []
    )
    if not feeds:
        raise FetchError(f"{source['id']} -> rss kind needs url: or feeds:")
    out: list[dict] = []
    failed: list[str] = []
    for feed in feeds:
        try:
            xml = http_get(feed["url"], timeout=25)
            root = ET.fromstring(xml)
        except FetchError as exc:
            failed.append(f"{feed['id']}: {exc}")
            continue
        except ET.ParseError as exc:
            failed.append(f"{feed['id']}: not xml ({exc})")
            continue
        entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        kept = 0
        for entry in entries:

            def pick(*names):
                for name in names:
                    found = entry.find(name)
                    if found is not None:
                        return found
                return None

            title = _text(pick("title", "{http://www.w3.org/2005/Atom}title"))
            link = _text(pick("link", "{http://www.w3.org/2005/Atom}link"))
            if not link:
                node = entry.find("{http://www.w3.org/2005/Atom}link")
                if node is not None:
                    link = node.get("href", "")
            summary = re.sub(
                r"<[^>]+>",
                " ",
                _text(
                    pick(
                        "description",
                        "summary",
                        "{http://www.w3.org/2005/Atom}summary",
                        "{http://www.w3.org/2005/Atom}content",
                    )
                ),
            )
            published = _text(
                pick(
                    "pubDate",
                    "published",
                    "{http://www.w3.org/2005/Atom}updated",
                    "{http://www.w3.org/2005/Atom}published",
                )
            )
            guid = _text(pick("guid", "{http://www.w3.org/2005/Atom}id")) or link
            if not title:
                continue
            out.append(
                make_item(
                    source["id"],
                    id_=hashlib.sha1((guid or title).encode()).hexdigest()[:16],
                    title=title,
                    url=link,
                    summary=summary,
                    published=_parse_feed_offset(published),
                    tags=[feed["id"]],
                    feed=feed["id"],
                    tier=feed.get("tier", 2),
                )
            )
            kept += 1
        if not kept:
            failed.append(f"{feed['id']}: parsed 0 entries")
    # Partial blindness is a failure: with half the feeds down a corroboration gate would lie.
    healthy = len(feeds) - len(failed)
    need = int(source.get("min_feeds_ok") or 1)
    if healthy < need:
        raise FetchError(
            f"{source['id']} -> {healthy}/{len(feeds)} feeds healthy, need {need}: "
            + "; ".join(failed[:4])
        )
    if not out:
        raise FetchError(f"{source['id']} -> parsed 0 items out of {len(feeds)} feeds")
    return out


def fetch_trendshift(source: dict) -> list[dict]:
    """trendshift.io listing page -> items (schema.org ItemList in application/ld+json)."""
    html = http_get(source["url"], timeout=30)
    blocks = re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    if not blocks:
        raise FetchError(f"{source['url']} -> no application/ld+json block (markup changed?)")
    payload = None
    for block in blocks:
        try:
            candidate = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and candidate.get("@type") == "ItemList":
            payload = candidate
            break
    if payload is None:
        raise FetchError(f"{source['url']} -> ld+json present but no ItemList")
    entries = payload.get("itemListElement") or []
    if not isinstance(entries, list) or not entries:
        raise FetchError(f"{source['url']} -> ItemList is empty")

    limit = int(source.get("limit") or len(entries))
    out: list[dict] = []
    for entry in entries[:limit]:
        if not isinstance(entry, dict):
            continue
        item = entry.get("item") or {}
        slug = str(item.get("name") or "").strip()
        if "/" not in slug:
            continue
        out.append(
            make_item(
                source["id"],
                id_=slug.lower(),
                title=slug,
                url=item.get("codeRepository") or item.get("url") or "",
                summary=item.get("description") or "",
                published=(item.get("dateCreated") or "")[:10],
                rank=entry.get("position"),
                tags=[item.get("programmingLanguage") or ""],
                slug=slug,
                lang=(item.get("programmingLanguage") or "").strip(),
                topics=item.get("topics") or [],
                created=(item.get("dateCreated") or "")[:10],
                updated=(item.get("dateModified") or "")[:10],
            )
        )
    if not out:
        raise FetchError(f"{source['url']} -> parsed 0 valid repos out of {len(entries)} entries")
    return out


# ------------------------------------------------------------- github enrich


def gh_token() -> str | None:
    """Token for the GitHub API: env first, then the gh CLI (never printed)."""
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(var)
        if value:
            return value.strip()
    for candidate in ("gh", "/usr/bin/gh", "/usr/local/bin/gh"):
        try:
            proc = subprocess.run(
                [candidate, "auth", "token"], capture_output=True, text=True, timeout=10
            )
        except FileNotFoundError, subprocess.SubprocessError:
            continue
        token = (proc.stdout or "").strip()
        if proc.returncode == 0 and token:
            return token
    return None


def enrich_github(items: list[dict], *, token: str | None = None) -> tuple[int, str | None]:
    """Add stars + topics. One 404 (repo deleted/renamed) is not a source failure."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    ok, err, not_found = 0, None, 0
    for item in items:
        slug = item["extra"].get("slug") or item["title"]
        try:
            data = json.loads(
                http_get(f"https://api.github.com/repos/{slug}", timeout=20, headers=headers)
            )
        except FetchError as exc:
            text = str(exc)
            if "HTTP 404" in text:
                not_found += 1
                continue
            err = text
            if "HTTP 403" in text or "HTTP 429" in text:
                break  # rate limited: stop hammering
            continue
        except json.JSONDecodeError:
            err = f"{slug}: github returned non-JSON"
            continue
        item["extra"]["stars"] = data.get("stargazers_count")
        item["extra"]["topics"] = data.get("topics") or []
        item["extra"]["fork"] = bool(data.get("fork"))
        item["extra"]["archived"] = bool(data.get("archived"))
        if not item["summary"]:
            item["summary"] = (data.get("description") or "").strip()
        if not item["extra"].get("lang") and data.get("language"):
            item["extra"]["lang"] = data["language"]
            item["tags"] = [data["language"]]
        ok += 1
    if not_found and not ok:
        err = f"{not_found} repos returned 404 (deleted or renamed)"
    return ok, err


KINDS: dict[str, dict] = {
    "trendshift_jsonld": {
        "fetch": fetch_trendshift,
        "enrich": enrich_github,
        "line": "github",
        "mode": "list",
    },
    "rss": {"fetch": fetch_rss, "enrich": None, "line": "generic", "mode": "new"},
}


def check_items(source: dict, items: list[dict]) -> None:
    """A listing that got suspiciously small is a broken extractor, not 'no news'."""
    min_items = int(source.get("min_items") or 0)
    if min_items and len(items) < min_items:
        raise FetchError(
            f"{source.get('url') or source['id']} -> only {len(items)} items, "
            f"expected at least {min_items} (schema drift?)"
        )


# ------------------------------------------------------------------- scoring

_SHORT_TOKEN = re.compile(r"^[a-z0-9]{1,5}$")


def fold(text: str) -> str:
    """Accent-insensitive: 'seisme' must match 'séisme'."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    ).lower()


def _hits(haystack: str, token: str) -> bool:
    token = fold(str(token)).strip()
    if not token:
        return False
    if _SHORT_TOKEN.match(token):
        return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) is not None
    return token in haystack


def _rule_hits(haystack: str, rule: dict) -> list[str]:
    tokens = [*rule.get("keywords", []), *rule.get("topics", [])]
    return [t for t in tokens if _hits(haystack, str(t))]


def item_text(item: dict, *, include_summary: bool = True) -> str:
    parts = [item.get("title", "")]
    if include_summary:
        parts.append(item.get("summary", ""))
    parts.append(" ".join(item.get("tags") or []))
    parts.append(" ".join(item["extra"].get("topics") or []))
    parts.append(item["extra"].get("lang") or "")
    return fold(" ".join(parts))


def score_item(item: dict, profile: dict, source_id: str) -> dict:
    """Deterministic score: +weight per matching like rule, -weight per matching dislike rule."""
    haystack = item_text(item)
    score = 0
    whys: list[dict] = []
    demoted: list[dict] = []
    for rule in profile.get("like") or []:
        hits = _rule_hits(haystack, rule)
        if hits:
            weight = int(rule.get("weight", 1))
            score += weight
            whys.append(
                {
                    "id": rule.get("id") or rule.get("name") or "rule",
                    "weight": weight,
                    "hits": hits[:4],
                }
            )
    for rule in profile.get("dislike") or []:
        hits = _rule_hits(haystack, rule)
        if hits:
            weight = int(rule.get("weight", -1))
            score += weight
            demoted.append(
                {
                    "id": rule.get("id") or rule.get("name") or "rule",
                    "weight": weight,
                    "hits": hits[:4],
                }
            )

    thresholds = profile.get("thresholds") or {}
    per_source = (thresholds.get("per_source") or {}).get(source_id) or {}
    highlight_at = int(per_source.get("highlight", thresholds.get("highlight", 4)))

    blocked = [fold(str(x)) for x in ((profile.get("language") or {}).get("block") or [])]
    if blocked and fold(item["extra"].get("lang") or "") in blocked:
        demoted.append({"id": "language", "weight": 0, "hits": [item["extra"].get("lang")]})
        score = min(score, highlight_at - 1)  # this used to change nothing at all
    if item["extra"].get("archived"):
        demoted.append({"id": "archived", "weight": 0, "hits": []})
        score = min(score, highlight_at - 1)

    item["score"] = score
    item["whys"] = whys
    item["demoted"] = demoted
    item["highlight"] = bool(whys) and score >= highlight_at and not item["extra"].get("archived")
    item["highlight_cap"] = per_source.get("max_highlight")
    return item


def split_items(items: list[dict], profile: dict, source_id: str) -> tuple[list[dict], list[dict]]:
    for item in items:
        score_item(item, profile, source_id)
    highlights = [i for i in items if i["highlight"]]
    rest = [i for i in items if not i["highlight"]]

    def key(item: dict):
        return (-item["score"], -(item.get("gained") or 0), item.get("rank") or 999)

    highlights.sort(key=key)
    cap = next((i["highlight_cap"] for i in highlights if i.get("highlight_cap")), None)
    if cap:
        dropped = highlights[int(cap) :]
        for item in dropped:
            item["highlight"] = False
            item["capped"] = True
        rest = sorted(rest + dropped, key=lambda i: i.get("rank") or 999)
        highlights = highlights[: int(cap)]
    return highlights, rest


# ---------------------------------------------------------------------- render


def clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def fmt_stars(item: dict) -> str:
    stars = item["extra"].get("stars")
    if stars is None:
        return "★?"
    gained = item.get("gained")
    base = f"★{stars / 1000:.1f}k".replace(".0k", "k") if stars >= 1000 else f"★{stars}"
    if gained:
        return base + f" (+{gained})"
    if gained is not None:
        return base + " (+0)"
    return base


def why_line(item: dict) -> str:
    """Every ranking decision, printed: matches, demotions, the cap."""
    bits = [f"{w['id']}({w['weight']})" for w in item.get("whys") or []]
    bits += [
        f"−{w['id']}({abs(w['weight'])})"
        for w in item.get("demoted") or []
        if w["id"] != "language"
    ]
    if item.get("capped"):
        bits.append("capped")
    return " · ".join(bits)


def line_github(item: dict, markdown: bool) -> list[str]:
    flag = " 🆕" if item.get("is_new") else ""
    slug = item["extra"].get("slug") or item["title"]
    out = [f"`{slug}`{flag} — {fmt_stars(item)} · trend #{item['rank']}"]
    meta = " · ".join(x for x in [item["extra"].get("lang"), why_line(item)] if x)
    if meta:
        out.append(f"   ↳ {meta}")
    if item["summary"]:
        out.append(f"   {clip(item['summary'], 150)}")
    if item["url"]:
        out.append(f"   {item['url']}")
    return out


def line_generic(item: dict, markdown: bool) -> list[str]:
    flag = " 🆕" if item.get("is_new") else ""
    when = (item.get("published") or "")[:16].replace("T", " ")
    source = item["extra"].get("feed") or item["source"]
    title = f"*{item['title']}*" if markdown else item["title"]
    out = [f"{title}{flag} — {source} · {when}" if when else f"{title}{flag} — {source}"]
    meta = why_line(item)
    if meta:
        out.append(f"   ↳ {meta}")
    if item["summary"]:
        out.append(f"   {clip(item['summary'], 200)}")
    if item["url"]:
        out.append(f"   {item['url']}")
    return out


LINE_RENDERERS = {"github": line_github, "generic": line_generic}


def render_list(
    source: dict,
    kind: dict,
    items: list[dict],
    highlights: list[dict],
    rest: list[dict],
    health: list[str],
    markdown: bool,
) -> str:
    label = source.get("label") or source["id"]
    line = LINE_RENDERERS[kind["line"]]
    if kind["line"] == "github":
        title = "🔥 *trending on GitHub*" if markdown else "🔥 trending on GitHub"
        lines = [
            f"{title} — week {iso_week()} · {len(items)} repos from {label}",
            f"_{now_iso()[:10]} · momentum = stars gained since last snapshot_",
            "",
        ]
    else:
        lines = [
            f"📡 {'*' + label + '*' if markdown else label} — {len(items)} items · "
            f"{now_iso()[:16].replace('T', ' ')}",
            "",
        ]
    if highlights:
        lines.append(f"⭐ *might interest you* — {len(highlights)} of {len(items)} · _by priority_")
        for item in highlights:
            lines.extend(line(item, markdown))
            lines.append("")
    else:
        lines.extend(["_⭐ nothing matched the interest profile_", ""])
    if rest:
        lines.append(f"⋯ *rest* — {len(rest)}")
        for item in rest:
            flag = " 🆕" if item.get("is_new") else ""
            title = item["extra"].get("slug") or item["title"]
            if kind["line"] == "github":
                meta = " · ".join(x for x in [item["extra"].get("lang"), fmt_stars(item)] if x)
                desc = clip(item["summary"], 70)
                lines.append(
                    f"#{item['rank']} `{title}`{flag} · {meta}" + (f" — {desc}" if desc else "")
                )
            else:
                desc = clip(item["summary"], 70)
                lines.append(f"- {title}{flag}" + (f" — {desc}" if desc else ""))
        lines.append("")
    lines.extend(["—", "health: " + " · ".join(health)])
    return "\n".join(lines)


def render_new(
    source: dict, kind: dict, fresh: list[dict], health: list[str], markdown: bool
) -> str:
    label = source.get("label") or source["id"]
    line = LINE_RENDERERS[kind["line"]]
    lines = [
        f"📡 {'*' + label + '*' if markdown else label} — {len(fresh)} new · "
        f"{now_iso()[:16].replace('T', ' ')}",
        "",
    ]
    for item in fresh:
        lines.extend(line(item, markdown))
        lines.append("")
    lines.extend(["—", "health: " + " · ".join(health)])
    return "\n".join(lines)


# ------------------------------------------------------------------ alert gate

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "with",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "its",
    "this",
    "that",
    "these",
    "those",
    "after",
    "before",
    "over",
    "under",
    "into",
    "about",
    "than",
    "then",
    "but",
    "not",
    "no",
    "you",
    "we",
    "they",
    "le",
    "la",
    "les",
    "des",
    "du",
    "de",
    "un",
    "une",
    "et",
    "ou",
    "en",
    "au",
    "aux",
    "pour",
    "par",
    "sur",
    "dans",
    "avec",
    "sans",
    "est",
    "sont",
    "apres",
    "avant",
    "plus",
    "moins",
    "son",
    "sa",
    "ses",
    "ce",
    "cette",
    "ces",
    "qui",
    "que",
    "dont",
    "il",
    "elle",
    "ils",
    "elles",
}

LEDGER_BUFFER: list[dict] = []


def tokens_of(text: str) -> set[str]:
    out = set()
    for raw in re.findall(r"[a-z0-9]+", fold(text)):
        if len(raw) < 3 or raw in _STOP:
            continue
        out.add(raw[:-1] if len(raw) > 4 and raw.endswith(("s", "x")) else raw)
    return out


def cluster_items(items: list[dict], window: timedelta, sim_threshold: float) -> list[dict]:
    """Group items that carry the same story. Compare to the cluster LEADER, never single-link."""
    when = now_dt()
    prepared = []
    for item in items:
        published = parse_iso(item.get("published")) or parse_iso(item.get("first_seen")) or when
        published = min(published, when)
        if when - published <= window:
            prepared.append((published, item))
    prepared.sort(key=lambda pair: (pair[0], pair[1]["id"]))

    token_sets = [tokens_of(item["title"] or item["summary"]) for _, item in prepared]
    doc_freq: dict[str, int] = {}
    for tokens in token_sets:
        for token in tokens:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    total = max(1, len(prepared))

    def weight(token: str) -> float:
        # log IDF, not 1+N/df: with the linear form a rare token's weight grows with the number of
        # unrelated items in the window, so a quiet day clusters fine and a busy one does not.
        return math.log(1.0 + total / max(1, doc_freq.get(token, 1)))

    def similarity(a: set[str], b: set[str]) -> tuple[float, int]:
        shared = a & b
        if len(shared) < 2:
            return 0.0, len(shared)
        numerator = sum(weight(t) for t in shared)
        denominator = min(sum(weight(t) for t in a), sum(weight(t) for t in b)) or 1.0
        return numerator / denominator, len(shared)

    clusters: list[dict] = []
    for (published, item), tokens in zip(prepared, token_sets):
        best, best_sim = None, 0.0
        for cluster in clusters:
            score, shared = similarity(tokens, cluster["anchor"])
            if shared >= 2 and score >= sim_threshold and score > best_sim:
                best, best_sim = cluster, score
        if best is None:
            clusters.append(
                {
                    "tokens": tokens,
                    "anchor": tokens,
                    "anchor_id": item["id"],
                    "items": [item],
                    "first_seen": published,
                }
            )
        else:
            best["items"].append(item)
            # The metric is containment, so it is asymmetric: comparing everything to the FIRST item
            # makes the result depend on feed order. Anchor on the shortest headline instead, which is
            # the most specific phrasing ("Seisme au Japon" is inside "Japon : seisme de magnitude 7").
            if (len(tokens), item["id"]) < (len(best["anchor"]), best["anchor_id"]):
                best["anchor"], best["anchor_id"] = tokens, item["id"]
    return clusters


def cluster_summary(cluster: dict) -> dict:
    outlets = sorted({item["extra"].get("feed") or item["source"] for item in cluster["items"]})
    best_tier = min(int(item["extra"].get("tier") or 2) for item in cluster["items"])
    counts: dict[str, int] = {}
    for item in cluster["items"]:
        for token in tokens_of(item["title"]):
            counts[token] = counts.get(token, 0) + 1
    core = sorted([t for t, n in counts.items() if n >= 2], key=lambda t: (-counts[t], t))[:12]
    return {
        "outlets": outlets,
        "best_tier": best_tier,
        "core": core,
        "items": cluster["items"],
        "first_seen": cluster["first_seen"],
        "text": " ".join(f"{i['title']} {i['summary']}" for i in cluster["items"]),
    }


def event_id(summary: dict) -> str:
    stamp = summary["first_seen"].strftime("%Y-%m-%d")
    # A cluster whose members share no two tokens has an empty core: identify it by its first item,
    # otherwise every such cluster collapses into one event (they used to share the id "sha1('')").
    key = " ".join(sorted(summary["core"])) or min(i["id"] for i in summary["items"])
    return hashlib.sha1((key + " " + stamp).encode()).hexdigest()[:10]


def same_event(event: dict, summary: dict) -> bool:
    ids = {item["id"] for item in summary["items"]}
    if ids & set(event.get("items") or []):
        return True
    core, old = set(summary["core"]), set(event.get("core") or [])
    if len(core) < 2 or len(old) < 2:
        return False
    shared = len(core & old)
    # One shared name is not the same story: require three tokens, or a real Jaccard overlap.
    return shared >= 3 or shared / len(core | old) >= 0.5


def gate_lane(summary: dict, gate: dict, profile: dict) -> str | None:
    """A: corroborated, tier-1 present, critical lexicon hit. B: everyone is running it."""
    outlets = len(summary["outlets"])
    text = fold(summary["text"])
    terms = [
        t for t in ((profile.get("alert_terms") or {}).get("critical") or []) if str(t).strip()
    ]
    critical_hit = any(_hits(text, term) for term in terms)
    if outlets >= int(gate.get("min_outlets", 3)) and summary["best_tier"] <= 1 and critical_hit:
        if not any(_rule_hits(text, rule) for rule in profile.get("dislike") or []):
            return "A"
    if outlets >= int(gate.get("strong_outlets", 5)):
        return "B"
    return None


def alert_payload(summary: dict) -> dict:
    """The minimal snapshot an alert needs — small enough to keep on a held event for hours."""
    lead = summary["items"][0]
    return {
        "title": lead["title"],
        "url": lead["url"],
        "summary": lead["summary"],
        "other_titles": [i["title"] for i in summary["items"][1:4] if i["title"] != lead["title"]],
        "outlets": list(summary["outlets"]),
    }


def render_alert(source: dict, payload: dict, escalation: bool) -> str:
    label = source.get("label") or source["id"]
    head = (
        "🚨 *"
        + ("escalating — " if escalation else "")
        + f"{label}* · {len(payload['outlets'])} outlets · {now_iso()[:16].replace('T', ' ')}"
    )
    lines = [head, f"*{payload['title']}*"]
    lines.extend(f"· {title}" for title in payload.get("other_titles") or [])
    lines.append(f"   ↳ {', '.join(payload['outlets'][:6])}")
    if payload.get("summary"):
        lines.append(f"   {clip(payload['summary'], 200)}")
    if payload.get("url"):
        lines.append(f"   {payload['url']}")
    return "\n".join(lines)


def in_quiet(quiet: str | None, tz: ZoneInfo) -> bool:
    if not quiet:
        return False
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$", str(quiet))
    if not match:
        raise ConfigError(f'quiet: {quiet!r} must look like "23:00-07:00"')
    start = int(match.group(1)) * 60 + int(match.group(2))
    end = int(match.group(3)) * 60 + int(match.group(4))
    local = now_dt().astimezone(tz)
    minute = local.hour * 60 + local.minute
    return start <= minute < end if start <= end else (minute >= start or minute < end)


def run_alert_source(
    source: dict, items: list[dict], snap: dict, profile: dict, tz: ZoneInfo, health: list[str]
) -> str:
    """Cluster -> gate -> event state machine -> at most one message per run."""
    gate = source.get("gate") or {}
    limits = source.get("limits") or {}
    window = parse_duration(gate.get("window", "6h")) or timedelta(hours=6)
    close_after = parse_duration(gate.get("close_after", "6h")) or timedelta(hours=6)
    remember = parse_duration(source.get("remember", "48h")) or timedelta(hours=48)
    steps = [int(x) for x in (gate.get("steps") or [3, 6, 10])]
    max_per_day = int(limits.get("max_per_day") or 5)
    gap = parse_duration(limits.get("min_gap", "20m")) or timedelta(minutes=20)

    events: dict = snap.setdefault("events", {})
    when = now_dt()
    summaries = [
        cluster_summary(c) for c in cluster_items(items, window, float(gate.get("sim", 0.45)))
    ]

    # 1. attach every multi-item cluster to an event; one that fails the gate is stored silently so a
    #    later corroborating headline can escalate it. A lone headline is not tracked at all.
    for summary in summaries:
        if len(summary["items"]) < 2:
            continue
        event = next((ev for ev in events.values() if same_event(ev, summary)), None)
        if event is None:
            ident = event_id(summary)
            event = events.setdefault(
                ident,
                {
                    "id": ident,
                    "core": summary["core"],
                    "items": [],
                    "outlets": [],
                    "best_tier": 2,
                    "first_seen": summary["first_seen"].isoformat(),
                    "last_seen": now_iso(),
                    "level": 0,
                    "alerted_at": None,
                    "status": "open",
                    "escalations": 0,
                },
            )
        event["core"] = summary["core"] or event.get("core") or []
        event["items"] = sorted(
            {*(event.get("items") or []), *(i["id"] for i in summary["items"])}
        )[:40]
        event["outlets"] = summary["outlets"]
        event["best_tier"] = summary["best_tier"]
        event["last_seen"] = now_iso()
        event["status"] = "open"
        event["_summary"] = summary

    # 2. close stale events; forget tombstones past `remember`. An event holding an unreleased alert
    #    stays open, otherwise quiet hours would silently drop it when the story ages out.
    for ident, event in list(events.items()):
        last = parse_iso(event.get("last_seen"))
        if (
            event.get("status") == "open"
            and last
            and when - last > close_after
            and not event.get("pending")
        ):
            event["status"] = "closed"
            event["closed_at"] = now_iso()
        closed_at = parse_iso(event.get("closed_at"))
        if event.get("status") == "closed" and closed_at and when - closed_at > remember:
            events.pop(ident, None)

    # 3. what may speak now
    today = when.astimezone(tz).strftime("%Y-%m-%d")
    budget = snap.setdefault("alerts", {"day": today, "count": 0, "held": 0})
    if budget.get("day") != today:
        budget.update({"day": today, "count": 0})
    last_alert = parse_iso(snap.get("last_alert_at"))
    quiet = in_quiet(limits.get("quiet"), tz)

    messages, deferred = [], 0

    def blocked(lane: str) -> bool:
        return (
            quiet
            or (budget["count"] >= max_per_day and lane != "B")
            or (last_alert is not None and when - last_alert < gap)
        )

    def emit(event: dict, payload: dict, level: int, escalation: bool, lane: str) -> None:
        nonlocal last_alert
        event["level"] = level
        event["alerted_at"] = now_iso()
        event["escalations"] = int(event.get("escalations") or 0) + (1 if escalation else 0)
        event.pop("pending", None)
        budget["count"] += 1
        snap["last_alert_at"] = now_iso()
        last_alert = when
        messages.append(render_alert(source, payload, escalation))
        LEDGER_BUFFER.append(
            {
                "run": now_iso(),
                "source": source["id"],
                "alert": event["id"],
                "level": level,
                "escalation": escalation,
                "outlets": len(payload["outlets"]),
            }
        )

    for event in events.values():
        if event.get("status") != "open":
            continue
        summary = event.get("_summary")
        if summary is not None:
            lane = gate_lane(summary, gate, profile)
            if lane is None:
                continue
            outlets = len(summary["outlets"])
            level = max([step for step in steps if outlets >= step] or [0])
            if event.get("alerted_at") is None:
                escalation = False
            elif level > int(event.get("level") or 0) and int(event.get("escalations") or 0) < 2:
                escalation = True
            else:
                continue  # same event, same level: stay silent
            payload = alert_payload(summary)
            if blocked(lane):
                # Hold the snapshot: by the time quiet hours end the items are out of the window, so a
                # held alert must render from what we saw, not from a re-cluster that no longer exists.
                event["pending"] = {
                    **payload,
                    "level": level,
                    "escalation": escalation,
                    "lane": lane,
                }
                deferred += 1
                continue
            emit(event, payload, level, escalation, lane)
        elif event.get("pending"):
            pending = event["pending"]
            if blocked(str(pending.get("lane") or "A")):
                deferred += 1
                continue
            emit(
                event, pending, int(pending.get("level") or 0), bool(pending.get("escalation")), "A"
            )

    for event in events.values():
        event.pop("_summary", None)

    if not messages:
        if deferred:
            health.append(f"🔇 {deferred} alert(s) held (quiet hours, daily cap or gap)")
        return ""
    if deferred:
        budget["held"] = int(budget.get("held") or 0) + deferred
    if budget.get("held"):
        messages.append(
            f"_held: {budget['held']} earlier alert(s) — quiet hours, daily cap or gap_"
        )
        budget["held"] = 0
    return "\n\n".join(messages)


# ---------------------------------------------------------------------- doctor


def doctor(home: Path) -> int:
    cfg = load_yaml(home / "sources.yaml")
    try:
        tz = ZoneInfo(str(cfg.get("tz") or "UTC"))
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"tz: {cfg.get('tz')!r} not found ({exc})")
    print(f"watchtower {SCRIPT_VERSION} — doctor")
    print(f"home  : {home}  ({HOME_KIND})")
    print(f"config: {home / 'sources.yaml'}")
    ok_all = True
    state = load_state(home / "state.json")
    for source in cfg.get("sources") or []:
        sid = source.get("id")
        if not sid:
            continue
        if not source.get("enabled", True):
            print(f"SKIP  {sid} (disabled)")
            continue
        kind = KINDS.get(source.get("kind", ""))
        if not kind:
            print(f"FAIL  {sid}: unknown kind {source.get('kind')!r}")
            ok_all = False
            continue
        started = time.time()
        try:
            items = kind["fetch"](source)
            check_items(source, items)
            print(f"OK    {sid}: {len(items)} items in {int((time.time() - started) * 1000)} ms")
        except FetchError as exc:
            ok_all = False
            print(f"FAIL  {sid}: {exc}")
        snap = (state.get("sources") or {}).get(sid) or {}
        sched = validate_schedule(source)
        if sched["every"] is None:
            print(
                f"      legacy (no every:)  last_ok={snap.get('last_ok') or 'never'}"
                f"  age={days_since(snap.get('last_ok')):.1f}d"
            )
            continue
        due_at = next_due(sched, tz, now_dt())
        overdue = days_since(snap.get("last_ok")) > 3 * sched["every"].total_seconds() / 86400
        at = ":".join(f"{n:02d}" for n in sched["at"]) if sched["at"] else ""
        print(
            f"      SCHED every={human_delta(sched['every'])}"
            f"{' at ' + at if at else ''}{' on ' + sched['on'] if sched['on'] else ''} {tz.key}"
            f"  last_attempt={snap.get('last_attempt') or 'never'}"
            f"  failures={snap.get('failures', 0)}"
            f"  next_due={due_at.isoformat()[:16] if due_at else '?'}"
            f"  {'OVERDUE' if overdue else 'due' if is_due(sched, snap, tz, now_dt()) else 'not due'}"
        )
    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = gh_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        rl = json.loads(http_get("https://api.github.com/rate_limit", timeout=15, headers=headers))[
            "resources"
        ]["core"]
        print(
            f"OK    github api: {rl['remaining']}/{rl['limit']} requests left "
            f"({'authenticated' if token else 'unauthenticated'})"
        )
    except Exception as exc:  # noqa: BLE001 - doctor reports, never raises
        ok_all = False
        print(f"FAIL  github api: {exc}")
    lock = Lock(home)
    with lock:
        lock_state = (
            "free (this run took it)"
            if lock.held
            else f"held by pid {(lock.holder or {}).get('pid')}"
        )
    print(f"lock  : {lock_state}")
    print("result:", "healthy" if ok_all else "DEGRADED")
    return 0 if ok_all else 1


# ------------------------------------------------------------------------ main


def run(args) -> int:
    global LEDGER_BUFFER
    home = HOME
    sources_cfg = home / "sources.yaml"
    interests_cfg = home / "interests.yaml"
    state_path = home / "state.json"

    cfg = load_yaml(sources_cfg)
    try:
        tz = ZoneInfo(str(cfg.get("tz") or "UTC"))
    except Exception as exc:  # noqa: BLE001
        raise ConfigError(f"tz: {cfg.get('tz')!r} not found ({exc})")
    sources = [s for s in cfg.get("sources") or [] if isinstance(s, dict) and s.get("id")]
    if args.source:
        sources = [s for s in sources if s["id"] in args.source]
    profile = load_yaml(interests_cfg)

    state = load_state(state_path)
    dry = args.dry_run or args.json  # --json is a read-only probe for other agents
    rendered: list[str] = []
    problems: list[str] = []
    dirty = False
    collected: dict[str, list[dict]] = {}
    failed_any = False
    gh_auth = None

    for source in sources:
        sid = source["id"]
        if not source.get("enabled", True):
            continue
        kind = KINDS.get(source.get("kind", ""))
        if not kind:
            problems.append(f"❌ {sid}: unknown kind {source.get('kind')!r}")
            failed_any = True
            continue
        sched = validate_schedule(source)
        snap = state.setdefault("sources", {}).setdefault(sid, {})
        if args.due and not args.force and not is_due(sched, snap, tz, now_dt()):
            continue  # skipped: no write, no network, no gh subprocess
        if not args.due and not args.source and not args.force and sched["every"] is not None:
            # A plain run is the legacy weekly wrapper: it must not fire a 15-minute news source.
            continue
        src_health: list[str] = []
        if not dry:
            snap["last_attempt"] = now_iso()
            snap["failures"] = int(snap.get("failures") or 0) + 1
            snap.setdefault("fail_since", now_iso())
            save_state(state_path, state)
            dirty = True

        try:
            items = kind["fetch"](source)
            check_items(source, items)
        except FetchError as exc:
            failed_any = True
            if not dry:
                append_ledger(home, {"run": now_iso(), "source": sid, "failed": str(exc)[:200]})
            problems.extend(notify_failure(sid, source, snap, str(exc)))
            continue
        except Exception as exc:  # noqa: BLE001 - one bad source must not kill the run
            failed_any = True
            if not dry:
                append_ledger(
                    home,
                    {
                        "run": now_iso(),
                        "source": sid,
                        "failed": f"{type(exc).__name__}: {exc}"[:200],
                    },
                )
            problems.extend(notify_failure(sid, source, snap, f"{type(exc).__name__}: {exc}"))
            continue

        mode = source.get("mode") or kind["mode"]
        enrich = kind.get("enrich")
        if enrich:
            if gh_auth is None and enrich is enrich_github:
                gh_auth = gh_token()
            enriched, gh_err = enrich(items, token=gh_auth)
            src_health.append(
                f"✅ {sid}: {len(items)} items"
                + (f" · github stars {enriched}/{len(items)}" if enriched else "")
            )
            if gh_err:
                src_health.append(f"⚠️ {sid}: {clip(gh_err, 70)}")
        else:
            src_health.append(f"✅ {sid}: {len(items)} items")

        seen = snap.get("items") or snap.get("repos") or {}
        for item in items:
            prev = seen.get(item["id"])
            stars = item["extra"].get("stars")
            if (
                prev
                and prev.get("stars") is not None
                and stars is not None
                and days_since(prev.get("last_seen")) <= 14
            ):
                item["gained"] = stars - prev["stars"]
            else:
                item["gained"] = None
            item["is_new"] = prev is None
            item["first_seen"] = (prev or {}).get("first_seen") or now_iso()[:10]
        collected[sid] = items

        block = ""
        printed: list[dict] = items
        if mode == "alert":
            block = run_alert_source(source, items, snap, profile, tz, src_health)
        elif mode == "new":
            take = int(source.get("take") or 0)
            fresh = sorted(
                [i for i in items if i.get("is_new")],
                key=lambda i: i.get("published") or "",
                reverse=True,
            )
            printed = fresh[:take] if take else fresh
            if len(fresh) > len(printed):
                src_health.append(
                    f"⏳ {len(fresh) - len(printed)} more new item(s) queued for the next run"
                )
            for item in printed:
                score_item(item, profile, sid)
            if printed:
                block = render_new(source, kind, printed, src_health, args.format == "markdown")
        else:
            highlights, rest = split_items(items, profile, sid)
            printed = highlights + rest
            block = render_list(
                source, kind, items, highlights, rest, src_health, args.format == "markdown"
            )

        signature = digest_signature(items, interests_cfg)
        changed = signature != snap.get("digest_hash")

        if not dry:
            for item in printed:
                prev = seen.get(item["id"]) or {}
                seen[item["id"]] = {
                    "stars": item["extra"].get("stars", prev.get("stars")),
                    "first_seen": prev.get("first_seen") or now_iso()[:10],
                    "last_seen": now_iso()[:10],
                    "runs": int(prev.get("runs", 0)) + 1,
                }
            remember = parse_duration(source.get("remember"))
            if remember:
                cutoff = now_dt() - remember
                for key, meta in list(seen.items()):
                    last = parse_iso(meta.get("last_seen"))
                    if last and last < cutoff:
                        seen.pop(key, None)
            snap["items"] = seen
            snap["repos"] = seen  # dual-write for one release, then drop
            snap["digest_hash"] = signature
            snap["last_run"] = now_iso()
            snap["last_ok"] = now_iso()
            if snap.get("notified_at"):
                snap.pop("notified_at")
                src_health.append(f"✅ {sid}: back after {snap.get('failures', 0)} failed run(s)")
            snap["failures"] = 0
            snap.pop("fail_since", None)
            snap["last_count"] = len(items)
            append_ledger(
                home,
                {
                    "run": now_iso(),
                    "source": sid,
                    "mode": mode,
                    "count": len(items),
                    "printed": bool(block),
                    "changed": changed,
                },
            )
        if block and (mode != "list" or changed or args.force or dry):
            rendered.append(block)
        if not dry:
            dirty = True

    if not dry:
        for record in LEDGER_BUFFER:
            append_ledger(home, record)
    LEDGER_BUFFER = []
    body = "\n\n".join(rendered)

    if args.json:
        # A read-only probe for other agents: --json must never consume items or fire state changes.
        print(
            json.dumps(
                {
                    "generated": now_iso(),
                    "home": str(home),
                    "sources": {
                        sid: [
                            {
                                "id": i["id"],
                                "title": i["title"],
                                "url": i["url"],
                                "summary": i["summary"],
                                "published": i["published"],
                                "score": i.get("score"),
                                "whys": i.get("whys", []),
                                "extra": i["extra"],
                            }
                            for i in items
                        ]
                        for sid, items in collected.items()
                    },
                },
                indent=1,
                ensure_ascii=False,
            )
        )
        return 1 if failed_any else 0

    if failed_any:
        parts = [p for p in (body, "\n".join(problems)) if p]
        if parts:
            print("\n\n".join(parts))
            sys.stdout.flush()
        if not dry and dirty:
            save_state(state_path, state)
        # Exit 1 only when something was actually printed: an empty message plus rc=1 reads as a
        # broken cron job, and a threshold-throttled failure is already in the ledger.
        return 1 if parts else 0

    if not body:
        # Nothing due, nothing to say: leave state.json untouched so a skipped tick is provably a no-op.
        if not dry and dirty:
            save_state(state_path, state)
        return 0

    print(body)
    sys.stdout.flush()
    if not dry:
        state.setdefault("runs", []).append({"run": now_iso(), "delivered": True})
        state["runs"] = state["runs"][-50:]
        save_state(state_path, state)
    return 0


def notify_failure(sid: str, source: dict, snap: dict, message: str) -> list[str]:
    """A dead source must surface — but not on every tick of a 15-minute source."""
    sched = validate_schedule(source)
    frequent = sched["every"] is not None and sched["every"] < timedelta(days=1)
    threshold = 3 if frequent else 1
    failures = int(snap.get("failures") or 0)
    notified = parse_iso(snap.get("notified_at"))
    if failures >= threshold and (notified is None or now_dt() - notified >= timedelta(hours=24)):
        snap["notified_at"] = now_iso()
        return [f"❌ {sid}: {message} (failure {failures})"]
    return []


def digest_signature(items: list[dict], interests_cfg: Path) -> str:
    """Silence is semantic: ids, summaries, scores and the profile — never the rendered text."""
    material = json.dumps(
        [
            {
                "id": i["id"],
                "desc": i.get("summary", ""),
                "score": i.get("score", 0),
                "highlight": bool(i.get("highlight")),
                "rank": i.get("rank"),
            }
            for i in items
        ],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(
        (hashlib.sha256(interests_cfg.read_bytes()).hexdigest() + material).encode()
    ).hexdigest()


def explain(home: Path, needle: str) -> int:
    cfg = load_yaml(home / "sources.yaml")
    profile = load_yaml(home / "interests.yaml", required=False)
    low = needle.lower()
    found = False
    for source in cfg.get("sources") or []:
        kind = KINDS.get(source.get("kind", ""))
        if not kind:
            continue
        try:
            items = kind["fetch"](source)[:60]
        except FetchError as exc:
            print(f"watchtower: {source['id']}: {exc}", file=sys.stderr)
            continue
        for item in items:
            if (
                low in item["id"].lower()
                or low in item["title"].lower()
                or low in (item["url"] or "").lower()
            ):
                found = True
                score_item(item, profile, source["id"])
                thresholds = profile.get("thresholds") or {}
                per_source = (thresholds.get("per_source") or {}).get(source["id"]) or {}
                print(f"{item['title']}  [{source['id']}]")
                print(f"  haystack: {item_text(item)[:220]}")
                for why in item["whys"]:
                    print(f"  + {why['id']}({why['weight']}) via {', '.join(why['hits'])}")
                for why in item["demoted"]:
                    print(
                        f"  - {why['id']}({why['weight']}) via {', '.join(why['hits']) or 'rule'}"
                    )
                print(
                    f"  score   : {item['score']} (highlight at "
                    f"{per_source.get('highlight', thresholds.get('highlight', 4))}, "
                    f"cap {per_source.get('max_highlight', '-')})"
                )
                print(f"  verdict : {'HIGHLIGHT' if item['highlight'] else 'rest'}")
                print(f"  url     : {item['url']}")
    if not found:
        print(f"watchtower: no item matched {needle!r}")
        return 1
    return 0


def _on_watchdog(signum, frame):  # noqa: ARG001
    raise WatchdogTimeout(f"run exceeded {WATCHDOG_SECONDS}s")


def main() -> int:
    global _NOW, HOME, HOME_KIND
    parser = argparse.ArgumentParser(
        description="deterministic feed collector + interest-scored digest"
    )
    parser.add_argument("--home", help="config/state directory (overrides $WATCHTOWER_HOME)")
    parser.add_argument(
        "--due", action="store_true", help="only sources whose `every:` slot has elapsed"
    )
    parser.add_argument("--source", action="append", help="run only this source id (repeatable)")
    parser.add_argument(
        "--doctor", action="store_true", help="probe sources and print schedule health"
    )
    parser.add_argument(
        "--force", action="store_true", help="print even if the content is unchanged"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--explain", metavar="ID|URL", help="print the scoring decision for one item"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="read only: never write state or ledger"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "text"],
        default="markdown",
        help="output flavour (default markdown, what the live Telegram job renders)",
    )
    parser.add_argument(
        "--now", help="pretend it is this time (ISO 8601); needs --dry-run or --home"
    )
    args = parser.parse_args()

    if args.now:
        _NOW = parse_iso(args.now)
        if _NOW is None:
            raise ConfigError(f"--now {args.now!r} is not an ISO timestamp")
        if not args.dry_run and not args.home:
            raise ConfigError(
                "--now needs --dry-run or an explicit --home (never freeze a live install)"
            )
    HOME, HOME_KIND = resolve_home(args.home)
    if args.now and not args.dry_run and HOME_KIND.startswith("legacy"):
        raise ConfigError("refusing --now against the live legacy home without --dry-run")

    if args.doctor:
        return doctor(HOME)
    if args.explain:
        return explain(HOME, args.explain)

    lock = Lock(HOME)
    with lock:
        if not lock.held:
            holder = lock.holder or {}
            if not args.dry_run:
                append_ledger(
                    HOME, {"run": now_iso(), "skip": "locked", "holder": holder.get("pid")}
                )
            print(
                f"watchtower: another run holds the lock (pid {holder.get('pid')}); skipping",
                file=sys.stderr,
            )
            return 0
        signal.signal(signal.SIGALRM, _on_watchdog)
        signal.alarm(WATCHDOG_SECONDS)
        try:
            return run(args)
        finally:
            signal.alarm(0)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WatchdogTimeout as exc:
        print(f"watchtower: {exc}", file=sys.stderr)
        raise SystemExit(3)
    except FetchError as exc:
        print(f"watchtower: {exc}", file=sys.stderr)
        raise SystemExit(3)

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
"""watchtower — deterministic collector for "what changed on the internet" digests.

One script, one source list, one shared interest profile, one state file.
No LLM calls: every item is scored in code, so a run costs nothing and can be
audited by reading the output.

    uv run --no-project watchtower.py            # collect + print the digest
    uv run --no-project watchtower.py --doctor   # probe every source, print OK/FAIL
    uv run --no-project watchtower.py --force    # print even if nothing changed

Layout (see README.md):
    <repo>/docs/home-server/watchtower/   code + example configs  (committed)
    $WATCHTOWER_HOME (default ~/.hermes/watchtower/)
        sources.yaml      the live source list
        interests.yaml    the live interest profile  (personal — never committed)
        state.json        seen slugs + star snapshots
        ledger/           one jsonl file per run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

UA = "watchtower/0.1 (personal feed digest; contact: local)"
HOME = Path(os.environ.get("WATCHTOWER_HOME", str(Path.home() / ".hermes" / "watchtower")))
SCRIPT_VERSION = "0.1"


# --------------------------------------------------------------------------- io


class FetchError(RuntimeError):
    """A source failed. Never silently degrade into 'no news'."""


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


def load_yaml(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"watchtower: missing config file {path}")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"watchtower: {path} must contain a YAML mapping")
    return data


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"sources": {}, "runs": []}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"watchtower: corrupt state file {path}: {exc}")


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True))
    tmp.replace(path)


def append_ledger(home: Path, record: dict) -> None:
    ledger_dir = home / "ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False)
    with (ledger_dir / f"{datetime.now(timezone.utc):%Y-%m}.jsonl").open("a") as fh:
        fh.write(line + "\n")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def days_since(stamp: str | None) -> float:
    """Age in days of a stored ISO date/short date, or a large number when unknown."""
    if not stamp:
        return 9999.0
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            when = datetime.strptime(stamp.replace("Z", "+0000"), fmt)
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - when).total_seconds() / 86400
    return 9999.0


def iso_week() -> str:
    y, w, _ = datetime.now(timezone.utc).isocalendar()
    return f"{y}-W{w:02d}"


# --------------------------------------------------------------------- sources


def fetch_trendshift(source: dict) -> list[dict]:
    """trendshift.io listing page -> normalised items.

    The page is SSR and carries one schema.org ItemList in application/ld+json.
    Verified fields per item: name (owner/repo), description, codeRepository,
    programmingLanguage, dateCreated, dateModified.
    """
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
    items = payload.get("itemListElement") or []
    if not isinstance(items, list) or not items:
        raise FetchError(f"{source['url']} -> ItemList is empty")

    limit = int(source.get("limit") or len(items))
    out = []
    for entry in items[:limit]:
        item = entry.get("item") or {}
        slug = (item.get("name") or "").strip()
        if "/" not in slug:
            continue
        out.append(
            {
                "source": source["id"],
                "id": slug.lower(),
                "slug": slug,
                "rank": entry.get("position"),
                "title": slug,
                "description": (item.get("description") or "").strip(),
                "url": item.get("codeRepository") or item.get("url") or "",
                "lang": (item.get("programmingLanguage") or "").strip(),
                "source_url": entry.get("url") or "",
                "created": (item.get("dateCreated") or "")[:10],
                "updated": (item.get("dateModified") or "")[:10],
            }
        )
    if not out:
        raise FetchError(f"{source['url']} -> parsed 0 valid repos out of {len(items)} entries")
    return out


FETCHERS = {"trendshift_jsonld": fetch_trendshift}


def check_items(source: dict, items: list[dict]) -> None:
    """A listing that got suspiciously small is a broken extractor, not 'no news'."""
    min_items = int(source.get("min_items") or 0)
    if min_items and len(items) < min_items:
        raise FetchError(
            f"{source['url']} -> only {len(items)} items, expected at least {min_items} (schema drift?)"
        )


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
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        token = (proc.stdout or "").strip()
        if proc.returncode == 0 and token:
            return token
    return None


def enrich_github(items: list[dict], *, token: str | None = None) -> tuple[int, str | None]:
    """Add stars + repo topics to items in place. Returns (enriched_count, error)."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    ok = 0
    err = None
    for item in items:
        try:
            raw = http_get(
                f"https://api.github.com/repos/{item['slug']}", timeout=20, headers=headers
            )
            data = json.loads(raw)
            item["stars"] = data.get("stargazers_count")
            item["topics"] = data.get("topics") or []
            item["fork"] = bool(data.get("fork"))
            item["archived"] = bool(data.get("archived"))
            if not item["description"]:
                item["description"] = (data.get("description") or "").strip()
            if not item["lang"] and data.get("language"):
                item["lang"] = data["language"]
            ok += 1
        except FetchError as exc:
            err = str(exc)
            if "HTTP 403" in err or "HTTP 429" in err:
                break  # rate limited: stop hammering, report it
        except json.JSONDecodeError:
            err = f"{item['slug']}: github returned non-JSON"
    return ok, err


# ---------------------------------------------------------------- interest

_SHORT_TOKEN = re.compile(r"^[a-z0-9]{1,5}$")


def _hits(haystack: str, token: str) -> bool:
    token = token.lower().strip()
    if not token:
        return False
    if _SHORT_TOKEN.match(token):
        return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) is not None
    return token in haystack


def _rule_hits(haystack: str, rule: dict) -> list[str]:
    tokens = [*rule.get("keywords", []), *rule.get("topics", [])]
    return [t for t in tokens if _hits(haystack, str(t))]


def score_item(item: dict, profile: dict, source_id: str) -> dict:
    """Attach score / matched rules / demotions deterministically."""
    haystack = " ".join(
        [
            item.get("slug", ""),
            item.get("description", ""),
            item.get("lang", ""),
            " ".join(item.get("topics") or []),
        ]
    ).lower()

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

    blocked_langs = [str(x).lower() for x in (profile.get("language", {}) or {}).get("block", [])]
    if item.get("lang", "").lower() in blocked_langs:
        demoted.append({"id": "language", "weight": 0, "hits": [item.get("lang")]})

    thresholds = profile.get("thresholds") or {}
    per_source = (thresholds.get("per_source") or {}).get(source_id) or {}
    highlight_at = int(per_source.get("highlight", thresholds.get("highlight", 4)))
    if item.get("archived"):
        demoted.append({"id": "archived", "weight": 0, "hits": []})
        score = min(score, highlight_at - 1)

    item["score"] = score
    item["whys"] = whys
    item["demoted"] = demoted
    item["highlight"] = bool(whys) and score >= highlight_at and not item.get("archived")
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
        demoted = highlights[int(cap) :]
        for item in demoted:
            item["highlight"] = False
        highlights = highlights[: int(cap)]
        rest = sorted(rest + demoted, key=lambda i: i.get("rank") or 999)
    return highlights, rest


# ------------------------------------------------------------------- render


def clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def fmt_stars(item: dict) -> str:
    stars = item.get("stars")
    if stars is None:
        return "★?"
    gained = item.get("gained")
    base = f"★{stars / 1000:.1f}k".replace(".0k", "k") if stars >= 1000 else f"★{stars}"
    if gained:
        base += f" (+{gained})"
    elif gained is not None:
        base += " (+0)"
    return base


def render(
    source: dict, items: list[dict], highlights: list[dict], rest: list[dict], health: list[str]
) -> str:
    label = source.get("label") or source["id"]
    lines = [
        f"🔥 *trending on GitHub* — week {iso_week()} · {len(items)} repos from {label}",
        f"_{now_iso()[:10]} · momentum = stars gained since last snapshot_",
        "",
    ]
    if highlights:
        lines.append(f"⭐ *might interest you* — {len(highlights)} of {len(items)} · _by priority_")
        for item in highlights:
            whys = " · ".join(f"{w['id']}({w['weight']})" for w in item["whys"])
            flag = " 🆕" if item.get("is_new") else ""
            head = f"`{item['slug']}`{flag} — {fmt_stars(item)} · trend #{item['rank']}"
            meta = " · ".join(x for x in [item.get("lang"), whys] if x)
            lines.append(head)
            if meta:
                lines.append(f"   ↳ {meta}")
            if item.get("description"):
                lines.append(f"   {clip(item['description'], 150)}")
            if item.get("url"):
                lines.append(f"   {item['url']}")
            lines.append("")
    else:
        lines.append("_⭐ nothing matched the interest profile this week_")
        lines.append("")

    if rest:
        lines.append(f"⋯ *rest* — {len(rest)}")
        for item in rest:
            flag = " 🆕" if item.get("is_new") else ""
            meta = " · ".join(x for x in [item.get("lang"), fmt_stars(item)] if x)
            desc = clip(item.get("description", ""), 70)
            tail = f" — {desc}" if desc else ""
            lines.append(f"#{item['rank']} `{item['slug']}`{flag} · {meta}{tail}")
        lines.append("")

    lines.append("—")
    lines.append("health: " + " · ".join(health))
    return "\n".join(lines)


# -------------------------------------------------------------------- doctor


def doctor(sources_cfg: Path, home: Path) -> int:
    print(f"watchtower {SCRIPT_VERSION} — doctor")
    print(f"config: {sources_cfg}")
    print(f"state : {home / 'state.json'}")
    ok_all = True
    cfg = load_yaml(sources_cfg)
    for source in cfg.get("sources") or []:
        if not source.get("enabled", True):
            print(f"SKIP  {source['id']} (disabled)")
            continue
        fetcher = FETCHERS.get(source.get("kind", ""))
        if not fetcher:
            print(f"FAIL  {source['id']}: unknown kind {source.get('kind')!r}")
            ok_all = False
            continue
        started = time.time()
        try:
            items = fetcher(source)
            ms = int((time.time() - started) * 1000)
            print(f"OK    {source['id']}: {len(items)} items in {ms} ms")
        except FetchError as exc:
            ok_all = False
            print(f"FAIL  {source['id']}: {exc}")
    try:
        headers = {"Accept": "application/vnd.github+json"}
        token = gh_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        raw = http_get("https://api.github.com/rate_limit", timeout=15, headers=headers)
        rl = json.loads(raw)["resources"]["core"]
        mode = "authenticated" if token else "unauthenticated"
        print(f"OK    github api: {rl['remaining']}/{rl['limit']} requests left ({mode})")
    except Exception as exc:  # noqa: BLE001 - doctor reports, never raises
        ok_all = False
        print(f"FAIL  github api: {exc}")
    state = load_state(home / "state.json")
    for sid, snap in (state.get("sources") or {}).items():
        print(
            f"state {sid}: last run {snap.get('last_run', 'never')} · {len(snap.get('repos', {}))} repos tracked"
        )
    print("result:", "healthy" if ok_all else "DEGRADED")
    return 0 if ok_all else 1


# ---------------------------------------------------------------------- main


def run(args) -> int:
    home = Path(args.home).expanduser()
    sources_cfg = home / "sources.yaml"
    interests_cfg = home / "interests.yaml"
    state_path = home / "state.json"

    cfg = load_yaml(sources_cfg)
    profile = load_yaml(interests_cfg)
    state = load_state(state_path)
    gh_auth = gh_token()

    rendered: list[str] = []
    health: list[str] = []
    changed_any = False

    for source in cfg.get("sources") or []:
        sid = source["id"]
        if not source.get("enabled", True):
            continue
        fetcher = FETCHERS.get(source.get("kind", ""))
        if not fetcher:
            health.append(f"❌ {sid}: unknown kind {source.get('kind')!r}")
            continue
        snap = state.setdefault("sources", {}).setdefault(sid, {"repos": {}})
        src_health: list[str] = []
        stale_days = days_since(snap.get("last_ok") or snap.get("last_run"))
        if stale_days > 10:
            src_health.append(
                f"⏰ last good run {int(stale_days)}d ago" if stale_days < 9999 else "⏰ first run"
            )
        try:
            items = fetcher(source)
            check_items(source, items)
        except FetchError as exc:
            snap["failures"] = int(snap.get("failures", 0)) + 1
            health.append(f"❌ {sid}: {exc}")
            continue
        snap["failures"] = 0

        enriched, gh_err = enrich_github(items, token=gh_auth)
        src_health.append(f"✅ {sid}: {len(items)} items")
        if enriched:
            src_health.append(f"github stars {enriched}/{len(items)}")
        if gh_err:
            src_health.append(f"⚠️ stars incomplete: {clip(gh_err, 70)}")

        seen_before = snap.get("repos") or {}

        for item in items:
            prev = seen_before.get(item["id"])
            # A stale snapshot (repo absent for weeks) would produce a fake spike: only
            # trust deltas measured against a recent sighting.
            if (
                prev
                and prev.get("stars") is not None
                and item.get("stars") is not None
                and days_since(prev.get("last_seen")) <= 14
            ):
                item["gained"] = item["stars"] - prev["stars"]
            else:
                item["gained"] = None
            item["is_new"] = prev is None

        highlights, rest = split_items(items, profile, sid)
        block = render(source, items, highlights, rest, src_health)
        # Silence is keyed on a SEMANTIC signature, not on the rendered text: stars move every
        # minute, so a text hash would re-send forever. The signature covers the item set, the
        # descriptions, the scores/the two-list split and the profile itself — so tuning
        # interests.yaml (or a repo rewriting its description) does produce a new message.
        signature = hashlib.sha256(
            (
                hashlib.sha256(interests_cfg.read_bytes()).hexdigest()
                + json.dumps(
                    [
                        {
                            "id": i["id"],
                            "desc": i.get("description", ""),
                            "score": i["score"],
                            "highlight": i["highlight"],
                            "rank": i.get("rank"),
                        }
                        for i in items
                    ],
                    sort_keys=True,
                    ensure_ascii=False,
                )
            ).encode()
        ).hexdigest()
        changed_any = changed_any or signature != snap.get("digest_hash")
        rendered.append(block)

        # state is written only after the text above is safely built
        for item in items:
            prev = seen_before.get(item["id"]) or {}
            seen_before[item["id"]] = {
                "stars": item.get("stars", prev.get("stars")),
                "first_seen": prev.get("first_seen") or now_iso()[:10],
                "last_seen": now_iso()[:10],
                "weeks": int(prev.get("weeks", 0)) + 1,
            }
        snap["repos"] = seen_before
        snap["digest_hash"] = signature
        snap["last_run"] = now_iso()
        snap["last_ok"] = now_iso() if not gh_err else snap.get("last_ok")
        snap["last_count"] = len(items)

        append_ledger(
            home,
            {
                "run": now_iso(),
                "source": sid,
                "count": len(items),
                "highlights": [i["slug"] for i in highlights],
                "rest": [i["slug"] for i in rest],
            },
        )

    # A source that returns zero items is a failure, not "no news".
    for source in cfg.get("sources") or []:
        sid = source["id"]
        snap = (state.get("sources") or {}).get(sid) or {}
        if snap.get("failures", 0) >= 3:
            health.append(
                f"💀 {sid} dead since {snap.get('dead_since') or snap.get('last_run') or '?'} ({snap['failures']} failed runs)"
            )

    body = "\n\n".join(rendered)

    if health:
        # A failing source must always be visible: a failure may never read as "no news",
        # so this branch prints (and exits 1) whether or not any other block changed.
        parts = [part for part in (body, "\n".join(health)) if part]
        print("\n\n".join(parts))
        sys.stdout.flush()
        save_state(state_path, state)
        return 1

    if not body:
        save_state(state_path, state)
        return 0

    if not changed_any and not args.force:
        # Nothing changed and nothing failed: stay silent (cron sends nothing).
        save_state(state_path, state)
        return 0
    print(body)
    sys.stdout.flush()
    state.setdefault("runs", []).append({"run": now_iso(), "delivered": True})
    state["runs"] = state["runs"][-50:]
    save_state(state_path, state)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="deterministic feed collector + interest-scored digest"
    )
    parser.add_argument("--home", default=str(HOME), help="config/state directory")
    parser.add_argument(
        "--doctor", action="store_true", help="probe every source and print OK/FAIL"
    )
    parser.add_argument(
        "--force", action="store_true", help="print even if the source content is unchanged"
    )
    args = parser.parse_args()
    home = Path(args.home).expanduser()
    if args.doctor:
        return doctor(home / "sources.yaml", home)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

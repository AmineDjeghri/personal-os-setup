# watchtower

One deterministic collector behind every "what's new on the internet" digest: it fetches each configured
source, scores every item against one shared interest profile, and prints only what is worth printing.
No LLM call in the hot path, no daemon, no web UI, no add-on — one script, one source list, one state file.

Three delivery shapes come out of the same pipeline:

- **`list`** — a whole ranked list, silent when the list has not changed (weekly GitHub trending).
- **`new`** — only items it has not shown you yet, capped per run (feeds, a backlog, deals).
- **`alert`** — only stories several outlets independently carried, with escalation and caps
  (important news: tell me once, not every tick).

Scheduling is data, not crontab lines: each source carries its own `every:` and the host runs one tick.

## Why not an add-on / not a third-party aggregator

- The digest is a scheduled fetch + filter + print. A tick cron runs that directly (`--no-agent`), so a
  NiceGUI app or an RSS server would only add a service to maintain.
- Third-party "agent internet access" CLIs are routers over upstream tools whose real value is the
  logged-in browser route — useless in a headless container, and cookie/session scraping risks bans.
  The two ideas worth borrowing are already here: an ordered backend per source class, and `--doctor`.

## Layout — three roles, deliberately split

| Role                                           | Lives in                   | Why                                        |
|------------------------------------------------|----------------------------|--------------------------------------------|
| Code + example configs                         | this directory (committed) | reviewable, versioned                      |
| Live config (`sources.yaml`, `interests.yaml`) | the watchtower home        | the interest profile is personal data      |
| State (`state.json`, `ledger/`, `.lock`)       | the watchtower home        | "already told you" memory + event history  |

```text
docs/home-server/watchtower/
  watchtower.py            PEP 723 script — uv run --no-project watchtower.py
  sources.example.yaml     schema for the live source list
  interests.example.yaml   schema for the live interest profile
<home>/                    resolved first-match-wins:
  sources.yaml             --home → $WATCHTOWER_HOME → $XDG_CONFIG_HOME/watchtower
  interests.yaml           → ~/.config/watchtower → legacy ~/.hermes/watchtower
  state.json  ledger/      (the legacy path is only used when it already holds sources.yaml)
```

Any host can run it — Hermes cron, a plain crontab, Claude Code, Codex, a laptop — because the script
never asks who is calling. The digest goes to **stdout** and the host decides where that lands.

## Run it

```bash
uv run --no-project watchtower.py                  # every enabled, non-scheduled source
uv run --no-project watchtower.py --due            # only sources whose `every:` slot elapsed (the tick)
uv run --no-project watchtower.py --source sports  # one source, ignore the clock
uv run --no-project watchtower.py --doctor         # probe every source + schedule health
uv run --no-project watchtower.py --json           # machine-readable items (read-only)
uv run --no-project watchtower.py --explain jellyfin   # why one item scored what it scored
uv run --no-project watchtower.py --dry-run        # read only: no state, no ledger
```

Exit codes: `0` ok **or** silent (nothing to say), `1` something failed and was printed, `2` config error,
`3` watchdog timeout. Silence is a feature: no output means nothing changed, nothing important, or
nothing new — never "the collector broke" (that prints).

## Scheduling (`every:`)

```yaml
tz: Europe/Paris          # only at:/quiet: use it; state, ledger and lock always stay UTC
sources:
  - id: critical-news
    every: 15m            # 15m · 1h · 1d · 1w ("every day" also parses); min 5m, max 4w
  - id: sports
    every: 1d
    at: "07:30"           # required for 1d/1w, quoted; local to tz
  - id: weekly
    every: 1w
    on: mon               # weekly alignment, default mon
```

- **One tick cron** (`*/5`) calls `--due`; the script decides which sources are eligible. Cron expressions
  are rejected on purpose: a second grammar plus cron's "a missed run is gone" rule is how schedules rot.
- **Slots, not elapsed time.** Due means "the last attempt predates the current slot" — `now - last_run >=
  15m` silently halves the cadence whenever a run starts a few seconds late.
- **Catch-up.** A weekly source three days late fires once on the next tick, then waits for its next slot.
  Missed slots are never replayed.
- **Backoff.** A failing source retries at 15/30/60/120/240/360 min, then every 6 h, and speaks once per
  24 h. A source that is skipped writes nothing and spawns no subprocess.
- **No `every:`** means legacy: only a plain run (no `--due`) picks it up, which is how an existing weekly
  cron keeps working untouched.

## Modes

- **`list`** (default) prints the ranked two-list digest and stays silent while the semantic signature is
  unchanged. Keeps item ids and star snapshots.
- **`new`** prints up to `take:` unseen items, newest first; silent when nothing is unseen. Keeps only what
  it printed, so the rest stays queued for the next run.
- **`alert`** prints one message per event with escalation capped; silent when the event is already known
  at that level. Keeps events, the daily budget and any quiet-hours hold.

`list` silence keys on a **semantic signature** — item ids + summaries + scores + the two-list split,
mixed with `interests.yaml` — never on rendered text (stars move every minute) and never on ids alone
(that would ignore a profile edit or a rewritten description).

## How scoring works (no LLM)

Every matching `like` rule adds its `weight` once; every matching `dislike` rule subtracts its weight. An
item is promoted to ⭐ when it matched at least one `like` rule **and** reaches `thresholds.highlight`
(optionally overridden per source, with a `max_highlight` cap). Demoted items are **never hidden** — they
drop into the rest list, and the rendered line names every rule that matched or demoted the item, so the
ranking is auditable and tuneable without reading the code. Matching is accent-insensitive ("seisme"
matches "séisme") over title + summary + tags + topics.

## The `alert` gate: what counts as "important"

Corroboration alone is not importance; three outlets can all run a celebrity story. Two lanes:

- **A** — `min_outlets` (3) distinct feeds **and** at least one tier-1 feed **and** a hit on your own
  `alert_terms.critical` lexicon, with no dislike rule matching.
- **B** — `strong_outlets` (5): everyone is running it, no lexicon needed.

Stories are clustered by IDF-weighted title overlap against the cluster's **shortest** headline (the
containment metric is asymmetric, so anchoring on the first-seen item made clustering depend on feed
order). Events then escalate 3 → 6 → 10 outlets, at most 2 re-alerts, close after `close_after` of silence
and stay tombstoned for `remember:` so a late outlet cannot reopen them. Caps: `max_per_day`, `min_gap`,
and `quiet:` hours that **hold and batch** — a held alert keeps its own snapshot, so it is still delivered
at 07:00 even though the story has aged out of the window by then.

**Partial blindness is a failure.** If fewer than `min_feeds_ok` feeds answer, the source fails instead of
reporting silence: with two of six feeds up, "3 outlets" can never be reached and silence would be a lie.

## Sources

`kind: trendshift_jsonld` (GitHub trending) and `kind: rss` (RSS 2.0 / Atom, either one `url:` or a
`feeds:` list with `id`/`tier`). Adding one is a YAML edit; a new kind is one `fetch_*` function plus a
`KINDS` entry and a `line()` renderer.

**trendshift.io (verified 2026-10):** the public listing pages are SSR and embed one schema.org `ItemList`
in `application/ld+json` — parse that payload, never the cards. `robots.txt` disallows `/api/`, so the paid
Signal API is off-limits. Stars come from the GitHub REST API (`GITHUB_TOKEN`/`GH_TOKEN` or the `gh` CLI:
5000/h instead of 60/h), and weekly momentum is stars now minus the stars stored by the previous run.

**Feeds (verified 2026-11, all 200):** Le Monde *une*, franceinfo, BBC World, Le Figaro, Guardian World,
France 24, hnrss.org/best, plus Google News RSS per query and locale for sports. **L'Équipe returns 403**
(bot protection) and Eurosport's feed is gone — do not build a sports source on either.

## Dedupe, state and health

- `state.json` keeps, per source: `last_attempt`, `last_ok`, `failures`, item ids with their star
  snapshot, `digest_hash`, and (alert mode) events with their level and daily budget.
- `--doctor` prints, per source: fetch OK/FAIL with timing, `every`/`at`/`on`/`tz`, `last_attempt`,
  `failures`, `next_due`, `OVERDUE` at 3× the period, plus GitHub headroom and whether the lock is free.
- `min_items` per source: fewer items than that count is a **failure** (schema drift), not "no news".
- Weekly momentum is only trusted against a sighting **within 14 days**, so a repo returning after a long
  absence shows no fake spike.
- The ledger (`ledger/YYYY-MM.jsonl`) gets one line per run and per alert — including failures that were
  throttled, so silence is still auditable.
- A tick that never runs cannot report its own absence; that is what an external heartbeat is for.

## Adding a source

1. Add an entry to `sources.yaml` with a `kind` that exists (`--doctor` proves it).
2. If the kind is new: write `fetch_<name>(source) -> list[dict]` returning the normalised item (`id`,
   `title`, `url`, `summary`, `published`, `rank`, `tags`, with per-kind fields under `extra`), register it
   in `KINDS` with a `line()` renderer, and treat "page loaded but parsed 0 items" as a `FetchError` — that
   is a broken extractor, not "no news".
3. Run it twice: the second run on unchanged input must print nothing. If it re-sends, the `id` (dedupe
   key) is wrong — fix that before adding the next source.

## Scheduled delivery (Hermes example)

```bash
hermes cron create "*/5 * * * *" --name watchtower-tick \
  --script watchtower_tick.sh --no-agent --deliver telegram
hermes cron create "0 8 * * 1" --name watchtower-weekly \
  --script watchtower_weekly.sh --no-agent --deliver telegram
```

Both wrappers live outside git and only pin `WATCHTOWER_HOME` (cron may run with a different `$HOME`): the
tick calls `watchtower.py --due`, the weekly one calls it plain so the legacy source behaves as before.

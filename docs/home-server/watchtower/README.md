# watchtower

One deterministic collector behind every "what's new on the internet" digest: it fetches each configured
source, scores every item against one shared interest profile, and prints a finished two-list digest —
"⭐ might interest you" and "everything else". No LLM call, no daemon, no add-on.

v1 ships **one source**: the weekly GitHub-trending list on trendshift.io. Adding a source is a YAML edit
(`sources.yaml`) once its `kind` exists; a new kind is one small `fetch_*` function.

## Why not an add-on / not a third-party aggregator

- The digest is a scheduled fetch+filter+print. Hermes cron runs that directly (`--no-agent`), so a
  NiceGUI app or an RSS server would only add a service to maintain.
- Third-party "agent internet access" CLIs (e.g. Agent-Reach) are routers over upstream tools whose real
  value is the logged-in browser route — useless in a headless container, and cookie/session scraping
  risks bans. The two ideas worth borrowing are already here: an ordered backend per source class, and a
  `--doctor` probe.

## Layout — three roles, deliberately split

| Role | Lives in | Why |
|---|---|---|
| Code + example configs | this directory (committed, public) | reviewable, versioned |
| Live config (`sources.yaml`, `interests.yaml`) | `~/.hermes/watchtower/` | the interest profile is personal data |
| State (`state.json`, `ledger/`) | `~/.hermes/watchtower/` | "already told you" memory + star snapshots |

```text
docs/home-server/watchtower/
  watchtower.py            PEP 723 script — uv run --no-project watchtower.py
  sources.example.yaml     schema for the live source list
  interests.example.yaml   schema for the live interest profile
~/.hermes/watchtower/      WATCHTOWER_HOME (override with --home or env)
  sources.yaml  interests.yaml  state.json  ledger/YYYY-MM.jsonl
~/.hermes/scripts/watchtower_weekly.sh   thin wrapper cron points at (outside git)
```

## Run it

```bash
uv run --no-project watchtower.py --doctor   # probe every source + the GitHub API, print OK/FAIL
uv run --no-project watchtower.py            # print the digest (silent when nothing changed)
uv run --no-project watchtower.py --force    # print even if the source content is identical
```

Exit codes: `0` ok (including "nothing changed, printed nothing"), `1` at least one source failed —
the failure text is printed too, so a cron delivery still reaches the chat with the reason in it.

## How scoring works (no LLM)

Every `like` rule that matches adds its `weight` (its *priority*, 1–5) once; every `dislike` rule
subtracts its weight. An item is promoted to ⭐ when it matched at least one `like` rule **and** its score
reaches `thresholds.highlight` (optionally overridden per source, with a `max_highlight` cap).
Excluded/demoted items are **never hidden** — they drop into the rest list. The matched rule ids are
printed on each promoted line, so the ranking is auditable and tuneable without reading the code.

The match text is `slug + description + language + GitHub topics`, so the same file will serve blog
headlines and catalog product names later; only the text fields fed to it change per source.

## Source: trendshift.io (verified 2026-10)

- No RSS, no free API, no MCP. There is a paid "Signal" API; `robots.txt` disallows `/api/` and
  `/apikeys/`, so it is off-limits.
- Public listing pages (`/weekly`, `/monthly`, `/yearly`, `/`, `/live-mentions`) are SSR and embed one
  schema.org `ItemList` in `application/ld+json`: 25 `ListItem`s with `position`, `url` and an `item`
  (`name` = owner/repo, `description`, `codeRepository`, `programmingLanguage`, `dateCreated`,
  `dateModified`). That payload is the sanctioned, cheap route — parse it, never scrape the cards.
- `/github-trending-repositories` carries **no** JSON-LD: expect `FAIL ... no application/ld+json block`
  if it is ever wired as a source.
- Stars are not in the JSON-LD. They come from the GitHub REST API (`/repos/{slug}`), with a token from
  `GITHUB_TOKEN`/`GH_TOKEN` or the `gh` CLI (5000/h instead of 60/h). Weekly momentum = stars now minus
  the stars stored by the previous run — no scraping of the "gained this week" markup needed.

## Dedupe and state

- `state.json` keeps, per repo: last star count, first/last seen date, and how many runs it has appeared in.
- Silence is keyed on a **semantic signature** — item ids + descriptions + scores + the two-list split, mixed
  with a hash of `interests.yaml` — never on the rendered text (stars move every minute, so a text hash would
  re-send forever) and never on slugs alone (that would ignore both a profile edit and a rewritten description).
  Identical signature ⇒ the run prints nothing and cron sends nothing.
- Weekly momentum is only trusted against a sighting **within 14 days**; a repo returning after a long absence
  shows no delta instead of a fake spike.
- `🆕` marks a repo that was not in the previous run.
- `last_ok` is a heartbeat; a run that finds it more than 10 days old says so in the health footer (a cron that
  stopped firing cannot report its own absence, so this only surfaces on the run after the gap).
- `min_items` per source: fewer items than that count is a **failure** (schema drift), not "no news".
- The ledger (`ledger/YYYY-MM.jsonl`) gets one line per run: count + promoted slugs — enough to audit what
  was sent without keeping the rendered text.
- State is written only after the digest text is built, so a crash mid-run re-sends next time instead of
  silently dropping a week.

## Scheduled delivery

```bash
hermes cron create "0 8 * * 1" --name watchtower-weekly \
  --script watchtower_weekly.sh --no-agent --deliver telegram
```

Weekly on purpose: trendshift's weekly list changes weekly; a daily run would re-report the same repos.
The wrapper pins `WATCHTOWER_HOME` because cron can run with a different `$HOME` (the webui container has
`HOME=/root`, where no config or state exists).

## Adding a source

1. Add an entry to `sources.yaml` with a `kind` that exists (`--doctor` proves it).
2. If the kind is new: write `fetch_<name>(source) -> list[dict]` returning the normalised item shape
   (`id`, `title`, `description`, `url`, `lang`, `rank`, …), register it in `FETCHERS`, and treat
   "page loaded but parsed 0 items" as a `FetchError` — that is a broken extractor, not "no news".
3. Run it twice: the second run on unchanged input must print nothing. If it re-sends, the `id` (dedupe
   key) is wrong — fix that before adding the next source.

# Built instance: watchtower

One collector for every future source of this class (trending repos now; RSS, catalogs later):
`<repo>/docs/home-server/watchtower/watchtower.py` + `sources.example.yaml` + `interests.example.yaml`, live
config/state in `~/.hermes/watchtower/`, wrapper `~/.hermes/scripts/watchtower_weekly.sh`, cron job
`watchtower-weekly` (`0 8 * * 1`, `--no-agent`). Extend that file rather than writing a second collector.

- **Two lists are one scoring pass**: `like` rules add `weight` (= priority) once each, `dislike` subtracts,
  promote when matched ≥1 like rule and score ≥ `thresholds.highlight` (per-source override + `max_highlight`
  cap). Matched rule ids print on every promoted line, so tuning needs no code read. One `interests.yaml`,
  no per-source profiles.
- **Momentum without an API**: store `stars` per repo in state; next run's delta *is* "gained this week".
  Resolve a GitHub token at startup from `GITHUB_TOKEN`/`GH_TOKEN` then `gh auth token` — the unauthenticated
  60/h limit is exhausted by two or three test runs and silently degrades to `★?`.
- **`--force` is the manual-verification flag**: the collector is silent when the source content is
  unchanged, so `--force` prints the digest for review and a second plain run proves dedupe.
- **Key the silence on a semantic signature, never on the rendered text or the slug list.** Stars/prices move
  continuously, so hashing the message re-sends forever; hashing slugs alone ignores both a profile edit and a
  rewritten description. Hash items+descriptions+scores+the two-list split, mixed with the profile file's hash.
- **Fix the cold-start and stale-metric traps**: a delta is only meaningful against a recent sighting (ignore
  snapshots older than ~2 weeks, print no metric instead of a fake spike), and a listing that returns far fewer
  items than its configured `min_items` is a **failure**, not "no news".
- **The cron wrapper must pin the state/config dir absolutely** (`export WATCHTOWER_HOME=/config/...`): cron
  can run with `HOME=/root` (webui container) where no config or state exists. Verify by running the wrapper
  once with a foreign `HOME`.
- **Forcing a first real delivery** (to prove the cron→chat plumbing) = nudge only the state's
  `content_hash`, then `hermes cron run <id>`; never delete the state file.

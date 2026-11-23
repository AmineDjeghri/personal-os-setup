# Built instances (verbatim from the skill)

## 3b. Built instance: `watchtower` (weekly trending repos)

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

## 3c. Built instance: AdGuard↔Freebox jobs (sync + stale devices)

Scripts live in `<repo>/docs/home-server/adguard_freebox/` (`sync_adguard_home_ip_mac.py`, `stale_devices.py`,
`freebox_auth.py`; its README is the canon). Both are `--no-agent` Hermes cron jobs: per-minute sync with
`--deliver local` (a failing run must not message every minute), weekly stale check to `telegram`.

- **Reachability from the Hermes container (probed):** the Freebox API and AdGuard's direct port (8082, answers
  401 without credentials) are both reachable; `requests` and `uv` are present. Prefer the Freebox LAN IP in the
  config over `mafreebox.freebox.fr` — AdGuard is the DNS, so a name lookup makes the job depend on itself.
- **Config/secrets path:** the scripts default to `~/.config/<job>/config.yaml`; `$HOME` is the persistent
  `/config` in the agent container, but cron can run with `HOME=/root` in the webui container — pass `--config`
  with an absolute path in the wrapper.
- **One Freebox app id = one token**, and registering needs a physical button press on the Freebox: a job moved
  from another host needs its token re-issued only if the old one is not copied across; never reuse the app id
  for a test run.
- **Order of work:** copy configs → `--doctor` / `--dry-run` → apply once by hand → run again (must report
  `0 change(s)`) → only then `hermes cron create`. Confirm `hermes cron create --help` for `--no-agent`/`--script`
  and the shortest allowed interval before promising a 1-minute cadence.
- **Reading new repo scripts when the checkout is on a stale branch with a dirty tree:** `git pull` fails
  (upstream gone) — `git fetch`, then `git show origin/main:<path>`; do not switch branches over the user's
  uncommitted changes. To run them, export a copy instead of touching the checkout:
  `git archive origin/main docs/home-server/adguard_freebox | tar -x --strip-components=3 -C /config/workspace/adguard_freebox`;
  the cron wrappers in `~/.hermes/scripts/` point at that copy.
- **Token step order (needs the user physically at the Freebox):** ask them to confirm they are at the box
  *before* launching `freebox_auth.py <app_id> <config> --url http://<freebox-lan-ip>` — it blocks up to 2 min for the
  button press, so run it with a ≥180 s timeout, then `chmod 600` the config (dir 700) and mask the token in any
  echoed output. Repeat per job (own app id each). `stale_devices.py --doctor` then proves login + API fields.
- **Secrets never pass through chat:** the AdGuard URL/user/password go into the sync config by the user's own
  by the user's own hand (HA file editor); the agent waits for "done", then runs `--dry-run --verbose`.
- **Reading a dry run:** the Freebox keeps ghost entries (a VM's pre-bridge-reset MAC). The sync skips the ghost
  with a `skipped <mac>: client '<name>' already follows another device` warning and moves the AdGuard client to
  the live MAC — expected, and the same ghost shows up in the stale report. The first apply may touch the
  `homeassistant` client (HA's own DNS identity): state the exact +/- ids to the user and get a yes before applying.
- **What the rewritten sync owns on a client:** MACs and IPs are overwritten from the Freebox every run;
  non-address ids (ClientIDs for DoH/DoT, CIDR ranges) and every other client setting (upstreams, blocked services)
  are preserved. A hand-added plain IP is therefore removed on the next run — tell the user to use a ClientID/CIDR
  or a DHCP reservation instead.
- **Doc/branch edits while the checkout is dirty:** `git worktree add -b <branch> <path> origin/main` gives a clean
  branch from main without touching the user's working tree; leave edits uncommitted, report the diff, and wait for
  the explicit per-action push approval. A fresh worktree has no `.venv` deps, so the repo's pre-commit hooks
  (`properdocs --strict`) fail on "Failed to spawn": run `uv sync --group dev --group docs` in the worktree (dev gives `pre-commit`, docs gives `properdocs`; `uvx ruff@<pinned version>` lints one file without either), never
  `--no-verify`. Markdown tables must stay column-aligned (markdownlint MD060): keep a table cell within the
  header width, put longer explanations in a bullet. Push a new branch with `git push -u origin <branch>` (the
  worktree branch tracks `origin/main` by default). In `personal-notes`, do not hand-commit: `vault_sync.sh`
  (the `vault-sync` job) commits and pushes `main` itself, so run it to land a notes edit. Mirror any wrapper fix (`sys.exit(run.returncode)`) into the live wrappers.
- **Do not create the sync job until the first real apply succeeds and the second run is silent.** A failing apply
  (e.g. a 400 "another client uses the same IP") would fail every minute. Create the independent weekly stale job
  meanwhile. Conflict recipe: `references/adguard-freebox-sync.md`.
- **Where the jobs get recorded for the user:** the personal-notes vault's `home-lab/architecture/overview.md`
  ("Hermes cron jobs" table: job, schedule, delivery, state, wrapper/config locations — no secrets, no hostnames).
  The old Ubuntu host crontab line stays until the Hermes sync runs clean, then is removed (two writers fight).
- **Where cron output lives:** `hermes cron runs <id>` (`--limit N`) and `hermes cron list` for status; every run
  (even a silent one, written as `Status: silent (empty output)`) leaves `~/.hermes/cron/output/<job_id>/<ts>.md`;
  history in `~/.hermes/cron/executions.db`. There is no `sync_agh.log` under Hermes (that was the old crontab
  redirect).
- **Retention (read from the code):** output files are pruned to the newest 50 per job (`cron.output_retention`,
  <=0 disables), so a 1-minute job keeps ~50 minutes of files. `executions.db` keeps the last 1000 finished runs
  across ALL jobs, a constant not a setting: an every-minute job evicts the history of weekly jobs within ~17 h.
  Say so before promising the user "logs" for a per-minute job.
- **Sync never edits a client it did not match** (by MAC, then name): a leftover hand-made client holding an IP the
  Freebox now gives another device yields the 400 and a failing run. By design — it may carry custom settings. The
  user's cleanup (delete the older clients in AdGuard) lets the next run add one fresh client and converge to
  `0 change(s)`; the ghost-MAC warning still prints every run until the Freebox entry is deleted, so the sync is
  not silent until then.
- **Two causes of "why is X not in the logs / still has an old IP" (both seen live):** (a) a client named by its MAC
  was created while the Freebox had no name for the device, and the sync never renames — the device IS in the log,
  under the MAC; fix = name it in the Freebox, then rename (or delete and let the sync recreate) the AdGuard client,
  deleting any older hand-made client of the same device first (name collision). (b) an unreachable old address on a
  LIVE Freebox entry (e.g. an old IPv4 on the VM's current MAC) stays in the client because the sync copies the
  Freebox list and the router offers no per-address delete; harmless, tell the user to leave it. DHCP static
  leases live in AdGuard (not the Freebox) and are never synced, so they drift after a MAC change — `network_audit.py`
  flags them. Docs rule: name devices in the Freebox before the first sync.
- **Why wrappers at all / exit code / ghost-warning noise:** `references/adguard-freebox-sync.md`.
- **"Search for all the potential problems" / any "why is device X missing or misnamed"** → run
  `network_audit.py` from the repo's `adguard_freebox` folder (read-only: MAC-named clients, static-lease mismatches, orphan clients, duplicate names, devices on dynamic leases; `--list` adds the harmless findings; runs as the weekly cron `network-audit`, silent when clean) or, for the query-log naming check, this skill's `scripts/adguard_freebox_audit.py` (7 checks) from the scripts folder, before explaining; recipe and
  how to read each finding: `references/adguard-freebox-sync.md` → "Full audit".
- **Cron pairing:** sync = `--deliver local --failure-deliver local` — never Telegram for an every-minute job
  until it has run clean for days (ghost-entry warning prints every tick; an outage would send one failure per
  minute; the user decided this explicitly); stale = `--deliver telegram` (one message a week); network-audit = same weekly Telegram (`every monday at 09:30`, wrapper `network_audit_run.py`, reuses the sync config and token, adds only the optional `audit_ignore_macs` / `old_address_days` keys). `every 1m` is accepted (verified; the first run lands
  within ~1–2 min of creation, then every minute). `hermes cron create --help` does not state the minimum, so for
  anything shorter create with `--paused` first. Add `--config <absolute path>` to the wrappers' `uv run`
  call so a `HOME=/root` run still finds the secrets.

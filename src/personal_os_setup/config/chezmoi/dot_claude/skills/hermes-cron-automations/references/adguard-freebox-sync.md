# AdGuard/Freebox sync + stale-devices as Hermes cron jobs

Scripts live in personal-os-setup `docs/home-server/adguard_freebox/` (uv run --script; read them from
`origin/main` with `git archive` when the checkout is on a dirty feature branch, never switch branches).

## Facts verified from the Hermes container
- Freebox API answers on its LAN IP and via the mafreebox name; AdGuard direct port (8082) answers 401 without creds.
- `$HOME=/config`, so the scripts' default `~/.config/<job>/config.yaml` is already persistent. Make the dir 700, file 600.
- `uv` and `requests` exist; scripts pull `pyyaml` themselves.
- `hermes cron create` has `--script` (file under ~/.hermes/scripts/), `--no-agent`, `--deliver`, `--failure-deliver`.
- Copy the scripts to a persistent workspace dir; wrappers in ~/.hermes/scripts/ point at that copy.

## Why a wrapper, not a copy of the script
Hermes runs a `.py` under `~/.hermes/scripts/` with ITS OWN Python: the `uv run --script` shebang and the inline
`# /// script` deps are ignored, so a copied script may lack `pyyaml`. `--interpreter` only takes a venv Python path
(not `uv`). The wrapper (subprocess `uv run --script <real script>`, print stdout, on failure print stderr, exit with
the child's code) keeps one source copy, isolated cached deps, and secrets outside git. Cost: it holds an absolute
path, so the scripts folder on the Hermes box must be refreshed when the repo changes. When the user first meets the
word "wrapper", explain it in two sentences before proceeding — it is Hermes-only plumbing, the scripts stay as-is.

## Setup order
1. `freebox_auth.py <app_id> <config> --url <LAN url>` once per job (user presses the Freebox arrow button, 2 min).
2. User adds AdGuard url/user/password to the sync config by hand (never take the password in chat).
3. `--dry-run --verbose` (sync) / `--doctor` (stale) before any write; apply once, rerun -> must print `0 change(s)`.
4. Create the cron job with local delivery first; only then choose Telegram.

## Pitfalls
- The readme's wrapper exits 0 even when the script fails, so Hermes sees no failed run and `--failure-deliver`
  never fires. Make the wrapper `sys.exit(run.returncode)`.
- A per-minute job with a persistent failure may repeat failure notices every minute; test what Hermes does
  (controlled failure via a bad config) before routing failures to Telegram.
- `--no-agent`: stdout is the message, empty stdout = silent run. The sync prints only on change/failure.
- Sync dry-run showed a stale MAC (pre-bridge-reset VM) being replaced on the HA client: expected, but it edits the
  client for HA's own DNS, so get approval before the first real apply.
- The sync's `skipped <mac>: client '<name>' already follows another device` warning (a ghost Freebox entry sharing a
  live client's name) is printed on EVERY run until the ghost is removed from the Freebox, so a per-minute job gets
  non-empty output each tick. Keep `--deliver local` (or clean the ghost) before any Telegram delivery.
- Output contract of the sync (timestamped lines): quiet run = nothing; `add|update '<name>': +<id> -<id>`;
  `FAILED to <action> '<name>': <why>`; one-line `adguard-sync FAILED: ...` + exit 1 when AdGuard/Freebox is
  unreachable; `--verbose`/`--dry-run` add `N devices, M change(s), K failed, L host(s) without a MAC skipped`.
- **First real apply can fail with `clients/update answered 400: another client "<X>" uses the same IP`.** The
  sync only edits the client it matched (MAC, then name) and never touches others, by design: an unmatched client
  (older entry of the same device, different name/MAC the Freebox no longer lists) may hold hand-made settings, so
  stripping its IPs or deleting it silently is unsafe. List the clients read-only (a small script using the config
  creds; never print the password), show the user both clients' ids, and let them choose: (1) delete/trim the old
  client, or (2) delete both and let the sync recreate one. A `--steal-addresses`-style opt-in flag is a feature
  request, not a workaround to improvise. Nothing is written on a 400, so the failure is safe to leave until decided.
- **A client gets several IPv4s for one MAC by design**: the sync copies every address the Freebox lists for that MAC,
  reachable or not, so a device keeps its identity in the query log across address changes. A leftover (e.g. an old
  pre-bridge-reset lease, unreachable for months) rides along until the Freebox itself stops listing it on the
  LIVE device entry. Deleting a different ghost entry (the old MAC) does NOT remove it: the stale address sits on the
  live entry, so the sync keeps it and a re-run reports `0 change(s)`. What drops it: the Freebox forgetting it over
  time, or the user deleting the live entry in the Freebox UI while the device is online (it re-registers with only
  its current address; brief name gap in the Freebox/HA integration, so the user does it, not the agent). The user
  reported the Freebox UI offers no delete/forget action on an active entry (only inactive ones), so treat that route
  as unavailable, say "leave it, it is harmless", and do not guess a Freebox API call against the router. Hand-removing
  it in AdGuard is undone by the next run. An opt-in "ignore addresses unreachable for N days" config key in the sync
  script is the only code fix; offer it, do not build it unasked. Harmless unless another device is later handed that address (then the 400
  above). Answer "why this extra IP?" from the data, not from the design: probe first (read-only Freebox probe below).
- **Read-only Freebox probe** (scratch `.py`, run with `uv run --with requests --with pyyaml python <file>` from the
  scripts folder): `sys.path.insert(0, <scripts dir>); import sync_adguard_home_ip_mac as s`, load the sync config,
  then `s.fbx_login(cfg)` -> `s.fbx_hosts(cfg, token)` -> `s.mac_of(host)`; print each host's `l3connectivities`
  (`addr`, `reachable`, `af`, `last_activity` age in days). Never print the token or password. Check function names
  with `grep -n "^def "` first; they are not `get_*`.
- Once the ghost Freebox entry is deleted the warning disappears and a quiet run is truly empty: the first cron tick
  is booked `Status: silent (empty output)` and still writes an output file. Create the sync job at that point.
- Outcome after the user deleted both conflicting clients: dry-run showed one `would add`, apply added one fresh
  client, second run `0 change(s)`; only the ghost-MAC warning remained. Next: create the sync job (local-only) or
  wait for the Freebox ghost to be deleted, user's choice.
- **"I don't see device X in the AdGuard query log" = a naming/matching problem, not a missing log.** Probe both sides
  read-only before explaining: (a) Freebox host by name/MAC with its addresses and `reachable`; (b) AdGuard
  `GET /control/clients` for the client holding that MAC/IP; (c) `GET /control/querylog?search=<ip>&limit=N` and group
  entries by `client_info.name`. Typical cause: the sync names a NEW client from the Freebox name at creation time and,
  if the Freebox had no name yet, falls back to the MAC; the sync never renames later, so the live device's traffic
  shows under a MAC-named client while an older hand-made client (same friendly name, an old/rotated MAC the Freebox no
  longer lists) stays empty. Fix is the user's in AdGuard: delete the old client (frees the name), then rename the
  MAC-named client; the sync matches by MAC and keeps the name. Afterwards offer to list other clients still named by a
  MAC. Pitfall: `search=<ip>` is a substring match (`192.168.1.2` also hits `.20`-`.29`), so group by exact
  `client` before concluding.
- **IPv6 per-device filtering works once the sync has run**: in a 500-query window every IPv6 query resolved to a named
  client (each phone client carries its MAC plus 4-8 IPv6 addresses). The user filters by client name in Query Log.
  Caveat to state: privacy/rotating IPv6 addresses only match after the Freebox lists them and the next 1-minute sync
  adds them.
- **`stale_devices.py` semantics (answer from the code)**: one record per MAC (entries merged), reported only when not
  reachable now and last sign of life (max over host + every address) is older than `threshold_days` (default 14);
  runs weekly via cron (the 14 days is silence, not cadence); read-only; never flags a stale address on a live device.
- **Full audit** (`scripts/adguard_freebox_audit.py`, read-only; run from the scripts folder with
  `uv run --with requests --with pyyaml python <path>`): report the offenders per check and propose a cleanup, do not
  apply it. How to read the findings: (1) MAC-named clients = the Freebox had no name at creation: the user names the
  device in the Freebox first (a device with no Freebox name stays a MAC; the doc says to name devices before the first
  sync), then renames the client in AdGuard; if a same-name stale client exists, delete it first (names are unique).
  (2) name drift is cosmetic, the user's hand names win, the sync never renames. (3) orphans (client MAC absent from the
  Freebox) are never touched by the sync and keep dead data: the user deletes the ones they recognise; laptops with a
  rotating/private MAC are the usual suspects; an IP-only client such as the HA DNS entry is left alone. (4) two
  near-identical names (apostrophe/space/case) are usually one device. (5) is empty in a healthy setup. (6) is the
  harmless old-address case above. (7) any unnamed IP in the log means a device the sync has not matched.
- **Which of two stale clients/devices is the real one** (e.g. two Apple Watches): compare, per MAC, the Freebox last
  activity (max over host and addresses) and whether the MAC is still in the Freebox list; AdGuard keeps only 7 days of
  query log (`GET /control/querylog/config` → `interval` ms), so a quiet device proves nothing there. The more recent
  one is the likelier live device, but say so as a guess. Watches join Wi-Fi only occasionally (mostly Bluetooth via
  the phone) and rotate their private Wi-Fi address, so a month of silence is not death; the tie-breaker is the
  device's own Settings → General → About → Wi-Fi Address, compared with the MACs.
- **Static IPs live in AdGuard (DHCP → static leases), never the Freebox** while AdGuard is the DHCP server; names for
  the sync come from the Freebox device page (`primary_name`), the DHCP hostname in the static lease is a separate field
  that AdGuard publishes as `<hostname>.lan`. Naming devices in the Freebox is correct: it feeds both the sync and the
  HA Freebox integration, but later renames reach neither existing AdGuard clients nor existing HA entities.
- **DHCP static-lease audit** (AdGuard is the DHCP server, so this is where "fixed IPs are missing" is answered):
  `GET /control/dhcp/status` returns `static_leases` (`mac`, `ip`, `hostname`) and `leases` (dynamic). Compare with the
  Freebox devices per MAC: (a) devices up on a dynamic lease or with no AdGuard lease (their IPv4 can change; the
  user adds static leases using each device's CURRENT address so nothing moves; a device that sets its own address, like
  a camera or the HA VM, has no lease by design), (b) static leases whose MAC the Freebox no longer lists (rotated
  private MAC, or the HA VM's pre-bridge-reset MAC), (c) a static IP differing from the address the device is on now
  (usually a lease added recently: it moves on the next renewal or Wi-Fi reconnect, check the MAC only if it does
  not), (d) two leases on one IPv4. Report, do not write: adding/removing leases is the user's call.
- **`network_audit.py` (repo script, weekly cron `network-audit`)** turns the full audit and the lease audit into one
  read-only job: alerts = MAC-named clients, mismatching static leases, orphan clients, near-duplicate names, devices
  up on dynamic leases; `--list` adds name drift and old unreachable addresses; empty output when clean; one-line
  `network-audit FAILED: ...` + exit 1 on errors. `audit_ignore_macs` in the sync config silences devices that are
  meant to stay dynamic. Keep checks as pure functions of (clients, leases, devices) so a scratch test with sample
  data covers them (the repo has no tests for these scripts). A separate script, not a flag on the sync or the stale
  check: it needs AdGuard credentials the Freebox-only stale job should not hold, and an AdGuard outage must not break
  the other jobs.
- Old vs new sync: new keeps hand-added ClientIDs/CIDR ranges and all client settings, resolves duplicate
  address claims, reports per-change failures and exits 1; old dropped settings, ignored POST errors, exited 0.

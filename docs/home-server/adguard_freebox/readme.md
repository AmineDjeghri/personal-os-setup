# AdGuard Home + Freebox scripts

Three standalone `uv run` scripts (no install, dependencies are declared in each file). Context and the
reasoning behind them: [Home server](../readme.md) (AdGuard Home, DHCP and DNS notes).

| File                                                       | What it does                                                                                                   | Writes anything?                       |
| ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| [freebox_auth.py](freebox_auth.py)                         | Registers an app on the Freebox (button press) and saves `freebox_url`, `app_id`, `app_token` in a config file | the config file only                   |
| [sync_adguard_home_ip_mac.py](sync_adguard_home_ip_mac.py) | Gives each AdGuard client the MAC and all the addresses the Freebox lists for it                               | AdGuard clients (not with `--dry-run`) |
| [stale_devices.py](stale_devices.py)                       | Lists devices unreachable for 14+ days and how to clean them up                                                | nothing, read-only                     |

Run everything from this folder: `cd docs/home-server/adguard_freebox`.

## Config files

One file per job, outside git, mode 600. The examples show every key:
[sync_adguard_home_ip_mac.example.yaml](sync_adguard_home_ip_mac.example.yaml) and
[stale_devices.example.yaml](stale_devices.example.yaml).

| Job           | Default config path                   | App id                           |
| ------------- | ------------------------------------- | -------------------------------- |
| AdGuard sync  | `~/.config/adguard-sync/config.yaml`  | `fr.homeassistant.adguard_sync`  |
| Stale devices | `~/.config/stale-devices/config.yaml` | `fr.homeassistant.stale_devices` |

Each job has its own app id and token. Pass `--config <file>` to use another path.

## Setup

### 1. Get a token (once per job)

```sh
uv run freebox_auth.py fr.homeassistant.adguard_sync ~/.config/adguard-sync/config.yaml --url http://192.168.1.254
uv run freebox_auth.py fr.homeassistant.stale_devices ~/.config/stale-devices/config.yaml --url http://192.168.1.254
```

Press the right-arrow button on the Freebox server within 2 minutes. `--url` is required: the LAN
address means the jobs do not depend on DNS (AdGuard Home is the DNS). `--app-name` sets the name shown in
the Freebox app list (default: the app id).

For the sync job, then add `adguard_url`, `adguard_user` and `adguard_password` to its config (see the example).

### 2. Check, then run

```sh
uv run sync_adguard_home_ip_mac.py --dry-run     # shows the changes, applies none
uv run sync_adguard_home_ip_mac.py --verbose     # applies them, prints a summary
uv run stale_devices.py --doctor                 # login, API fields, what would be reported
uv run stale_devices.py                          # the message (nothing when no device is stale)
uv run stale_devices.py --list                   # everything, without the message length cap
uv run stale_devices.py --threshold-days 7       # try another threshold without editing the config
```

### 3. Schedule

Both jobs run well as **Hermes cron jobs** with `--no-agent` (no LLM, the script output is the message, an
empty output is a silent run). The cron `--script` must be a file in `~/.hermes/scripts/`, so each job gets a
small wrapper that runs the script:

```python
# ~/.hermes/scripts/adguard_sync_run.py  (stale_devices_collect.py is the same with stale_devices.py)
import subprocess
import sys

run = subprocess.run(
    [
        "uv",
        "run",
        "--script",
        "/path/to/personal-os-setup/docs/home-server/adguard_freebox/sync_adguard_home_ip_mac.py",
    ],
    capture_output=True,
    text=True,
)
print(run.stdout, end="")
if run.returncode:
    print(run.stderr, end="")
sys.exit(run.returncode)
```

#### Why a wrapper and not a copy of the script

Hermes only runs a script that sits in `~/.hermes/scripts/`, and it runs a `.py` there with **its own
Python**: the `uv run --script` shebang and the inline `# /// script` dependency block are ignored. The
wrapper is a Hermes-only shim that calls `uv run --script` on the real script. The scripts stay as they are
in the repo, and the same files still run from a `crontab` or a laptop.

What happens on each tick:

1. Hermes runs the wrapper with its own Python.
2. The wrapper starts `uv run --script <real script>` as a subprocess. `uv` installs `requests` and `pyyaml`
   in an isolated, cached environment, so nothing depends on what Hermes' Python ships.
3. The wrapper prints the script's stdout. An empty stdout is a silent run: the sync prints only when it
   changed something or failed.
4. On failure it also prints stderr (the `adguard-sync FAILED ...` line) and **exits with the script's exit
   code**. Without `sys.exit`, a failed sync would be a quiet "success" for Hermes, and `--failure-deliver`
   would never fire.

Why this is better than copying the script into `~/.hermes/scripts/`:

- **One copy.** A fix merged in the repo is what cron runs next, with no re-copying.
- **No dependency gamble.** A copied script would run under Hermes' Python, where `pyyaml` may be missing.
  `--interpreter` only accepts a venv Python path, not `uv`, so it is heavier than the wrapper.
- **Secrets stay out.** The configs live in `~/.config/...`, outside git and outside the scripts folder.

The cost: the wrapper holds an absolute path to the script, so keep a clone (or a copy) of this folder on
the Hermes box and update it when the scripts change.

```sh
hermes cron create "every 1m" --name adguard-sync --script adguard_sync_run.py --no-agent --deliver local --failure-deliver local
hermes cron create "every monday at 09:00" --name stale-devices --script stale_devices_collect.py --no-agent --deliver telegram
hermes cron list                # schedule and next run
hermes cron runs <id>           # what each run printed
```

- **Never deliver the every-minute sync to Telegram.** Use `--deliver local --failure-deliver local` and read
  the runs with `hermes cron runs <id>`. Two things would turn it into spam: the warning about a stale
  Freebox entry that shares a name with a live AdGuard client is printed on every run until the entry is
  removed, and an AdGuard outage would produce one failure message per minute. Only consider Telegram for
  failures after a few days of clean runs. The weekly stale job sends one message a week, so it uses Telegram.
  Check `hermes cron create --help` for the interval syntax and the shortest interval allowed.
- Config files (secrets) must sit in a persistent directory of the Hermes box, not one lost on a rebuild.
- Without Hermes, the sync also runs from a user `crontab -e` on any machine that reaches the LAN. `flock`
  stops a slow run from overlapping the next one:

  ```sh
  * * * * * flock -n /tmp/adguard-sync.lock /home/<user>/.local/bin/uv run /path/to/sync_adguard_home_ip_mac.py >> $HOME/sync_agh.log 2>&1
  ```

Exit codes: `0` ok, `1` the config, AdGuard or the Freebox could not be read, or a change failed. A failure
prints one line starting with `adguard-sync FAILED` or `stale-devices check FAILED`.

## Testing

### A. Without any network (any computer)

```sh
uv run sync_adguard_home_ip_mac.py --help
uv run stale_devices.py --help
uv run freebox_auth.py --help
ruff check . && ruff format --check .     # from the repo root's tooling (make lint)
pre-commit run codespell --files readme.md *.py *.yaml
```

With no config file, both jobs must fail cleanly: `uv run stale_devices.py --config /nonexistent.yaml` prints
`stale-devices check FAILED: config file not found ...` and exits 1.

### B. From your computer, against the real LAN (read-only)

Your computer only has to be on the same network as the Freebox and AdGuard Home. Nothing here changes the
server's setup.

1. Register a **test app**, never the server's app id (an app id has one token):

   ```sh
   uv run freebox_auth.py fr.homeassistant.stale_devices_test /tmp/stale-test.yaml --url http://192.168.1.254
   ```

2. Run the read-only checks with that config:

   ```sh
   uv run stale_devices.py --config /tmp/stale-test.yaml --doctor
   uv run stale_devices.py --config /tmp/stale-test.yaml --list
   ```

   `--doctor` must print `OK   Freebox login and device list` and a non-zero count of devices with an activity
   timestamp. A line starting with `FAIL` means the Freebox API fields changed.

3. For the sync, build a test config (same keys as the example, the test app's `freebox_url`, `app_id` and
   `app_token`, plus your AdGuard URL and credentials) and **only** run the dry run:

   ```sh
   uv run sync_adguard_home_ip_mac.py --config /tmp/sync-test.yaml --dry-run --verbose
   ```

   Expected: lines like `would update 'Phone': +192.168.1.50 -192.168.1.9` and a summary
   (`N devices, M change(s), 0 failed, K host(s) without a MAC skipped`). Run it twice: with `--dry-run`
   nothing is applied, so the list is the same.

4. Clean up: `rm /tmp/stale-test.yaml /tmp/sync-test.yaml`, and remove the test app from the Freebox
   (Freebox OS settings, the list of authorized applications).

### C. On the server

1. Copy or create the real configs (step 1 above), run each `--dry-run` / `--doctor`.
2. Apply once by hand: `uv run sync_adguard_home_ip_mac.py --verbose`, then run it again. The second run must
   print only the summary: `0 change(s)`. Anything else means it is not converging, so stop and read the lines.
3. Check in AdGuard Home → Settings → Client settings → Persistent clients.
4. Only then add the cron lines.

### What good looks like

| Check                     | Expected                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------------------- |
| second sync run in a row  | `0 change(s)`, no other output without `--verbose`                                          |
| sync with AdGuard stopped | `adguard-sync FAILED: cannot reach AdGuard Home ...`, exit 1, nothing read from the Freebox |
| stale job, nothing stale  | empty output                                                                                |
| stale job, wrong token    | `stale-devices check FAILED: Freebox login refused ...`, exit 1                             |

## Troubleshooting

| Symptom                                                | Cause                                                                                              |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| `Freebox login refused`                                | the token or app id in the config does not match the app registered on the Freebox                 |
| `AdGuard Home ... answered 401`                        | wrong credentials; if AdGuard runs in Home Assistant, the user needs "local access only" unchecked |
| `AdGuard Home clients/update answered 400 ... already` | an address is on another AdGuard client you created by hand; remove it there                       |
| `FAIL no activity timestamp found`                     | the Freebox API stopped sending `last_activity` / `last_time_reachable`                            |
| sync and stale disagree about a device                 | the Freebox lists it under several entries; the scripts merge entries with the same MAC            |

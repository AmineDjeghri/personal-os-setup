# Platform adapter dependencies (extras) + restarting only the gateway

Verified on the HA-addon deployment: one container, one uv-created venv, gateway supervised by
`run.sh`. Covers two symptoms that both look like "the gateway is broken".

## 1. Why a chat platform goes dark while the gateway stays up
Log signature, all inside one second:
```
INFO  gateway.platform_registry: Platform 'Telegram' dependencies missing — attempting install...
WARN  gateway.platform_registry: Platform 'Telegram' requirements not met (Run `hermes setup` to install Telegram support.)
ERROR gateway.run: Platform 'telegram' is registered but adapter creation failed (check dependencies and config)
WARN  gateway.run: No adapter could be created for any of the 1 configured platform(s)... Gateway will continue for cron job execution.
```
Two independent mechanisms, both needed to explain it:
1. **The library was never installed.** The add-on's install line is
   `uv pip install --python "$VENV_DIR/bin/python" -e ".[all,dev]"`, and `all` =
   `cron, pty, mcp, uvloop, homeassistant, sms, acp, google, web, youtube` — the per-platform extras
   (`telegram`, `discord`, `slack`) are deliberately NOT in it. Chat adapters are opt-in and nothing in
   the add-on installs them.
2. **The lazy install can never succeed.** The "attempting install" path shells out to `pip`, and a
   uv-created venv ships no `pip` (`venv/bin/pip` absent) — hence `requirements not met` ~5 ms later.

Read the extras instead of guessing which library a platform needs:
```
python -c "import tomllib;ex=tomllib.load(open('pyproject.toml','rb'))['project']['optional-dependencies'];print(ex['all']);print(ex.get('telegram'))"
```

## 2. Which interpreter the venv is
`run.sh` decides with `required_python_version()`: the literal `3.11` is ONLY the fallback used when
`<checkout>/.python-version` is absent; the checkout pins `3.14` (tracked upstream) and
`hermes_runtime_works()` moves aside and rebuilds any venv whose interpreter does not match the pin.
Confirm all three before saying anything about the interpreter:
```
cat <HERMES_HOME>/hermes-agent/.python-version           # 3.14
cat <HERMES_HOME>/hermes-agent/venv/pyvenv.cfg           # home = .../uv/python/cpython-3.14.7-... ; version_info = 3.14.7
ls -la <HERMES_HOME>/hermes-agent/venv/bin/python        # -> uv-managed cpython-3.14.7
```
If the user asserts a version is "being forced", check these files and state the contradiction plainly —
the fallback literal is easy to mistake for the effective setting.

## 3. Install + verify
```
cd <HERMES_HOME>/hermes-agent
uv pip install --python venv/bin/python "hermes-agent[telegram]"
venv/bin/python -B -c "import importlib;print(importlib.import_module('plugins.platforms.telegram.adapter').check_telegram_requirements())"   # must print True
```
- `hermes-agent[<platform>]` beats hand-picking `python-telegram-bot[webhooks]==22.8`: the extra is the
  project's own pin and cannot drift. Never take `latest`.
- `check_telegram_requirements()` is the adapter's own gate — the gateway will not construct the adapter
  without it, so verify True BEFORE restarting (it is also a pure read: safe in a read-only pass).
- This recurs on every venv rebuild (mechanism 1 of §1). Durable fix is add-on side: an extra
  `uv pip install --python "$VENV_DIR/bin/python" "hermes-agent[telegram]"` after the `.[all,dev]` line.
  It is not a Hermes setting, and `hermes setup` / `pip install` are dead ends in a venv with no pip.

## 4. Restart only the gateway
```
ps -o pid,ppid,args -p <gateway-pid>   # walk up: gateway → hermes-gateway-supervisor.py → bash /run.sh
kill -TERM <supervisor-pid>            # forwards SIGTERM to the gateway, exits 0
```
- Success evidence: `Gateway slot exited with containment proven; restarting in 3s...`, then a fresh
  `Starting Hermes Gateway...` block where the platform no longer reports `dependencies missing`.
- A non-zero supervisor exit is treated as unsafe (`FATAL: unsafe gateway supervisor exit`) and the loop
  stops restarting — the clean SIGTERM path is the only supported restart. Never SIGKILL the gateway.
- Do NOT restart the add-on/container for this: it kills the agent's own ttyd/tmux session mid-work and is
  unnecessary for a gateway-level change.
- System-modifying → approval gate. Prompts time out here; a BLOCKED/timeout result is NOT consent.
  Report the exact pending command and wait for the user's word.

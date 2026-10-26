# Triage a Hermes add-on boot log (read-only)

Companion to the "Log triage" section of SKILL.md. Use when the user pastes add-on/gateway
startup output and asks what is wrong.

## 1. Attribute the log before diagnosing

Two Home Assistant add-ons run Hermes against ONE shared `HERMES_HOME`
(`/addon_configs/<repo>_<slug>/.hermes`): the third-party **Hermes Agent** add-on
(`<vendor>/<addon-repo>`, add-on dir `<slug>/`) and the user's own
**hermes-webui** add-on (from the user's `ha-addons` repo, `addons/hermes-webui/`). They are different
containers with different run scripts, ports and banners — a pasted log may not be from the
container you are running in.

| Marker in the log | Belongs to |
|---|---|
| `[run]`-prefixed lines, nginx ingress/HTTP/HTTPS port trio, `Profile <name> (PID n):` banner, `HASS_TOKEN injected`, "TLS certificates: using existing" | Hermes Agent add-on (`<slug>/run.sh`) |
| `HERMES_WEBUI_*` env, WebUI on its own port, workspace + `HERMES_WEBUI_STATE_DIR` lines | hermes-webui add-on (`addons/hermes-webui/run.sh`) |

Confirm the installed set and slugs (MCP `ha_get_app`, or `ha_get_app(slug=…)` for one) before
naming it. The Agent add-on runs ONE shared clone + venv (`$HOME/.hermes/hermes-agent`,
`…/venv`) with one home per profile, installs via `uv pip install -e ".[all,dev]"`, and ships a
`dashboard-patches.py` that rewrites the dashboard for HA ingress.

## 2. Dependency-store (PM) layout — what to read when a sync fails

- `<hermes home>/installs/<key>/` (key = sha256 of the resolved project root, first 16 hex) holds `pm-runtime/`, `facts.json`, `inputs/` stamps and the `source-completion-pending` marker.
- A failed sync becomes visible as `hermes: source-update completion failed: <err>; running with the previous dependencies — run 'hermes update' to finish it` (printed on import by `hermes_bootstrap.py`; the process continues on the previous generation).
- A traceback whose outer frame is `python -I -c "import sys, runpy; sys.path.insert(0, '<root>'); …"` means the process was RE-EXECUTED into another interpreter — it was not written by the add-on; compare `sys.executable` with the store's Python.
- Base dependencies are Python-version gated (e.g. `ruamel.yaml` only for `python_version >= '3.14'`) while some modules import them unconditionally → an environment built on the wrong Python, or one whose sync never committed, dies at import with `ModuleNotFoundError`.


## 3. Failure signatures

| Log line | Meaning | Where it surfaces |
|---|---|---|
| `source-update completion failed: … /dev/null/installs/<key>/pm-runtime` | home resolution was patched during import (§4) | sync aborts; a later surface dies on a missing dep |
| `ModuleNotFoundError` in a dashboard process | that interpreter lacks a base dep (deps never synced for this revision) | nginx `/dashboard/` → `connect() failed (111: Connection refused)` |
| `could not read dashboard token` | the dashboard never served index.html — read it as "dashboard process is dead" | nginx dashboard routes refused/502 |
| `Platform '<x>' is explicitly disabled … credentials will NOT start its adapter` | `platforms.<x>.enabled: false` in `config.yaml`; env credentials no longer override it (HA access may still work via MCP) | adapter missing from `gateway_state.json` |
| `WARNING: prefix.py … pattern changed upstream - nested addon routes (/profile/...) may 404` | the add-on's ingress patch script could not raise upstream's prefix-length ceiling | affects only nested profile routes, not single-profile setups |

## 4. The `/dev/null` patched-home class

- `<hermes home>` comes from `hermes_constants.get_default_hermes_root()`; dependency state sits
  under it. So a path rooted at `/dev/null` in ANY Hermes error means that function returned
  `/dev/null` **at call time**, or `HERMES_HOME=/dev/null`. It is never a config-file problem.
- Real mechanism: an add-on gateway launcher re-points
  `hermes_constants.get_default_hermes_root` to `Path(os.devnull)` for the duration of
  `import hermes_cli.main` (its intent: neutralize a sticky interactive-profile probe). Upstream
  now imports `hermes_bootstrap` inside that window, so the bootstrap's own launch preparation
  resolves the store to `/dev/null/installs/<key>/pm-runtime` → `Errno 20 / ENOTDIR`, and the
  sync degrades to "previous dependencies".
- How to confirm without shell access: fetch the add-on's own scripts from its repo
  (`web_extract` on `raw.githubusercontent.com/<owner>/<repo>/<branch>/<addon>/<file>`), then
  `search_files` those files for `get_default_hermes_root`, `os.devnull`, `Path(os.devnull)`, and
  assignments to upstream modules. `gateway-launcher.py`, `profile-init.sh`, `nginx-render.sh`,
  `dashboard-patches.py`, `run.sh` are the files that patch upstream in this add-on.
- Fix belongs to the add-on/upstream: hand over upstream's own printed remedy (`hermes update`
  run in that add-on's Terminal, which does not go through the patch), plus the targeted unblock
  (install the missing dep into the failing surface's interpreter, pinned to the tree's own
  `pyproject.toml` gate), and recommend reporting the patch collision to the add-on author.
  Never "fix" it by editing the shared checkout in place.

## 5. Read-only evidence path

No shell → `read_file`/`search_files`/`web_extract`/MCP `ha_get_app` (approval-gate rules: SKILL.md).


## 6. Surface → interpreter map (Agent add-on)

Its `run.sh` starts: the per-profile gateway via
`gateway-child.sh → gateway-supervisor.py → gateway-launcher.py` (the patched-import window lives
here), each dashboard as
`"$VENV_DIR/bin/python" -c "from hermes_cli.web_server import start_server; start_server(host='127.0.0.1', port=…)"`,
and per-profile ttyd sessions with `HERMES_HOME` pinned per profile. Consequences: a broken
repository dependency generation kills surfaces one at a time, and a healthy gateway proves
nothing about the interpreter the dashboard uses.

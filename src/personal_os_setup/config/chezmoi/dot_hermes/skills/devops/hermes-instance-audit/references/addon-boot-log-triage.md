# Triage a Hermes add-on boot log (read-only)

Companion to the "Log triage" section of SKILL.md. Use when the user pastes add-on/gateway
startup output and asks what is wrong.

## 1. Attribute the log before diagnosing

Two Home Assistant add-ons run Hermes against ONE shared `HERMES_HOME`
(`/addon_configs/<repo>_<slug>/.hermes`): the third-party **Hermes Agent** add-on
(`<vendor>/<addon-repo>`, add-on dir `<slug>/`) and the user's own
**hermes-webui** add-on (his `ha-addons` repo, `addons/hermes-webui/`). They are different
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

- `<hermes home>/installs/<key>/` — key = `sha256(resolved project root)[:16]`
  (`pm/environments.py: install_key`). Under it: `pm-runtime/` (PM's runtime env + `pm-runtime.json`),
  `facts.json`, `inputs/` stamps, and the `source-completion-pending` marker.
- `hermes_bootstrap.py` — module-level code runs on import: it calls
  `hermes_cli.venv_sync.prepare_launch(project_root, argv)`; on any exception it prints
  `hermes: source-update completion failed: <err>; running with the previous dependencies — run 'hermes update' to finish it`
  and continues on the previous generation. That message is where a failed sync becomes visible.
- `hermes_cli/venv_sync.py` — `prepare_launch` (gates on `.git`, `pyproject.toml`, the install
  stamp), `_finish_source_update`, `_sync_source_dependencies`, `completion_pending_path`.
- `relaunch_command()` prints the interpreter as
  `python -I -c "import sys, runpy; sys.path.insert(0, '<root>'); sys.argv = [...]; exec(...)"`.
  Seeing that string as your traceback's outer frame means the process was RE-EXECUTED into
  another interpreter — it was not written by the add-on. Compare `sys.executable` with
  `hermes_cli/_launchers.resolve_store_python(root)`: a different interpreter triggers the re-exec.
- Base dependencies are Python-version gated (e.g. `ruamel.yaml` only for
  `python_version >= '3.14'`) while some modules import them unconditionally
  (`hermes_yaml.py: from ruamel.yaml import YAML`) → an environment built on the wrong Python,
  or one whose sync never committed, dies at import with `ModuleNotFoundError`.

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

## 5. Read-only evidence path (works while the shell is approval-gated)

Approval-gated `terminal`/`execute_code` can time out to BLOCKED; multi-line scripts, `python -c`
and `curl | python` shapes are the worst offenders, so do not plan a diagnosis that needs them.
Done without the shell, in this order:

1. `read_file` / `search_files` over the shared checkout (`$HERMES_HOME/hermes-agent`) for every
   symbol in the traceback — this is what turns "plausible story" into a mechanism (function name,
   call site, line).
2. `search_files(target='files', pattern='<dep>*')` inside the failing interpreter's
   `site-packages` to prove a missing dependency on disk.
3. `web_extract` the add-on's own scripts from its GitHub repo to see what it sets, patches and
   launches (the launcher's monkeypatch and the dashboard's interpreter are both only visible there).
4. MCP `ha_get_app` / `ha_get_logs(source='supervisor', slug=…)` for add-on options and its log stream.

Several small file-tool calls beat one clever shell one-liner; if a shell probe is genuinely
needed, ask for it explicitly and never retry a call that was blocked.

## 6. Surface → interpreter map (Agent add-on)

Its `run.sh` starts: the per-profile gateway via
`gateway-child.sh → gateway-supervisor.py → gateway-launcher.py` (the patched-import window lives
here), each dashboard as
`"$VENV_DIR/bin/python" -c "from hermes_cli.web_server import start_server; start_server(host='127.0.0.1', port=…)"`,
and per-profile ttyd sessions with `HERMES_HOME` pinned per profile. Consequences: a broken
repository dependency generation kills surfaces one at a time, and a healthy gateway proves
nothing about the interpreter the dashboard uses.

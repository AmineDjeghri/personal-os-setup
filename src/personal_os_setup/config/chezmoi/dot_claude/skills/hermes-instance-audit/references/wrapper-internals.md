# The add-on wrapper: options, source selection, patches

Depth for the add-on image triage (`addon-image-update-triage.md`). Everything here is read-only reconnaissance of the running
add-on image: `/run.sh` (entrypoint), `/usr/local/lib/hermes-source-channel.py` (selector),
`/usr/local/bin/hermes-dashboard-patches` (ingress patches), `/data/options.json` (options),
`$HERMES_HOME/source-checks/` (core's own update identity).

## 1. Option → code path (what a changelog bullet can even reach)

| Options state | What runs at startup |
|---|---|
| existing `$SRC_DIR/.git`, blank `git_ref`, `auto_update: false` | NOTHING source-related: no clone, no fetch, no channel read, no pull |
| no `$SRC_DIR/.git` (fresh) | staged clone `<src>.clone.XXXXXX`, verified against the published commit when a pin was resolved, moved into place only after the check; a source path existing without `.git` is fatal |
| `auto_update: true` + official URL + blank `git_ref` | native source-channel resolver (`hermes-source-channel.py update`) picks and applies the target; failure keeps the existing checkout and startup continues |
| `auto_update: true` + explicit ref or custom URL | legacy path: `git stash` → `git pull --ff-only` → `git stash pop` → submodules |
| `enable_desktop_backend: false` | no desktop backend; no Go/toolchain download |
| `git_ref` non-empty on a fresh clone | that ref is cloned directly (branch or tag) |

Probe: `grep -n "AUTO_UPDATE\|GIT_REF\|DESKTOP_BACKEND" /run.sh`; the function is
`install_hermes_core()`. Dependency/Python/venv work sits AFTER source selection and only runs when
the runtime probe fails or the pinned `.python-version` changed.

## 2. Where the saved channel lives

- Per profile `config.yaml`: `update.installs.<sha256(resolved source root)[:16]>.channel`. Every
  configured profile home is read; a record in any of them counts.
- No record → `stable`, non-explicit → **forward-only** moves (an unset default never walks back).
  `main` requires a native-capable checkout; an older checkout lacking the native source-channel API
  holds a non-stable channel with an actionable warning and keeps starting.
- Two profiles naming different channels is a fatal startup conflict ("select one channel for the
  shared install") — report it as a config defect; do not hand-edit config files.
- `$HERMES_HOME/source-checks/<sha16>.json` = core's own identity record (`head`, `branch`,
  `channel` of the checkout as it sees it, `behind`, `commits`). Use it for "how far behind", never
  as the add-on's chosen channel (they are written by different layers).

## 3. Ingress patches — why the checkout is dirty

`/usr/local/bin/hermes-dashboard-patches SRC_DIR STATUS_FILE` runs at every start and patches:

- `web/src/lib/api.ts` — modern path: injects an `import.meta.url` base fallback
  (`HA-ADDON-IMPORT-META-FALLBACK-PATCHED`); legacy path: rewrites `const BASE = …`
  (`HA-ADDON-BASE-PATCHED`).
- `web/vite.config.ts` — forces a relative asset base (`/* HA-ADDON-BASE-INJECTED */` + `base: "./"`).
- legacy-only: `web/src/plugins/usePlugins.ts`, `web/src/main.tsx` (router basename).
- `hermes_cli/dashboard_auth/prefix.py` — raises upstream's `X-Forwarded-Prefix` length ceiling
  (64 → 256) because HA Ingress tokens are long (`HA-ADDON-PREFIX-LIMIT-PATCHED`).

Properties that matter for triage: idempotent (marker present = already patched), non-fatal on
drift (prints `WARNING: <file> pattern changed upstream` and continues), and re-applied after any
successful source update, so a two-file `M` status is the healthy steady state.

## 4. Probe commands used

```bash
hostname                                    # <sha16>-<addon-slug> = which container
cat /data/options.json                      # this container's options
curl -s -H "Authorization: Bearer $SUPERVISOR_TOKEN" -o /tmp/self.json \
     http://supervisor/addons/self/info     # version / version_latest
hermes --version                            # CORE version + install dir only
git -C $SRC_DIR remote -v                   # '[tree:0]' => partial clone
git -C $SRC_DIR status --porcelain
git -C $SRC_DIR count-objects -vH
git -C $SRC_DIR tag | wc -l; git -C $SRC_DIR branch -a | wc -l
```

Sizes that matter on an HA box: `du -sh $HERMES_HOME/{hermes-agent,tools,cache,logs,installs,state.db}`;
inside the checkout `.git`, `node_modules`, `venv` and the built web dist dominate.

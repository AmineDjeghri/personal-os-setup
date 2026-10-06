---
name: chezmoi-scripts
description: Use when adding/debugging a chezmoi run_/run_once_/run_onchange_ script under config/chezmoi/, or when a dotfiles sync script "isn't firing" — "why didn't my script run", "add a script that starts X after sync", "the hyprland/noctalia script isn't triggering". Covers how this app's "apply selected" scopes chezmoi apply to specific targets, and why that means scripts often don't run even though their sibling config file did apply.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# chezmoi script scoping in personal-os-setup

## The core gotcha: a targeted `chezmoi apply` does not run sibling scripts

The "Sync dotfiles" tab's `apply selected`/`diff selected` buttons never run a bare `chezmoi apply` — `chezmoi_apply()` in `tasks/system/chezmoi.py` always passes the selected paths as explicit targets: `chezmoi apply --force --parent-dirs <target1> <target2> ...`. A `run_`/`run_once_`/`run_onchange_` script only executes if **its own managed path** is in that target list — being in the *same directory* as a targeted file is not enough:

- `chezmoi apply <only .zshrc>` → noctalia/hypr untouched, scripts don't run.
- `chezmoi apply <only noctalia/config.toml>` (a **sibling** of the script in the same dir) → the script still does **not** run.
- `chezmoi apply <the script's own managed path>` → script runs.

Reproduce it against a scratch source dir before relying on the behaviour:
```sh
mkdir -p /tmp/t/{home,src/dot_config/x} && cd /tmp/t
echo x > src/dot_config/x/file.txt
printf '#!/bin/bash\necho RAN\n' > src/dot_config/x/run_after_thing.sh
HOME=$PWD/home chezmoi --source $PWD/src apply -v --force --parent-dirs $PWD/home/.config/x/file.txt
# "RAN" does not print -- the script's own path wasn't a target.
```

## Why this matters for the frontend's dotfiles tree

`chezmoi_managed_paths()` (`tasks/system/chezmoi.py`) calls `chezmoi managed --include=files,scripts,symlinks`, so **scripts show up as their own selectable leaf entries** in the tree (`app.py`'s `Tree[DotfileTreeNode]`), separate from the config files next to them. Tree-node selection (`on_tree_node_selected` → `data.all_file_paths()`) selects every leaf under whichever node you click:

- Select only `noctalia/config.toml` and click `apply selected` → the config applies, but `run_after_ensure-noctalia-running.sh.tmpl` (a sibling leaf) does **not** fire.
- Select the whole `noctalia` **folder** → the script leaf is included, so it fires.
- Same rule for `run_after_check-hyprland-plugins.sh.tmpl` under `hypr`.

**Practical rule when testing or writing docs about "sync X":** tell the user (or write in the Start guide) to select the *whole folder* for anything with an accompanying `run_*` script — otherwise the script silently never runs and the change looks like it "didn't work" even though the file applied fine.

## Script prefix semantics

- `run_<name>` — runs on **every** `chezmoi apply` that targets it, no state tracking. Used for `dot_config/noctalia/run_after_ensure-noctalia-running.sh.tmpl` and `dot_config/hypr/run_after_check-hyprland-plugins.sh.tmpl` — both idempotent "recheck and self-heal if needed" scripts, which is exactly what this prefix is for.
- `run_once_<name>` — runs once ever per this machine's chezmoi state (tracked by content hash); re-running identical content is a no-op even if targeted. Used for `dot_config/vicinae/run_once_after_enable-vicinae.sh.tmpl`, `dot_config/coolercontrol/run_once_after_enable-coolercontrold.sh.tmpl`.
- `run_onchange_<name>` — runs when targeted **and** the script's own content (or anything hashed into it via `{{ include "..." | sha256sum }}` comments) changed since the last *successful* (exit 0) run. Used for `dot_config/noctalia/run_onchange_after_set-greeter-keymap.sh.tmpl`.
- `_before_`/`_after_` controls ordering relative to file application in the same pass, not targeting/scoping.

⚠️ **`run_onchange_` + a script that always `exit 0` = permanently stuck after the first run.** `--force` reapplies changed *files*; it does **not** re-run a `run_onchange_` script whose tracked content hasn't changed. So the first successful run records the hash as applied even when the script's actual job failed, and every later apply skips the script silently (zero output, 0.03s). State that can drift outside chezmoi's awareness (`hyprpm remove` run by hand, say) is then never noticed. **If a script's job is "keep re-checking and self-healing", use `run_`, not `run_onchange_`** — `run_onchange_` is only for scripts whose purpose is tied to specific tracked content (e.g. reapplying a keymap when the keymap config changes).

## hyprpm plugins: build vs. load are different, and only one is automatable

`run_after_check-hyprland-plugins.sh.tmpl` only *loads* already-built plugins; it never builds them. `hyprctl plugin load <path-to-.so>` is a plain unprivileged Hyprland IPC call (like `hyprctl eval`) — it just needs the cached `.so`, no sudo. `hyprctl plugin list` (not `hyprpm list`) is the source of truth for what's loaded, since `plugin load` doesn't update hyprpm's own `state.toml`.

Building (`hyprpm add <repo>`) needs hyprpm's internal `sudo`, which works when run directly but **hangs when chezmoi invokes it** (stranded password prompt in the Logs tab, needing a manual kill). So the script never attempts `hyprpm add`/`update`; for anything not yet built it logs/notifies the exact command to run manually in a real terminal. Don't reintroduce those calls without a NOPASSWD sudoers rule first — a host security-policy change, needing the same per-action confirmation as any sudo step (see `AGENTS.md`).

## `hyprctl keyword` vs `hyprctl eval` for Lua-configured Hyprland

This repo's `dot_config/hypr/*.lua` files use Hyprland's Lua config parser (the `hl.config({...})`/`hl.plugin.*` API — see `hyprbars.lua`, `hyprland.lua`). On a Lua-parsed config the classic `hyprctl keyword <key> <value>` is rejected outright (`keyword can't work with non-legacy parsers. Use eval.`). Use `hyprctl eval` with the same Lua table shape the `.lua` files use:
```sh
hyprctl eval 'hl.config({ plugin = { hyprbars = { enabled = false } } })'
```
That's the way to toggle a loaded plugin's live behaviour (e.g. hide/show hyprbars) without touching hyprpm, and the fix for hyprbars staying invisible after a hot-load (the `if hl.plugin.hyprbars then ... end` block not reliably re-applying) — toggling `enabled` false→true via `eval` forces it. The script does this automatically for every plugin in its `plugins=(...)` list that `hyprctl plugin list` shows as loaded; it needs no privilege and is a no-op for plugins whose lua config exposes no `enabled` key.

## Keep `hyprland.lua`'s top-level requires guarded

`require()` calls at the top of `hyprland.lua` must not be bare. A required module that is transiently missing or broken mid-sync (chezmoi's reload trigger races the file writes) throws, and a bare `require` **aborts the rest of the file** — so nothing after it, `binds.lua` included, ever loads, and `hyprctl configerrors` latches the error until a later reload catches every file valid at once (not something `sleep` fixes). Reading shared globals like `TERMINAL`/`APP_LAUNCHER` from a module at load time has the same failure mode without a nil-check. Rules: wrap each top-level require in a `pcall`-based `requireModule()` helper, and keep load-bearing shared state (the former `variables.lua`) at the top of `hyprland.lua` itself, where it isn't fetched via `require`.

## Adding a new script

Follow the shape of the existing ones (`vicinae`/`coolercontrol`/`noctalia`): `set -eu`, a `notify()` helper using `notify-send` if present, an early exit if the required binary is missing, then the idempotent check-then-act body. See [[add-system-action]] for the surrounding `SystemAction`/dotfiles machinery, and keep [[repo-gotchas]]'s and `AGENTS.md`'s "confirm before running" rule in mind — a script committed here really executes on the next apply.

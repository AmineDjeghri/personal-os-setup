---
name: chezmoi-scripts
description: Use when adding/debugging a chezmoi run_/run_once_/run_onchange_ script under config/chezmoi/, or when a dotfiles sync script "isn't firing" — "why didn't my script run", "add a script that starts X after sync", "the hyprland/noctalia script isn't triggering". Covers how this app's "apply selected" scopes chezmoi apply to specific targets, and why that means scripts often don't run even though their sibling config file did apply.
---

# chezmoi script scoping in personal-os-setup

Verified directly against a real `chezmoi` binary (v2.72.0), not assumed from docs — see the exact commands below if you want to reproduce.

## The core gotcha: a targeted `chezmoi apply` does not run sibling scripts

The "Sync dotfiles" tab's `apply selected`/`diff selected`/etc. buttons never run a bare `chezmoi apply` — `chezmoi_apply()` in `tasks/system/chezmoi.py` always passes the selected paths as explicit targets: `chezmoi apply --force --parent-dirs <target1> <target2> ...`. A `run_`/`run_once_`/`run_onchange_` script only executes if **its own managed path** is included in that target list — being in the *same directory* as a targeted file is not enough:

- `chezmoi apply <only .zshrc>` → noctalia/hypr untouched, scripts don't run.
- `chezmoi apply <only noctalia/config.toml>` (a **sibling** file in the same dir as the script) → the script still does **not** run, even though it's in the same folder.
- `chezmoi apply <the script's own managed path>` → script runs.

Reproduce this yourself with a scratch source dir if you need to double-check chezmoi's current behavior before relying on it:
```sh
mkdir -p /tmp/t/{home,src/dot_config/x} && cd /tmp/t
echo x > src/dot_config/x/file.txt
printf '#!/bin/bash\necho RAN\n' > src/dot_config/x/run_after_thing.sh
HOME=$PWD/home chezmoi --source $PWD/src apply -v --force --parent-dirs $PWD/home/.config/x/file.txt
# "RAN" does not print -- the script's own path wasn't a target.
```

## Why this matters for the frontend's dotfiles tree

`chezmoi_managed_paths()` (`tasks/system/chezmoi.py`) calls `chezmoi managed --include=files,scripts,symlinks` — **scripts show up as their own selectable leaf entries** in the tree (`app.py`'s `Tree[DotfileTreeNode]`), separate from the config files they live next to. Tree-node selection (`on_tree_node_selected` → `data.all_file_paths()`) selects every leaf under whichever node you click:

- Select only `noctalia/config.toml` and click `apply selected` → the config applies, but `run_after_ensure-noctalia-running.sh.tmpl` (a sibling leaf) does **not** fire.
- Select the whole `noctalia` **folder** → the script leaf is included too, so it fires.
- Same rule for `run_after_check-hyprland-plugins.sh.tmpl` under `hypr`.

**Practical rule when testing or writing docs about "sync X":** always tell the user (or write in the Start guide) to select the *whole folder* for anything that has an accompanying `run_*` script, not just the specific config file inside it — otherwise the script silently never runs and the change looks like it "didn't work" even though the file itself applied fine.

## Script prefix semantics (chezmoi's own rules, for reference)

- `run_<name>` — runs on **every** `chezmoi apply` that targets it, no state tracking at all. Used for `dot_config/noctalia/run_after_ensure-noctalia-running.sh.tmpl` and `dot_config/hypr/run_after_check-hyprland-plugins.sh.tmpl` — both are idempotent "recheck and self-heal if needed" scripts, which is exactly what this prefix is for.
- `run_once_<name>` — runs once ever per this machine's chezmoi state (tracked by content hash); re-running the exact same script content again is a no-op even if targeted. Used for `dot_config/vicinae/run_once_after_enable-vicinae.sh.tmpl`, `dot_config/coolercontrol/run_once_after_enable-coolercontrold.sh.tmpl`.
- `run_onchange_<name>` — runs when targeted **and** the script's own content (or anything hashed into it via `{{ include "..." | sha256sum }}` comments) has changed since the last *successful* (exit 0) run — **`--force` does not override this**, confirmed directly (see the pitfall below). Used for `dot_config/noctalia/run_onchange_after_set-greeter-keymap.sh.tmpl`.
- `_before_`/`_after_` in the name controls ordering relative to file application in the same apply pass, not targeting/scoping — doesn't affect any of the above.

**Pitfall that cost real debugging time: `run_onchange_` + a script that always `exit 0` = permanently stuck after the first run.** `dot_config/hypr/check-hyprland-plugins.sh.tmpl` was originally `run_onchange_`, hash-tracking `hyprbars.lua`/`binds.lua`. It's also written to always `exit 0` (warn on a missing plugin, don't fail the apply) — a reasonable choice on its own. Combined, the two choices broke retries entirely: the first time it ran with a given content hash, chezmoi recorded that hash as "successfully applied," regardless of whether the plugin actually got installed inside. Every later `chezmoi apply --force` against unchanged content then skipped the script outright — **zero output, 0.03s, no attempt at anything** — because `--force` reapplies changed *files*, it does not re-run a `run_onchange_` script whose tracked content hasn't changed. Confirmed by editing the script (any content change) and watching it immediately execute again; reverting the edit made it skip again just as immediately. Plugin state can drift outside chezmoi's awareness (e.g. `hyprpm remove`, run manually) with nothing in `run_onchange_`'s hash tracking able to notice — the script was effectively dead after its first successful run. Fixed by switching to plain `run_`: no hash gating, always re-attempts, still cheap when there's nothing to do (a few `hyprctl`/`hyprpm list` checks). **If a script's job is "keep re-checking and self-healing," use `run_`, not `run_onchange_` — `run_onchange_` is for scripts whose entire purpose is tied to specific tracked file content (e.g. reapplying a keymap only when the keymap config itself changes), not for idempotent drift-correction.**

## hyprpm plugins: build vs. load are different, and only one is automatable

`run_after_check-hyprland-plugins.sh.tmpl` only *loads* already-built plugins; it never
builds them. `hyprctl plugin load <path-to-.so>` is a plain unprivileged Hyprland IPC
call (like `hyprctl eval`) — it just needs the cached `.so` to exist, no sudo. Note
`hyprctl plugin list` (not `hyprpm list`) is the source of truth for what's actually
loaded, since `plugin load` doesn't update hyprpm's own `state.toml`.

Building a plugin (`hyprpm add <repo>`) needs hyprpm's own internal `sudo` call, which
works fine run directly but **hangs when chezmoi invokes it** — reproduced on a real
machine: the app got stuck with a stranded password prompt in the Logs tab, needing a
manual kill, even after typing the password once. So the script never attempts
`hyprpm add`/`update` — for anything not yet built, it just logs/notifies the exact
`hyprpm add <repo>` command to run manually in a real terminal. Don't reintroduce
`hyprpm add`/`update` into this script without a NOPASSWD sudoers rule removing the
interactive-password step first (a host security policy change, needs the same explicit
per-action confirmation as any other sudo step in this repo — see `CLAUDE.md`).

## `hyprctl keyword` vs `hyprctl eval` for Lua-configured Hyprland

This repo's `dot_config/hypr/*.lua` files use Hyprland's newer Lua config parser (the `hl.config({...})`/`hl.plugin.*` API — see `hyprbars.lua`, `hyprland.lua`). On a Lua-parsed config, the classic `hyprctl keyword <key> <value>` command is rejected outright: `keyword can't work with non-legacy parsers. Use eval.` Use `hyprctl eval` with the same Lua table shape the `.lua` files already use instead, e.g.:
```sh
hyprctl eval 'hl.config({ plugin = { hyprbars = { enabled = false } } })'
```
This is the practical way to toggle a plugin's live behavior (e.g. hide/show hyprbars) without touching hyprpm at all, once the plugin is already loaded. It's also the actual fix for hyprbars staying visually invisible after a hot-load (the `if hl.plugin.hyprbars then ... end` block in `hyprbars.lua` not reliably re-applying) — toggling `enabled` false→true via `eval` forces it. The script runs this automatically for every plugin in its `plugins=(...)` list that shows as loaded per `hyprctl plugin list`, since it needs no privilege at all and is a harmless no-op for plugins whose lua config doesn't expose an `enabled` key.

## Adding a new script

Follow the shape of the existing ones (`vicinae`/`coolercontrol`/`noctalia` scripts): `set -eu`, a `notify()` helper using `notify-send` if present, an early exit if the required binary is missing, then the idempotent check-then-act body. See [[add-system-action]] for how the surrounding `SystemAction`/dotfiles section machinery works, and keep destructive/host-mutating command additions here in mind for [[repo-gotchas]]'s and `CLAUDE.md`'s "confirm before running" rule — a script committed here will actually execute on a real machine the next time someone selects its folder and applies.

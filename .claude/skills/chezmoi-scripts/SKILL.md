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
- Same rule for `run_onchange_after_install-hyprland-plugins.sh.tmpl` under `hypr` — and it's `run_onchange_`, so it additionally needs the hash-tracked `hyprbars.lua`/`binds.lua` content to have changed since the last time it *successfully* ran (see the `# ... hash: {{ include ... | sha256sum }}` comment lines at the top of that script — that's the change-trigger, not the folder selection alone).

**Practical rule when testing or writing docs about "sync X":** always tell the user (or write in the Start guide) to select the *whole folder* for anything that has an accompanying `run_*` script, not just the specific config file inside it — otherwise the script silently never runs and the change looks like it "didn't work" even though the file itself applied fine.

## Script prefix semantics (chezmoi's own rules, for reference)

- `run_<name>` — runs on **every** `chezmoi apply` that targets it (used for `dot_config/noctalia/run_after_ensure-noctalia-running.sh.tmpl`, an idempotent "start if not running" check, safe to re-run constantly).
- `run_once_<name>` — runs once ever per this machine's chezmoi state (tracked by content hash); re-running the exact same script content again is a no-op even if targeted. Used for `dot_config/vicinae/run_once_after_enable-vicinae.sh.tmpl`, `dot_config/coolercontrol/run_once_after_enable-coolercontrold.sh.tmpl`.
- `run_onchange_<name>` — runs when targeted **and** the script's own content (or anything hashed into it via `{{ include "..." | sha256sum }}` comments) has changed since the last successful run. Used for `dot_config/hypr/run_onchange_after_install-hyprland-plugins.sh.tmpl` and `dot_config/noctalia/run_onchange_after_set-greeter-keymap.sh.tmpl`.
- `_before_`/`_after_` in the name controls ordering relative to file application in the same apply pass, not targeting/scoping — doesn't affect any of the above.

## Adding a new script

Follow the shape of the existing ones (`vicinae`/`coolercontrol`/`noctalia` scripts): `set -eu`, a `notify()` helper using `notify-send` if present, an early exit if the required binary is missing, then the idempotent check-then-act body. See [[add-system-action]] for how the surrounding `SystemAction`/dotfiles section machinery works, and keep destructive/host-mutating command additions here in mind for [[repo-gotchas]]'s and `CLAUDE.md`'s "confirm before running" rule — a script committed here will actually execute on a real machine the next time someone selects its folder and applies.

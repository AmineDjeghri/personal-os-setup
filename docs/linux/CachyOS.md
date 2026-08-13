# CachyOS Hyprland Developer Workstation Setup

> Work in progress.
>
> This document tracks a migration from Windows to a native Linux development
> workstation. It is updated as the setup is tested and refined.

## Goal

Replace a Windows 11 + WSL workflow with a fully native Linux environment.

| Before     | After                            |
|------------|----------------------------------|
| Windows 11 | CachyOS                          |
| WSL        | Native Linux development         |
| GlazeWM    | Hyprland (no KDE Plasma desktop) |
| ShareX     | grim + slurp + satty             |
| Raycast    | Vicinae                          |
| —          | Noctalia (bar / control centre)  |
| —          | Ghostty (terminal)               |
| —          | Native Linux gaming              |

KDE applications (Dolphin, Spectacle) are used where they are the best option.

---

## Installation

### Secure Boot

Disabled — the CachyOS installer was blocked by Secure Boot.

### Bootloader and filesystem

- Bootloader: **Limine**
- Filesystem: **Btrfs**
- Encryption: **LUKS**


### Keyboard layout defaults to QWERTY on first login

Even if you selected **AZERTY** during installation, Hyprland's login/greeter session
(**noctalia-greeter**, run via **greetd** — already the default for this Hyprland+Noctalia
setup) can still start in **QWERTY**. The layout lives in
`/var/lib/noctalia-greeter/greeter.toml`:

```toml
[keyboard]
layout = "fr,us"
options = "grp:alt_shift_toggle"  # switch layouts with Alt+Shift
```

This file is root-owned and lives outside chezmoi's `$HOME` scope, so it isn't managed
by this repo yet. This command backs up the original, then upserts the `[keyboard]`
section (replacing it if it already exists, appending it if not) without touching the
rest of the file:

```bash
sudo cp /var/lib/noctalia-greeter/greeter.toml /var/lib/noctalia-greeter/greeter.toml.bak 2>/dev/null

sudo awk '
  /^\[keyboard\]/ { print; print "layout = \"fr,us\""; print "options = \"grp:alt_shift_toggle\""; in_kb=1; done=1; next }
  /^\[/ && in_kb { in_kb=0 }
  in_kb && /^(layout|options)[[:space:]]*=/ { next }
  { print }
  END { if (!done) print "\n[keyboard]\nlayout = \"fr,us\"\noptions = \"grp:alt_shift_toggle\"" }
' /var/lib/noctalia-greeter/greeter.toml | sudo tee /var/lib/noctalia-greeter/greeter.toml.new >/dev/null

sudo mv /var/lib/noctalia-greeter/greeter.toml.new /var/lib/noctalia-greeter/greeter.toml
sudo systemctl restart greetd
```

There is no on-screen button/icon in the greeter to switch layouts — per the
[Noctalia greeter docs](https://docs.noctalia.dev/greeter/), switching only works
through the XKB keybind set in `options` above (Alt+Shift here).

Until `[keyboard]` is set, type your password using the QWERTY layout to log in,
then:

1. Log in (QWERTY password entry).
2. Install this app and sync the hyprland folder (already set to `"fr,us"` in this project's config).
3. Reboot so the new layout takes effect everywhere, including the login screen.
4. Install a browser — this project's `packages.yaml` already lists `helium-browser-bin`
   and `brave-bin` under `cachyos.pacman.Browsers`.

---

### After first boot

```bash
sudo pacman -Syu
```

Verify the NVIDIA driver:

```bash
nvidia-smi
```

If this prints GPU information, the driver is working. CachyOS ships the NVIDIA
stack preinstalled and keeps the kernel module in sync with the running kernel,
so there is normally nothing to install.

You can also click the temperature readout in the Noctalia top bar to see CPU
temperature, GPU name and general system information without opening settings.


## Packages

Most of the packages below are managed by this project — run the app and install
them from the UI rather than by hand:

```bash
sudo pacman -S make

./install_unix.sh
```

The catalog lives in `src/personal_os_setup/config/packages.yaml`, under a single
`cachyos:` key. This project targets CachyOS specifically — generic Arch and
other derivatives are not supported.

Two package managers are used:

- **pacman** — official repositories
- **paru** — AUR. CachyOS ships paru by default;

Vicinae has its own installer:

```bash
curl -fsSL https://vicinae.com/install | bash
```

---

## Desktop

### Configuration files

Copy the personal configuration for Hyprland and Noctalia into `~/.config`.
Enable **View → Show Hidden Files** in Dolphin to see the directory.

Verify the keybindings afterward — for example `ALT+F` for fullscreen.

### Settings owned by Noctalia, not Hyprland

Some desktop behavior that most Hyprland setups configure in `hyprland.conf` (or via
standalone daemons like `hypridle`/`hyprlock`/`hyprpaper`) is instead configured in
Noctalia's own `~/.config/noctalia/config.toml`.

- **Idle timeout / screen lock / suspend** — `[idle.behavior.*]`. No `hypridle`/`hyprlock` installed or needed.
- **Wallpaper** — `[theme] source = "wallpaper"` plus the `nzlov/daily-wallpaper`
  plugin under `[plugins]`. No `swww`/`hyprpaper`.
- **Night light / blue light filter** — `[nightlight]`. Note `wlsunset` is still in
  `packages.yaml` too — check which one is actually active before assuming both run.
- **Screenshot pipeline** — `[shell.screenshot]` routes through Noctalia's own
  screenshot action (piped to `satty`).
- **Session menu** (lock / logout / reboot / shutdown / suspend) — `[[shell.session.actions]]`,
  each with its own shortcut inside the session menu.

### Editing the lockscreen layout

The lockscreen widget layout is edited live, not through a config file: click the lock
icon (`lockscreen-edit` in the bar's `start` list, top-left of the Noctalia bar) to
toggle edit mode. Switch to an empty workspace first — otherwise windows behind the
lockscreen preview get in the way of seeing the live editing.

### Hyprland plugins

`hyprpm` builds plugins from source, so the build tooling above must be
installed first.

```bash
hyprpm update

# ALT+TAB window switcher
hyprpm add https://github.com/gfhdhytghd/hymission
hyprpm enable hymission

# Title bars: drag, close, maximise
hyprpm add https://github.com/hyprwm/hyprland-plugins
hyprpm enable hyprbars

hyprpm reload
hyprpm list
```

Test `ALT+TAB` for the switcher, and dragging / closing / maximizing windows for hyprbars.

---

## Shell

CachyOS defaults to **fish** as the login shell, with `cachyos-fish-config` and
`cachyos-zsh-config` both installed.

This setup moves to **zsh** with oh-my-zsh and the powerlevel10k prompt. `.zshrc` and
`.p10k.zsh`, plus oh-my-zsh itself and all its plugins/theme, are managed via
[chezmoi](https://www.chezmoi.io/), with its source directory vendored inside this
repo at `src/personal_os_setup/config/chezmoi/`. oh-my-zsh/plugins/theme are declared as
`git-repo` externals in `.chezmoiexternal.toml`.

The app's "Sync dotfiles" tab lists every chezmoi-managed file as a checkbox (none
checked by default — pick which ones you mean to act on); use **diff selected** to
preview changes, **apply selected** to write them to your home directory, **re-add
selected** to pull live edits back into the repo, or **forget selected** to stop
tracking a file (the live file is left untouched — only the repo's copy is removed).
Check everything and run the corresponding action to reproduce the old whole-tree
`chezmoi apply`/`diff`/`re-add` behavior. To start tracking a new file, use
**chezmoi: track a new file** and enter its path — this copies it into the repo (never
edit a live dotfile directly and expect it to be under version control). chezmoi has
no auto-backup, so always run **diff selected** before **apply selected**.
`set zsh as default shell` remains a separate `zsh` action.
---

## Theming

Noctalia can set application themes directly (**Noctalia settings → Themes**).
Personal themes are kept rather than using the bundled ones.

Do not remove the Qt5/Qt6 theme packages — the Noctalia theme cannot currently
be removed without affecting them.

## Gaming

`packages.yaml` currently only installs `steam` under `cachyos.pacman.Gaming` — the pieces
below are not yet in the catalog and need to be added/installed later in the next update.

### Base packages

- `cachyos-gaming-meta` — CachyOS's own meta-package, pulls in `gamemode`, `mangohud`,
  `lib32-mesa`/`lib32-vulkan-*` and other 32-bit Proton/Wine runtime deps in one shot.
  Installing this covers most of the packages below without listing them individually.
- CachyOS already ships a gaming-optimized kernel (`linux-cachyos`, BORE/EEVDF scheduler)
  and repo-level `-O3`/`x86-64-v3` optimized packages by default — nothing to configure here,
  it's the baseline the whole distro is built on.

### GameMode

`gamemode` temporarily applies CPU governor/scheduler/GPU tweaks while a game runs. Add
`gamemoderun %command%` as a Steam launch option per game, or `gamemode --dlsym`.

Conflict to know about: **GameMode and `ananicy-cpp` both try to renice the same
processes.** If `ananicy-cpp` is running (check `systemctl status ananicy-cpp`), stop/disable
it before relying on GameMode, or expect fights over process priority.

### MangoHud

FPS/frametime/CPU/GPU overlay. `mangohud %command%` as a Steam launch option (combine with
GameMode: `gamemode mangohud %command%`), or `mangohud --dlsym` for OpenGL titles that need
the dlsym hook. Config: `~/.config/MangoHud/MangoHud.conf`.

### Proton

Prefer **Proton-CachyOS** (CachyOS's own Proton fork, tracks Proton's bleeding-edge branch)
over stock Steam Proton for anything demanding — it merges fixes faster and, as of the
mid-2026 update, **auto-detects and enables HDR per-game** with no launch options needed.
Install/manage versions via **ProtonUp-Qt** (also handles GE-Proton if a specific game needs
it instead). Set the version per-game in Steam: right-click → Properties → Compatibility.

### HDR / 10-bit desktop

Desktop HDR is a Hyprland output setting, independent of Steam/Proton — do this first if you
want HDR games to actually look right, not just run:

1. Enable HDR in the monitor's own OSD menu first.
2. The monitor output config here is generated by **nwg-displays**
   (`~/.config/hypr/config/monitors.lua`, "Do not edit manually") — its "Enable 10-bit
   support" toggle only sets `bitdepth = 10`. That alone is 10-bit **SDR**, not HDR.
3. Real HDR needs both `bitdepth = 10` **and** `cm = "hdr"` on the monitor block. nwg-displays'
   GUI does not expose `cm`, and will not preserve a manually-added `cm` line the next time it
   rewrites the file. Either hand-edit `cm = "hdr"` in knowing it may get clobbered on the next
   nwg-displays change, or switch to **HyprDisplays**
   ([ryzendew/HyprDisplays](https://github.com/ryzendew/HyprDisplays)), the actively developed
   successor with first-class HDR/10-bit/wide-gamut/VRR toggles.
4. Verify: `hyprctl monitors -j` — the target output's `currentFormat` should move off
   `XRGB8888` to a 10-bit format once both fields are set.

## Apps shortcuts
For per-app configuration and shortcuts (Vicinae, Obsidian, PyCharm, Bitwarden, Nautilus,
the terminal tools cheatsheet), plus a table of what's available on CachyOS vs. Windows/macOS
and their alternatives, check
[apps_configuration_and_shorcuts.md](../apps/apps_configuration_and_shorcuts.md#app-availability--alternatives-across-oses).

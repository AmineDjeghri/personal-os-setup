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

### Secret storage (gnome-keyring, not KWallet)

Hyprland has no built-in Secret Service — anything that stores secrets (Nautilus/GVfs unlocking a
LUKS drive, browsers saving passwords, etc.) talks to `org.freedesktop.secrets` over D-Bus, and
nothing provides that name unless something starts a daemon for it. KDE's `kwallet` isn't advised to be used without plasma.

**`gnome-keyring` is used instead** — password-based, no GPG key needed, and the standard choice on non-KDE Wayland compositors:
- **Not auto-unlocked with the login password, by choice.** `pam_gnome_keyring.so` can do this, but it doesn't look at "whichever keyring is currently set as default"
- Apps using `libsecret` (Nautilus/GVfs, GTK/GNOME apps, Chromium-based browsers) otherwise just work — the manual prompt above is the only friction point.
- To view/delete stored secrets: `sudo pacman -S seahorse` ("Passwords and Keys" GUI), or `secret-tool` for CLI lookups. <!-- pragma: allowlist secret -->
- Bitwarden (website/app logins, secure notes, cards) is unrelated and doesn't cover this — it doesn't integrate with the system Secret Service, so it can't store or auto-unlock OS-level secrets like this LUKS passphrase, SSH SFTP, or NetworkManager WiFi keys.

**Troubleshooting: `Error storing passphrase in keyring (the sessions wrapping the secret does not exist)`** when unlocking a drive in Nautilus, and/or drives disappearing from the sidebar — Kill and restart Nautilus after installing `gnome-keyring`

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

**Quick visual check (two monitors, one HDR + one non-HDR):** Play the same HDR YouTube video
(e.g. https://youtu.be/MV5hhbqDNLs?t=145) at 2Min25 in a browser window on each display — one on
the HDR-enabled monitor, one on a monitor still in SDR (or disable HDR in that monitor).
Then drag the SDR video window over onto the HDR display, right next to the other one, and compare them side by side.
If HDR is actually working, the window that started on the HDR display should look visibly brighter/punchier in
highlights and more saturated than the dragged-over one, even though both are now physically on
the same HDR-capable panel — because the dragged-in window was already tone-mapped down to SDR
before the move, while the other was rendered with the real PQ curve and wide gamut from the
start.  For a rigorous, numeric confirmation (not just "does it look different"), use the mpv IPC method [below](#Verifying-HDR-actually-works).


Desktop HDR is a Hyprland output setting, independent of Steam/Proton — do this first if you
want HDR games to actually look right, not just run:

1. Enable HDR in the monitor's own OSD menu first if your monitor has this.
2. `~/.config/hypr/config/monitors.lua`, Real HDR needs both `bitdepth = 10` **and** `cm = "hdr"` on the monitor block.
nwg-displays' GUI does not expose `cm`, and might not preserve a manually-added `cm` line the next time
3. Verify: `hyprctl monitors -j` — the target output's `currentFormat` should move off
   `XRGB8888` to a 10-bit format (e.g. XBGR2101010) once both fields are set.
4. **If YouTube (or other browser video) starts buffering/stuttering after enabling HDR**,
   reboot the machine and confirm.
5. **If the HDR monitor looks grey/washed out after the machine has been suspended** (idle
   long enough to trigger Noctalia's `lock-and-suspend`, then resumed) — this is a known,
   confirmed Hyprland bug: HDR/color-management state doesn't get correctly re-committed to
   the display on resume, even though Hyprland's own config values are still correct
   (`hyprctl monitors -j` still reports the right `sdrBrightness`/`sdrMaxLuminance`/etc. — the
   panel just isn't showing it). See
   [Washed out colors after resume from hibernation with monitor cm hdr · Issue #9724](https://github.com/hyprwm/Hyprland/discussions/9724)
   and the related [Discussion #10950](https://github.com/hyprwm/Hyprland/discussions/10950)
   (same class of bug on any HDR state transition, not just resume). Confirmed fix on this
   machine: **turn the monitor off and back on** (forces it to re-read the DRM state). If that's
   inconvenient, `hyprctl reload` is the documented lighter-weight workaround — try that first.
6. To confirm HDR is actually being decoded and displayed correctly end-to-end (not just that
   the monitor *format* changed), see [Verifying HDR actually works](#verifying-hdr-actually-works)
   in the apps doc — it queries mpv's live negotiated color state over IPC, rather than trusting the OSD.

With `cm = "hdr"` active, non-HDR apps (browser UI, etc.) aren't blasted at full HDR
brightness — Hyprland maps them into the `sdrBrightness`/`sdrMaxLuminance` slice above, while
surfaces that actually signal HDR metadata (e.g. a real HDR video) get their own negotiated range.

#### Verifying HDR actually works


End-to-end HDR (source → mpv → Hyprland → panel) was verified using this HDR10 test video:
https://www.youtube.com/watch?v=njX2bu-_Vw4 — playing it in mpv fullscreen via yt-dlp, then
querying mpv's live negotiated state over its JSON IPC socket rather than trusting the OSD:

1. Launch mpv with an IPC socket so its internal state can be queried while playing:
   ```bash
   mpv --input-ipc-server=/tmp/mpvsocket --fullscreen "https://www.youtube.com/watch?v=njX2bu-_Vw4"
   ```
2. From another terminal, query the three relevant properties via `socat` (or `echo` piped to
   `nc -U`):
   ```bash
   echo '{"command":["get_property","video-params"]}' | socat - /tmp/mpvsocket
   echo '{"command":["get_property","video-out-params"]}' | socat - /tmp/mpvsocket
   echo '{"command":["get_property","video-target-params"]}' | socat - /tmp/mpvsocket
   ```
3. What each answers:
    - **`video-params`** — the *source*'s real color metadata. HDR10 content should report
      `primaries: bt.2020`, `gamma: pq`, plus a mastering `max-luma`/`max-cll`.
    - **`video-out-params`** — what mpv actually sends to the display. If this matches
      `video-params` (same primaries/gamma/max-luma), mpv is passing the real HDR signal through
      rather than tone-mapping it down to SDR before output.
    - **`video-target-params`** — what mpv detected the *display itself* can do, negotiated live
      through Hyprland's Wayland color-management protocol (mpv needs
      `--target-colorspace-hint` for this). A genuine `bt.2020`/`pq` result with a `max-luma`
      close to the panel's real peak-nit spec (not clamped to ~225 or ~500 nits) confirms
      Hyprland is correctly advertising the display's HDR capability and mpv is targeting it.

4. A `solitaryBlockedBy: ['OPAQUE']` flag may still show up in Hyprland's scene-graph debug
   output for the mpv surface — that only affects *direct scanout* eligibility (a compositing
   performance optimization), not the color/brightness pipeline, so it doesn't indicate broken
   HDR.
5. Quick on-screen sanity check without IPC: press `I` in mpv for the full stats overlay,
   which also lists the negotiated colorspace/gamma/luma fields (less detail than the IPC query,
   but fast to eyeball, and stays in view when using windowed test videos).

## Apps shortcuts
For per-app configuration and shortcuts (Vicinae, Obsidian, PyCharm, Bitwarden, Nautilus,
the terminal tools cheatsheet), plus a table of what's available on CachyOS vs. Windows/macOS
and their alternatives, check
[apps_configuration_and_shorcuts.md](../apps/apps_configuration_and_shorcuts.md#app-availability--alternatives-across-oses).

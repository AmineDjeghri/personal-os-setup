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

---

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

### Manual fallback

If you are setting up before the app is available:

```bash
# Core CLI
sudo pacman -S ripgrep fd fzf jq tree btop fastfetch bat eza zoxide

# Build tooling (needed for Hyprland plugins)
sudo pacman -S base-devel cmake meson cpio git nlohmann-json

# Screenshot and annotation (bound to CTRL+Print in the Hyprland config)
sudo pacman -S grim slurp satty wl-clipboard

# Display and brightness
sudo pacman -S wdisplays brightnessctl wlsunset ddcutil
sudo modprobe i2c-dev            # required by ddcutil for external monitors

# Theming and Wayland integration
sudo pacman -S breeze-gtk kde-gtk-config qt5-wayland qt6-wayland hyprpolkitagent

# AUR
paru -S pycharm
```


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

Test `ALT+TAB` for the switcher, and dragging / closing / maximising windows for
hyprbars.

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

- **Dolphin**: Menu (hamburger) → Configure → Window Color Scheme → Breeze Dark
- **Qt**: run `qt6ct` (and `qt5ct`) to configure Qt application theming

---

## Still to do
- Install gaming packages from CachyOS Hello
- Configure Vicinae
- configure Noctalia
- Test desktop integration end to end
- Verify theming consistency across GTK and Qt applications
- Remove Kitty and Alacritty once Ghostty is confirmed
- Remove other unnecessary packages after testing

### Applications to try

- [Spectacle](https://apps.kde.org/spectacle/) — screenshots
- KDE Connect — phone integration

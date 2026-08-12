Apps configuration and shortcuts
================================

Settings, shortcuts, and cross-OS alternatives for the apps used by this project's Windows,
macOS, and CachyOS setups.

**Table of Contents**
<!-- TOC -->
* [Apps configuration and shortcuts](#apps-configuration-and-shortcuts)
  * [App availability & alternatives across OSes](#app-availability--alternatives-across-oses)
  * [1. General OS shortcuts](#1-general-os-shortcuts)
  * [2. Window Manager & Launcher](#2-window-manager--launcher)
    * [2.1. Windows: GlazeWM and Zebar](#21-windows-glazewm-and-zebar)
    * [2.2. macOS: AeroSpace + JankyBorders](#22-macos-aerospace--jankyborders)
    * [2.3. CachyOS: Hyprland + Noctalia](#23-cachyos-hyprland--noctalia)
    * [2.4. Launcher: Raycast / Vicinae](#24-launcher-raycast--vicinae)
  * [3. Terminal](#3-terminal)
    * [3.1. Windows Terminal](#31-windows-terminal)
    * [3.2. Terminal commands cheatsheet (macOS/CachyOS)](#32-terminal-commands-cheatsheet-macoscachyos)
  * [4. File manager](#4-file-manager)
    * [4.1. Windows: Files](#41-windows-files)
    * [4.2. CachyOS: Nautilus](#42-cachyos-nautilus)
  * [5. IDE & editors](#5-ide--editors)
    * [5.1. PyCharm (All platforms)](#51-pycharm-all-platforms)
      * [5.1.1. Tips & tricks](#511-tips--tricks)
      * [5.1.2. Personal PyCharm shortcuts](#512-personal-pycharm-shortcuts)
      * [5.1.3. Python remote interpreter (SSH/WSL)](#513-python-remote-interpreter-sshwsl)
      * [5.1.4. PyCharm remote deployment](#514-pycharm-remote-deployment)
      * [5.1.5. Remote SSH for ReactJS](#515-remote-ssh-for-reactjs)
    * [5.2. ZED (All platforms)](#52-zed-all-platforms)
  * [6. Notes / knowledge base](#6-notes--knowledge-base)
    * [6.1. Obsidian (All platforms)](#61-obsidian-all-platforms)
      * [Sync Obsidian vaults with iOS:](#sync-obsidian-vaults-with-ios)
  * [7. Passwords & security](#7-passwords--security)
    * [7.1. Bitwarden (All platforms)](#71-bitwarden-all-platforms)
    * [7.2. Disk encryption](#72-disk-encryption)
  * [8. Hardware, peripherals & monitoring](#8-hardware-peripherals--monitoring)
    * [8.1. HWiNFO (Windows) vs Hardware Monitoring (CachyOS)](#81-hwinfo-windows-vs-hardware-monitoring-cachyos)
    * [8.2. Keychron Launcher (All platforms)](#82-keychron-launcher-all-platforms)
    * [8.3. Multi-monitor: DisplayFusion (Windows only & paid)](#83-multi-monitor-displayfusion-windows-only--paid)
  * [9. Audio](#9-audio)
  * [10. Screenshots & screen recording](#10-screenshots--screen-recording)
    * [10.1. Screenshots](#101-screenshots)
    * [10.2. Screen recording](#102-screen-recording)
<!-- TOC -->

## App availability & alternatives across OSes

A single table covering every app/tool in
[packages.yaml](../../src/personal_os_setup/config/packages.yaml), plus a few OS-native features
that aren't in packages.yaml (disk encryption, audio control, general shortcuts). The **Notes**
column links to a dedicated section below when one exists, or to `packages.yaml` otherwise.
`✅` = present/used on that OS, `—` = not present/not applicable, `*` = see the footnote below the
table.

| Category / App                  | Windows                                                                                                     | macOS                                                  | Linux (CachyOS/Ubuntu Server)                                                     | Notes                                                                                                                                                                                                                                                                                                                            |
|---------------------------------|-------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| General OS shortcuts            | ✅                                                                                                          | ✅ (key remap)                                         | ✅ (Noctalia)                                                                     | → [§1](#1-general-os-shortcuts) · `Win+V` clipboard, `Win+L` lock · macOS remap in [macos_darwin/README.md](../macos_darwin/README.md#windowslinux-behavior-mimicking-in-macos) · CachyOS lock/idle in [CachyOS.md](../linux/CachyOS.md#settings-owned-by-noctalia-not-hyprland)                                                 |
| Window Manager                  | ✅ GlazeWM + Zebar                                                                                          | ✅ AeroSpace + JankyBorders                            | ✅ Hyprland + Noctalia                                                            | → [§2.1](#21-windows-glazewm-and-zebar) / [§2.2](#22-macos-aerospace--jankyborders) / [§2.3](#23-cachyos-hyprland--noctalia)                                                                                                                                                                                                     |
| Launcher                        | ✅ Raycast (MS Store)                                                                                       | ✅ Raycast                                             | ✅ Vicinae                                                                        | → [§2.4](#24-launcher-raycast--vicinae) · Raycast plugins work with Vicinae                                                                                                                                                                                                                                                      |
| Terminal emulator               | ✅ Windows Terminal                                                                                         | ✅ Ghostty                                             | ✅ Ghostty                                                                        | → [§3.1](#31-windows-terminal) · Ghostty is in `Dev_tools` in packages.yaml                                                                                                                                                                                                                                                      |
| Terminal tools cheatsheet       | via WSL only                                                                                                | ✅                                                     | ✅                                                                                | → [§3.2](#32-terminal-commands-cheatsheet-macoscachyos) · `Ctrl+T`/`Ctrl+R`/`Alt+C` (fzf)                                                                                                                                                                                                                                        |
| File manager                    | ✅ Files                                                                                                    | ✅ Finder (native)                                     | ✅ Nautilus                                                                       | → [§4.1](#41-windows-files) / [§4.2](#42-cachyos-nautilus) · macOS: native, no dedicated config                                                                                                                                                                                                                                  |
| PyCharm                         | ✅                                                                                                          | ✅                                                     | ✅                                                                                | → [§5.1](#51-pycharm-all-platforms) · shortcuts: [§5.1.2](#512-personal-pycharm-shortcuts)                                                                                                                                                                                                                                       |
| ZED                             | ✅                                                                                                          | ✅                                                     | ✅                                                                                | → [§5.2](#52-zed-all-platforms) · no special config documented yet                                                                                                                                                                                                                                                               |
| Obsidian                        | ✅                                                                                                          | ✅                                                     | ✅                                                                                | → [§6.1](#61-obsidian-all-platforms) · settings: `Ctrl+Alt+S` (same as PyCharm)                                                                                                                                                                                                                                                  |
| Bitwarden                       | ✅*                                                                                                         | ✅*                                                    | ✅ (pacman)                                                                       | → [§7.1](#71-bitwarden-all-platforms) · alt: iCloud Passwords (Windows/macOS/iOS)                                                                                                                                                                                                                                                |
| Disk encryption                 | ✅ BitLocker                                                                                                | ✅ FileVault (native)                                  | ✅ LUKS2                                                                          | → [§7.2](#72-disk-encryption) · CachyOS confirmed live via `cryptsetup`/`lsblk` (LUKS version 2) · macOS not documented yet                                                                                                                                                                                                      |
| Hardware monitoring             | ✅ HWiNFO                                                                                                   | —                                                      | ✅ CoolerControl + OpenRGB + nvtop + rivalcfg + nct6687d-dkms-git (sensor driver) | → [§8.1](#81-hwinfo-windows-vs-hardware-monitoring-cachyos)                                                                                                                                                                                                                                                                      |
| Keychron Launcher               | ✅                                                                                                          | ✅                                                     | ✅                                                                                | → [§8.2](#82-keychron-launcher-all-platforms) · browser-based (WebHID), no install                                                                                                                                                                                                                                               |
| Multi-monitor management        | ✅ DisplayFusion (paid)                                                                                     | ✅ native (AeroSpace workspaces)                       | ✅ native (Hyprland workspaces) + wdisplays (GUI config)                          | → [§8.3](#83-multi-monitor-displayfusion-windows-only--paid)                                                                                                                                                                                                                                                                     |
| Audio control                   | ✅ EarTrumpet                                                                                               | ✅ native menu bar                                     | ✅ Noctalia (per-app mixing unconfirmed)                                          | → [§9](#9-audio)                                                                                                                                                                                                                                                                                                                 |
| Screenshots                     | ✅ ShareX                                                                                                   | ✅ Shottr                                              | ✅ grim + slurp + satty                                                           | → [§10.1](#101-screenshots)                                                                                                                                                                                                                                                                                                      |
| Screen recording                | ✅ OBS + native `Win+Alt+R`                                                                                 | ✅ QuickRecorder + OBS                                 | ✅ gpu-screen-recorder-ui                                                         | → [§10.2](#102-screen-recording)                                                                                                                                                                                                                                                                                                 |
| Browsers                        | Helium, Brave                                                                                               | Helium, Brave, Safari                                  | Helium, Brave                                                                     | → [packages.yaml](../../src/personal_os_setup/config/packages.yaml)                                                                                                                                                                                                                                                              |
| Messaging                       | Discord, WhatsApp, Viber, Telegram                                                                          | Discord, WhatsApp, Viber, Telegram                     | Telegram, Vesktop (Discord)                                                       | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Meetings                        | Zoom, MS Teams                                                                                              | Zoom, MS Teams                                         | Zoom (paru)                                                                       | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Media players                   | Stremio, VLC, Feishin, Spotify, Apple Music                                                                 | Stremio, VLC                                           | VLC, mpv, gwenview                                                                | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Gaming                          | Steam, Epic, GeForce Experience, Ubisoft Connect, Oculus, SideQuest, Xbox Game Pass, EA Desktop, DS4Windows | —                                                      | Steam                                                                             | → packages.yaml · Xbox Game Pass/EA Desktop/DS4Windows: manual install, not in packages.yaml                                                                                                                                                                                                                                     |
| Cloud drives                    | Google Drive, OneDrive, iCloud, Mega Drive (free 50GB)                                                      | Google Drive                                           | —                                                                                 | → packages.yaml · Mega Drive: manual install, not in packages.yaml                                                                                                                                                                                                                                                               |
| Video/photo editing             | OBS, Shotcut, Canva                                                                                         | CapCut, Canva                                          | —                                                                                 | → packages.yaml · OBS also in [§10.2](#102-screen-recording)                                                                                                                                                                                                                                                                     |
| AI apps                         | ChatGPT (MS Store), MCPJam Inspector                                                                        | Ollama, ChatGPT, AnythingLLM, MCPJam Inspector         | Ollama                                                                            | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Devices software                | Logitech G HUB, Brother iPrintScan, SteelSeries GG, MSI Center, Ryzen Master, Turtle Beach                  | —                                                      | rivalcfg (paru)                                                                   | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Fonts                           | via the app's "Install JetBrainsMono Nerd Font" button                                                      | via the app's "Install JetBrainsMono Nerd Font" button | `ttf-jetbrains-mono-nerd` (pacman)                                                | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Winget UI Manager               | ✅ UniGetUI                                                                                                 | —                                                      | —                                                                                 | → packages.yaml · Windows-only, no alternative                                                                                                                                                                                                                                                                                   |
| VPN & torrent                   | NordVPN, qBittorrent                                                                                        | —                                                      | nordvpn-bin, qbittorrent                                                          | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Remote desktop                  | AnyDesk                                                                                                     | AnyDesk                                                | anydesk-bin (paru)                                                                | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Wallpaper                       | Bing Wallpaper                                                                                              | Bing Wallpaper (`bing-wallpaper` cask)                 | Noctalia `daily-wallpaper` plugin                                                 | → packages.yaml / [§2.3](#23-cachyos-hyprland--noctalia)                                                                                                                                                                                                                                                                         |
| Bootable USB / partitioning     | — native Disk Management                                                                                    | —                                                      | Ventoy, KDE Partition Manager                                                     | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| Notes / text editors (other)    | Notion, PDFgear                                                                                             | Notion, PDFgear (webinstall)                           | —                                                                                 | → packages.yaml · Obsidian has its own row above                                                                                                                                                                                                                                                                                 |
| Dev tools (other)               | VS Code, Docker Desktop, ComfyUI Desktop, MongoDB Compass, Make, IntelliJ IDEA, Webstorm, WriterSide        | Docker Desktop, ComfyUI                                | claude-code, docker + docker-compose, meson, neovim                               | → packages.yaml · IntelliJ IDEA/Webstorm/WriterSide: manual install, not in packages.yaml                                                                                                                                                                                                                                        |
| Night light / blue light filter | ✅ native (Night light)                                                                                     | ✅ native (Night Shift)                                | ✅ wlsunset / Noctalia `[nightlight]`                                             | → packages.yaml (`wlsunset`) / [§2.3](#23-cachyos-hyprland--noctalia)                                                                                                                                                                                                                                                            |
| macOS utilities (other)         | —                                                                                                           | Swift-Quit, Ice, Alt-Tab, Badgeify                     | —                                                                                 | → packages.yaml · menu-bar/app-switching utilities                                                                                                                                                                                                                                                                               |
| System update notifier          | ✅ native (Windows Update)                                                                                  | ✅ native (Software Update)                            | ✅ cachy-update                                                                   | → packages.yaml                                                                                                                                                                                                                                                                                                                  |
| CachyOS utilities (other)       | —                                                                                                           | —                                                      | wine, hyprpicker, nwg-look, brightnessctl, ddcutil                                | → packages.yaml · wine runs Windows apps on Linux; hyprpicker is a color picker; nwg-look is GTK theme/icon/cursor config; brightnessctl/ddcutil control monitor brightness                                                                                                                                                      |
| Windows utilities (other)       | Wintoys, Windows HDR Calibration, Speedtest, RevoUninstaller, PhotoSync, WinRAR, Hass.Agent, CCleaner       | —                                                      | —                                                                                 | → packages.yaml · CCleaner: manual install, not in packages.yaml                                                                                                                                                                                                                                                                 |
| Agenda & Mail (web apps)        | ✅ Google Calendar, Gmail                                                                                   | ✅ Google Calendar, Gmail                              | ✅ Google Calendar, Gmail                                                         | manual install, not in packages.yaml · create a browser app shortcut (Chromium: ⋮ → More Tools → Create shortcut → window mode) and set it as the default mail/calendar handler · notification extensions in [awesome_websites_browser_extensions.md](../apps/awesome_websites_browser_extensions.md#11-productivity-extensions) |
| Video editing (other)           | Creative Cloud (Adobe Premiere Pro), CapCut, Microsoft Clipchamp                                            | —                                                      | —                                                                                 | manual install, not in packages.yaml · macOS CapCut is already in the `Video/photo editing` row above                                                                                                                                                                                                                            |
| Image editing (other)           | Adobe Photoshop, or free alternative [Photopea](https://www.photopea.com/)                                  | —                                                      | —                                                                                 | manual install, not in packages.yaml                                                                                                                                                                                                                                                                                             |
| Office suite                    | Microsoft 365, Office 2021                                                                                  | —                                                      | —                                                                                 | manual install, not in packages.yaml                                                                                                                                                                                                                                                                                             |
| PDF editing (other)             | Adobe Acrobat Reader DC, Sejda (3 free tasks/hour)                                                          | —                                                      | —                                                                                 | manual install, not in packages.yaml · PDFgear (packages.yaml-installed) is in the `Notes / text editors` row above                                                                                                                                                                                                              |
| Game streaming                  | Parsec, Nvidia GeForce Now                                                                                  | —                                                      | —                                                                                 | manual install, not in packages.yaml                                                                                                                                                                                                                                                                                             |
| PowerShell                      | ✅ PowerShell 7                                                                                             | —                                                      | —                                                                                 | manual install, not in packages.yaml · [install link](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows)                                                                                                                                                                           |
| Game development                | Unity, Unreal Engine, Blender                                                                               | —                                                      | —                                                                                 | manual install, not in packages.yaml                                                                                                                                                                                                                                                                                             |
| SFTP client                     | Filezilla                                                                                                   | —                                                      | —                                                                                 | manual install, not in packages.yaml                                                                                                                                                                                                                                                                                             |

\* Bitwarden itself is cross-platform, but only the CachyOS entry is installed via this project's
package manager (`pacman`, `Utilities` category in
[packages.yaml](../../src/personal_os_setup/config/packages.yaml)). On Windows/macOS, install it
manually as a browser extension or desktop app.

## 1. General OS shortcuts

**Windows:**
- Display copy-paste history: `Win + V`
- Lock screen: `Win + L`
- More general Windows UI/UX shortcuts and tweaks (taskbar, screen lock timeout, multi-monitor,
  etc.) are in [windows_workflow/README.md](../windows_workflow/README.md#12-windows-configuration).

**macOS:**
- Keys are remapped so the same physical shortcuts work as on Windows/Linux (Globe key acts as
  Ctrl, Option as Alt) — see
  [Windows/Linux behavior mimicking in macOS](../macos_darwin/README.md#windowslinux-behavior-mimicking-in-macos)
  for the full remap and its `Globe+C` / `Globe+V` copy-paste, `Option+C` terminal-cancel
  consequences.
- Native lock shortcut: `Cmd+Ctrl+Q`. Native clipboard history isn't built in — Raycast can
  provide it (see [§2.4](#24-launcher-raycast--vicinae)).

**CachyOS:**
- Lock/idle/suspend behavior is owned by Noctalia, not Hyprland — see
  [Settings owned by Noctalia, not Hyprland](../linux/CachyOS.md#settings-owned-by-noctalia-not-hyprland)
  (also see [§2.3](#23-cachyos-hyprland--noctalia) for the window-manager shortcuts).
- Keyboard layout switch: `Alt+Shift` — see
  [Keyboard layout defaults to QWERTY on first login](../linux/CachyOS.md#keyboard-layout-defaults-to-qwerty-on-first-login).

## 2. Window Manager & Launcher

### 2.1. Windows: GlazeWM and Zebar

- Automatic installation of the settings available with the personal-OS-Setup TUI [app](../../README.md#windows-11) by selecting `Sync GlazeWM config`.
- Manual installation:
    - Download [my .glaze-wm config folder](../../src/personal_os_setup/config/windows/.glzr) and place it in `C:\Users\%userprofile%\.glaze-wm`

shortcuts: You can read more about the shortcuts :
- [GlazeWM](https://github.com/glzr-io/glazewm?tab=readme-ov-file#config-documentation)
- [Zebar](https://github.com/glzr-io/zebar)

- close a window: `alt + shift + q`:
- reload the config: `alt + shift + r`:
- Maximize & un-maximize : `alt + f`
- Hide: `alt+m` (use `alt+f` to make it appear again)
- Switch between multiple full-screen apps in the same workspace : `alt + tab`
- If a window (like a dialog box) is missing or missized, moving it to another workspace will usually fix the issue.

### 2.2. macOS: AeroSpace + JankyBorders

AeroSpace is the macOS tiling window manager used in this setup — the macOS counterpart to
[GlazeWM](#21-windows-glazewm-and-zebar) (Windows) and Hyprland (CachyOS, see
[§2.3](#23-cachyos-hyprland--noctalia) below).

- **AeroSpace**: tiling window manager.
  - Tutorial: https://www.youtube.com/watch?v=-FoWClVHG5g
  - Docs: https://nikitabobko.github.io/AeroSpace/
- **JankyBorders**: adds window borders (requires AeroSpace).
- My config: [.aerospace.toml](../../src/personal_os_setup/config/darwin/.aerospace.toml)

### 2.3. CachyOS: Hyprland + Noctalia

Hyprland (window manager) + Noctalia (bar / control centre) is CachyOS's counterpart to
[GlazeWM](#21-windows-glazewm-and-zebar) (Windows) and
[AeroSpace](#22-macos-aerospace--jankyborders) (macOS). Full installation, plugin setup, and
Noctalia's configuration ownership (idle/lock, wallpaper, night light, screenshot pipeline,
session menu) are documented in [CachyOS.md](../linux/CachyOS.md#desktop) — this section only
covers the day-to-day shortcuts.

- `Alt+F` — fullscreen
- `Alt+Tab` — window switcher (via the `hymission` Hyprland plugin)
- Drag / close / maximize via title bars (via the `hyprbars` Hyprland plugin)
- Vicinae is the launcher — see [§2.4](#24-launcher-raycast--vicinae)

### 2.4. Launcher: Raycast / Vicinae

Raycast (Windows/macOS) and Vicinae (CachyOS/Linux) are the same kind of launcher — Raycast
plugins work with Vicinae.

**Windows:** available via the Microsoft Store (`msstore` in packages.yaml); no repo-specific
config documented yet.

**macOS (Raycast):**
- Use Raycast as a "PowerShell equivalent" launcher.
- Replace Spotlight:
  - Remove the Spotlight shortcut in macOS keyboard settings.
  - Configure the same shortcut for Raycast.
- Finder is still useful for macOS-specific settings and edge cases.

**CachyOS (Vicinae):**
- **Typing a path**: Vicinae ships a built-in "Search Files" command (indexed
  search with a content preview, reachable from the root search or its own dedicated
  command).
- **Extensions**:  Currently, installed:
  - `port-killer`, `process-manager` — kill/manage running processes and listening ports
  - `kill-process`, `port-manager` — Raycast equivalents of the above (process/port management)
  - `systemd` — start/stop/restart/enable/disable a unit straight from the launcher
  - and a lot of other extensions in [`run_onchange_after_install-vicinae-extensions.sh.tmpl`](../../src/personal_os_setup/config/chezmoi/dot_config/vicinae/run_onchange_after_install-vicinae-extensions.sh.tmpl)


## 3. Terminal

### 3.1. Windows Terminal

- Automatic installation of the Terminal settings available with
  this [command](../windows_workflow/README.md#2-software). Select the second option.
- wget on Windows terminal: add it to your terminal: https://www.programmersought.com/article/90723524682/

See [§3.2](#32-terminal-commands-cheatsheet-macoscachyos) for the macOS/CachyOS terminal
(Ghostty) and shell setup.

### 3.2. Terminal commands cheatsheet (macOS/CachyOS)

These reflect what's actually installed/aliased by this project — see
[terminal_tools in packages.yaml](../../src/personal_os_setup/config/packages.yaml) and
[.zshrc](../../src/personal_os_setup/config/chezmoi/dot_zshrc).

- `ls` / `ll` / `lt` → aliased to `eza` (icons, git status, tree view)
- `cat` → aliased to `bat` (syntax highlighting); also set as the `man` pager
- `top` → aliased to `btop` (resource monitor)
- `df` → aliased to `duf`; `du` → aliased to `dua` (`dui` for the interactive TUI)
- `rg` (ripgrep) and `fd` → faster `grep`/`find`, used directly under their own binary names (not aliased over the originals)
- Fuzzy search (`fzf-zsh-plugin`): `Ctrl+T` fuzzy-finds a file, `Ctrl+R` fuzzy-searches shell history, `Alt+C` fuzzy-`cd`s into a subdirectory
- `Tab` / arrow keys → `zsh-autocomplete` shows and lets you navigate a live completion menu as you type, including folder selection while navigating paths
- Right arrow / `End` → accepts the greyed-out suggestion from `zsh-autosuggestions` (predicted from your history)
- Commands turn green/red as you type → `zsh-syntax-highlighting`
- `↑` → standard shell history; `z <name>` (zoxide) jumps straight to a frecent directory instead of `cd`-ing there manually
- `tldr <command>` (tealdeer) → simplified, example-based man pages
- `fastfetch` → replaces `neofetch` (deprecated upstream); runs automatically on every new interactive shell

## 4. File manager

macOS uses Finder natively — no repo-specific config, just the tab/path-bar tweaks in
[macos_darwin/README.md](../macos_darwin/README.md#4-uiux-tweaks).

### 4.1. Windows: Files

- Files: Replace the Windows File Explorer. Manage all your files with increased productivity. Work across multiple
  folders with tabs and so much more.
    - Download [Files](https://files.community/). There are two versions: direct installer (free) & Microsoft Store (
      paid)
    - Replace Windows File explorer with Files: [link](https://files.community/docs/configuring/replace-file-explorer/)
    - You can import my settings: [link](Files_3.0.15.0.zip). Open Files -> Settings -> advanced -> import settings

### 4.2. CachyOS: Nautilus

Nautilus is the GNOME file manager used on CachyOS/Hyprland (replaces Dolphin — no KDE
session deps like kwallet/kded/portals to fight with under Hyprland).

Better to install it together with **all** of its extensions from the `Files explorer`
category in [packages.yaml](../../src/personal_os_setup/config/packages.yaml) rather than
just the `nautilus` package alone:

- `gvfs` — virtual filesystem backend Nautilus uses for all mounting (local disks, udisks2, trash, etc.)
- `gvfs-smb` — Windows/SMB network share support
- `gvfs-nfs` — NFS network share support
- `gvfs-mtp` — Android phone (MTP) support
- `gvfs-gphoto2` — digital camera (PTP) support
- `gvfs-afc` — iPhone/iPad support
- `gvfs-goa` + `gnome-online-accounts` — cloud storage account integration (Google/Microsoft/Nextcloud)
- `sushi` — spacebar quick-preview (like macOS Quick Look)
- `nautilus-python` — extension framework required by most Python-based Nautilus plugins
- `ghostty-nautilus` — adds Ghostty terminal to the Nautilus context menu

Use personal-setup-os for installing it.

## 5. IDE & editors

### 5.1. PyCharm (All platforms)

- I prefer to use PyCharm & other Intellij products like WriterSide...(the Pro version is free for students)
- My personal shortcuts & tips & settings for this app [here](#512-personal-pycharm-shortcuts)

#### 5.1.1. Tips & tricks

- I've been using PyCharm (professional edition) for more than 3 years now, even if I used VSCode for 2 years before
  that, the Intellij suite is just amazing. Intellij suite with all the plugins for students is completely free.
- Change the default location of projects : instead of PycharmProjects. Settings -> Appearance & behavior -> system settings
- Change the terminal font to JetBrainsMono Nerd Font: Settings -> Tools -> Terminal -> Font settings
- If you are on Windows, use pycharm with WSL.
- Sync pycharm settings : https://www.jetbrains.com/help/pycharm/sharing-your-ide-settings.html#IDE_settings_sync
- You can save your current layout (all plugin positions) by going to Window | Layouts | Save Current Layout as New and
  switch to it from new projects by Window | Layouts | <name of your layout> | Apply.
- Project settings : Everytime you start a project make sure to
    - Change the source folder for imports (https://stackoverflow.com/a/34304165).
    - Edit the configuration template of python and python tests(autodetect and pytest) to
  select a default working directory for all your scripts. If you changed the source folder, it should match it. This will prevent you from having problems with working directory location when running from the terminal and pycharm.
- I always use the run button (or shortcut) instead of the terminal to run my files (specifically fastapi or streamlit) so pycharm can highlight the errors and make them easily clickable.
- Use the debug function when needed.
- You can Run pytest just by right-clicking on a function bloc, file, or folder!
- Git Clone: You can directly clone a repository from your git accounts by going to the Menu bar | VCS | Get from
  Version Control | GitHub | and select the right repository.
- You can write a ``#TODO`` in the .py files or ``[//]: # (TODO  Add Google TV setup  ) `` in the markdown files to see them
  in the TODO panel.
- Commits : [doc](https://www.jetbrains.com/help/pycharm/log-tab.html)
    - pre-commit hooks: Just run in the interminal pre-commit install. Pycharm should detect it. After the installation, see in the commit panel (where you enter the commit message) (wheel button) next to the
      message if `Run git hooks` is there. If it isn't, then restart pycharm. Next time your commit, pycharm will run the pre-commit hooks
    - When you write in your terminal: `pip list | grep pre-commit` you should see the package.
      Running `pre-commit --version` should also work.
    - Check the Amend commit box if you want to concatenate commits
    - If you want to delete a pushed commit :
        - Make sure that the branch isn't protected: open IDE settings Ctrl+Alt+S then go to git settings. You will see
          in the Push settings the protected branches. Note that if a branch is marked as protected on GitHub, PyCharm
          will automatically mark it as protected when you check it out, but you can modify it.
        - To delete a pushed commit, you have to options: drop a commit, or reset a current branch to a specific commit.
          After doing one or the other, open the push panel and instead of selecting 'push', select 'force push'.
          Remember that you need to force push, otherwise pycharm will tell you that there are changes on the remote
          that need to be merged.
- Docker :
    - Use docker with pycharm, straightforward to pull and create images & containers. Specially, if you want to test
      your app, you can create an ubuntu container in less then 5sec.
    - In Pycharm settings, configure docker to run under WSL & not Windows. It will automatically detect the ports.
- Remote/local terminal & interpreter :
    - When creating a project with pycharm, you should use the anaconda python (windows or wsl) and not install python
      or using another one like virtualenv.
    - You can use ubuntu as default terminal in pycharm: tools>terminal and put in a shell path: `ubuntu run`
    - Add WSL interpreter in Pycharm (add interpreter -> WSL). For example, Conda, installed in WSL, will be available
      in Pycharm.
    - You can use docker as an interpreter in Pycharm (If you have a powerful computer like a desktop or a Macbook,
      otherwise, a laptop with Windows 11 + WSL2 + pycharm + docker isn't a good idea). To set Docker Port Bindings When
      Using Pycharm Run/Debug Go to: Python file > Edit Configuration > Docker container settings (click on open folder
      icon) At Edit Docker Container Settings, you can add Port bindings. Or set the python configuration to use this so
      all the python files can use the same configuration.
- Always use Markdown code and add `py` to tell the Markdown that it's python code. When you will do refactor. It will
  change the python code in the readme.
- Plugins: You can download plugins from the settings menu. I recommend the following plugins:
    - GitHub copilot (autocomplete, but also provides functions when you right-click on something like: explain,
      generate tests...etc.)
    - default plugins: services with docker...
    - TBD
- PyCharm has keyboard shortcuts for most of its commands related to editing, navigation, refactoring, debugging, and
  other tasks. Memorizing these hotkeys can help you stay more productive by keeping your hands on the
  keyboard. [Link to Cheatsheet](https://resources.jetbrains.com/storage/products/pycharm/docs/PyCharm_ReferenceCard.pdf)
- If the plugin Table of contents doesn't work on a Markdown file, create a small table with the title &
  two`<!-- TOC -->`, it should detect it.
- Pycharm has fuzzy search when creating a file. For example, 'alt+p' then 'alt+ins' then 'pf' to create a python file
- (To confirm) Pycharm Jupyter Notebook: Use the one provided in Pycharm. It provides better autocomplete.
- WriterSide issue : files eit

#### 5.1.2. Personal PyCharm shortcuts

Official[Link to Cheatsheet](https://resources.jetbrains.com/storage/products/pycharm/docs/PyCharm_ReferenceCard.pdf)

Some of them are re-mapped :

The macOS shortcuts are inverted in my system so i can use the same commands as in windows. The ones in this list works for both since i use the name of the key and not the real inverted key.
**Panels & windows :**

| Panel                        | Windows (MacOS) Shortcut                     |
|------------------------------|----------------------------------------------|
| Press the blue button        | alt+p  (command+p)                           |
| project panel          alt+P |                                              |
| terminal panel               | alt + T  (command+t)                         |
| new terminal                 | alt maj T                                    |
| settings                     | ctrl+alt+S (fn+,)then type with the keyboard |
| **Git**                      |                                              |
| Git commit  panel            | ctrl + K (command +t)                        |
| Git panel                    | alt + g (command +g)                         |
| Git update                   | not defined yet                              |
| git emoji                    | show toolbar like alt+w then alt+g           |
| git emoji                    | open git panel with alt+k then alt+ctrl+g    |
| git menu                     | show toolbar like alt+w then alt+g           |
| git menu                     | show toolbar like alt+w then alt+g           |
| **run/debug**                |                                              |
| debug                        | maj + F9                                     |
| git menu                     | alt+9                                        |
| debug panel                  | show toolbar like alt+w then alt+g           |
| run                          | maj +F10                                     |
| run panel                    | alt+ 0                                       |

**Code editor**

| Action                                           | Shortcut                                     | more                                                                                                               |
|--------------------------------------------------|----------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| call actions                                     | alt+enter                                    | reformat code, correct code & more , used in editor                                                                |
| insert / create new                              | alt+ insert                                  | can be used in editor (insert tables ect..) or project panel (create new files)                                    |
| create new branch                                | ctrl+alt+n                                   |                                                                                                                    |
| find all                                         | double shift                                 | search everything like files, actions, classes                                                                     |
| find actions                                     | ctrl+shit+a                                  | search actions like tools (docker, remote server) but also execute shortcuts                                       |
| find files                                       | ctrl+shift+n                                 |                                                                                                                    |
| find in files                                    | ctrl+shift+f                                 |                                                                                                                    |
| find inside current panel                        | ctrl + F                                     | can be used in editor                                                                                              |
| show recent files                                | ctrl + E                                     |                                                                                                                    |
| show recent locations                            | ctrl + shift + E                             |                                                                                                                    |
| Quick documentation                              | Ctrl + Q                                     |                                                                                                                    |
| Quick documentation                              | Ctrl + Q                                     |                                                                                                                    |
| **select**                                       |                                              |
| **refactor**                                     |                                              |
| extract method/constant/variable/field/parameter | Ctrl + Alt + M/C/V/F/P                       |                                                                                                                    |
| select bloc                                      | ctrl + w                                     | select (the more you press w, the more it wraps other parts. you can then press any other thing to wrap it arround |
| select  with multiple cursors                    | ctrl + alt shift + mouse                     |                                                                                                                    |
| Select multiple occurrences of a word            | alt j                                        |                                                                                                                    |
| all case-sensitively matching words              | Ctrl Alt Shift J                             |                                                                                                                    |
| move bloc                                        | ctrl + shift + arrow                         |                                                                                                                    |
| refactor (change signature:add/remove parameter) | alt+r + first option                         |                                                                                                                    |                                        |
| rename                                           | alt+r then select the second option (rename) |                                                                                                                    |
| delete/cut line                                  | ctrl+x                                       |                                                                                                                    |
| duplicate line                                   | ctrl+d                                       |                                                                                                                    |
| **moving**                                       |                                              |
| Go to declaration or usages	                      | ctrl+B                                       | works as bold typo in markdown files                                                                               |
| end of line                                      | :End:                                        |                                                                                                                    |
| beginning of line                                | Home                                         |                                                                                                                    |
| next word:                                       | Ctrl+Right                                   |                                                                                                                    |
| previous word                                    | Ctrl+Left                                    |                                                                                                                    |
| jump to line                                     | ctrl+g                                       |                                                                                                                    |

#### 5.1.3. Python remote interpreter (SSH/WSL)

- add a remote python interpreter: usually found with `which python` on the remote server or WSL.
- PyCharm envs: You can clean out old PyCharm interpreters that are no longer associated with a project see the
  image [here](https://github.com/AmineDjeghri/BetterWindowsUX/blob/master/pycharm_interpreters.PNG) .
- This gives you a listing where you can get rid of old virtualenvs that PyCharm thinks are still around

#### 5.1.4. PyCharm remote deployment

WARNING: project folder needs to be on windows and not WSL to use the remote ssh. Do not host folders outside WSL if you
are not using a remote interpreter, there
are  [WSL perforamance issues](https://github.com/microsoft/WSL/issues/4197?notification_referrer_id=MDE4Ok5vdGlmaWNhdGlvblRocmVhZDUyMzA5ODA3MjozMjcxNTkxMw%3D%3D#issuecomment-1727108838))

Defining a server as default:
A deployment server is considered default if its settings apply by default during automatic upload of changed files. To
define a deployment server as the default one, follow these steps:

Choose the desired server on the Deployment page. You can open this page it two possible ways: either
Settings/Preferences | Build, Execution, Deployment | Deployment, or Tools | Deployment | You will see your servers,
right click on the one you want to set it as default, and click 'use as default'

Enabling automatic upload:
As soon as the default server is set, you can make upload to this server automatic. This can be done in the following
two ways:

Open the deployment Options (Settings/Preferences | Deployment | Options or Tools | Deployment | Options from the main
menu), and in the Upload changed files automatically to the default server field choose Always, or On explicit save
action. The difference between these two choices is explained in the field description.
In the main menu, select Tools | Deployment | Automatic upload. Note that automatic upload in this case is performed in
the Always mode.

#### 5.1.5. Remote SSH for ReactJS

- First, make sure that in the server, the React project is running when you run `yarn dev run`
- In pycharm, go to configuration and create a new config for npm
- select package.json from the local folder
- select command: run
- select scripts: dev
- Node interpreter: copy and paste the result of the command `which node` in the remote server
- package manager: yarn, for example
- environment: `PATH=` put the result of the command `echo $PATH`

### 5.2. ZED (All platforms)

No special configuration is documented yet — installed via `packages.yaml` (`Dev_tools` category)
on all three OSes.

## 6. Notes / knowledge base

### 6.1. Obsidian (All platforms)

- Obsidian plugins are saved inside the vault (a folder). You need to copy the .obisidian folder every time you create a
  new vault to keep the same plugins and workspace
- You can copy my [.obsidian](../windows_workflow/win_dotfiles/.obsidian) folder to get the same confi as me. The shortcut for settings is the same as pycharm (alt + ctrl + s)
- Do not sync the ``workspace.json`` file since it contains sensitive information (name of files, etc..)
- Install the community plugins: TBD
- Install the community themes: TBD
- Sync: use Google Drive ou GitHub to sync the repositories remotely.
- Git : always use the git clone with HTTPS and not SSH. Use a classic token and not the password.
- Run ``git config --global credential.helper store`` to save the credentials for the user after the first push/pull.
- if you are on Windows. Install git on Windows (PowerShell: 'winget install git.git').
- You can configure the git plugin in settings to automatically push and pull every x minutes.
- The source control panel can be found on the left panel. Maybe need to change the size of the left panel to view it
- if you face a problem with dubious ownership of repository, run this
  command `git config --global --add safe.directory '*'`
- if you face a problem with fatal: could not read Username for 'https://github.com'. go to the folder from a terminal and run git pull.

#### Sync Obsidian vaults with iOS:
  * Download obsidian on your mobile, and check if the obsidian folder is available in iCloud in the Files app .
  * Download the obsidian git repository in your phone (either with your phone or a computer) and place it in the obsidian folder in iCloud.
  * Open Obsidian app, it should show you the discovered vaults (your GitHub repo ), open it.
  * Wait a little bit then reload the obsidian app if the community plugins aren't visible.
  * After entering the repo, git will ask you a remote URL and you might get a lot of popups about a problem with git (ssh, remote url, etc..):
    * Using Obsidian mobile app, inside your vault, open the command palette, and search for 'git delete remote'. And delete any if present.
    * Search in the command palette for ``git edit remote`` and add the name of the remote which is 'origin' and the https url of your repo.
    * If you don't know how to do it, check the equivalent on Obsidian Desktop app. The mobile app is a bit tricky to set up the name and the url of the remote.
  * Configure the parameters of the git plugin in obsidian and put your username, token, email... configure also a commit message to specify that the changes where from your phone.
  * Make sure that the theme is the same as the one on your computer. Since sometimes Obsidian on your mobile forces change the theme. Usually the files '.obsidian/app.json' and '.obsidian/appearance.json' will change and a copy of them is made named ``appearance_2.json`` and ``app_2.json`` . Use the copies to revert the changes.

## 7. Passwords & security

### 7.1. Bitwarden (All platforms)

Bitwarden is an open-source password manager available on Windows, macOS, Linux, iOS, Android, and as a browser extension.

**Tips & tricks:**
- You can share passwords with other people by creating an **Organisation** and **Collections**. A password can belong to multiple collections, so you can share it with two different organizations independently.
- The **browser extension** is the main daily driver — install it on all your browsers.
- On Windows: activate **Unlock with Windows Hello** in the extension settings for fast, secure unlock.
- On Windows: enable **Start automatically on login** and disable **Close to tray** so Bitwarden is always available.
- Activate **Two-Factor Authentication (2FA)** in your account settings.
- You can **import passwords** from another password manager directly from the web vault: Settings → Import data.

**Vaultwarden (self-hosted open-source Bitwarden backend):**
- Vaultwarden is a lightweight, open-source reimplementation of the Bitwarden server API.
- All official Bitwarden clients (iOS, Android, Windows, macOS, browser extensions) work with it — just point them at your self-hosted URL.
- Install it as a **Home Assistant add-on**: https://github.com/hassio-addons/app-vaultwarden
- After installing, configure your Bitwarden clients to use your self-hosted server URL instead of `bitwarden.com`.

### 7.2. Disk encryption

- **Windows**: BitLocker. Enable it in Windows settings (Windows Pro/Education/Enterprise
  editions only) — see [windows_workflow/README.md](../windows_workflow/README.md#12-windows-configuration).
- **CachyOS**: LUKS2 via `cryptsetup`, set up at install time (`Encryption: LUKS` in
  [CachyOS.md](../linux/CachyOS.md#bootloader-and-filesystem)). Confirmed on this project's
  reference machine: `lsblk -f` shows `crypto_LUKS` version **2** on every encrypted partition.
- **macOS**: FileVault — not yet documented in this repo.

## 8. Hardware, peripherals & monitoring

### 8.1. HWiNFO (Windows) vs Hardware Monitoring (CachyOS)

**Windows — HWiNFO:**
- export file: regedit -> ``Ordinateur\HKEY_CURRENT_USER\Software\HWiNFO64``
- import settings: double-click on the downloaded file to restore settings. Check
  mine [here](../../src/personal_os_setup/config/windows/HWINFO_settings.reg)

**CachyOS — CoolerControl, OpenRGB, nvtop, rivalcfg:**
- Installed via the `Hardware Monitoring` category in
  [packages.yaml](../../src/personal_os_setup/config/packages.yaml).
- CoolerControl needs its daemon enabled after install: `systemctl enable --now coolercontrold`.
- `nvtop` complements `btop`, which doesn't show GPU stats.

No macOS equivalent is documented in this repo.

### 8.2. Keychron Launcher (All platforms)

Keychron Launcher (https://launcher.keychron.com/) is the browser-based configurator for QMK/VIA-compatible Keychron
keyboards — key remapping, macros, lighting, and firmware updates, all from a web app (WebHID), no install required.
Works on Linux the same as Windows/macOS: open it in a Chromium-based browser (Chrome, Edge, Opera, Helium, etc.).

- **Keychron K1 Max**: must be connected **via USB-C cable** to be recognized by Launcher — flip the mode switch on
  the back of the keyboard to cable mode first. It will not be work correctly over the 2.4GHz dongle or Bluetooth.
- **On Linux, skip the Keychron Toolbox driver install step** — Toolbox is a native Windows/Mac app with no Linux
  build, and Launcher doesn't need it there. Just click **Next** past that step in the firmware-update flow.
- My K1 Max keymap's base layer was remapped to media/brightness keys without holding Fn. And the F1-F12 keys need the Fn holded to work.

### 8.3. Multi-monitor: DisplayFusion (Windows only & paid)

- DisplayFusion is a program that will help you to manage your multiple monitors. It allows you to create different
  profiles for your monitor setups, such as single, dual, or triple monitors. You can configure specific applications to
  always open on designated monitors within each profile. With just one click, you can switch between these profiles,
  and DisplayFusion will automatically rearrange your windows according to the rules you set. This makes it easy to
  adapt your workspace to different scenarios, whether you're working with one monitor or multiple monitors.
- Link to my settings containing different profile for 1, 2, 3 and TV
  settings. [here](../windows_workflow/win_dotfiles/DisplayFusion%20Backup.reg)
    - use the Steam version (it can be used on multiple computers with the same steam account)
    - it adds a lot of features to Windows monitor settings.
    - There are four apps available after the installation. The main ones are: DisplayFusion and "monitor settings
      displayfusion"

macOS ([AeroSpace](#22-macos-aerospace--jankyborders)) and CachyOS
([Hyprland](#23-cachyos-hyprland--noctalia)) handle multi-monitor workspace assignment natively
through the window manager — no equivalent paid tool is used there.

## 9. Audio

- **Windows — EarTrumpet**: per-app volume mixer, lives in the system tray.
- **CachyOS — Noctalia**: the bar's volume widget is the primary audio control (see
  [§2.3](#23-cachyos-hyprland--noctalia)); whether it supports per-app mixing the way EarTrumpet
  does isn't confirmed in this repo yet — verify and update this line.
- **macOS**: native menu bar volume control; no dedicated app documented in this repo.

## 10. Screenshots & screen recording

### 10.1. Screenshots

- **Windows — ShareX**: screen capturing with regions and GIF recording, use `Ctrl+Print`. You
  can import your settings, follow this
  [link](https://techunwrapped.com/can-i-take-my-sharex-capture-settings-to-another-pc/).
- **macOS — Shottr**: lightweight screen capture tool. https://shottr.cc/
- **CachyOS — grim + slurp + satty + wl-clipboard**: Noctalia's screenshot action
  (`[shell.screenshot]` in its config) pipes through this stack — see
  [CachyOS.md](../linux/CachyOS.md#settings-owned-by-noctalia-not-hyprland) for where it's
  configured.

### 10.2. Screen recording

- **Windows**: OBS Studio, or the native screen recorder `Win+G` / `Win+Alt+R`.
- **macOS**: QuickRecorder (https://github.com/lihaoyun6/QuickRecorder), or OBS Studio.
- **CachyOS — gpu-screen-recorder-ui**: fullscreen overlay UI in the style of ShadowPlay; pulls
  in `gpu-screen-recorder` + `gpu-screen-recorder-notification` as hard dependencies.

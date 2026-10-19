# macOS (Darwin) setup

This document describes how to get a productive macOS setup (terminal + apps + UX tweaks) consistent with the rest of this repo.


## Windows/Linux behavior mimicking in macOS

If you're coming from Windows or Linux, macOS has some different behaviors. You can remap keys to make the layout feel closer to Windows. This is useful if you frequently switch between macOS and Windows/Linux, as it reduces muscle memory conflicts and makes your workflow more consistent across platforms.

Here are useful tweaks to make it feel more familiar:
- **Invert mouse scrolling**: By default, macOS uses "natural" scrolling (like on iOS). To get Windows-like scrolling behavior, go to **System Settings > Mouse** and invert the scrolling.
- **Keyboard layout**: Change macOS shortcuts to behave like Linux/Windows (This is useful if you want to use the same keyboard layout to copy-paste on all your devices)
  ![SCR-20241117-sbna.png](SCR-20241117-sbna.png)

Keep the mapping consistent and avoid mixing multiple remap tools.

After doing this, when you see some tutorials using macOS keyboard shortcuts, remember that you changed the keyboard layout.
- **Command (⌘)** is the macOS equivalent of **Ctrl** and handles most system shortcuts (copy, paste, save, etc.). After remapping, the **Globe key** (leftmost modifier key) becomes your Command key, functioning exactly like the **Ctrl** key on Windows/Linux keyboards.

- **Option (⌥)** is similar to **Alt** on Windows and is used for special characters and alternative shortcuts. After remapping, the **Option key** (rightmost modifier key) becomes your secondary modifier, equivalent to **Alt** on Windows/Linux.

- **Control (⌃)** is typically used for secondary actions like interrupting commands in the terminal (Ctrl+C). After remapping, the **Option key** replaces Control for these terminal operations, so you'll use **Option+C** to cancel instead of **Ctrl+C**.

- **Globe key** (the dedicated key on the far left) which is used for emojis and switch between languages has been remapped to function as **Control (⌃)**, providing the traditional Control key functionality when needed.

- **Delete** behaves like Backspace on Windows. To delete characters forward (like Delete on Windows), use **Fn + Delete**.

After remapping our keys, to copy-paste, it will be the same as in Windows/Linux keyboard:
- **Globe** + **C** to copy
- **Globe** + **V** to paste


## Installation Process

The Personal OS Setup provides a **Terminal UI (TUI) application** that guides you through the installation process. Once you run the one-liner installer, you'll see an interactive interface with the following steps:

Use [README.md](../../README.md#linux--wsl2--macos) as it automatically handles the OS setup with the interactive TUI application.


### 1. Package Selection
The app displays all available packages from [packages.yaml](../../src/personal_os_setup/config/packages.yaml) organized by category:
- **Core tools**: `git`, `curl`, `zsh`
- **Dev tools**: `uv`, `Pycharm`, `Ghostty`, `Zed`, `Docker-Desktop`
- **Utilities**: `Raycast`, `Alt-Tab`, `AeroSpace`, `Shottr`
- **Messaging**: `Discord`, `WhatsApp`, `Telegram`
- **Media**: `Stremio`, `VLC`

You can multi-select packages using the interactive interface.


### 2. Terminal Setup (Zsh + Oh My Zsh + Powerlevel10k)
This section is the same as Linux. Follow the terminal ZSH instructions in [Linux](../linux/README.md#2-terminal-setup-zsh--oh-my-zsh--powerlevel10k).

## 3. Recommended apps

For per-app configuration and shortcuts shared across platforms (PyCharm, Obsidian, Raycast,
Bitwarden, Zed, the terminal tools cheatsheet), plus a table of what's available on macOS vs.
Windows/CachyOS and their alternatives, check
[apps_configuration_and_shorcuts.md](../apps/apps_configuration_and_shorcuts.md#app-availability--alternatives-across-oses).


## 4. UI/UX tweaks

- Enable sudo with Touch ID:

```sh
sed -e 's/^#auth/auth/' /etc/pam.d/sudo_local.template | sudo tee /etc/pam.d/sudo_local
```
- Night Shift.
- Auto-hide the dock.
- Remove unused menu bar icons:
  - Hold `command` then drag the icon out of the menu bar (not all apps support it).
- Finder:
  - Show tab bar.
  - Show path bar: View → Show Path Bar (or `Option + Command + P`). The path bar at the bottom of the Finder window shows the full path to the current folder and lets you click any part of it to navigate directly there.
  - Show hidden files: `command + shift + .`


## 5. Notes

- Some apps do not have import/export settings and require manual configuration (e.g. Ice, AltTab).
- Some apps might need manual installation (e.g. Badgeify).


## 6. Testing the macOS flow in a VM

You can exercise the macOS flow (the app's darwin tasks drive Homebrew) end to end in a disposable VM from a Linux host,
with [Quickemu](https://github.com/quickemu-project/quickemu) — **not** libvirt, so this works differently from the other
`make vm-*` targets. The caveats (CPU requirements, no GPU acceleration, why `make vm-list` doesn't show it, the Apple
EULA) are listed in [Testing this project in a VM](../linux/CachyOS.md#testing-this-project-in-a-vm).

1. Install Quickemu on the Linux host once (it isn't part of `make vm-deps`): `paru -S quickemu` on Arch/CachyOS, or the
   install section of its README elsewhere.
2. Download and boot the guest (several GB from Apple; a window opens; pick another release with
   `MACOS_VERSION=sonoma`):
   ```bash
   make vm-macos
   ```
   First boot lands in macOS Recovery.
   Pick the right disk, or the installer reports "37.6 MB free": in *Disk Utility* use **View → Show All Devices** and
   erase the large **Apple VirtIO Block Media** (~137 GB, the virtual disk) as APFS / GUID Partition Map, named
   `Macintosh HD`. Ignore the other two: **QEMU HARDDISK Media** (~400 MB) is the OpenCore bootloader, and the ~2.5 GB
   volume (`disk2s1`) is the Recovery image you booted from. Then choose *Reinstall macOS* and select `Macintosh HD`.
   Click through Setup Assistant afterwards. Re-running `make vm-macos` later just starts the existing guest again.
3. Inside the guest, open Terminal and install the **Command Line Tools** (they provide `git` and `make`, which
   `install_unix.sh` needs):
   ```bash
   xcode-select --install
   ```
4. Install **Homebrew** (the app finds it via `PATH`, and its macOS package tasks report `brew` as missing without it):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   The guest is Intel (x86_64), so Homebrew installs under `/usr/local`. Open a new Terminal tab and check
   `brew --version` before going on.
5. Run the app with the one-liner from the [README](../../README.md#linux--wsl2--macos) (it clones the repo into
   `~/.personal-os-setup`, runs `make install` and `make run`), then use `personal-os-setup` for later runs. Exercise the
   Packages tab (brew formulae/casks), the Zsh and dotfiles sections, etc.
6. `make vm-clean` deletes the guest and its disk (`.vm/macos/`) — including Apple's recovery image, which the next
   `make vm-macos` downloads again.

The automated half of this lives in CI: the `integration-macos` job runs the integration tests on a hosted `macos-latest`
runner. The VM is for the click-through parts CI doesn't cover.

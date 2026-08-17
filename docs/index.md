# Documentation

Explore the documentation using the vertical navbar, or jump straight to a section:

- **Windows/WSL2**: [docs/windows_workflow](windows_workflow/README.md)
- **Linux/WSL2**: [docs/linux](linux/README.md)
- **macOS**: [docs/macos_darwin](macos_darwin/README.md)
- **TV setup** (Google TV + Stremio): [docs/android-tv](android-tv/readme.md)
- **Home server / Home Assistant**: [docs/home-server](home-server/readme.md)
- **Apps setup & shortcuts**: [docs/apps](apps/apps_configuration_and_shorcuts.md)
- **Websites & browser extensions**: [docs/apps](apps/awesome_websites_browser_extensions.md)

## Features & Benefits

- **One-liner installers**
    - Windows: PowerShell script that installs selected apps via `winget`, enables WSL, applies Windows Terminal defaults, and fetches GlazeWM config.
    - Linux / WSL / macOS: Bash script that installs Zsh/OMZ/P10k, terminal tools, and optional NVIDIA for Linux.

- **Cross-OS Python TUI**
    - Built with [Textual](https://textual.textualize.io/), with:
        - OS detection (Windows, WSL, Linux, macOS),
        - System action sections (WSL tools, Windows utilities, package managers).

- **Unified package catalog**
    - `src/personal_os_setup/config/packages.yaml` as a single source of truth for packages.
    - Concrete backends implemented:
        - Linux:
            - Ubuntu: `UbuntuAptManager`, `UbuntuSnapManager`,
            - Arch: `ArchLinuxYayManager`
        - Windows: `WindowsWingetManager`,
        - macOS: `DarwinBrewManager`, `DarwinBrewCaskManager`.

- **WSL workflow helpers**
    - Actions to:
        - List installed / online distros,
        - Install a distro with optional custom location,
        - Export / import / move / unregister distros,
        - Shutdown and update WSL.

- **Windows Terminal helpers**
    - Apply consistent defaults (Night Owl scheme, JetBrains Mono font, opacity, elevation).
    - Add a dedicated **Ubuntu profile** with an icon.

- **Curated documentation**
    - Windows & Linux workflows, TV setup (Google TV + Stremio), home server (Ubuntu Server + KVM + Home Assistant), app shortcuts, and browser extensions, mirrored to a static site via `properdocs`.

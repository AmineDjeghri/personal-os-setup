# Personal OS Setup

> [!TIP]
> **V2 is here** — the terminal UI has been rebuilt with [Textual](https://textual.textualize.io/), bringing tabs, colors, progress bars, and a much nicer look and feel.

![Logo](docs/images/logo.png)

| App Showcase                                            |
|---------------------------------------------------------|
| ![Desktop with terminals](docs/images/app_showcase.gif) |


> [!NOTE]
> **Update notes**
>
> | Platform           | Version / Details       | Updated   |
> |--------------------|-------------------------|-----------|
> | macOS              | 26                      | July 2026 |
> | CachyOS            | Linux `7.1.3-2-cachyos` | July 2026 |
> | Ubuntu (server)    | 24/26                   | June 2026 |
> | Windows 11 / WSL 2 | 11                      | May 2026  |


An opinionated setup **app + documentation hub** for building a fast, clean, and consistent environment across **Windows**, **Linux**, **macOS**, **WSL2**, and even your **living room stack** (**Google TV** + **Stremio**) and **home server** (**Home Assistant**).

Improve your UX and productivity with a reproducible setup for:

- Development tools and package management
- WSL2 workflows
- GPU drivers
- Terminal UX (Zsh/Oh-My-Zsh/Powerlevel10k)
- Window tiling management
- Home automation (Home Assistant)
- TV setup (Google TV + Stremio/Nuvio)

The image above is the app that runs on your terminal, it supports multiple OSes (Windows, Linux, macOS, WSL2) and can be used with a mouse to click on the buttons.
You can follow this repository to get a similar setup on Windows 11, Linux, macOS, or a hybrid workflow (Windows + WSL).


![Windows 11](https://img.shields.io/badge/Windows%2011-%230079d5.svg?style=for-the-badge&logo=Windows%2011&logoColor=white)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
[![Linux](https://img.shields.io/badge/-Linux-grey?style=for-the-badge&logo=linux)](https://www.microsoft.com/en-in/windows)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Arch](https://img.shields.io/badge/Arch%20Linux-1793D1?logo=arch-linux&logoColor=fff&style=for-the-badge)

**Table of contents**
<!-- TOC -->
* [Personal OS Setup](#personal-os-setup)
    * [Get started](#get-started)
      * [Linux / WSL2 / macOS](#linux--wsl2--macos)
      * [Windows 11](#windows-11)
  * [What is this repo?](#what-is-this-repo)
    * [Features & Benefits](#features--benefits)
    * [Docs and websites](#docs-and-websites)
  * [Project TODO / Roadmap](#project-todo--roadmap)
    * [Docs & site](#docs--site)
    * [Quality & UX](#quality--ux)
  * [Check the documentation](#check-the-documentation)
  * [Contributing (For developers)](#contributing-for-developers)
<!-- TOC -->




### Get started

#### Linux / WSL2 / macOS
Get started with one command in bash/zsh:

```bash
sh -c "$(wget https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/install_unix.sh -O -)"
```

The script installs the repository into `~/.personal-os-setup` (or reuses/updates it if it already exists there) and links a `personal-os-setup` command into `~/.local/bin`, so you can run it again from anywhere. If you already have the repo cloned and run the script from inside it, it updates that checkout in place instead.

If you are using a headless server (ubuntu-server for example), prefer to use a client with a GUI and connect to the server via SSH so you can copy-paste the commands and use Personal-OS-Setup with a mouse.

#### Windows 11
Get started with one command (run it in PowerShell as administrator):
```powershell
$u='https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/install_windows.ps1'; $p="$env:TEMP\install_windows.ps1"; iwr $u -UseBasicParsing -OutFile $p; powershell -ExecutionPolicy Bypass -File $p
```

The script installs the repository into `%USERPROFILE%\.personal-os-setup` (or reuses/updates it if it already exists there) and adds a `personal-os-setup` command to your PATH, so you can run it again from anywhere. If you already have the repo cloned and run the script from inside it, it updates that checkout in place instead.

> [!TIP]
> You can fork this repository and change the apps/packages you need so it reflects what you want to install in your environment.

## What is this repo?

This repo is a personal “OS setup Terminal UI App”:

### Features & Benefits

- **One‑liner installers**
  - Windows: PowerShell script that installs selected apps via `winget`, enables WSL, applies Windows Terminal defaults, and fetches GlazeWM config.
  - Linux / WSL/ macOS: Bash script that installs Zsh/OMZ/P10k, terminal tools, and optional NVIDIA for Linux.

- **Cross‑OS Python TUI**
  - TermTk‑based app (`main.py`) with:
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


### Docs and websites

- **Windows/WSL2 docs**:
  here: [LINK](docs/windows_workflow/README.md)

- **Linux/WSL2 docs**:
  here: [LINK](docs/linux/README.md)

- **macOS docs**:
  here: [LINK](docs/macos_darwin/README.md)

- **TV setup docs**: Read me about it
  here: [LINK](docs/android-tv/readme.md)

- **Home server / Home Assistant docs**:
  here: [LINK](docs/home-server/readme.md)

- **Apps setup docs**:
  [LINK](docs/apps/apps_configuration_and_shorcuts.md)

- **Websites & Browser extensions docs**:
  [LINK](docs/apps/awesome_websites_browser_extensions.md)



**For Windows users: Why you should use WSL2?**
WSL2 enables users to run Linux applications and use command-line tools natively on their Windows machines.
This integration allows users
to enjoy the familiarity of Windows while simultaneously harnessing the power and flexibility of Linux.
Also, a surprising number of Linux GUI apps can run on WSL. GUI applications are officially supported on WSL2 and
referred to as [WSLg](https://github.com/microsoft/wslg)(No installation required).

|              | macOS                                                                         | Linux                                                                      | Windows with WSL                                                                                                                                                                                                                          |
|--------------|-------------------------------------------------------------------------------|----------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Advantages   | (+) Excellent for coding and video editing. Supports Adobe & Office products. | (+) Ideal for coding and gaming, providing good performance in both areas. | - (+) Seamless compatibility with diverse software, including Adobe & Office products. </br> (+) Optimal choice for gaming enthusiasts </br> (+) Well-suited for coding with Windows Subsystem for Linux (WSL) and no need for dual boot. |
| Inconvenient | (-) Limited gaming capabilities compared to Windows & Linux.                  | (-) Lacks support for Adobe & Office products and certain software.        | (-) UI is not smooth and responsive compared to macOS & Linux                                                                                                                                                                             |

Within the domain of development, Unix-based systems such as Linux and macOS frequently garner attention. Nevertheless,
the integration of WSL allows smooth coding alongside the utilization of Adobe and Microsoft products that may lack
support on Linux. This flexibility, coupled with the ability to handle resource-intensive games beyond macOS
capabilities, positions Windows-WSL as an enticing platform, ensuring a well-rounded computing experience for all users,
regardless of their workplace constraints.

Based on your needs, you can choose your OS.

## Project TODO / Roadmap
- [ ] add missing apps
- [ ] Some dotfiles integration (GlazeWM, aerospace, raycast...)
- [ ] Chezmoi integration

### Docs & site

- [ ] Fix broken README one‑liners (curl/wget URLs to this repo) and update URL to main branch

### Quality & UX

- [ ] Update UX/UI.
  - [ ] Display a checkmark when a package is installed.
- [ ] Add tests and CI coverage for:
  - [ ] Parsing `packages.yaml`.
  - [ ] Package manager factory mapping.
  - [ ] Windows/WSL command runner behavior.
  - [x] Docker image to test Arch
  - [ ] Docker image to test Ubuntu
  - [ ] Docker image to test macOS


## Check the documentation
You can check the documentation (website).

## Contributing (For developers)
Check the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information.

**Star History Chart**
[![Star History Chart](https://api.star-history.com/svg?repos=aminedjeghri/awesomewindows11&type=Date)](https://star-history.com/#aminedjeghri/awesomewindows11&Date)

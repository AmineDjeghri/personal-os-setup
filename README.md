# Personal OS Setup

![Windows 11](https://img.shields.io/badge/Windows%2011-%230079d5.svg?style=for-the-badge&logo=Windows%2011&logoColor=white)
![macOS](https://img.shields.io/badge/mac%20os-000000?style=for-the-badge&logo=macos&logoColor=F0F0F0)
[![Linux](https://img.shields.io/badge/-Linux-grey?style=for-the-badge&logo=linux)](https://www.microsoft.com/en-in/windows)
![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)
![Arch](https://img.shields.io/badge/Arch%20Linux-1793D1?logo=arch-linux&logoColor=fff&style=for-the-badge)

[![CI](https://github.com/AmineDjeghri/personal-os-setup/actions/workflows/ci.yml/badge.svg)](https://github.com/AmineDjeghri/personal-os-setup/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/AmineDjeghri/personal-os-setup)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-website-blue)](http://personal-os-setup.aminedjeghri.com/)
[![Stars](https://img.shields.io/github/stars/AmineDjeghri/personal-os-setup?style=social)](https://github.com/AmineDjeghri/personal-os-setup)

![Logo](docs/images/logo.png)

| App Showcase                                            |
|---------------------------------------------------------|
| ![Desktop with terminals](docs/images/app_showcase.gif) |

A terminal app for installing packages and configuring Windows, Linux, macOS and WSL2,
with guides for desktops, home servers and Android TV.

## Get started

### Linux / WSL2 / macOS

```bash
sh -c "$(wget https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/install_unix.sh -O -)"
```

### Windows 11

Run PowerShell as administrator:

```powershell
$u='https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/install_windows.ps1'; $p="$env:TEMP\install_windows.ps1"; iwr $u -UseBasicParsing -OutFile $p; powershell -ExecutionPolicy Bypass -File $p
```

Then launch the app from any terminal:

```bash
personal-os-setup
```

Installation uses `~/.personal-os-setup` on Unix or `%USERPROFILE%\.personal-os-setup` on Windows.
Running the installer inside an existing clone updates that checkout instead.
The launcher pulls updates before starting the app. System changes require confirmation in the TUI.

## Develop

With Make, Bash, Git and uv available:

```bash
git clone https://github.com/AmineDjeghri/personal-os-setup.git
cd personal-os-setup
make install-dev
make pre-commit-install
make check
make run
```

`make check` runs static/docs checks, safe tests and isolated package installation.
CI also runs OS integration on disposable hosts. To link the launcher to your clone,
run `./install_unix.sh` or `./install_windows.ps1` from that clone.

| Task                         | Guide                                                                              |
|------------------------------|------------------------------------------------------------------------------------|
| Set up your editor and tools | [Setup](docs/developer/1.setup.md)                                                 |
| Find the relevant code       | [Project structure](docs/developer/2.project-structure.md)                         |
| Prepare a contribution       | [Contributing](CONTRIBUTING.md) and [conventions](docs/developer/3.conventions.md) |
| Run tests                    | [Testing](docs/developer/4.testing.md)                                             |
| Publish a release            | [Release](docs/developer/5.release.md)                                             |
| Try system changes in a VM   | [VM lab](docs/vm/README.md)                                                        |

Run `make help` for all targets. Agent instructions are in `AGENTS.md`; project skills are in
`.claude/skills/`.

## Platform guides

[Documentation site](http://personal-os-setup.aminedjeghri.com/) ·
[Linux](docs/linux/README.md) · [CachyOS](docs/linux/CachyOS.md) ·
[macOS](docs/macos_darwin/README.md) · [Windows and WSL](docs/windows_workflow/README.md) ·
[Home server](docs/home-server/readme.md) · [Android TV](docs/android-tv/readme.md).

[![Star History Chart](https://star-history.dera.page/svg?repos=AmineDjeghri/personal-os-setup)](https://star-history.dera.page/#AmineDjeghri/personal-os-setup)

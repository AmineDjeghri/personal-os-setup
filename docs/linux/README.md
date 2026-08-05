# Linux setup

If you are using a headless server (ubuntu-server for example), prefer to use a client with a GUI and connect to the server via SSH so you can copy-paste the commands and use Personal-OS-Setup with a mouse.

## Installation Process

The Personal OS Setup provides a **Terminal UI (TUI) application** that guides you through the installation process. Once you run the one-liner installer, you'll see an interactive interface with the following steps:

Use [README.md](../../README.md#linux--wsl2--macos) as it automatically handles the OS setup with the interactive TUI application.

Before installing packages, it's recommended to update your system.

### 1. Package Selection
The app displays all available packages from [packages.yaml](../../src/personal_os_setup/config/packages.yaml) organized by category:
- **Core tools**: `git`, `curl`, `zsh`
- **Terminal tools**: `bat`, `btop`, `fzf`, `lsd`, `fastfetch`
- **Apps**: Code editor, messaging apps, media players, etc.

You can multi-select packages using the interactive interface.

### 2. Terminal Setup (Zsh + Oh My Zsh + Powerlevel10k)
The app provides buttons to automate the terminal configuration:

- **Install JetBrainsMono Nerd Font**: Required for proper theme rendering
- **Apply ~/.zshrc**: Configures shell aliases and environment variables
- **Apply ~/.p10k.zsh**: Applies Powerlevel10k theme configuration
- **Sync zsh plugins/theme**: Installs Oh My Zsh plugins and themes
- **Set zsh as default shell**: Makes Zsh your default login shell

**Python Management**: The zshrc configuration replaces both `python3` and `python` with the alias `uv run python`, ensuring you always use the `uv` package manager for Python execution instead of the system Python.

**.env Detection**: The configuration automatically detects and loads `.env` files from your project directories, making environment variables available in your shell session without manual setup.

**How plugin updates actually happen**: oh-my-zsh's own auto-updater
(`zstyle ':omz:update' mode auto` in `.zshrc`) only keeps the oh-my-zsh
**core framework** current on shell startup — it never touches custom
plugins or the theme. Those (oh-my-zsh itself, `zsh-autocomplete`,
`zsh-autosuggestions`, `zsh-syntax-highlighting`, `fzf-zsh-plugin`,
`powerlevel10k`) are instead declared as `git-repo` externals in
[.chezmoiexternal.toml](../../src/personal_os_setup/config/chezmoi/.chezmoiexternal.toml),
each with a `refreshPeriod = "168h"` (7 days). That refresh isn't tied to
clicking **Sync zsh plugins/theme** specifically: *any* `chezmoi apply`
call — even one scoped to a single unrelated dotfile from the "Sync
dotfiles" tab — rebuilds chezmoi's full target state first, which checks
every external's cache and silently re-pulls any that are more than 7 days
stale.

See the [zshrc configuration file](../../src/personal_os_setup/config/unix/.zshrc) for the default configuration used by this project.

If you need to revert changes:
- Uninstall Oh My Zsh and Powerlevel10k files
- Uninstall Zsh package
- Reset Bash as default shell

Additional system configuration options (only if you have NVIDIA GPU):
- **Detect NVIDIA**: Check if NVIDIA GPU is available
- **Setup NVIDIA (WSL)**: Configure NVIDIA drivers for WSL2
- **Detect CUDA**: Check CUDA installation
- **Setup CUDA (Advanced)**: Configure CUDA for GPU computing

### CUDA Installation (Native Linux)

To install CUDA on native Linux, follow the pre-installation actions from the official guide:
[CUDA Installation Guide for Linux](https://docs.nvidia.com/cuda/archive/12.6.0/cuda-installation-guide-linux/index.html#pre-installation-actions)


### CUDA in Docker

To enable GPU support inside Docker containers, install the NVIDIA Container Toolkit:
[NVIDIA Container Toolkit Install Guide (apt — Ubuntu/Debian)](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#with-apt-ubuntu-debian)

### Docker post-install: run without sudo (Ubuntu)

By default, Docker requires `sudo` to run. To allow your user (and any tools or scripts) to use Docker without `sudo`, add yourself to the `docker` group:

```sh
sudo groupadd docker          # create the group (usually already exists)
sudo usermod -aG docker $USER # add your user to the group
newgrp docker                 # activate the change in the current shell
```

> **Pro Tip:** `newgrp docker` only applies to the current terminal window. For a permanent, system-wide effect, log out of your SSH session and log back in.

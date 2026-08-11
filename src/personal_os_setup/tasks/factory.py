from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from pydantic import BaseModel, ConfigDict

from personal_os_setup.detect_os import PackageRef, _is_wsl
from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager
from personal_os_setup.tasks.managers.arch_paru import ArchParuManager
from personal_os_setup.tasks.managers.base import PackageManager
from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewCaskManager, DarwinBrewManager
from personal_os_setup.tasks.managers.ubuntu_apt import UbuntuAptManager
from personal_os_setup.tasks.managers.ubuntu_snap import UbuntuSnapManager
from personal_os_setup.tasks.managers.webinstall import WebInstallManager
from personal_os_setup.tasks.managers.windows_msstore import WindowsMSStoreManager
from personal_os_setup.tasks.managers.windows_winget import WindowsWingetManager
from personal_os_setup.tasks.system.chezmoi import chezmoi_add, chezmoi_refresh_zsh_externals
from personal_os_setup.tasks.system.docker_tasks import docker_post_install_linux
from personal_os_setup.tasks.system.font import install_jetbrainsmono_nerd_font
from personal_os_setup.tasks.system.help import (
    show_commands,
    show_documentation_link,
    show_packages_yaml_path,
)
from personal_os_setup.tasks.system.nvidia_tasks import (
    detect_cuda,
    detect_nvidia,
    setup_cuda,
    setup_nvidia_arch,
    setup_nvidia_ubuntu,
    setup_nvidia_windows,
    setup_nvidia_wsl_instructions,
)
from personal_os_setup.tasks.system.windows_tasks import (
    apply_windows_terminal_ui_defaults,
    download_glazewm_config,
)
from personal_os_setup.tasks.system.windows_wsl_tasks import (
    add_windows_terminal_ubuntu_profile,
    wsl_export,
    wsl_import,
    wsl_install,
    wsl_list_online,
    wsl_list_verbose,
    wsl_move,
    wsl_shutdown,
    wsl_unregister,
    wsl_update,
    wsl_version,
)
from personal_os_setup.tasks.system.zsh import set_zsh_as_default_shell
from personal_os_setup.tasks.task import TaskResult

_PACKAGE_MANAGER_FACTORY_BY_DISTRO: dict[str, dict[str, Callable[[], PackageManager]]] = {
    "ubuntu": {
        "apt": UbuntuAptManager,
        "snap": UbuntuSnapManager,
        "webinstall": WebInstallManager,
    },
    "darwin": {
        "brew": DarwinBrewManager,
        "cask": DarwinBrewCaskManager,
        "webinstall": WebInstallManager,
    },
    "windows": {
        "winget": WindowsWingetManager,
        "msstore": WindowsMSStoreManager,
        "webinstall": WebInstallManager,
    },
    "cachyos": {
        "pacman": ArchPacmanManager,
        "paru": ArchParuManager,
    },
}

# Only show primary package managers to avoid duplicate buttons for the same distro
# (e.g. Ubuntu also has "snap"/"webinstall" backends, but only "apt" is surfaced).
_UI_VISIBLE_MANAGERS_BY_DISTRO: dict[str, list[str]] = {
    "windows": ["winget"],
    "ubuntu": ["apt"],
    "darwin": ["brew"],
    "cachyos": ["pacman", "paru"],
}

Section = tuple[str, list["SystemAction"]]


class SystemAction(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    label: str
    run: Callable[[], TaskResult]
    prompt_label: str | None = None
    prompt_initial: str = ""
    run_with_prompt: Callable[[str], TaskResult] | None = None
    confirm: bool = False
    confirm_message: str | None = None
    backup_target: Path | None = None


def get_package_manager(*, distro: str, manager: str) -> PackageManager | None:
    """Return a unified package manager backend for the given environment.

    Args:
        distro: A normalized distro identifier (e.g. `"ubuntu"`).
        manager: The package manager identifier (e.g. `"apt"`).

    Returns:
        A `PackageManager` instance if supported, otherwise `None`.
    """
    factory = _PACKAGE_MANAGER_FACTORY_BY_DISTRO.get(distro, {}).get(manager)
    return factory() if factory else None


# Section: "<manager name>" (one per primary manager, e.g. "apt", "brew") — update/upgrade/cleanup for that package manager.
def _package_manager_sections(distro: str) -> list[Section]:
    """Build one section per primary package manager for `distro` (update/upgrade/cleanup)."""
    factories = _PACKAGE_MANAGER_FACTORY_BY_DISTRO.get(distro, {})
    allowed_managers = _UI_VISIBLE_MANAGERS_BY_DISTRO.get(distro, list(factories.keys()))

    sections: list[Section] = []
    for manager_name in allowed_managers:
        factory = factories.get(manager_name)
        if factory is None:
            continue
        pm = factory()
        sections.append(
            (
                manager_name,
                [
                    SystemAction(
                        label="update",
                        run=pm.update,
                        confirm=True,
                        confirm_message=f"This will only update the {manager_name} package list/cache. Run the upgrade action to upgrade all packages. "
                        f"Proceed?",
                    ),
                    SystemAction(
                        label="upgrade",
                        run=pm.upgrade,
                        confirm=True,
                        confirm_message="This will iterate through packages and upgrade them one by one. You may be prompted to accept installation for some apps. Proceed?",
                    ),
                    SystemAction(label="cleanup", run=pm.cleanup),
                ],
            )
        )
    return sections


def _doc_section(distro: str) -> Section:
    actions = [
        SystemAction(label="show commands", run=show_commands),
        SystemAction(label="open documentation site", run=show_documentation_link),
        SystemAction(label="open packages.yaml", run=show_packages_yaml_path),
    ]
    if distro == "cachyos":
        actions.append(
            SystemAction(
                label="enable vicinae (copy command)",
                run=lambda: TaskResult(
                    ok=True,
                    summary="systemctl --user enable --now vicinae",
                    details="Run this once to start the Vicinae launcher daemon and keep it "
                    "enabled on login.",
                ),
            )
        )
    return ("Doc", actions)


# Section: "Sync dotfiles" — installs zsh setup prerequisites/fonts and applies chezmoi-managed dotfiles (zsh, p10k, etc).

# Packages tagged with this category in packages.yaml (git, zsh, curl, chezmoi, plus
# CLI tools like fzf/zoxide/eza/bat) are treated as the prerequisites for the zsh
# setup specifically -- other chezmoi-managed dotfiles (e.g. zed, noctalia) need none.
_ZSH_PREREQ_CATEGORY = "terminal_tools"


def _zsh_prereq_packages(packages: list[PackageRef]) -> list[PackageRef]:
    return [p for p in packages if p.category.lower() == _ZSH_PREREQ_CATEGORY]


def _install_zsh_prereqs(packages: list[PackageRef], distro: str) -> TaskResult:
    prereqs = _zsh_prereq_packages(packages)
    if not prereqs:
        return TaskResult(ok=True, summary="No zsh setup prerequisites configured for this distro")

    lines: list[str] = []
    failures = 0
    for p in prereqs:
        pm = get_package_manager(distro=distro, manager=p.manager)
        if pm is None:
            failures += 1
            lines.append(f"{p.name}: no {p.manager} installer available")
            continue
        if pm.is_installed(p.name):
            lines.append(f"{p.name}: already installed")
            continue
        res = pm.install(p.name)
        if not res.ok:
            failures += 1
        lines.append(res.summary)

    ok = failures == 0
    summary = f"Installed {len(prereqs) - failures}/{len(prereqs)} zsh setup prerequisites"
    return TaskResult(ok=ok, summary=summary, details="\n".join(lines))


def _dotfiles_section(distro: str, packages: list[PackageRef]) -> Section:
    prereqs = _zsh_prereq_packages(packages)
    prereq_names = ", ".join(p.name for p in prereqs)
    return (
        "Sync dotfiles",
        [
            SystemAction(
                label="install zsh setup prerequisites",
                run=lambda: _install_zsh_prereqs(packages, distro),
                confirm=True,
                confirm_message=(
                    f"Install the zsh setup prerequisites ({prereq_names})? "
                    "Only needed if you're syncing .zshrc/.p10k.zsh -- other dotfiles "
                    "(e.g. zed, noctalia) don't need these."
                    if prereqs
                    else "No zsh setup prerequisites are configured for this distro."
                ),
            ),
            SystemAction(
                label="install JetBrainsMono Nerd Font",
                run=install_jetbrainsmono_nerd_font,
                confirm=True,
                confirm_message="Install JetBrainsMono Nerd Font for terminals?",
            ),
            SystemAction(
                label="chezmoi: track a new file",
                run=lambda: TaskResult(
                    ok=True,
                    summary="Provide the path to a file to start tracking in this repo's "
                    "chezmoi source dir, e.g. ~/.config/foo/config.toml",
                ),
                run_with_prompt=lambda value: chezmoi_add(Path(value).expanduser()),
                prompt_label=(
                    "Path to a file to start tracking in this repo's chezmoi source dir "
                    "(e.g. ~/.config/foo/config.toml)"
                ),
                prompt_initial="~/.",
            ),
            SystemAction(
                label="set zsh as default shell",
                run=set_zsh_as_default_shell,
                confirm=True,
                confirm_message="Set your default shell to zsh? (OS reboot required)",
            ),
            SystemAction(
                label="sync zsh plugins/theme",
                run=chezmoi_refresh_zsh_externals,
                confirm=True,
                confirm_message="Pull oh-my-zsh, its plugins, and its theme from upstream?",
            ),
        ],
    )


# Section: "docker" — post-install step so Docker can be run without sudo.
def _docker_section() -> Section:
    return (
        "docker",
        [
            SystemAction(
                label="post-install: run docker without sudo",
                run=docker_post_install_linux,
            ),
        ],
    )


def _nvidia_setup_action(*, system: str, distro: str) -> SystemAction:
    """Return the single OS-specific "setup nvidia" action for the `system`/`nvidia_actions` section."""
    if system == "windows":
        return SystemAction(
            label="setup nvidia (windows)",
            run=setup_nvidia_windows,
            confirm=True,
            confirm_message="This will show NVIDIA setup guidance for Windows. Proceed?",
        )
    if system == "linux" and _is_wsl():
        return SystemAction(
            label="setup nvidia (wsl)",
            run=setup_nvidia_wsl_instructions,
            confirm=True,
            confirm_message="This will show NVIDIA setup guidance for WSL (Windows host driver). Proceed?",
        )
    if distro == "ubuntu":
        return SystemAction(
            label="setup nvidia (ubuntu)",
            run=setup_nvidia_ubuntu,
            confirm=True,
            confirm_message="This will attempt to install NVIDIA drivers on Ubuntu (reboot required). Proceed?",
        )
    if distro == "cachyos":
        return SystemAction(
            label=f"setup nvidia ({distro})",
            run=setup_nvidia_arch,
            confirm=True,
            confirm_message="This will report NVIDIA driver status and show the right packages for your kernel. Proceed?",
        )
    return SystemAction(
        label=f"setup nvidia ({distro})",
        run=lambda: TaskResult(
            ok=False, summary=f"NVIDIA setup not implemented for distro: {distro}"
        ),
        confirm=True,
        confirm_message=f"NVIDIA setup is not implemented for distro '{distro}'. Proceed to show details?",
    )


# Section: "system" — detects NVIDIA/CUDA and runs the OS-appropriate NVIDIA driver setup.
def _nvidia_section(*, system: str, distro: str) -> Section:
    return (
        "system",
        [
            SystemAction(label="detect nvidia", run=detect_nvidia),
            _nvidia_setup_action(system=system, distro=distro),
            SystemAction(label="detect cuda", run=detect_cuda),
            SystemAction(label="setup cuda (advanced)", run=setup_cuda),
        ],
    )


def _windows_terminal_settings_path() -> Path:
    return (
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Packages"
        / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
        / "LocalState"
        / "settings.json"
    )


# Section: "WSL" — everyday WSL operations (list/install distros, update, shutdown, Windows Terminal profile).
def _wsl_section(settings_path: Path) -> Section:
    return (
        "WSL",
        [
            SystemAction(label="List installed distros", run=wsl_list_verbose),
            SystemAction(label="List online distros", run=wsl_list_online),
            SystemAction(
                label="Install distro",
                run=lambda: TaskResult(
                    ok=True,
                    summary=(
                        "Provide input as: <DistributionName>|location=<Folder(optional)>\n"
                        "Examples:\n"
                        "- Ubuntu\n"
                        "- Ubuntu|location=D:\\WSL\\Ubuntu\n"
                        "Note: this action uses --no-launch by default."
                    ),
                ),
                run_with_prompt=wsl_install,
                prompt_label=(
                    "Install input: <DistributionName>|location=<Folder(optional)>\n"
                    "Example: Ubuntu|location=D:\\WSL\\Ubuntu"
                ),
                prompt_initial="Ubuntu",
                confirm=True,
                confirm_message="This will run wsl --install (no-launch by default). Proceed?",
            ),
            SystemAction(label="version", run=wsl_version),
            SystemAction(
                label="Update WSL",
                run=wsl_update,
                confirm=True,
                confirm_message="This will update WSL components. Proceed?",
            ),
            SystemAction(
                label="Shutdown WSL",
                run=wsl_shutdown,
                confirm=True,
                confirm_message="This will shut down all running WSL distros. Proceed?",
            ),
            SystemAction(
                label="Add Windows Terminal profile for WSL Ubuntu",
                run=add_windows_terminal_ubuntu_profile,
                confirm=True,
                confirm_message="This will add a new profile for Ubuntu in Windows Terminal. A backup of the settings.json file will be created. Proceed?",
                backup_target=settings_path,
            ),
        ],
    )


# Section: "Advanced WSL" — destructive/rarer WSL operations (move, export, import, delete a distro).
def _advanced_wsl_section() -> Section:
    return (
        "Advanced WSL",
        [
            SystemAction(
                label="Move WSL distro to new location",
                run=lambda: TaskResult(
                    ok=True,
                    summary="Provide input as: <DistributionName>|<NewLocation>",
                ),
                run_with_prompt=wsl_move,
                prompt_label="Move input: <DistributionName>|<NewLocation>  e.g. Ubuntu|D:\\WSL\\Ubuntu",
                prompt_initial="Ubuntu|D:\\WSL\\Ubuntu",
                confirm=True,
                confirm_message="This will move the distro to a new location. Proceed?",
            ),
            SystemAction(
                label="Export distro",
                run=lambda: TaskResult(
                    ok=True,
                    summary="Provide input as: <DistributionName>|<FileName> . For example: "
                    "Ubuntu|C:\\Temp\\ubuntu.tar  . You can get the distro name with the button 'installed "
                    "distros'",
                ),
                run_with_prompt=wsl_export,
                prompt_label="Export input: <DistributionName>|<FileName>  e.g. Ubuntu|C:\\Temp\\ubuntu.tar",
                prompt_initial="Ubuntu|C:\\Temp\\ubuntu.tar",
                confirm=True,
                confirm_message="This will export the distro to a tar file. Proceed?",
            ),
            SystemAction(
                label="Import distro",
                run=lambda: TaskResult(
                    ok=True,
                    summary="Provide input as: <DistributionName>|<InstallLocation>|<FileName>",
                ),
                run_with_prompt=wsl_import,
                prompt_label=(
                    "Import input: <DistributionName>|<InstallLocation>|<FileName>"
                    "e.g. Ubuntu|D:\\WSL\\Ubuntu|C:\\Temp\\ubuntu.tar"
                ),
                prompt_initial="Ubuntu|D:\\WSL\\Ubuntu|C:\\Temp\\ubuntu.tar",
                confirm=True,
                confirm_message="This will import a distro from a tar file. Proceed?",
            ),
            SystemAction(
                label="Delete distro",
                run=lambda: TaskResult(
                    ok=True,
                    summary="Provide the DistributionName to unregister",
                ),
                run_with_prompt=wsl_unregister,
                prompt_label="DistributionName to unregister (DELETES the distro)",
                prompt_initial="Ubuntu",
                confirm=True,
                confirm_message="This will unregister (DELETE) the distro. Proceed?",
            ),
        ],
    )


# Section: "Windows utilities" — Nerd Font install, Windows Terminal defaults, and GlazeWM config download.
def _windows_utilities_section(settings_path: Path) -> Section:
    return (
        "Windows utilities",
        [
            SystemAction(
                label="install JetBrainsMono Nerd Font",
                run=install_jetbrainsmono_nerd_font,
                confirm=True,
                confirm_message="Install JetBrainsMono Nerd Font for terminals?",
            ),
            SystemAction(
                label="Update Windows Terminal default UI",
                run=apply_windows_terminal_ui_defaults,
                confirm=True,
                confirm_message="This will update Windows Terminal settings.json (theme/font/opacity) and "
                "requires FiraCode Nerd font installed. Proceed?",
                backup_target=settings_path,
            ),
            SystemAction(
                label="Install GlazeWM config",
                run=download_glazewm_config,
                confirm=True,
                confirm_message="This will download and overwrite GlazeWM config.yaml. Proceed?",
            ),
        ],
    )


def get_system_action_sections(
    *, system: str, distro: str, info: str | None, packages: list[PackageRef] | None = None
) -> list[Section]:
    """Build the ordered list of `(section_name, [SystemAction])` tuples for this OS/distro.

    Sections are assembled conditionally on `system`/`distro`: package-manager
    sections always come first, then zsh/chezmoi/docker (Linux+macOS), NVIDIA
    (Windows+Linux), and WSL/Windows-utility sections (Windows only).

    Args:
        system: Normalized OS family (e.g. `"windows"`, `"darwin"`, `"linux"`).
        distro: Normalized distro identifier (e.g. `"ubuntu"`).
        info: Extra environment info (e.g. WSL detection note), or `None`.
        packages: The full package catalog for this distro, used to populate the
            "install zsh setup prerequisites" action in the dotfiles section (packages
            tagged with the `"terminal_tools"` category in `packages.yaml`).
    """
    sections: list[Section] = []

    # Package managers (apt, snap, brew...) - at the top for quick access.
    sections.extend(_package_manager_sections(distro))

    #################
    ## Linux & Darwin
    #################
    if system in {"darwin", "linux"}:
        sections.append(_doc_section(distro))
        sections.append(_dotfiles_section(distro, packages or []))

    ########
    ## Docker
    ########
    if distro in {"ubuntu", "cachyos"}:
        sections.append(_docker_section())

    ########
    ## NVIDIA
    ########
    if system in {"windows", "linux"}:
        sections.append(_nvidia_section(system=system, distro=distro))

    ########
    ## Windows
    ########
    if system == "windows":
        settings_path = _windows_terminal_settings_path()
        sections.append(_wsl_section(settings_path))
        sections.append(_advanced_wsl_section())
        sections.append(_windows_utilities_section(settings_path))

    return sections

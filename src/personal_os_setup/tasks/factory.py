from __future__ import annotations

import os
from personal_os_setup.detect_os import _is_wsl
from personal_os_setup.tasks.managers.arch_pacman import ArchPacmanManager
from personal_os_setup.tasks.managers.arch_paru import ArchParuManager
from personal_os_setup.tasks.managers.base import PackageManager
from personal_os_setup.tasks.managers.darwin_brew import DarwinBrewManager, DarwinBrewCaskManager
from personal_os_setup.tasks.managers.ubuntu_apt import UbuntuAptManager
from personal_os_setup.tasks.managers.ubuntu_snap import UbuntuSnapManager
from personal_os_setup.tasks.managers.windows_msstore import WindowsMSStoreManager
from personal_os_setup.tasks.managers.webinstall import WebInstallManager
from personal_os_setup.tasks.managers.windows_winget import WindowsWingetManager
from personal_os_setup.tasks.system.chezmoi import chezmoi_apply, chezmoi_diff, chezmoi_re_add
from personal_os_setup.tasks.system.font import install_jetbrainsmono_nerd_font
from personal_os_setup.tasks.system.help import show_commands
from personal_os_setup.tasks.system.docker_tasks import docker_post_install_linux
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
    wsl_install,
    wsl_list_online,
    wsl_list_verbose,
    wsl_update,
    wsl_version,
    wsl_shutdown,
    wsl_unregister,
    wsl_export,
    wsl_import,
    wsl_move,
    add_windows_terminal_ubuntu_profile,
)
from personal_os_setup.tasks.system.zsh import (
    set_bash_as_default_shell,
    set_zsh_as_default_shell,
    uninstall_oh_my_zsh_and_p10k,
    uninstall_zsh_apt,
)
from personal_os_setup.tasks.task import TaskResult
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from typing import Callable

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


def get_system_action_sections(
    *, system: str, distro: str, info: str | None
) -> list[tuple[str, list[SystemAction]]]:
    sections: list[tuple[str, list[SystemAction]]] = []

    # Package managers (apt, snap, brew...) - at the top for quick access
    # Only show primary package managers to avoid duplication
    primary_managers = {
        "windows": ["winget"],
        "ubuntu": ["apt"],
        "darwin": ["brew"],
        "cachyos": ["pacman", "paru"],
    }

    factories = _PACKAGE_MANAGER_FACTORY_BY_DISTRO.get(distro, {})
    allowed_managers = primary_managers.get(distro, list(factories.keys()))

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
                        confirm_message=f"This will iterate through packages and upgrade them one by one. You may be prompted to accept installation for some apps. Proceed?",
                    ),
                    SystemAction(label="cleanup", run=pm.cleanup),
                ],
            )
        )

    #################
    ## Linux & Darwin
    #################
    if system in {"darwin", "linux"}:
        # help
        sections.append(
            (
                "help",
                [
                    SystemAction(label="show commands", run=show_commands),
                ],
            )
        )
        # zsh
        zsh_actions: list[SystemAction] = []

        zsh_actions.extend(
            [
                SystemAction(
                    label="install JetBrainsMono Nerd Font",
                    run=install_jetbrainsmono_nerd_font,
                    confirm=True,
                    confirm_message="Install JetBrainsMono Nerd Font for terminals?",
                ),
                SystemAction(label="chezmoi: diff", run=chezmoi_diff),
                SystemAction(
                    label="chezmoi: apply",
                    run=chezmoi_apply,
                    confirm=True,
                    confirm_message="This applies chezmoi-managed dotfiles (.zshrc, .p10k.zsh) "
                    "and clones oh-my-zsh/plugins/theme (declared in .chezmoiexternal.toml) "
                    "to your home directory. Run 'chezmoi: diff' first to preview. Proceed?",
                ),
                SystemAction(
                    label="chezmoi: re-add",
                    run=chezmoi_re_add,
                    confirm=True,
                    confirm_message="This pulls your current dotfiles back into the repo's chezmoi source dir, "
                    "overwriting the vendored versions there. Proceed?",
                ),
                SystemAction(
                    label="set zsh as default shell",
                    run=set_zsh_as_default_shell,
                    confirm=True,
                    confirm_message="Set your default shell to zsh? (OS reboot required)",
                ),
            ]
        )
        sections.append(
            (
                "zsh",
                zsh_actions,
            )
        )
        # zsh uninstall
        zsh_uninstall_actions: list[SystemAction] = [
            SystemAction(
                label="uninstall: oh-my-zsh + p10k files",
                run=uninstall_oh_my_zsh_and_p10k,
                confirm=True,
                confirm_message="This will delete oh-my-zsh and related zsh config files. Proceed?",
            ),
        ]
        # apt-only, so it always fails on Arch/macOS. Only offer it where it can work.
        if distro == "ubuntu":
            zsh_uninstall_actions.append(
                SystemAction(
                    label="uninstall zsh (apt)",
                    run=uninstall_zsh_apt,
                    confirm=True,
                    confirm_message="This will uninstall zsh via apt (sudo required). Proceed?",
                )
            )
        zsh_uninstall_actions.append(
            SystemAction(
                label="set bash as default shell",
                run=set_bash_as_default_shell,
                confirm=True,
                confirm_message="Set your default shell to bash?",
            )
        )
        sections.append(("zsh uninstall", zsh_uninstall_actions))

    ########
    ## Docker
    ########
    if distro in {"ubuntu", "cachyos"}:
        sections.append(
            (
                "docker",
                [
                    SystemAction(
                        label="post-install: run docker without sudo",
                        run=docker_post_install_linux,
                    ),
                ],
            )
        )

    ########
    ## NVIDIA
    ########
    if system in {"windows", "linux"}:
        nvidia_actions: list[SystemAction] = [
            SystemAction(label="detect nvidia", run=detect_nvidia)
        ]

        if system == "windows":
            nvidia_actions.append(
                SystemAction(
                    label="setup nvidia (windows)",
                    run=setup_nvidia_windows,
                    confirm=True,
                    confirm_message="This will show NVIDIA setup guidance for Windows. Proceed?",
                )
            )
        elif system == "linux" and _is_wsl():
            nvidia_actions.append(
                SystemAction(
                    label="setup nvidia (wsl)",
                    run=setup_nvidia_wsl_instructions,
                    confirm=True,
                    confirm_message="This will show NVIDIA setup guidance for WSL (Windows host driver). Proceed?",
                )
            )
        elif distro == "ubuntu":
            nvidia_actions.append(
                SystemAction(
                    label="setup nvidia (ubuntu)",
                    run=setup_nvidia_ubuntu,
                    confirm=True,
                    confirm_message="This will attempt to install NVIDIA drivers on Ubuntu (reboot required). Proceed?",
                )
            )
        elif distro == "cachyos":
            nvidia_actions.append(
                SystemAction(
                    label=f"setup nvidia ({distro})",
                    run=setup_nvidia_arch,
                    confirm=True,
                    confirm_message="This will report NVIDIA driver status and show the right packages for your kernel. Proceed?",
                )
            )
        else:
            nvidia_actions.append(
                SystemAction(
                    label=f"setup nvidia ({distro})",
                    run=lambda: TaskResult(
                        ok=False, summary=f"NVIDIA setup not implemented for distro: {distro}"
                    ),
                    confirm=True,
                    confirm_message=f"NVIDIA setup is not implemented for distro '{distro}'. Proceed to show details?",
                )
            )

        sections.append(
            (
                "system",
                [
                    *nvidia_actions,
                    SystemAction(label="detect cuda", run=detect_cuda),
                    SystemAction(label="setup cuda (advanced)", run=setup_cuda),
                ],
            )
        )

    ########
    ## Windows
    ########
    if system == "windows":
        settings_path = (
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Packages"
            / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
            / "LocalState"
            / "settings.json"
        )

        sections.append(
            (
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
        )

        ########
        ## Windows:  WSL
        ########
        sections.append(
            (
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
        )

        ########
        ## Windows: Utilities
        ########
        sections.append(
            (
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
        )

    return sections

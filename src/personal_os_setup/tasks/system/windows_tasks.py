from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import urlopen

from personal_os_setup.tasks.task import TaskResult


def _windows_terminal_settings_path() -> Path:
    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        return Path("")
    return (
        Path(localappdata)
        / "Packages"
        / "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
        / "LocalState"
        / "settings.json"
    )


def apply_windows_terminal_ui_defaults() -> TaskResult:
    settings_path = _windows_terminal_settings_path()
    if not settings_path.exists():
        return TaskResult(
            ok=False,
            summary="Windows Terminal settings.json not found",
            details=str(settings_path),
        )

    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return TaskResult(
            ok=False, summary="read Windows Terminal settings: failed", details=str(e)
        )

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        data["profiles"] = profiles

    defaults = profiles.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        profiles["defaults"] = defaults

    schemes = data.get("schemes")
    if not isinstance(schemes, list):
        schemes = []
        data["schemes"] = schemes

    night_owl = {
        "name": "Night Owl",
        "cursorColor": "#80a4c2",
        "selectionBackground": "#1d3b53",
        "background": "#011627",
        "foreground": "#D6DEEB",
        "black": "#011627",
        "blue": "#82AAFF",
        "cyan": "#21C7A8",
        "green": "#22DA6E",
        "purple": "#C792EA",
        "red": "#EF5350",
        "white": "#FFFFFF",
        "yellow": "#c5e478",
        "brightBlack": "#575656",
        "brightBlue": "#82AAFF",
        "brightCyan": "#7FDBCA",
        "brightGreen": "#22DA6E",
        "brightPurple": "#C792EA",
        "brightRed": "#EF5350",
        "brightWhite": "#FFFFFF",
        "brightYellow": "#FFEB95",
    }

    if not any(isinstance(s, dict) and s.get("name") == "Night Owl" for s in schemes):
        schemes.append(night_owl)

    defaults["colorScheme"] = "Night Owl"
    defaults["font"] = {"face": "JetBrainsMono Nerd Font", "size": 12.0}
    defaults["opacity"] = 90
    defaults["elevate"] = True
    defaults["selectionBackground"] = "#FFFF00"

    try:
        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return TaskResult(
            ok=False, summary="write Windows Terminal settings: failed", details=str(e)
        )

    return TaskResult(ok=True, summary="Windows Terminal UI defaults applied")


def download_glazewm_config() -> TaskResult:
    userprofile = os.environ.get("USERPROFILE")
    if not userprofile:
        return TaskResult(ok=False, summary="USERPROFILE not set")

    dest_dir = Path(userprofile) / ".glzr" / "glazewm"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / "config.yaml"

    url = "https://raw.githubusercontent.com/AmineDjeghri/personal-os-setup/main/docs/windows_workflow/win_dotfiles/.glzr/glazewm/config.yaml"

    try:
        with urlopen(url) as resp:  # noqa: S310
            content = resp.read()
        dest.write_bytes(content)
    except Exception as e:  # noqa: BLE001
        return TaskResult(ok=False, summary="download GlazeWM config: failed", details=str(e))

    return TaskResult(ok=True, summary="GlazeWM config installed", details=str(dest))

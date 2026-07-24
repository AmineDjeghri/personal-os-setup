from __future__ import annotations

import json
import uuid

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.system.windows_tasks import _windows_terminal_settings_path
from personal_os_setup.tasks.task import TaskResult


def wsl_install(value: str) -> TaskResult:
    parts = [p.strip() for p in (value or "").split("|") if p.strip()]
    distro = parts[0] if parts else ""
    options = parts[1:] if parts else []

    location: str | None = None
    flags: set[str] = set()
    for opt in options:
        if "=" in opt:
            k, v = [x.strip() for x in opt.split("=", 1)]
            if k.lower() == "location":
                location = v
        else:
            flags.add(opt.lower())

    argv: list[str] = ["wsl.exe", "--install"]
    if distro:
        argv += ["--distribution", distro]
    # Default behavior: don't auto-launch the distro after install.
    argv.append("--no-launch")
    if location:
        argv += ["--location", location]

    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary=f"wsl --install {distro}".strip(), details=details)
    return TaskResult(ok=False, summary=f"wsl --install {distro} failed".strip(), details=details)


def wsl_list_online() -> TaskResult:
    res = run(["wsl.exe", "--list", "--online"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="wsl --list --online", details=details)
    return TaskResult(ok=False, summary="wsl --list --online failed", details=details)


def wsl_list_verbose() -> TaskResult:
    res = run(["wsl.exe", "--list", "--verbose"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="wsl --list --verbose", details=details)
    return TaskResult(ok=False, summary="wsl --list --verbose failed", details=details)


def wsl_update() -> TaskResult:
    res = run(["wsl.exe", "--update"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="wsl --update", details=details)
    return TaskResult(ok=False, summary="wsl --update failed", details=details)


def wsl_version() -> TaskResult:
    res = run(["wsl.exe", "--version"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="wsl --version", details=details)
    return TaskResult(ok=False, summary="wsl --version failed", details=details)


def wsl_shutdown() -> TaskResult:
    res = run(["wsl.exe", "--shutdown"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="wsl --shutdown", details=details)
    return TaskResult(ok=False, summary="wsl --shutdown failed", details=details)


def _parse_two_fields(value: str, *, sep: str = "|") -> tuple[str, str] | None:
    parts = [p.strip() for p in (value or "").split(sep, 1)]
    if len(parts) != 2:
        return None
    if not parts[0] or not parts[1]:
        return None
    return parts[0], parts[1]


def wsl_unregister(distribution: str) -> TaskResult:
    distribution = (distribution or "").strip()
    if not distribution:
        return TaskResult(ok=False, summary="wsl --unregister: missing distribution name")
    res = run(["wsl.exe", "--unregister", distribution], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary=f"wsl --unregister {distribution}", details=details)
    return TaskResult(ok=False, summary=f"wsl --unregister {distribution} failed", details=details)


def wsl_export(value: str) -> TaskResult:
    parsed = _parse_two_fields(value)
    if parsed is None:
        return TaskResult(
            ok=False,
            summary="wsl --export: invalid input",
            details="Expected format: <DistributionName>|<FileName>, e.g. Ubuntu|C:\\Temp\\ubuntu.tar",
        )
    distro, filename = parsed
    res = run(["wsl.exe", "--export", distro, filename], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary=f"wsl --export {distro}", details=details)
    return TaskResult(ok=False, summary=f"wsl --export {distro} failed", details=details)


def wsl_import(value: str) -> TaskResult:
    parts = [p.strip() for p in (value or "").split("|")]
    if len(parts) < 3 or not parts[0] or not parts[1] or not parts[2]:
        return TaskResult(
            ok=False,
            summary="wsl --import: invalid input",
            details=(
                "Expected format: <DistributionName>|<InstallLocation>|<FileName>, "
                "e.g. Ubuntu|D:\\WSL\\Ubuntu|C:\\Temp\\ubuntu.tar"
            ),
        )

    distro, install_location, filename = parts[0], parts[1], parts[2]
    argv = ["wsl.exe", "--import", distro, install_location, filename]
    if len(parts) >= 4 and parts[3]:
        argv += ["--version", parts[3]]
    res = run(argv, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary=f"wsl --import {distro}", details=details)
    return TaskResult(ok=False, summary=f"wsl --import {distro} failed", details=details)


def wsl_move(value: str) -> TaskResult:
    parsed = _parse_two_fields(value)
    if parsed is None:
        return TaskResult(
            ok=False,
            summary="wsl --manage --move: invalid input",
            details="Expected format: <DistributionName>|<NewLocation>, e.g. Ubuntu|D:\\WSL\\Ubuntu",
        )
    distro, new_location = parsed

    manage_res = run(["wsl.exe", "--manage", distro, "--move", new_location], check=False)
    manage_details = (manage_res.stdout + "\n" + manage_res.stderr).strip()
    if manage_res.returncode == 0:
        return TaskResult(ok=True, summary=f"wsl --manage {distro} --move", details=manage_details)
    return TaskResult(
        ok=False, summary=f"wsl --manage {distro} --move failed", details=manage_details
    )


def add_windows_terminal_ubuntu_profile() -> TaskResult:
    # First, ensure WSL is available and an Ubuntu distro is installed.
    wsl_res = run(["wsl.exe", "--list", "--verbose"], check=False)
    details = (wsl_res.stdout + "\n" + wsl_res.stderr).strip()
    if wsl_res.returncode != 0:
        return TaskResult(
            ok=False,
            summary="WSL not available (wsl --list --verbose failed)",
            details=details,
        )

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

    profiles = (data.get("profiles") or {}).get("list")
    if not isinstance(profiles, list):
        return TaskResult(ok=False, summary="Windows Terminal settings: profiles.list missing")

    # Always create a new Ubuntu profile with a fresh GUID
    profiles.append(
        {
            "name": "Ubuntu",
            "guid": "{" + str(uuid.uuid4()) + "}",
            "startingDirectory": "~",
            "commandline": "ubuntu run",
            "icon": "https://assets.ubuntu.com/v1/49a1a858-favicon-32x32.png",
        }
    )

    try:
        settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        return TaskResult(
            ok=False, summary="write Windows Terminal settings: failed", details=str(e)
        )

    return TaskResult(ok=True, summary="Windows Terminal: Ubuntu profile applied")

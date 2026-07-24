from __future__ import annotations

import platform
from importlib import resources
from pathlib import Path
from typing import Iterable, Any

import yaml
from pydantic import BaseModel, ConfigDict


class OSInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    family: str
    distro: str
    info: str | None = None


class PackageCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]

    def for_distro(self, distro: str) -> dict[str, Any]:
        packages = self.data.get("packages", {})
        distro_block = packages.get(distro, {})
        if not isinstance(distro_block, dict):
            return {}
        return distro_block


class PackageRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    manager: str
    category: str


def _is_wsl() -> bool:
    if Path("/proc/sys/fs/binfmt_misc/WSLInterop").exists():
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except Exception:  # noqa: BLE001
        return False


def detect_os(
    *,
    system: str | None = None,
    os_release_path: Path | None = None,
    is_wsl: bool | None = None,
) -> OSInfo:
    """Detect the current OS/distro.

    The keyword-only overrides let tests exercise this function for real
    (real filesystem paths, no mocking) against a Linux distro other than
    the one actually running the test suite.
    """
    system = (system or platform.system()).lower()
    if system == "windows":
        return OSInfo(family="windows", distro="windows")
    if system == "darwin":
        return OSInfo(family="darwin", distro="darwin")
    if system == "linux":
        os_release = os_release_path or Path("/etc/os-release")
        if not os_release.exists():
            distro = "linux"
        else:
            data: dict[str, str] = {}
            for line in os_release.read_text(encoding="utf-8").splitlines():
                if not line or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip().strip('"')

            distro = data.get("ID", "linux").lower()
        wsl = _is_wsl() if is_wsl is None else is_wsl
        return OSInfo(family=system, distro=distro, info="OS running inside WSL" if wsl else None)
    return OSInfo(family="unknown", distro="unknown")


def iter_packages(distro_block: dict) -> Iterable[PackageRef]:
    for manager, categories in distro_block.items():
        if not isinstance(categories, dict):
            continue
        for category, items in categories.items():
            if not isinstance(items, list):
                continue
            for name in items:
                if not isinstance(name, str) or not name.strip():
                    continue
                yield PackageRef(name=name.strip(), manager=str(manager), category=str(category))


def build_packages_for_os() -> tuple[str, str, str | None, list[PackageRef]]:
    """Detect OS/distro and return the filtered package list for that distro."""
    os_info = detect_os()
    system = os_info.family
    distro = os_info.distro
    info = os_info.info
    pkg = resources.files("personal_os_setup")
    data = yaml.safe_load((pkg / "config" / "packages.yaml").read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        data = {}
    catalog = PackageCatalog(data=data)

    distro_block = catalog.for_distro(distro)
    packages = list(iter_packages(distro_block))
    return system, distro, info, packages

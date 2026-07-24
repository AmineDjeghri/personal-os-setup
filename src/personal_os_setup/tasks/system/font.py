from __future__ import annotations

import os
import platform
import shutil
import tempfile
import zipfile
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from personal_os_setup.detect_os import _is_wsl

from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.task import TaskResult


def _packaged_font_zip() -> Traversable:
    pkg = resources.files("personal_os_setup")
    candidates = [
        pkg / "config" / "JetBrainsMonoNerdFont-Regular.zip",
        pkg / "config" / "unix" / "JetBrainsMonoNerdFont-Regular.zip",
    ]
    for p in candidates:
        try:
            if p.is_file():
                return p
        except Exception:  # noqa: BLE001
            continue
    raise FileNotFoundError("Packaged font zip not found: JetBrainsMonoNerdFont-Regular.zip")


def _extract_font_files(*, zip_res: Traversable, dest_dir: Path) -> list[Path]:
    extracted: list[Path] = []
    with zip_res.open("rb") as fp:
        with zipfile.ZipFile(fp) as zf:
            for name in zf.namelist():
                lower = name.lower()
                if lower.endswith("/"):
                    continue
                if not (lower.endswith(".ttf") or lower.endswith(".otf")):
                    continue
                target = dest_dir / Path(name).name
                target.write_bytes(zf.read(name))
                extracted.append(target)
    return extracted


def install_jetbrainsmono_nerd_font() -> TaskResult:
    system = platform.system().lower()

    try:
        zip_res = _packaged_font_zip()
    except Exception as e:  # noqa: BLE001
        return TaskResult(ok=False, summary="locate packaged font zip: failed", details=str(e))

    if system == "linux":
        if _is_wsl():
            return TaskResult(
                ok=False,
                summary="You are running WSL, JetBrainsMono Nerd Font should be installed on Windows.",
            )
        dest_dir = Path.home() / ".local" / "share" / "fonts" / "JetBrainsMonoNerdFont"
        dest_dir.mkdir(parents=True, exist_ok=True)

        already = list(dest_dir.glob("*.ttf")) + list(dest_dir.glob("*.otf"))
        if already:
            return TaskResult(
                ok=True, summary="JetBrainsMono Nerd Font already installed", details=str(dest_dir)
            )

        try:
            extracted = _extract_font_files(zip_res=zip_res, dest_dir=dest_dir)
        except Exception as e:  # noqa: BLE001
            return TaskResult(ok=False, summary="extract fonts: failed", details=str(e))

        actions: list[str] = [f"installed {len(extracted)} font files", str(dest_dir)]

        if shutil.which("fc-cache") is not None:
            res = run(["fc-cache", "-f", str(dest_dir)], check=False)
            details = (res.stdout + "\n" + res.stderr).strip()
            actions.append("ran: fc-cache -f")
            if details:
                actions.append(details)

        return TaskResult(
            ok=True, summary="JetBrainsMono Nerd Font installed", details="\n".join(actions).strip()
        )

    if system == "windows":
        localappdata = os.environ.get("LOCALAPPDATA")
        if not localappdata:
            return TaskResult(ok=False, summary="LOCALAPPDATA not set")

        dest_dir = Path(localappdata) / "Microsoft" / "Windows" / "Fonts"
        dest_dir.mkdir(parents=True, exist_ok=True)

        actions: list[str] = [str(dest_dir)]

        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                extracted = _extract_font_files(zip_res=zip_res, dest_dir=tmp_dir)
                if not extracted:
                    return TaskResult(ok=False, summary="no font files found in zip")

                copied: list[Path] = []
                for font_file in extracted:
                    target = dest_dir / font_file.name
                    if not target.exists():
                        shutil.copy2(font_file, target)
                        copied.append(target)

                actions.append(f"copied {len(copied)} font files")

                try:
                    import winreg  # type: ignore

                    key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
                    ) as key:
                        for p in copied:
                            value_name = f"{p.stem} (TrueType)"
                            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, p.name)
                    actions.append("registered fonts in HKCU")
                except Exception as e:  # noqa: BLE001
                    actions.append("font registry update failed")
                    actions.append(str(e))

                try:
                    import ctypes

                    for p in copied:
                        ctypes.windll.gdi32.AddFontResourceW(str(p))
                    ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
                except Exception:  # noqa: BLE001
                    pass

        except Exception as e:  # noqa: BLE001
            return TaskResult(ok=False, summary="install fonts: failed", details=str(e))

        return TaskResult(
            ok=True, summary="JetBrainsMono Nerd Font installed", details="\n".join(actions).strip()
        )

    if system == "darwin":
        dest_dir = Path.home() / "Library" / "Fonts"
        dest_dir.mkdir(parents=True, exist_ok=True)

        already = list(dest_dir.glob("JetBrainsMono*"))
        if already:
            return TaskResult(
                ok=True, summary="JetBrainsMono Nerd Font already installed", details=str(dest_dir)
            )

        actions: list[str] = [str(dest_dir)]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                extracted = _extract_font_files(zip_res=zip_res, dest_dir=tmp_dir)
                if not extracted:
                    return TaskResult(ok=False, summary="no font files found in zip")

                copied: list[Path] = []
                for font_file in extracted:
                    target = dest_dir / font_file.name
                    if not target.exists():
                        shutil.copy2(font_file, target)
                        copied.append(target)
                actions.append(f"copied {len(copied)} font files")
                actions.append("Restart terminal apps to pick up the new font")
        except Exception as e:  # noqa: BLE001
            return TaskResult(ok=False, summary="install fonts: failed", details=str(e))

        return TaskResult(
            ok=True, summary="JetBrainsMono Nerd Font installed", details="\n".join(actions).strip()
        )

    return TaskResult(ok=False, summary=f"Unsupported OS for font install: {system}")

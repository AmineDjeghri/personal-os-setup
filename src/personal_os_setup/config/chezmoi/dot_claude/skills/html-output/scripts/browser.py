"""Find a Chromium-based browser for headless PDF/PNG rendering on Linux, macOS and Windows."""

import os
from pathlib import Path
import shutil


# Names resolved on PATH (Linux, and anything the user put on PATH elsewhere).
PATH_NAMES = (
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "microsoft-edge",
    "microsoft-edge-stable", "brave", "brave-browser", "helium", "helium-browser", "vivaldi",
    "vivaldi-stable", "opera", "thorium-browser", "ungoogled-chromium", "chrome", "msedge",
)
# macOS apps are not on PATH.
MACOS_APPS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Helium.app/Contents/MacOS/Helium",
    "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",
)
# Windows installs are not on PATH either: per-machine under Program Files, per-user under LOCALAPPDATA.
WINDOWS_ROOTS = ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
WINDOWS_APPS = (
    r"Google\Chrome\Application\chrome.exe",
    r"Microsoft\Edge\Application\msedge.exe",  # shipped with Windows 10/11
    r"BraveSoftware\Brave-Browser\Application\brave.exe",
    r"Chromium\Application\chrome.exe",
    r"Vivaldi\Application\vivaldi.exe",
)
NAME_HINTS = ("chrom", "helium", "brave", "edge", "vivaldi", "opera", "thorium")
NOT_BROWSERS = ("chromedriver", "chrome-gnome-shell", "chrome-remote", "crashpad")


def _windows_apps():
    for root in WINDOWS_ROOTS:
        base = os.environ.get(root)
        if base:
            for app in WINDOWS_APPS:
                yield str(Path(base) / app)


def _scan_path():
    """Executables on PATH whose name looks like a Chromium-based browser (last resort)."""
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            low = name.lower()
            full = os.path.join(folder, name)
            if (
                any(hint in low for hint in NAME_HINTS)
                and not any(bad in low for bad in NOT_BROWSERS)
                and os.access(full, os.X_OK)
                and not os.path.isdir(full)
            ):
                yield full


def find_browser(explicit=None):
    """Return a browser path: explicit, CHROME_BIN, PATH names, macOS apps, Windows installs, PATH scan."""
    candidates = [explicit] if explicit else [os.environ.get("CHROME_BIN"), *PATH_NAMES, *MACOS_APPS, *_windows_apps()]
    for candidate in filter(None, candidates):
        found = shutil.which(candidate) or (candidate if Path(candidate).is_file() else None)
        if found:
            return found
    if not explicit:
        for found in _scan_path():
            print(f"browser: {found} (found by scanning PATH)")
            return found
    raise SystemExit(
        "No Chromium-based browser found (Chrome, Edge, Brave, Chromium, Helium, Vivaldi...). "
        "Pass --browser /path/to/browser or set CHROME_BIN. Find one with "
        "`ls /usr/bin /opt | grep -i -E 'chrom|helium|brave|edge|vivaldi'` or `flatpak list` (Linux), "
        "`ls /Applications` (macOS), or `where /r \"%ProgramFiles%\" msedge.exe` (Windows)."
    )

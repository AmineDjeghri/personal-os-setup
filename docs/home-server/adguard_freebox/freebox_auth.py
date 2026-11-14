#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///

"""Register an app on the Freebox and save its token in a config file.

The Freebox asks for a physical button press on the box. Each app id gets its own token, so each job
registers once and keeps its own config file. The file gets ``freebox_url``, ``app_id`` and
``app_token``; other keys already in it are kept.

Use the router's LAN address as ``--url``, so the jobs do not depend on DNS (AdGuard Home is the DNS).

Usage:
    freebox_auth.py fr.homeassistant.adguard_sync ~/.config/adguard-sync/config.yaml --url URL
    freebox_auth.py fr.homeassistant.stale_devices ~/.config/stale-devices/config.yaml --url URL
"""

import argparse
import os
import socket
import sys
import time
from pathlib import Path

import requests
import yaml

REQUEST_TIMEOUT = 5  # seconds
MAX_WAIT_ATTEMPTS = 120  # ~2 minutes of polling for the physical button press


def save_config(path: Path, values: dict) -> None:
    """Merge ``values`` into the YAML config file, readable by the owner only.

    The file is created with mode 600 from the start, so the token is never world-readable, and the
    other keys already in the file are kept.

    Args:
        path: Config file to create or update.
        values: Keys to set.
    """
    saved = (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}
    saved.update(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(yaml.safe_dump(saved, sort_keys=False))
    path.chmod(0o600)


def register(base: str, app_id: str, app_name: str, device_name: str, config: Path) -> int:
    """Ask the Freebox for a token, wait for the button press and save the token.

    Args:
        base: Freebox URL, for example ``http://192.168.1.254``.
        app_id: Unique id of the app.
        app_name: Name shown in the Freebox app list.
        device_name: Name of the machine the app runs on, shown in the same list.
        config: Config file that receives ``freebox_url``, ``app_id`` and ``app_token``.

    Returns:
        Exit code: 0 when the token was granted and saved, 1 otherwise.
    """
    payload = {
        "app_id": app_id,
        "app_name": app_name,
        "app_version": "1.0.0",
        "device_name": device_name,
    }
    try:
        resp = requests.post(
            f"{base}/api/v4/login/authorize/", json=payload, timeout=REQUEST_TIMEOUT
        ).json()
    except (requests.RequestException, ValueError) as exc:
        print(f"Connection failed: {exc}")
        return 1
    if not resp.get("success"):
        print(f"Error: {resp}")
        return 1
    app_token = resp["result"]["app_token"]
    track_id = resp["result"]["track_id"]

    print(
        ">>> Press the RIGHT ARROW button on the Freebox server now (waiting up to 2 minutes) <<<"
    )
    status = "pending"
    for _ in range(MAX_WAIT_ATTEMPTS):
        time.sleep(1)
        try:
            status = requests.get(
                f"{base}/api/v4/login/authorize/{track_id}", timeout=REQUEST_TIMEOUT
            ).json()["result"]["status"]
        except (requests.RequestException, ValueError, KeyError) as exc:
            print(f"Lost the Freebox while waiting for the button: {exc}")
            return 1
        if status != "pending":
            break

    if status != "granted":
        reason = "no button press detected" if status == "pending" else f"status {status}"
        print(f"Not authorized ({reason}). Run it again when you are ready to press the button.")
        return 1
    save_config(config, {"freebox_url": base, "app_id": app_id, "app_token": app_token})
    print(f"Token saved in {config} (mode 600).")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and register the app.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code from :func:`register`.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app_id", help="unique id of the app, e.g. fr.homeassistant.stale_devices")
    parser.add_argument("config", type=Path, help="YAML config file that receives the token")
    parser.add_argument("--url", required=True, help="Freebox LAN URL, e.g. http://192.168.1.254")
    parser.add_argument("--app-name", help="name in the Freebox app list (default: the app id)")
    parser.add_argument("--device-name", default=socket.gethostname())
    args = parser.parse_args(argv)
    return register(
        args.url.rstrip("/"),
        args.app_id,
        args.app_name or args.app_id,
        args.device_name,
        args.config,
    )


if __name__ == "__main__":
    sys.exit(main())

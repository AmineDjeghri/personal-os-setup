#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
# ]
# ///

"""Register an app on the Freebox and print its token.

The Freebox asks for a physical button press on the box. Run it once per app: an app id gets one token.

Usage:
    freebox_auth.py                                  # the AdGuard sync app
    freebox_auth.py --app-id fr.me.other --app-name "Other app"
"""

import argparse
import socket
import sys
import time

import requests

REQUEST_TIMEOUT = 5  # seconds
MAX_WAIT_ATTEMPTS = 120  # ~2 minutes of polling for the physical button press


def register(base: str, app_id: str, app_name: str, device_name: str) -> int:
    """Ask the Freebox for a token, wait for the button press and print the token.

    Args:
        base: Freebox URL, for example ``http://mafreebox.freebox.fr``.
        app_id: Unique id of the app.
        app_name: Name shown in the Freebox app list.
        device_name: Name of the machine the app runs on, shown in the same list.

    Returns:
        Exit code: 0 when the token was granted, 1 otherwise.
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

    print("\n" + "=" * 50)
    print(">>> GO PRESS THE 'RIGHT ARROW' BUTTON ON YOUR FREEBOX SERVER NOW! <<<")
    print("=" * 50 + "\n")

    status = "pending"
    for _ in range(MAX_WAIT_ATTEMPTS):
        time.sleep(1)
        try:
            status = requests.get(
                f"{base}/api/v4/login/authorize/{track_id}", timeout=REQUEST_TIMEOUT
            ).json()["result"]["status"]
        except requests.RequestException as exc:
            print(f"Connection failed while waiting for authorization: {exc}")
            return 1
        except (ValueError, KeyError) as exc:
            print(f"Unexpected reply while waiting for authorization: {exc}")
            return 1
        if status != "pending":
            break

    if status == "granted":
        print("SUCCESS! Here is the app token. KEEP IT SAFE:")
        print("-" * 60)
        print(app_token)
        print("-" * 60)
        print("Put it in the app_token key of the script's config file.")
        return 0
    if status == "pending":
        print(
            f"Timed out after {MAX_WAIT_ATTEMPTS}s: no button press detected. "
            "Run the script again when you are ready to press it."
        )
    else:
        print(f"Authorization denied. Status: {status}")
    return 1


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments and register the app.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code from :func:`register`.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://mafreebox.freebox.fr", help="Freebox URL")
    parser.add_argument("--app-id", default="fr.homeassistant.adguard_sync")
    parser.add_argument("--app-name", default="AdGuard Sync")
    parser.add_argument("--device-name", default=socket.gethostname())
    args = parser.parse_args(argv)
    return register(args.url.rstrip("/"), args.app_id, args.app_name, args.device_name)


if __name__ == "__main__":
    sys.exit(main())

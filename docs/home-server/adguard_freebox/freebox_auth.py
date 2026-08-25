#!/home/amine/.local/bin/uv run
# /// script
# dependencies = [
#   "requests",
# ]
# ///

"""Get the app token from the Freebox API."""

import requests
import time

FREEBOX_URL = "http://mafreebox.freebox.fr"


def register():
    # 1. Request Authorization
    payload = {
        "app_id": "fr.homeassistant.adguard_sync",
        "app_name": "AdGuard Sync",
        "app_version": "1.0.0",
        "device_name": "Home Assistant",
    }

    try:
        r = requests.post(f"{FREEBOX_URL}/api/v4/login/authorize/", json=payload)
        resp = r.json()
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    if not resp.get("success"):
        print(f"Error: {resp}")
        return

    app_token = resp["result"]["app_token"]
    track_id = resp["result"]["track_id"]

    print("\n" + "=" * 50)
    print(">>> GO PRESS THE 'RIGHT ARROW' BUTTON ON YOUR FREEBOX SERVER NOW! <<<")
    print("=" * 50 + "\n")

    # 2. Wait for user to press the button
    status = "pending"
    while status == "pending":
        time.sleep(1)
        r = requests.get(f"{FREEBOX_URL}/api/v4/login/authorize/{track_id}")
        status = r.json()["result"]["status"]

    if status == "granted":
        print("\nSUCCESS! Here is your App Token. KEEP IT SAFE:")
        print("-" * 60)
        print(app_token)
        print("-" * 60)
        print("Copy this token into the main script configuration.")
    else:
        print(f"\nAuthorization denied or timed out. Status: {status}")


if __name__ == "__main__":
    register()

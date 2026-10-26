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
REQUEST_TIMEOUT = 5  # seconds; same value the sibling sync script uses for AdGuard
MAX_WAIT_ATTEMPTS = 120  # ~2 minutes of polling for the physical button press


def register():
    # 1. Request Authorization
    payload = {
        "app_id": "fr.homeassistant.adguard_sync",
        "app_name": "AdGuard Sync",
        "app_version": "1.0.0",
        "device_name": "Home Assistant",
    }

    try:
        r = requests.post(
            f"{FREEBOX_URL}/api/v4/login/authorize/",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
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

    # 2. Wait for user to press the button (bounded: ~2 minutes)
    status = "pending"
    for _ in range(MAX_WAIT_ATTEMPTS):
        time.sleep(1)
        try:
            r = requests.get(
                f"{FREEBOX_URL}/api/v4/login/authorize/{track_id}",
                timeout=REQUEST_TIMEOUT,
            )
            status = r.json()["result"]["status"]
        except requests.RequestException as e:
            print(f"Connection failed while waiting for authorization: {e}")
            return
        except (ValueError, KeyError) as e:
            print(f"Unexpected reply while waiting for authorization: {e}")
            return
        if status != "pending":
            break

    if status == "granted":
        print("\nSUCCESS! Here is your App Token. KEEP IT SAFE:")
        print("-" * 60)
        print(app_token)
        print("-" * 60)
        print("Copy this token into the main script configuration.")
    elif status == "pending":
        print(
            f"\nTimed out after {MAX_WAIT_ATTEMPTS}s: no button press detected. "
            "Run the script again when you are ready to press it."
        )
    else:
        print(f"\nAuthorization denied. Status: {status}")


if __name__ == "__main__":
    register()

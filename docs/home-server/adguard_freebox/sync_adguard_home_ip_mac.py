#!/home/amine/.local/bin/uv run
# /// script
# dependencies = [
#   "requests",
# ]
# ///

"""Sync AdGuard Home clients with Freebox devices."""

from datetime import datetime

import requests
import hmac
import hashlib

# --- CONFIGURATION ---
# AdGuard Home Config
# Try first the creds in the browser before using them here.
AGH_URL = "http://<HAOS_IP>:8082"  # Direct AdGuard port, not through Ingress
AGH_USER = "adguard"  # C (if adguard is in home assistant create a user , you need to uncheck 'local access' only in Home Assistant
AGH_PASS = "PASSWORD"

# Freebox Config
FBX_URL = "http://mafreebox.freebox.fr"
FBX_APP_ID = "fr.homeassistant.adguard_sync"
# The token you just generated with freebox_auth.py
FBX_APP_TOKEN = "AUTH_TOKEN"


# ---------------------


def fbx_login():
    """Authenticates with Freebox using the Challenge-Response mechanism.

    Returns: session_token (str) or None
    """
    try:
        # 1. Get the Challenge
        r = requests.get(f"{FBX_URL}/api/v4/login/")
        if r.status_code != 200:
            print(f"Failed to reach Freebox login: {r.status_code}")
            return None

        challenge = r.json()["result"]["challenge"]

        # 2. specific HMAC-SHA1 encryption of the challenge using your Token
        password = hmac.new(
            FBX_APP_TOKEN.encode("utf-8"), challenge.encode("utf-8"), hashlib.sha1
        ).hexdigest()

        # 3. Open the Session
        payload = {"app_id": FBX_APP_ID, "password": password}
        r = requests.post(f"{FBX_URL}/api/v4/login/session/", json=payload)
        resp = r.json()

        if resp.get("success"):
            return resp["result"]["session_token"]
        else:
            print(f"Freebox Login Failed: {resp}")
            return None
    except Exception as e:
        print(f"Freebox connection error: {e}")
        return None


def get_fbx_devices(session_token):
    """Fetch all devices from Freebox LAN Browser."""
    headers = {"X-Fbx-App-Auth": session_token}
    try:
        # 'lan/browser/pub' is the endpoint that lists all networked devices
        r = requests.get(f"{FBX_URL}/api/v4/lan/browser/pub", headers=headers)
        if not r.json().get("success"):
            print("Failed to get LAN list")
            return []
        return r.json()["result"]
    except Exception as e:
        print(f"Error fetching devices: {e}")
        return []


def test_agh_connection():
    """Test connection to AdGuard Home before syncing."""
    try:
        print("Testing AdGuard Home connection...")
        r = requests.get(f"{AGH_URL}/control/status", auth=(AGH_USER, AGH_PASS), timeout=5)
        if r.status_code == 200:
            print(f"✓ AdGuard Home connected successfully")
            return True
        else:
            print(f"✗ AdGuard Home returned status {r.status_code}")
            print(f"  Response: {r.text[:200]}")
            return False
    except requests.exceptions.ConnectionError as e:
        print(f"✗ Cannot connect to AdGuard Home at {AGH_URL}")
        print(f"  Error: {e}")
        return False
    except requests.exceptions.Timeout:
        print(f"✗ AdGuard Home connection timed out at {AGH_URL}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error testing AdGuard connection: {e}")
        return False


def get_agh_clients():
    """Fetch existing AdGuard clients to preserve settings."""
    try:
        r = requests.get(f"{AGH_URL}/control/clients", auth=(AGH_USER, AGH_PASS), timeout=5)
        if r.status_code != 200:
            print(f"Warning: Failed to fetch clients from AdGuard (status {r.status_code})")
            return {}
        # Map existing clients by MAC address and by name
        client_map_by_mac = {}
        client_map_by_name = {}
        clients = r.json().get("clients", [])
        for c in clients:
            # Map by MAC address
            for ident in c["ids"]:
                if ":" in ident and len(ident) == 17:  # Simple MAC check
                    client_map_by_mac[ident.lower()] = c
            # Map by client name
            client_map_by_name[c.get("name", "").lower()] = c
        return {"by_mac": client_map_by_mac, "by_name": client_map_by_name}
    except Exception as e:
        print(f"Error fetching AdGuard clients: {e}")
        return {"by_mac": {}, "by_name": {}}


def sync():
    print("--- Starting Sync via Freebox API ---")

    # 0. Test AdGuard connection first
    if not test_agh_connection():
        print("ERROR: Cannot proceed without AdGuard connection. Check configuration:")
        print(f"  AGH_URL: {AGH_URL}")
        print(f"  AGH_USER: {AGH_USER}")
        print("  Make sure credentials are correct and AdGuard is accessible.")
        return

    # 1. Login to Freebox
    token = fbx_login()
    if not token:
        return

    # 2. Get Data
    print("Fetching devices from Freebox...")
    fbx_devices = get_fbx_devices(token)

    # 3. Get Current AdGuard State
    agh_clients = get_agh_clients()
    agh_by_mac = agh_clients.get("by_mac", {})
    agh_by_name = agh_clients.get("by_name", {})

    synced_count = 0
    skipped_count = 0

    for dev in fbx_devices:
        # We only care about devices with a MAC address
        if "l2ident" not in dev or dev["l2ident"]["type"] != "mac_address":
            dev_name = dev.get("primary_name") or dev.get("default_name") or "Unknown"
            l2_info = dev.get("l2ident", {})
            print(f"Skipping '{dev_name}' - No MAC address (l2ident: {l2_info})")
            skipped_count += 1
            continue

        mac = dev["l2ident"]["id"].lower()

        # Determine the best name: User-set name > Hostname > MAC
        name = dev.get("primary_name") or dev.get("default_name") or mac

        # Try to find existing client by MAC first, then by name
        existing_client = agh_by_mac.get(mac) or agh_by_name.get(name.lower())

        # --- Collect IPs ---
        # The Freebox 'l3connectivities' list contains ALL IPs (IPv4, IPv6 Global, IPv6 Link-Local)
        ip_list = set()
        ip_list.add(mac)  # Always add MAC as an ID

        if "l3connectivities" in dev:
            for conn in dev["l3connectivities"]:
                # We specifically want IPv6 global (2a01...) and link-local (fe80...)
                # We add all addresses including unreachable ones to track offline devices
                ip_list.add(conn["addr"])

        final_ids = list(ip_list)

        # --- Sync to AdGuard ---
        if existing_client:
            # UPDATE EXISTING
            current_ids = set(existing_client["ids"])

            # Replace IPs with current list from Freebox (removes stale IPs)
            if set(final_ids) != current_ids:
                print(f"Updating '{name}' - Syncing IPs")
                new_ids = final_ids

                payload = {
                    "name": existing_client["name"],  # Identifying name
                    "data": {
                        "name": existing_client["name"],  # Required field
                        "ids": new_ids,
                        "use_global_settings": True,
                        "filtering_enabled": existing_client.get("filtering_enabled", True),
                        "parental_enabled": existing_client.get("parental_enabled", False),
                        "safesearch_enabled": existing_client.get("safesearch_enabled", False),
                        "safebrowsing_enabled": existing_client.get("safebrowsing_enabled", False),
                        "tags": existing_client.get("tags", []),
                    },
                }
                try:
                    requests.post(
                        f"{AGH_URL}/control/clients/update", auth=(AGH_USER, AGH_PASS), json=payload
                    )
                    synced_count += 1
                except Exception as e:
                    print(f"Failed to update {name}: {e}")
        else:
            # CREATE NEW
            print(f"Creating new client: '{name}'")
            payload = {"name": name, "ids": final_ids, "use_global_settings": True}
            try:
                r = requests.post(
                    f"{AGH_URL}/control/clients/add", auth=(AGH_USER, AGH_PASS), json=payload
                )
                synced_count += 1
            except Exception as e:
                print(f"Failed to create {name}: {e}")

    print(
        f"Sync Complete. Updated/Created {synced_count} devices, Skipped {skipped_count} devices. Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )


if __name__ == "__main__":
    sync()

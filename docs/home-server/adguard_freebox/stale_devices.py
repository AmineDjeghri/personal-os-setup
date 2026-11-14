#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///

"""List Freebox devices that have been unreachable for N days.

Meant for a weekly Hermes cron job with ``--no-agent``: stdout is the message, an empty stdout is a silent
run. It never changes anything on the Freebox or in Home Assistant, it only tells you what to clean up.

Usage:
    stale_devices.py --auth          # once: press the Freebox button, the token is saved in the config
    stale_devices.py                 # print the message (nothing when no device is stale)
    stale_devices.py --doctor        # check login, API fields and show what would be reported
    stale_devices.py --list          # like the default, without the message length cap
"""

import argparse
import hashlib
import hmac
import json
import socket
import sys
import time
from pathlib import Path

import requests
import yaml

DEFAULT_CONFIG = Path.home() / ".config" / "stale-devices" / "config.yaml"
DEFAULTS = {
    "freebox_url": "http://192.168.1.254",
    "app_id": "fr.homeassistant.stale_devices",
    "app_token": "",
    "threshold_days": 14,
    "ignore_macs": [],
}
REQUEST_TIMEOUT = 5  # seconds
AUTH_MAX_WAIT = 120  # seconds to wait for the button press
MAX_MESSAGE_CHARS = 3500  # stays under Telegram's 4096-character limit
DAY = 86400

CLEANUP_STEPS = """\
Clean up, in this order:
1. Forget the device in the Freebox web interface: Periphériques réseau (http://mafreebox.freebox.fr/).
2. In Home Assistant, reload the Freebox integration: Settings > Devices & services > Freebox > ... > Reload.
3. Remove the leftover entities: Settings > Devices & services > Entities, search the device name,
   select it, Remove selected.
To keep a device off this list, add its MAC address to ignore_macs in the config file."""


def load_config(path: Path) -> dict:
    """Read the YAML config and fill in the defaults.

    Args:
        path: Location of the config file.

    Returns:
        The configuration with defaults applied and MAC addresses lower-cased.
    """
    cfg = dict(DEFAULTS)
    if path.exists():
        cfg.update(yaml.safe_load(path.read_text()) or {})
    cfg["ignore_macs"] = {str(m).lower() for m in (cfg.get("ignore_macs") or [])}
    return cfg


def fbx_login(cfg: dict) -> str:
    """Open a Freebox session with the challenge-response login.

    Args:
        cfg: Configuration with ``freebox_url``, ``app_id`` and ``app_token``.

    Returns:
        The session token.

    Raises:
        RuntimeError: If the Freebox is unreachable or refuses the login.
    """
    base = cfg["freebox_url"].rstrip("/")
    if not cfg["app_token"]:
        raise RuntimeError("app_token is empty in the config file")
    try:
        challenge = requests.get(f"{base}/api/v4/login/", timeout=REQUEST_TIMEOUT).json()["result"][
            "challenge"
        ]
        password = hmac.new(cfg["app_token"].encode(), challenge.encode(), hashlib.sha1).hexdigest()
        resp = requests.post(
            f"{base}/api/v4/login/session/",
            json={"app_id": cfg["app_id"], "password": password},
            timeout=REQUEST_TIMEOUT,
        ).json()
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise RuntimeError(f"cannot reach the Freebox at {base}: {exc}") from exc
    if not resp.get("success"):
        raise RuntimeError(f"Freebox login refused: {resp.get('msg', resp)}")
    return resp["result"]["session_token"]


def authorize(cfg: dict, path: Path) -> int:
    """Register this script as a Freebox app and save its token in the config file.

    The Freebox asks for a physical button press on the box. A new ``app_id`` gets its own token, so the
    token used by the AdGuard sync script is left untouched.

    Args:
        cfg: Configuration with ``freebox_url`` and ``app_id``.
        path: Config file to create or update (written with mode 600).

    Returns:
        Exit code: 0 when the token was saved, 1 otherwise.
    """
    base = cfg["freebox_url"].rstrip("/")
    payload = {
        "app_id": cfg["app_id"],
        "app_name": "Stale devices",
        "app_version": "1.0.0",
        "device_name": socket.gethostname(),
    }
    try:
        resp = requests.post(
            f"{base}/api/v4/login/authorize/", json=payload, timeout=REQUEST_TIMEOUT
        ).json()
        token, track_id = resp["result"]["app_token"], resp["result"]["track_id"]
    except (requests.RequestException, ValueError, KeyError) as exc:
        print(f"Cannot register with the Freebox at {base}: {exc}")
        return 1
    print(
        ">>> Press the RIGHT ARROW button on the Freebox server now (waiting up to 2 minutes) <<<"
    )
    status = "pending"
    for _ in range(AUTH_MAX_WAIT):
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
        print(
            f"Not authorized (status: {status}). Run --auth again when ready to press the button."
        )
        return 1
    saved = yaml.safe_load(path.read_text()) if path.exists() else {}
    saved = {**(saved or {}), "app_id": cfg["app_id"], "app_token": token}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(saved, sort_keys=False))
    path.chmod(0o600)
    print(f"Token saved in {path} (mode 600). Next: stale_devices.py --doctor")
    return 0


def get_hosts(cfg: dict, token: str) -> list[dict]:
    """Fetch every device known to the Freebox LAN browser.

    Args:
        cfg: Configuration with ``freebox_url``.
        token: Session token from :func:`fbx_login`.

    Returns:
        The raw host records.

    Raises:
        RuntimeError: If the Freebox does not return the device list.
    """
    base = cfg["freebox_url"].rstrip("/")
    try:
        resp = requests.get(
            f"{base}/api/v4/lan/browser/pub",
            headers={"X-Fbx-App-Auth": token},
            timeout=REQUEST_TIMEOUT,
        ).json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"cannot read the device list: {exc}") from exc
    if not resp.get("success"):
        raise RuntimeError(f"Freebox refused the device list: {resp.get('msg', resp)}")
    return resp["result"]


def mac_of(host: dict) -> str | None:
    """Return the MAC address of a host, lower-cased, or None when it has none."""
    ident = host.get("l2ident") or {}
    return ident["id"].lower() if ident.get("type") == "mac_address" and ident.get("id") else None


def last_seen(host: dict) -> int | None:
    """Return the most recent activity timestamp of a host, across all its addresses.

    Args:
        host: A raw Freebox host record.

    Returns:
        Epoch seconds of the latest sign of life, or None when the Freebox has none.
    """
    stamps = [host.get("last_activity"), host.get("last_time_reachable")]
    for conn in host.get("l3connectivities") or []:
        stamps += [conn.get("last_activity"), conn.get("last_time_reachable")]
    stamps = [s for s in stamps if isinstance(s, int) and s > 0]
    return max(stamps) if stamps else None


def is_up(host: dict) -> bool:
    """Return True when the Freebox currently sees the host."""
    return bool(host.get("reachable") or host.get("active"))


def host_name(host: dict) -> str:
    """Return the best display name of a host."""
    return host.get("primary_name") or host.get("default_name") or mac_of(host) or "unknown"


def ipv4_of(host: dict) -> str:
    """Return the first IPv4 address recorded for a host, or an empty string."""
    for conn in host.get("l3connectivities") or []:
        if conn.get("af") == "ipv4":
            return conn.get("addr", "")
    return ""


def find_stale(
    hosts: list[dict], now: int, threshold_days: int, ignore_macs: set[str]
) -> list[dict]:
    """Select the hosts that are down and silent for at least ``threshold_days``.

    Args:
        hosts: Raw Freebox host records.
        now: Current time, epoch seconds.
        threshold_days: Minimum silence, in days.
        ignore_macs: Lower-cased MAC addresses to leave out.

    Returns:
        One dict per stale device (name, mac, ipv4, last_seen, days), longest silence first. ``days`` is None
        when the Freebox has no activity record for the device.
    """
    stale = []
    for host in hosts:
        mac = mac_of(host)
        if is_up(host) or (mac and mac in ignore_macs):
            continue
        seen = last_seen(host)
        if seen is not None and (now - seen) < threshold_days * DAY:
            continue
        stale.append(
            {
                "name": host_name(host),
                "mac": mac or "no MAC",
                "ipv4": ipv4_of(host),
                "last_seen": seen,
                "days": None if seen is None else (now - seen) // DAY,
            }
        )
    return sorted(stale, key=lambda d: (d["days"] is None, -(d["days"] or 0)))


def describe(dev: dict) -> str:
    """Format one stale device as a single line."""
    ip = f" {dev['ipv4']}," if dev["ipv4"] else ""
    if dev["days"] is None:
        seen = "no activity recorded"
    else:
        seen = f"last seen {time.strftime('%Y-%m-%d', time.localtime(dev['last_seen']))}, {dev['days']} days ago"
    return f"- {dev['name']} ({dev['mac']},{ip} {seen})"


def render(stale: list[dict], threshold_days: int, cap: bool = True) -> str:
    """Build the message, or an empty string when nothing is stale.

    Args:
        stale: Result of :func:`find_stale`.
        threshold_days: Threshold shown in the title.
        cap: Cut the device list so the message stays under the Telegram limit.

    Returns:
        The message text.
    """
    if not stale:
        return ""
    title = f"Freebox: {len(stale)} device(s) unreachable for {threshold_days}+ days"
    lines, used = [], len(title) + len(CLEANUP_STEPS) + 80
    for dev in stale:
        line = describe(dev)
        if cap and used + len(line) > MAX_MESSAGE_CHARS:
            lines.append(f"... and {len(stale) - len(lines)} more (run stale_devices.py --list)")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join([title, "", *lines, "", CLEANUP_STEPS])


def doctor(cfg: dict, hosts: list[dict], now: int) -> None:
    """Print a health report: API fields present, and what would be reported."""
    with_mac = sum(1 for h in hosts if mac_of(h))
    with_stamp = sum(1 for h in hosts if last_seen(h) is not None)
    up = sum(1 for h in hosts if is_up(h))
    stale = find_stale(hosts, now, cfg["threshold_days"], cfg["ignore_macs"])
    unknown = sum(1 for d in stale if d["days"] is None)
    print("OK   Freebox login and device list")
    print(
        f"     {len(hosts)} devices, {up} up now, {with_mac} with a MAC, {with_stamp} with an activity timestamp"
    )
    print(f"     threshold {cfg['threshold_days']} days, {len(cfg['ignore_macs'])} ignored MAC(s)")
    print(f"     {len(stale)} would be reported ({unknown} with no activity record)")
    if hosts and with_stamp == 0:
        print("FAIL no activity timestamp found: the Freebox API fields may have changed")
    for dev in stale[:5]:
        print(f"     e.g. {describe(dev)[2:]}")


def main(argv: list[str] | None = None) -> int:
    """Run the check.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code: 0 on success (even when devices are reported), 1 when the Freebox cannot be read.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--doctor", action="store_true", help="check login and API fields, then summarize"
    )
    parser.add_argument(
        "--list", action="store_true", help="print every stale device, no length cap"
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="get a Freebox token (button press) and save it in the config",
    )
    parser.add_argument("--threshold-days", type=int, help="override the configured threshold")
    parser.add_argument(
        "--devices-json", type=Path, help="read the host list from a file instead of the Freebox"
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.auth:
        return authorize(cfg, args.config)
    if args.threshold_days:
        cfg["threshold_days"] = args.threshold_days
    try:
        if args.devices_json:
            hosts = json.loads(args.devices_json.read_text())
        else:
            hosts = get_hosts(cfg, fbx_login(cfg))
    except RuntimeError as exc:
        # In a --no-agent cron job stdout is the message: a broken check must say so, not stay silent.
        print(f"stale-devices check FAILED: {exc}")
        return 1

    now = int(time.time())
    if args.doctor:
        doctor(cfg, hosts, now)
        return 0
    stale = find_stale(hosts, now, cfg["threshold_days"], cfg["ignore_macs"])
    text = render(stale, cfg["threshold_days"], cap=not args.list)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
    stale_devices.py                 # print the message (nothing when no device is stale)
    stale_devices.py --doctor        # check login, API fields and show what would be reported
    stale_devices.py --list          # like the default, without the message length cap
"""

import argparse
import hashlib
import hmac
import sys
import time
from pathlib import Path

import requests
import yaml

DEFAULT_CONFIG = Path.home() / ".config" / "stale-devices" / "config.yaml"
REQUIRED = ("freebox_url", "app_id", "app_token")
DEFAULTS = {"threshold_days": 14, "ignore_macs": []}
REQUEST_TIMEOUT = 5  # seconds
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
    """Read the YAML config, fill in the defaults and check the values.

    Args:
        path: Location of the config file, created by ``freebox_auth.py``.

    Returns:
        The configuration with ``ignore_macs`` as a set of lower-cased MACs.

    Raises:
        RuntimeError: If the file is missing or unreadable, a required key is missing, or a value has
            the wrong type.
    """
    if not path.exists():
        raise RuntimeError(f"config file not found: {path} (create it with freebox_auth.py)")
    try:
        loaded = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError(f"{path} must contain key: value lines")
    cfg = {**DEFAULTS, **loaded}
    missing = [key for key in REQUIRED if not cfg.get(key)]
    if missing:
        raise RuntimeError(f"missing in {path}: {', '.join(missing)} (run freebox_auth.py)")
    if not isinstance(cfg["threshold_days"], int) or cfg["threshold_days"] < 1:
        raise RuntimeError(f"threshold_days must be a whole number of days (>= 1) in {path}")
    if not isinstance(cfg["ignore_macs"] or [], list):
        raise RuntimeError(f"ignore_macs must be a list of MAC addresses in {path}")
    cfg["ignore_macs"] = {str(mac).lower() for mac in cfg["ignore_macs"] or []}
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


def ipv4_of(host: dict) -> str:
    """Return the first IPv4 address recorded for a host, or an empty string."""
    for conn in host.get("l3connectivities") or []:
        if conn.get("af") == "ipv4":
            return conn.get("addr", "")
    return ""


def merge_hosts(hosts: list[dict]) -> list[dict]:
    """Turn raw Freebox hosts into one record per device.

    The Freebox can list a device more than once (one entry per address or interface). Entries with the
    same MAC are one device: it is up when any entry is up, and its last sign of life is the latest of
    all entries. Without this, an old entry of a device that is on right now would be reported as stale.
    Hosts without a MAC cannot be matched, so each stays on its own.

    Args:
        hosts: Raw Freebox host records.

    Returns:
        One dict per device: ``name``, ``mac`` (or "no MAC"), ``ipv4``, ``up`` and ``seen`` (epoch
        seconds, or None when the Freebox has no activity record).
    """
    merged: dict[str, dict] = {}
    for index, host in enumerate(hosts):
        mac = mac_of(host)
        name = host.get("primary_name") or host.get("default_name") or mac or "unknown"
        seen = last_seen(host)
        dev = merged.setdefault(
            mac or f"#{index}",
            {"name": name, "mac": mac or "no MAC", "ipv4": "", "up": False, "seen": None},
        )
        dev["up"] = dev["up"] or is_up(host)
        dev["ipv4"] = dev["ipv4"] or ipv4_of(host)
        if seen is not None:
            dev["seen"] = max(seen, dev["seen"] or 0)
    return list(merged.values())


def find_stale(
    hosts: list[dict], now: int, threshold_days: int, ignore_macs: set[str]
) -> list[dict]:
    """Select the devices that are down and silent for at least ``threshold_days``.

    Args:
        hosts: Raw Freebox host records.
        now: Current time, epoch seconds.
        threshold_days: Minimum silence, in days.
        ignore_macs: Lower-cased MAC addresses to leave out.

    Returns:
        The stale devices from :func:`merge_hosts` plus ``days`` (None when the Freebox has no activity
        record for the device), longest silence first, unknown last.
    """
    stale = []
    for dev in merge_hosts(hosts):
        if dev["up"] or dev["mac"] in ignore_macs:
            continue
        if dev["seen"] is not None and (now - dev["seen"]) < threshold_days * DAY:
            continue
        days = None if dev["seen"] is None else (now - dev["seen"]) // DAY
        stale.append({**dev, "days": days})
    return sorted(stale, key=lambda d: (d["days"] is None, -(d["days"] or 0)))


def describe(dev: dict) -> str:
    """Format one stale device as a single line."""
    ip = f" {dev['ipv4']}," if dev["ipv4"] else ""
    if dev["days"] is None:
        seen = "no activity recorded"
    else:
        date = time.strftime("%Y-%m-%d", time.localtime(dev["seen"]))
        seen = f"last seen {date}, {dev['days']} days ago"
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


def doctor(cfg: dict, hosts: list[dict], now: int) -> int:
    """Print a health report: API fields present, and what would be reported.

    Args:
        cfg: Configuration.
        hosts: Raw Freebox host records.
        now: Current time, epoch seconds.

    Returns:
        Exit code: 1 when the Freebox returned devices but no activity timestamp at all.
    """
    devices = merge_hosts(hosts)
    with_mac = sum(1 for d in devices if d["mac"] != "no MAC")
    with_stamp = sum(1 for d in devices if d["seen"] is not None)
    stale = find_stale(hosts, now, cfg["threshold_days"], cfg["ignore_macs"])
    unknown = sum(1 for d in stale if d["days"] is None)
    print("OK   Freebox login and device list")
    print(
        f"     {len(devices)} devices, {sum(d['up'] for d in devices)} up now, {with_mac} with a MAC, "
        f"{with_stamp} with an activity timestamp"
    )
    print(f"     threshold {cfg['threshold_days']} days, {len(cfg['ignore_macs'])} ignored MAC(s)")
    print(f"     {len(stale)} would be reported ({unknown} with no activity record)")
    for dev in stale[:5]:
        print(f"     e.g. {describe(dev)[2:]}")
    if devices and with_stamp == 0:
        print("FAIL no activity timestamp found: the Freebox API fields may have changed")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the check.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code: 0 on success (even when devices are reported), 1 when the config or the Freebox
        cannot be read, or when ``--doctor`` finds the API fields gone.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--doctor", action="store_true", help="check login and API fields")
    parser.add_argument("--list", action="store_true", help="print every stale device, no cap")
    parser.add_argument("--threshold-days", type=int, help="override the configured threshold")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
        if args.threshold_days is not None:
            cfg["threshold_days"] = max(1, args.threshold_days)
        hosts = get_hosts(cfg, fbx_login(cfg))
    except (RuntimeError, OSError, ValueError) as exc:  # unreadable or invalid config included
        # In a --no-agent cron job stdout is the message: a broken check must say so, not stay silent.
        print(f"stale-devices check FAILED: {exc}")
        return 1

    now = int(time.time())
    if args.doctor:
        return doctor(cfg, hosts, now)
    text = render(
        find_stale(hosts, now, cfg["threshold_days"], cfg["ignore_macs"]),
        cfg["threshold_days"],
        not args.list,
    )
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

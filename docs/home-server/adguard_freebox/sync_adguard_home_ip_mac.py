#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///

"""Keep the AdGuard Home clients in step with the Freebox device list.

For every Freebox device that has a MAC address, the matching AdGuard client gets the MAC plus every
address the Freebox lists for it (IPv4, global IPv6, link-local, even unreachable ones), so AdGuard's
query log follows a device through IPv6 changes. A client is matched by MAC first, then by name; a
device AdGuard does not know yet is created. Settings you made on a client (blocked services, upstreams,
...) are kept, only its address list is replaced.

Meant for a cron job every minute: it prints nothing when nothing changed, one line per change, and exits
1 when something failed, so a log file only grows when there is something to read.

Usage:
    sync_adguard_home_ip_mac.py                  # sync
    sync_adguard_home_ip_mac.py --dry-run        # show what would change, change nothing
    sync_adguard_home_ip_mac.py --verbose        # also print a summary on every run
"""

import argparse
import hashlib
import hmac
import ipaddress
import re
import sys
import time
from pathlib import Path

import requests
import yaml

DEFAULT_CONFIG = Path.home() / ".config" / "adguard-sync" / "config.yaml"
REQUIRED = (
    "adguard_url",
    "adguard_user",
    "adguard_password",
    "freebox_url",
    "app_id",
    "app_token",
)
REQUEST_TIMEOUT = 5  # seconds
MAC_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")


def log(message: str) -> None:
    """Print a message with a timestamp, so a cron log can be read later."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}")


def load_config(path: Path) -> dict:
    """Read the YAML config and check the required keys.

    Args:
        path: Location of the config file.

    Returns:
        The configuration.

    Raises:
        RuntimeError: If the file is missing, unreadable, or a required key is empty.
    """
    if not path.exists():
        raise RuntimeError(
            f"config file not found: {path} (see sync_adguard_home_ip_mac.example.yaml)"
        )
    try:
        cfg = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    if not isinstance(cfg, dict):
        raise RuntimeError(f"{path} must contain key: value lines")
    missing = [key for key in REQUIRED if not cfg.get(key)]
    if missing:
        raise RuntimeError(f"missing in {path}: {', '.join(missing)}")
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


def fbx_hosts(cfg: dict, token: str) -> list[dict]:
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
        raise RuntimeError(f"cannot read the Freebox device list: {exc}") from exc
    if not resp.get("success"):
        raise RuntimeError(f"Freebox refused the device list: {resp.get('msg', resp)}")
    return resp["result"]


class AdGuard:
    """Minimal AdGuard Home client: list, add and update persistent clients."""

    def __init__(self, cfg: dict) -> None:
        """Prepare a session that sends the basic-auth credentials with every call."""
        self.base = cfg["adguard_url"].rstrip("/")
        self.session = requests.Session()
        self.session.auth = (cfg["adguard_user"], cfg["adguard_password"])

    def _call(self, method: str, path: str, **kwargs) -> requests.Response:
        try:
            resp = self.session.request(
                method, f"{self.base}/control/{path}", timeout=REQUEST_TIMEOUT, **kwargs
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"cannot reach AdGuard Home at {self.base}: {exc}") from exc
        if not resp.ok:
            raise RuntimeError(
                f"AdGuard Home {path} answered {resp.status_code}: {resp.text[:200]}"
            )
        return resp

    def clients(self) -> list[dict]:
        """Return the persistent clients (an empty list when there are none)."""
        try:
            return self._call("GET", "clients").json().get("clients") or []
        except ValueError as exc:
            raise RuntimeError(f"AdGuard Home sent an unreadable client list: {exc}") from exc

    def add(self, client: dict) -> None:
        """Create a client."""
        self._call("POST", "clients/add", json=client)

    def update(self, old_name: str, client: dict) -> None:
        """Replace the client currently called ``old_name`` with ``client``."""
        self._call("POST", "clients/update", json={"name": old_name, "data": client})


def mac_of(host: dict) -> str | None:
    """Return the MAC address of a host, lower-cased, or None when it has none."""
    ident = host.get("l2ident") or {}
    return ident["id"].lower() if ident.get("type") == "mac_address" and ident.get("id") else None


def host_name(host: dict, mac: str) -> str:
    """Return the best name of a host: the name set on the Freebox, then its hostname, then the MAC."""
    return host.get("primary_name") or host.get("default_name") or mac


def collect_devices(hosts: list[dict]) -> tuple[list[dict], int]:
    """Turn raw Freebox hosts into one record per MAC, with the addresses each one owns.

    The Freebox keeps old addresses of devices that are off. When two devices claim the same address
    (an old lease handed out again), AdGuard refuses the second one, so each address goes to the device
    that is reachable on it, or else to the one that used it last.

    Args:
        hosts: Raw Freebox host records.

    Returns:
        The devices as dicts (``name``, ``mac``, ``ids``), and the number of hosts skipped for having
        no MAC address.
    """
    by_mac: dict[str, dict] = {}
    skipped = 0
    for host in hosts:
        mac = mac_of(host)
        if mac is None:
            skipped += 1
            continue
        dev = by_mac.setdefault(mac, {"name": host_name(host, mac), "mac": mac, "claims": {}})
        for conn in host.get("l3connectivities") or []:
            addr = conn.get("addr")
            if addr:
                rank = (bool(conn.get("reachable")), conn.get("last_activity") or 0)
                dev["claims"][addr] = max(rank, dev["claims"].get(addr, rank))

    owner: dict[str, tuple] = {}
    for dev in by_mac.values():
        for addr, rank in dev["claims"].items():
            owner[addr] = max((rank, dev["mac"]), owner.get(addr, (rank, dev["mac"])))
    for dev in by_mac.values():
        dev["ids"] = {dev["mac"]} | {a for a in dev["claims"] if owner[a][1] == dev["mac"]}
    return list(by_mac.values()), skipped


def is_managed(ident: str) -> bool:
    """Return True for a MAC or IP address: the ids this script owns.

    Anything else on a client (a ClientID, a CIDR range) was added by hand and is left alone.
    """
    if MAC_RE.match(ident.lower()):
        return True
    try:
        ipaddress.ip_address(ident)
    except ValueError:
        return False
    return True


def plan_changes(clients: list[dict], devices: list[dict]) -> tuple[list[dict], list[str]]:
    """Compare the Freebox devices with the AdGuard clients and list what must change.

    Args:
        clients: AdGuard persistent clients.
        devices: Result of :func:`collect_devices`.

    Returns:
        The changes (``action`` add or update, ``name``, ``added``, ``removed``, ``client``) and
        the warnings about devices that were skipped.
    """
    by_mac, by_name = {}, {}
    for client in clients:
        for ident in client.get("ids", []):
            if MAC_RE.match(ident.lower()):
                by_mac[ident.lower()] = client
        by_name[client.get("name", "").lower()] = client

    changes, warnings, claimed = [], [], set()
    for dev in devices:
        existing = by_mac.get(dev["mac"]) or by_name.get(dev["name"].lower())
        name = existing["name"] if existing else dev["name"]
        if name.lower() in claimed:
            warnings.append(
                f"skipped {dev['mac']}: the AdGuard client '{name}' already follows another device"
            )
            continue
        claimed.add(name.lower())

        if existing is None:
            client = {"name": name, "ids": sorted(dev["ids"]), "use_global_settings": True}
            changes.append(
                {
                    "action": "add",
                    "name": name,
                    "added": client["ids"],
                    "removed": [],
                    "client": client,
                }
            )
            continue
        current = existing.get("ids", [])
        new_ids = sorted(dev["ids"]) + [i for i in current if not is_managed(i)]
        if set(new_ids) != set(current):
            changes.append(
                {
                    "action": "update",
                    "name": name,
                    "added": sorted(set(new_ids) - set(current)),
                    "removed": sorted(set(current) - set(new_ids)),
                    "client": {**existing, "ids": new_ids},
                }
            )
    return changes, warnings


def apply_changes(agh: AdGuard, changes: list[dict], dry_run: bool) -> int:
    """Send the changes to AdGuard Home, one by one, and report each one.

    Args:
        agh: AdGuard Home client.
        changes: Result of :func:`plan_changes`.
        dry_run: Only print what would be done.

    Returns:
        The number of changes that failed.
    """
    failures = 0
    for change in changes:
        diff = " ".join([f"+{a}" for a in change["added"]] + [f"-{r}" for r in change["removed"]])
        if dry_run:
            log(f"would {change['action']} '{change['name']}': {diff}")
            continue
        try:
            if change["action"] == "add":
                agh.add(change["client"])
            else:
                agh.update(change["name"], change["client"])
        except RuntimeError as exc:
            failures += 1
            log(f"FAILED to {change['action']} '{change['name']}': {exc}")
        else:
            log(f"{change['action']} '{change['name']}': {diff}")
    return failures


def main(argv: list[str] | None = None) -> int:
    """Run one sync.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code: 0 when everything is in step, 1 when AdGuard or the Freebox could not be read or a
        change failed.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--dry-run", action="store_true", help="show the changes, apply none")
    parser.add_argument("--verbose", action="store_true", help="print a summary on every run")
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
        agh = AdGuard(cfg)
        # AdGuard first: if it is down, nothing is read from the Freebox and nothing is created blindly.
        clients = agh.clients()
        hosts = fbx_hosts(cfg, fbx_login(cfg))
    except RuntimeError as exc:
        log(f"adguard-sync FAILED: {exc}")
        return 1

    devices, skipped = collect_devices(hosts)
    changes, warnings = plan_changes(clients, devices)
    for warning in warnings:
        log(f"warning: {warning}")
    failures = apply_changes(agh, changes, args.dry_run)
    if args.verbose:
        log(
            f"{len(devices)} devices, {len(changes)} change(s), {failures} failed, "
            f"{skipped} host(s) without a MAC skipped"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

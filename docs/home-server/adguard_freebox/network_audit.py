#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///

"""Audit AdGuard Home against the Freebox and report what does not line up.

Read-only: it never changes AdGuard Home or the Freebox. Meant for a weekly Hermes cron job with
``--no-agent``: stdout is the message, an empty stdout is a silent run (everything lines up).

It reports, because each one needs a decision from you:
  - AdGuard clients named by a MAC address (the device had no name in the Freebox when it was created)
  - DHCP static leases whose MAC the Freebox does not know, or whose device is on another address
  - AdGuard clients whose MAC the Freebox does not know any more (leftovers)
  - AdGuard clients whose names differ only by case, spaces or punctuation (probably one device twice)
  - devices that are up on a dynamic lease: their IPv4 can change, add a static lease or ignore them

``--list`` adds the harmless findings: names that differ between the Freebox and AdGuard, and old
unreachable addresses still attached to a device that is up.

Usage:
    network_audit.py                 # print the message (nothing when everything lines up)
    network_audit.py --doctor        # check both logins and show the counts
    network_audit.py --list          # also print the harmless findings, without the length cap
"""

import argparse
import hashlib
import hmac
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
DEFAULTS = {"audit_ignore_macs": [], "old_address_days": 90}
REQUEST_TIMEOUT = 5  # seconds
MAX_MESSAGE_CHARS = 3500  # stays under Telegram's 4096-character limit
DAY = 86400
MAC_RE = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")


def load_config(path: Path) -> dict:
    """Read the YAML config, fill in the defaults and check the values.

    Args:
        path: Location of the config file, shared with ``sync_adguard_home_ip_mac.py``.

    Returns:
        The configuration with ``audit_ignore_macs`` as a set of lower-cased MACs.

    Raises:
        RuntimeError: If the file is missing or unreadable, a required key is missing, or a value has
            the wrong type.
    """
    if not path.exists():
        raise RuntimeError(
            f"config file not found: {path} (see sync_adguard_home_ip_mac.example.yaml)"
        )
    try:
        loaded = yaml.safe_load(path.read_text()) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError(f"{path} must contain key: value lines")
    cfg = {**DEFAULTS, **loaded}
    missing = [key for key in REQUIRED if not cfg.get(key)]
    if missing:
        raise RuntimeError(f"missing in {path}: {', '.join(missing)}")
    if not isinstance(cfg["old_address_days"], int) or cfg["old_address_days"] < 1:
        raise RuntimeError(f"old_address_days must be a whole number of days (>= 1) in {path}")
    if not isinstance(cfg["audit_ignore_macs"] or [], list):
        raise RuntimeError(f"audit_ignore_macs must be a list of MAC addresses in {path}")
    cfg["audit_ignore_macs"] = {str(mac).lower() for mac in cfg["audit_ignore_macs"] or []}
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


def agh_get(cfg: dict, path: str) -> dict:
    """Call a read-only AdGuard Home API endpoint and return its JSON body.

    Args:
        cfg: Configuration with the AdGuard URL and credentials.
        path: Endpoint below ``/control/``, for example ``clients``.

    Returns:
        The decoded JSON object.

    Raises:
        RuntimeError: If AdGuard Home is unreachable, answers an error, or sends invalid JSON.
    """
    base = cfg["adguard_url"].rstrip("/")
    try:
        resp = requests.get(
            f"{base}/control/{path}",
            auth=(cfg["adguard_user"], cfg["adguard_password"]),
            timeout=REQUEST_TIMEOUT,
        )
        if not resp.ok:
            raise RuntimeError(
                f"AdGuard Home {path} answered {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json() or {}
    except requests.RequestException as exc:
        raise RuntimeError(f"cannot reach AdGuard Home at {base}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"AdGuard Home sent an unreadable {path} answer: {exc}") from exc


def mac_of(host: dict) -> str | None:
    """Return the MAC address of a host, lower-cased, or None when it has none."""
    ident = host.get("l2ident") or {}
    return ident["id"].lower() if ident.get("type") == "mac_address" and ident.get("id") else None


def normalise(name: str) -> str:
    """Reduce a name to lower-case letters and digits, so 'MacBook AXA' equals 'Macbook-AXA'."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def collect_devices(hosts: list[dict]) -> list[dict]:
    """Turn raw Freebox hosts into one record per MAC.

    Args:
        hosts: Raw Freebox host records.

    Returns:
        One dict per device: ``name``, ``mac``, ``up``, ``ipv4`` (the address it is reachable on, or
        None) and ``old`` (the unreachable addresses with the epoch second of their last activity).
    """
    devices: dict[str, dict] = {}
    for host in hosts:
        mac = mac_of(host)
        if mac is None:
            continue
        name = host.get("primary_name") or host.get("default_name") or mac
        dev = devices.setdefault(
            mac, {"name": name, "mac": mac, "up": False, "ipv4": None, "old": {}}
        )
        dev["up"] = dev["up"] or bool(host.get("active") or host.get("reachable"))
        for conn in host.get("l3connectivities") or []:
            addr = conn.get("addr")
            if not addr:
                continue
            if conn.get("reachable"):
                if conn.get("af") == "ipv4":
                    dev["ipv4"] = addr
            else:
                dev["old"][addr] = max(conn.get("last_activity") or 0, dev["old"].get(addr, 0))
    return list(devices.values())


def client_macs(client: dict) -> list[str]:
    """Return the MAC addresses listed in an AdGuard client's ids, lower-cased."""
    return [i.lower() for i in client.get("ids", []) if MAC_RE.match(i.lower())]


def check_mac_named(clients: list[dict], devices: list[dict], ignore: set[str]) -> list[str]:
    """List the AdGuard clients whose name is a MAC address.

    Args:
        clients: AdGuard persistent clients.
        devices: Result of :func:`collect_devices`.
        ignore: MACs to leave out.

    Returns:
        One line per client, saying what the Freebox calls the device now.
    """
    by_mac = {d["mac"]: d for d in devices}
    lines = []
    for client in clients:
        mac = client["name"].lower()
        if not MAC_RE.match(mac) or mac in ignore:
            continue
        dev = by_mac.get(mac)
        now_called = dev["name"] if dev and dev["name"] != mac else None
        hint = (
            f"the Freebox calls it '{now_called}'"
            if now_called
            else "no name in the Freebox either"
        )
        lines.append(f"{client['name']}: {hint}")
    return lines


def check_static_leases(static: list[dict], devices: list[dict], ignore: set[str]) -> list[str]:
    """List the DHCP static leases that do not match the Freebox.

    Args:
        static: AdGuard DHCP static leases (``mac``, ``ip``, ``hostname``).
        devices: Result of :func:`collect_devices`.
        ignore: MACs to leave out.

    Returns:
        One line per lease whose MAC the Freebox does not know, or whose device is up on another
        IPv4 address.
    """
    by_mac = {d["mac"]: d for d in devices}
    lines = []
    for lease in static:
        mac = lease["mac"].lower()
        if mac in ignore:
            continue
        label = f"{lease.get('hostname') or mac} ({mac}) -> {lease['ip']}"
        dev = by_mac.get(mac)
        if dev is None:
            lines.append(f"{label}: MAC not in the Freebox (old or rotated MAC?)")
        elif dev["up"] and dev["ipv4"] and dev["ipv4"] != lease["ip"]:
            lines.append(f"{label}: the device is on {dev['ipv4']}")
    return lines


def check_orphans(clients: list[dict], devices: list[dict], ignore: set[str]) -> list[str]:
    """List the AdGuard clients whose MACs the Freebox does not know.

    The sync script never touches them, so their addresses stay as they were.

    Args:
        clients: AdGuard persistent clients.
        devices: Result of :func:`collect_devices`.
        ignore: MACs to leave out.

    Returns:
        One line per leftover client. Clients without any MAC (hand-made, IP-only) are not reported.
    """
    known = {d["mac"] for d in devices}
    lines = []
    for client in clients:
        macs = client_macs(client)
        if not macs or MAC_RE.match(client["name"].lower()):
            continue
        if any(m in known or m in ignore for m in macs):
            continue
        lines.append(f"{client['name']}: {', '.join(macs)}")
    return lines


def check_duplicate_names(clients: list[dict]) -> list[str]:
    """List the groups of AdGuard clients whose names differ only by case, spaces or punctuation."""
    groups: dict[str, list[str]] = {}
    for client in clients:
        groups.setdefault(normalise(client["name"]), []).append(client["name"])
    return [" / ".join(f"'{n}'" for n in names) for names in groups.values() if len(names) > 1]


def check_no_static(
    static: list[dict], leases: list[dict], devices: list[dict], ignore: set[str]
) -> list[str]:
    """List the devices that are up but have no DHCP static lease.

    Args:
        static: AdGuard DHCP static leases.
        leases: AdGuard dynamic DHCP leases.
        devices: Result of :func:`collect_devices`.
        ignore: MACs to leave out, for devices that are meant to stay dynamic or self-addressed.

    Returns:
        One line per device, with the address it is on now and whether AdGuard leased it.
    """
    fixed = {lease["mac"].lower() for lease in static}
    dynamic = {lease["mac"].lower(): lease["ip"] for lease in leases if "." in lease.get("ip", "")}
    lines = []
    for dev in sorted(devices, key=lambda d: d["name"].lower()):
        if not dev["up"] or dev["mac"] in fixed or dev["mac"] in ignore:
            continue
        source = "dynamic lease" if dev["mac"] in dynamic else "no AdGuard lease"
        lines.append(f"{dev['name']} ({dev['mac']}): {dev['ipv4'] or '?'}, {source}")
    return lines


def check_name_drift(clients: list[dict], devices: list[dict]) -> list[str]:
    """List the AdGuard clients whose name differs from the Freebox name of the same MAC."""
    by_mac = {d["mac"]: d for d in devices}
    lines = []
    for client in clients:
        if MAC_RE.match(client["name"].lower()):
            continue
        for mac in client_macs(client):
            dev = by_mac.get(mac)
            if dev:
                if dev["name"] != client["name"]:
                    lines.append(f"AdGuard '{client['name']}' / Freebox '{dev['name']}'")
                break
    return lines


def check_old_addresses(devices: list[dict], now: int, days: int) -> list[str]:
    """List the devices that are up but still carry addresses unreachable for ``days`` days."""
    lines = []
    for dev in sorted(devices, key=lambda d: d["name"].lower()):
        if not dev["up"]:
            continue
        count = sum(1 for seen in dev["old"].values() if seen and now - seen > days * DAY)
        if count:
            lines.append(f"{dev['name']}: {count} address(es)")
    return lines


def build_sections(
    clients: list[dict],
    static: list[dict],
    leases: list[dict],
    devices: list[dict],
    cfg: dict,
    now: int,
) -> tuple[list[tuple[str, str, list[str]]], list[tuple[str, str, list[str]]]]:
    """Run every check and group the results.

    Args:
        clients: AdGuard persistent clients.
        static: AdGuard DHCP static leases.
        leases: AdGuard dynamic DHCP leases.
        devices: Result of :func:`collect_devices`.
        cfg: Configuration with ``audit_ignore_macs`` and ``old_address_days``.
        now: Current time, epoch seconds.

    Returns:
        The findings that need a decision, then the harmless ones. Each section is
        ``(title, what to do, lines)``, and sections without lines are dropped.
    """
    ignore = cfg["audit_ignore_macs"]
    alerts = [
        (
            "Clients named by a MAC",
            "name the device in the Freebox, then rename the client in AdGuard",
            check_mac_named(clients, devices, ignore),
        ),
        (
            "Static leases that do not match",
            "fix or delete the lease in AdGuard > Settings > DHCP settings",
            check_static_leases(static, devices, ignore),
        ),
        (
            "Clients the Freebox does not know",
            "delete the leftover client in AdGuard > Settings > Client settings",
            check_orphans(clients, devices, ignore),
        ),
        (
            "Clients that look like the same device",
            "keep the one whose MAC the Freebox lists, delete the other",
            check_duplicate_names(clients),
        ),
        (
            "Up on a dynamic lease (the IPv4 can change)",
            "add a static lease, or add the MAC to audit_ignore_macs",
            check_no_static(static, leases, devices, ignore),
        ),
    ]
    info = [
        (
            "Names that differ (Freebox / AdGuard)",
            "harmless: the sync only names a client when it creates it",
            check_name_drift(clients, devices),
        ),
        (
            f"Old unreachable addresses (over {cfg['old_address_days']} days)",
            "harmless: the Freebox keeps them, the sync copies them",
            check_old_addresses(devices, now, cfg["old_address_days"]),
        ),
    ]
    return (
        [section for section in alerts if section[2]],
        [section for section in info if section[2]],
    )


def render(
    alerts: list[tuple[str, str, list[str]]],
    info: list[tuple[str, str, list[str]]],
    cap: bool = True,
) -> str:
    """Build the message, or an empty string when nothing needs a decision.

    Args:
        alerts: Findings that need a decision.
        info: Harmless findings, printed only when ``cap`` is False (``--list``).
        cap: Cut the message so it stays under the Telegram limit.

    Returns:
        The message text.
    """
    sections = list(alerts) + ([] if cap else list(info))
    if not sections:
        return ""
    total = sum(len(lines) for _, _, lines in alerts)
    headline = (
        f"Network audit: {total} thing(s) to look at"
        if total
        else "Network audit: nothing needs a decision, harmless findings below"
    )
    out = [headline, ""]
    for title, todo, lines in sections:
        out.append(f"{title} ({len(lines)}): {todo}")
        out.extend(f"- {line}" for line in lines)
        out.append("")
    text = "\n".join(out).rstrip()
    if cap and len(text) > MAX_MESSAGE_CHARS:
        text = (
            text[: MAX_MESSAGE_CHARS - 60].rsplit("\n", 1)[0]
            + "\n... cut, run network_audit.py --list"
        )
    return text


def doctor(
    cfg: dict, clients: list[dict], static: list[dict], devices: list[dict], now: int
) -> int:
    """Print a health report: what was read and what would be reported.

    Args:
        cfg: Configuration.
        clients: AdGuard persistent clients.
        static: AdGuard DHCP static leases.
        devices: Result of :func:`collect_devices`.
        now: Current time, epoch seconds.

    Returns:
        Exit code: 1 when the Freebox returned no device with a MAC, so no check can mean anything.
    """
    print("OK   Freebox login and device list, AdGuard Home clients and DHCP status")
    print(
        f"     {len(devices)} devices ({sum(d['up'] for d in devices)} up), "
        f"{len(clients)} AdGuard clients, {len(static)} static leases, "
        f"{len(cfg['audit_ignore_macs'])} ignored MAC(s)"
    )
    if not devices:
        print("FAIL no Freebox device has a MAC address: the API fields may have changed")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the audit.

    Args:
        argv: Command-line arguments, defaults to ``sys.argv``.

    Returns:
        Exit code: 0 on success (even when things are reported), 1 when the config, AdGuard Home or the
        Freebox cannot be read.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--doctor", action="store_true", help="check both logins and show counts")
    parser.add_argument(
        "--list", action="store_true", help="also print the harmless findings, no cap"
    )
    args = parser.parse_args(argv)

    try:
        cfg = load_config(args.config)
        clients = agh_get(cfg, "clients").get("clients") or []
        dhcp = agh_get(cfg, "dhcp/status")
        hosts = fbx_hosts(cfg, fbx_login(cfg))
    except (RuntimeError, OSError, ValueError) as exc:
        # In a --no-agent cron job stdout is the message: a broken check must say so, not stay silent.
        print(f"network-audit FAILED: {exc}")
        return 1

    static = dhcp.get("static_leases") or []
    leases = dhcp.get("leases") or []
    devices = collect_devices(hosts)
    now = int(time.time())
    if args.doctor:
        return doctor(cfg, clients, static, devices, now)
    alerts, info = build_sections(clients, static, leases, devices, cfg, now)
    text = render(alerts, info, not args.list)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

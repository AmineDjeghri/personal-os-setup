"""Read-only audit: AdGuard persistent clients vs the Freebox device list.

Run from the folder holding the sync scripts (the cron wrappers' copy), with deps from uv:

    cd /config/workspace/adguard_freebox
    uv run --with requests --with pyyaml python <this file> [config.yaml]

The config is the sync config (adguard_url/user/password + Freebox keys). Nothing is written and no secret is
printed. Seven checks, each prints only the offenders:
  1 clients named by a MAC (Freebox had no name when the client was created)
  2 AdGuard name != Freebox name (the sync never renames: cosmetic)
  3 clients whose MAC the Freebox no longer lists (orphans the sync never touches)
  4 clients whose names look the same after stripping punctuation/case (duplicates of one device)
  5 one Freebox name matching several clients / several Freebox devices
  6 unreachable addresses older than 90 days still attached to a live device
  7 query log: raw (unnamed) client IPs, and traffic shown under a MAC name
"""

import collections
import re
import sys
import time
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path.cwd()))
import sync_adguard_home_ip_mac as s  # noqa: E402  (run from the scripts folder)

CONFIG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".config/adguard-sync/config.yaml"
cfg = yaml.safe_load(CONFIG.read_text())
base = cfg["adguard_url"].rstrip("/") + "/control"
auth = (cfg["adguard_user"], cfg["adguard_password"])
MAC = re.compile(r"^([0-9a-f]{2}:){5}[0-9a-f]{2}$")
now = time.time()


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


clients = requests.get(base + "/clients", auth=auth, timeout=5).json()["clients"] or []
hosts = s.fbx_hosts(cfg, s.fbx_login(cfg))
devs, skipped = s.collect_devices(hosts)
fbx = {d["mac"]: d for d in devs}
print(f"AdGuard clients: {len(clients)} | Freebox devices: {len(devs)} | hosts without MAC: {skipped}")

print("\n1. Clients named by a MAC:")
for c in clients:
    if MAC.match(c["name"].lower()):
        d = fbx.get(c["name"].lower())
        print(f"   {c['name']} -> Freebox name now: {d['name'] if d else '(not in Freebox)'}")

print("\n2. AdGuard name differs from the Freebox name:")
for c in clients:
    for m in (i.lower() for i in c["ids"] if MAC.match(i.lower())):
        d = fbx.get(m)
        if d and d["name"] != c["name"] and not MAC.match(c["name"].lower()):
            print(f"   AdGuard {c['name']!r} vs Freebox {d['name']!r}")
            break

print("\n3. Clients the Freebox does not know:")
for c in clients:
    macs = [i.lower() for i in c["ids"] if MAC.match(i.lower())]
    if not macs:
        print(f"   {c['name']!r}: no MAC (hand-made or IP-only), ids={len(c['ids'])}")
    elif not any(m in fbx for m in macs):
        print(f"   {c['name']!r}: MAC {macs} not in Freebox, ids={len(c['ids'])}")

print("\n4. Names that look the same:")
groups = collections.defaultdict(list)
for c in clients:
    groups[norm(c["name"])].append(c["name"])
for names in groups.values():
    if len(names) > 1:
        print("  ", names)

print("\n5. One Freebox name, several clients / devices:")
by_fbx = collections.defaultdict(set)
for c in clients:
    for i in c["ids"]:
        if i.lower() in fbx:
            by_fbx[norm(fbx[i.lower()]["name"])].add(c["name"])
for names in by_fbx.values():
    if len(names) > 1:
        print("  ", sorted(names))
fb_names = collections.defaultdict(list)
for d in devs:
    fb_names[norm(d["name"])].append(d["mac"])
for name, macs in fb_names.items():
    if len(macs) > 1:
        print(f"   Freebox has {len(macs)} devices called {name!r}: {macs}")

print("\n6. Old unreachable addresses (>90 days) on live devices:")
old = collections.Counter()
for h in hosts:
    if not (h.get("active") or h.get("reachable")):
        continue
    for conn in h.get("l3connectivities") or []:
        last = conn.get("last_activity") or 0
        if not conn.get("reachable") and last and now - last > 90 * 86400:
            old[h.get("primary_name") or s.mac_of(h)] += 1
for name, n in old.most_common():
    print(f"   {name}: {n}")

log = requests.get(base + "/querylog", params={"limit": 1000}, auth=auth, timeout=30).json().get("data", [])
unnamed = collections.Counter(e["client"] for e in log if not (e.get("client_info") or {}).get("name"))
mac_named = collections.Counter(
    (e.get("client_info") or {}).get("name")
    for e in log
    if MAC.match(((e.get("client_info") or {}).get("name") or "").lower())
)
print(f"\n7. Query log (last {len(log)}): unnamed clients {dict(unnamed.most_common(8))}; under a MAC name {dict(mac_named)}")

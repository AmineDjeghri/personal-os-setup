#!/usr/bin/env python3
"""Convert an AIOStreams config export into an importable template.

Verified transformation (AIOStreams v2.34) against the export in
personal-os-setup/src/personal_os_setup/config/others/aiostreams-config.json:
keep the full config body, drop the per-user `trusted` flag, make the debrid
services wizard-driven, and parameterize every preset that hardcoded a
service-id list. Read the printed summary and fix what it flags - the script
cannot judge whether a URL or a string is personal.

Usage:
  python3 export-to-template.py --source aiostreams-config.json \
      --out aiostreams-template.json --id <owner>.<name> --name "AIOStreams Starter" \
      --author <handle> --description "..." \
      --source-url https://raw.githubusercontent.com/<owner>/<repo>/main/<path>/aiostreams-template.json
"""

import argparse
import datetime
import json
import re
import sys

DEBRID = [
    "realdebrid",
    "alldebrid",
    "premiumize",
    "debridlink",
    "torbox",
    "offcloud",
    "easydebrid",
    "debrider",
    "pikpak",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="config export (JSON)")
    ap.add_argument("--out", required=True, help="template to write")
    ap.add_argument("--id", required=True, help="namespaced id, e.g. owner.my-template")
    ap.add_argument("--name", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument(
        "--source-url",
        default=None,
        help="main-branch raw URL; enables the importer's update notice",
    )
    ap.add_argument("--category", default="Debrid")
    ap.add_argument(
        "--selectable",
        nargs="*",
        default=DEBRID,
        help="service ids the wizard may offer (default: the debrid list)",
    )
    ap.add_argument("--addon-description", default="AIOStreams - one addon, all your sources")
    a = ap.parse_args()

    cfg = json.load(open(a.source))

    svc = []
    for s in cfg["services"]:
        if s["id"] in a.selectable:
            svc.append(
                {"__if": f"services.{s['id']}", "id": s["id"], "enabled": True, "credentials": {}}
            )
        else:
            svc.append({"id": s["id"], "enabled": False, "credentials": {}})

    body = {k: v for k, v in cfg.items() if k not in ("trusted", "services")}
    body["services"] = svc
    body["addonDescription"] = a.addon_description

    # Keep EVERY preset, disabled ones included: the public guide documents the
    # optional disabled addons by name, so trimming them breaks documented steps.
    presets = json.loads(json.dumps(cfg["presets"]))
    replaced = []
    for p in presets:
        if p["type"] == "tmdb-addon":
            p["options"]["Enable Adult Content"] = False
        o = p.get("options", {})
        if o.get("services"):
            replaced.append(f"{p['type']}: {o['services']} -> {{{{services}}}}")
            o["services"] = "{{services}}"
    body["presets"] = presets

    md = {
        "id": a.id,
        "name": a.name,
        "description": a.description,
        "author": a.author,
        "source": "external",
        "version": "1.0.0",
        "category": a.category,
        "services": list(a.selectable),
        "serviceRequired": False,
        "changelog": [
            {
                "version": "1.0.0",
                "date": datetime.date.today().isoformat(),
                "content": "- Initial release.",
            }
        ],
    }
    if a.source_url:
        md["sourceUrl"] = a.source_url

    with open(a.out, "w") as f:
        json.dump({"metadata": md, "config": body}, f, indent=2, ensure_ascii=False)
        f.write("\n")

    v = json.load(open(a.out))  # verify what is on disk, not the dict we built
    blob = json.dumps(v)
    bad_secrets = re.findall(r'"(?:apiKey|api_key|password|token)"\s*:\s*"[^"]+"', blob)
    missing = [
        k
        for k in ("id", "name", "description", "author", "category", "version", "source")
        if not v["metadata"].get(k)
    ]
    print(
        f"wrote {a.out}: {len(open(a.out, 'rb').read())} bytes, "
        f"{len(v['config'])} config keys, {len(v['config']['presets'])} presets"
    )
    print("service lists parameterized:", replaced or "none")
    print("urls in file:", sorted(set(re.findall(r"https?://[^\"\\ ]+", blob))))
    print("non-empty credential values:", bad_secrets or "none")
    if missing or bad_secrets:
        print("FAIL: metadata missing", missing, "| secrets", bad_secrets)
        sys.exit(1)
    print("OK - review the URL list, then publish")


if __name__ == "__main__":
    main()

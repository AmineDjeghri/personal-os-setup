---
name: vm-lab
description: Use when working with the local KVM/QEMU VM test lab — "spin up a VM", "test this in a CachyOS/Ubuntu VM", "make vm-*". CachyOS host only (libvirt/pacman-based); documents the required make vm-deps step, why re-running with new credentials does nothing until you clean, and the manual sync requirement against packages.yaml.
---

# Local VM lab (`scripts/vm.sh` + `makefiles/vm.mk`)

A libvirt/QEMU helper for booting throwaway VMs to test OS-setup flows without touching the host. **CachyOS-host only** (its dependency check shells out to `pacman -Qi`) — not usable from Ubuntu/macOS dev machines.

⚠️ **Every command in this skill mutates the host or a VM's disk state** (installs packages, needs `sudo`, creates/destroys VMs, downloads multi-GB ISOs). Confirm the specific command with the user before running any of them — including `make vm-deps`, any `vm-*` target, and `scripts/vm.sh` invocations — even if the user already asked you to "set up the VM lab" in general terms. See the repo-wide rule in `CLAUDE.md` § "Safety: always confirm before system-mutating actions".

## One-time setup

`make vm-deps` checks for `qemu-full libvirt virt-manager dnsmasq edk2-ovmf cloud-image-utils` via `pacman -Qi`. If anything's missing, it tells you to install it **through the app's own Packages tab** (Dev_tools category) rather than installing it itself — this is deliberate, keeping package installs funneled through the TUI's package-manager code path rather than duplicated in Make.

⚠️ This package list is a **manual mirror** of `packages.yaml`'s `cachyos.pacman.Dev_tools` VM-related entries — nothing checks that they stay in sync. If you add/remove a VM dependency, update both places.

After deps are present, `make vm-deps` also does `sudo systemctl enable --now libvirtd.service`, adds your user to the `libvirt`/`kvm` groups, and starts the default virsh network — **requires sudo**, and **you must log out and back in** for the new group membership to take effect before VM commands will work.

## Commands

`scripts/vm.sh {cachyos|ubuntu-server-auto|ubuntu-server-manual|ubuntu-desktop|list|clean}`, wrapped by `make vm-cachyos` / `make vm-ubuntu-server` / `make vm-ubuntu-server-manual` / `make vm-ubuntu` / `make vm-list` / `make vm-clean`.

State (ISOs, disks, cloud-init seeds) lives under `.vm/` at repo root (gitignored).

## Gotchas

- **`make vm-clean` is destructive**: it `virsh destroy`+`undefine`s every `pos-*` VM and deletes the disk/cloud-init dirs (cached ISOs are kept). Confirm with the user before running it if VMs might hold in-progress work.
- **Re-running a VM target on an existing VM name just resumes it — it does not pick up new settings.** If you change `AUTOINSTALL_USER`/`AUTOINSTALL_PASSWORD` env vars for `vm-ubuntu-server` (auto-install) and re-run, nothing changes until you `make vm-clean` first.
- `AUTOINSTALL_USER`/`AUTOINSTALL_PASSWORD` default to `amine`/`amine` if not overridden — a weak default plaintext credential, acceptable only because it's scoped to an ephemeral local dev VM, not anything network-exposed.
- The CachyOS ISO URL is scraped from SourceForge's RSS feed (no official stable "latest" URL exists) and is **not cryptographically verified** — only presence/size is trusted. If SourceForge changes its markup, `fetch_cachyos_iso_url()` breaks and tells you to download manually rather than silently using a bad URL.
- Ubuntu image URLs are hardcoded to a specific release (currently `26.04`) inside `scripts/vm.sh` — bump this manually when a new LTS/interim release ships, it isn't derived dynamically.
- The Ubuntu auto-install flow attaches the cloud-init seed ISO as the *second* CD-ROM device (`/dev/sr1`) — this is order-of-operations dependent on how `virt-install`'s `--disk`/`--location` args are ordered in the script; don't reorder those args without re-testing a full auto-install run.

Requires `virt-install`, `cloud-localds` (auto-install path only), `curl`, `openssl`, `sha256sum`, `virsh` on `PATH` — `scripts/vm.sh` fails fast with a clear "run `make vm-deps` first" message if any are missing.

---
name: vm-lab
description: Use when working with the local KVM/QEMU VM test lab — "spin up a VM", "test this in a CachyOS/Ubuntu/Windows/macOS VM", "make vm-*". CachyOS host only (libvirt/pacman-based); documents the required make vm-deps step, why re-running with new credentials does nothing until you clean, and the manual sync requirement against packages.yaml.
metadata:
  hermes:
    origin: repo:personal-os-setup
---

# Local VM lab (`scripts/vm.sh` + `makefiles/vm.mk`)

A libvirt/QEMU helper for booting throwaway VMs to test OS-setup flows without touching the host. **CachyOS-host only** (its dependency check shells out to `pacman -Qi`).

⚠️ **Every command in this skill mutates the host or a VM's disk state** (installs packages, needs `sudo`, creates/destroys VMs, downloads multi-GB ISOs). Confirm the specific command with the user before running any of them — including `make vm-deps`, any `vm-*` target, and `scripts/vm.sh` invocations — even if the user already asked for the VM lab in general terms. Canon: `AGENTS.md` § "Safety: confirm before system-mutating actions (MANDATORY)".

## One-time setup

`make vm-deps` checks for `qemu-full libvirt virt-manager virt-viewer dnsmasq edk2-ovmf cloud-image-utils swtpm` via `pacman -Qi` (apt/dnf equivalents on those hosts; `swtpm` = the emulated TPM 2.0 for the Windows guest). Anything missing, it tells you to install it **through the app's own Packages tab** (Dev_tools category) rather than installing it itself — package installs stay funneled through the TUI's package-manager code path.

⚠️ That package list is a **manual mirror** of `packages.yaml`'s `cachyos.pacman.Dev_tools` VM entries — nothing checks that they stay in sync. Update both when you add/remove a VM dependency.

`make vm-deps` then does `sudo systemctl enable --now libvirtd.service`, adds your user to the `libvirt`/`kvm` groups, and starts the default virsh network — **requires sudo**, and **you must log out and back in** before VM commands work.

## Commands

`scripts/vm.sh {cachyos|ubuntu-server-auto|ubuntu-server-manual|ubuntu-desktop|windows|macos|list|clean}`, wrapped by `make vm-cachyos` / `make vm-ubuntu-server` / `make vm-ubuntu-server-manual` / `make vm-ubuntu` / `make vm-windows` / `make vm-macos` / `make vm-list` / `make vm-clean`.

`make vm-windows` is different: Windows ISOs can't be downloaded automatically (Microsoft licensing), so run it as `WIN_ISO=/path/to/windows.iso make vm-windows` (the script copies the ISO into `.vm/isos/` and dies with an actionable message if `WIN_ISO` is unset). Defaults: Windows 11, UEFI + Secure Boot + `swtpm` TPM 2.0, SATA disk + e1000e NIC (inbox drivers, so no virtio-win ISO), 80 GB disk (Win11 setup rejects < 64 GB). Env knobs: `WIN_ISO_SHA256`, `WIN_VERSION=10` (no-TPM fallback), `WIN_DISK_GB`. The rationale is in `docs/vm/README.md`; the end-to-end test walkthrough (boot → `install_windows.ps1` → TUI) is in `docs/windows_workflow/README.md`.

`make vm-macos` is the other exception and is **not libvirt**: macOS guests need OpenCore + Apple's recovery image, which [Quickemu](https://github.com/quickemu-project/quickemu) automates (`quickget macos <release>` then `quickemu --vm macos-<release>.conf`, run with `.vm/macos/` as cwd). Env knob: `MACOS_VERSION` (`mojave catalina big-sur monterey ventura sonoma sequoia tahoe`, default `tahoe` = macOS 26, what `macos-latest` currently runs in CI). The rationale is in `docs/vm/README.md`; the end-to-end walkthrough (boot → Command Line Tools → Homebrew → app) is in `docs/macos_darwin/README.md`.

State (ISOs, disks, cloud-init seeds, the Quickemu macOS guest) lives under `.vm/` at repo root (gitignored).

## Gotchas

- **`make vm-clean` is destructive**: it `virsh destroy`+`undefine`s every `pos-*` VM and deletes the disk/cloud-init dirs and `.vm/macos/` (cached ISOs are kept, but the macOS recovery image lives in the guest dir, so it is re-downloaded). It skips `.vm/macos/` and says so if a Quickemu process still references it. Confirm before running it if VMs might hold in-progress work.
- **Re-running a VM target on an existing VM name just resumes it — it does not pick up new settings.** Change `AUTOINSTALL_USER`/`AUTOINSTALL_PASSWORD` for `vm-ubuntu-server` and re-run, and nothing changes until you `make vm-clean` first.
- `AUTOINSTALL_USER`/`AUTOINSTALL_PASSWORD` default to `pos-dev` (the password falls back to the resolved user name when unset) — a throwaway credential, scoped to an ephemeral local dev VM. Override via env vars for anything longer-lived.
- The CachyOS ISO URL is scraped from SourceForge's RSS feed and is **not cryptographically verified** — only presence/size is trusted. If the markup changes, `fetch_cachyos_iso_url()` breaks and tells you to download manually rather than silently using a bad URL.
- Ubuntu image URLs are hardcoded to a specific release (currently `26.04`) inside `scripts/vm.sh` — bump manually when a new release ships, it isn't derived dynamically.
- **`vm-windows` can't be validated without KVM and a real ISO.** The `virt-install` flags (`--boot firmware=efi,firmware.feature0.name=secure-boot,firmware.feature0.enabled=yes` (the shorter `firmware.secure-boot=` option does not exist in virt-install 5.1.0, and requesting `enrolled-keys` fails with "Unable to find 'efi' firmware that is compatible" because Arch's edk2-ovmf ships no firmware descriptor with that feature, so the VARS file has no Microsoft keys; Win11 setup only needs Secure Boot *capable*), `--tpm backend.type=emulator,backend.version=2.0,model=tpm-crb`) were checked against virt-install's source/man page, not by booting. Unlike the Linux guests it omits `--noreboot` on purpose (Windows setup reboots repeatedly). At the installer, click into the console and press a key at "Press any key to boot from CD or DVD".
- **`vm-macos` is invisible to `make vm-list`/`virsh`/virt-manager** (plain QEMU under the user, no libvirt domain), and upstream has no supported libvirt import (quickemu issue #437) — don't generate libvirt XML for it. Quickemu is listed in `packages.yaml` (CachyOS `paru` Dev_tools; an install-page link on Ubuntu) but deliberately not checked by `vm-deps`, since only `vm-macos` needs it; the script dies with that hint if `quickemu`/`quickget` are missing. Never pre-download a macOS image on the agent's behalf — it is multi-GB and the user's host does it.
- **`vm-macos` can't be validated without KVM, Quickemu and Apple's download.** Only the argument validation, missing-binary message and Make wiring were exercised without them. CPU: SSE4.1 (all releases), AVX2 (Ventura+), both checked from `/proc/cpuinfo`; some AMD Ryzen mobile CPUs hit a TSC hang on Ventura+ (see the Quickemu wiki's macOS page for `tsc=reliable` and `qe_mac_apid`). No GPU acceleration; SPICE copy/paste unavailable on macOS. Apple's EULA restricts macOS guests to Apple hardware — the user's call.
- The Ubuntu auto-install flow attaches the cloud-init seed ISO as the *second* CD-ROM device (`/dev/sr1`) — order-of-operations dependent on `virt-install`'s `--disk`/`--location` args; don't reorder them without re-testing a full auto-install run.

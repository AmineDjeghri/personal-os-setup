# Guest images and hardware for a local VM lab

Sourcing rules and the guest flags that make a plain ISO boot with no extra downloads.

## Windows guest

- **The ISO is user-supplied.** Microsoft's download flow needs a browser session and its live links expire,
  so the VM script takes a path (`WIN_ISO=/path/to.iso`), optionally a checksum
  (`WIN_ISO_SHA256=…`, verified when set, warned when not), copies it into the gitignored ISO cache so
  libvirt's QEMU user can read it, and fails with a clear message plus a generic download-page pointer when
  unset. Never bake a scraped direct URL into the script.
- **Windows 11 defaults** (all chosen so the plain ISO boots with zero driver ISO):
  - UEFI via OVMF with Microsoft keys enrolled — libvirt `--boot uefi,firmware.secure-boot=yes,firmware.enrolled-keys=yes`.
  - Emulated TPM 2.0 — `--tpm backend.type=emulator,backend.version=2.0,model=tpm-crb` (needs `swtpm` +
    `swtpm_setup` on the host; on Debian/Ubuntu also the split `swtpm-tools` package).
  - Disk on **SATA** (`bus=sata`) and NIC `e1000e`, video `vga`: Windows ships inbox drivers for AHCI and
    e1000e. Virtio is faster but needs the separate virtio-win ISO and a manual driver load in setup, so it is
    not the default path.
  - Disk **80 GB** qcow2 sparse — Windows 11 setup refuses less than 64 GB.
  - `--clock offset=localtime` (Windows expects local RTC) and **no `--noreboot`** — setup reboots several
    times and virt-install must restart the domain.
  - 4 GB RAM / 2 vCPU minimum; a sane lab default is higher (6 GB / 4 vCPU).
- **Fallback:** a Windows-10 guest boots with plain UEFI and no TPM, for hosts without swtpm; it is
  out of support, so prefer 11 with TPM.
- Cleanup: guests with a TPM need `virsh undefine <name> --nvram --tpm`, not a bare `undefine`.
- Install is manual in the GUI console, including "press any key to boot from CD" — say so in the target's output.

## macOS guest

The community route (OSX-KVM and forks) is technically workable on a normal Linux host:

- Needs QEMU ≥8.2, Intel VT-x/AMD SVM, SSE4.1 (Sierra+), AVX2 (Ventura+); modern AMD is fine, old AMD is not.
- The installer image **is obtainable without a Mac**: the project's `fetch-macOS-v2.py` pulls `BaseSystem.dmg`
  from Apple's CDN (then `dmg2img` → qcow2 disk → OpenCore boot script, or its bundled libvirt XML with
  path placeholders + `virsh define`). Headless boot script plus SSH/VNC notes exist.
- One host-level change beyond qemu/libvirt: `kvm ignore_msrs=1` in `/etc/modprobe.d` (system-mutating —
  requires explicit confirmation).
- Install is interactive (Disk Utility, APFS); limits to state up front: no graphical acceleration, unreliable sound, no USB3.
- It is **not** an ISO+`virt-install` flow like the Linux guests, so wrapping it means a thin orchestration
  script that clones the upstream project into the gitignored VM cache (not a fork of it).
- **EULA:** Apple permits macOS guests only on Apple hardware. Present it as the user's decision, and note what
  a local macOS VM actually buys over a hosted macOS runner (interactive TUI smoke testing only, if the CI
  runner already exercises the platform's package manager).

### The low-effort macOS route: a QEMU-wrapper project

A wrapper project can remove the manual steps entirely — one command downloads the recovery image, OpenCore and
OVMF firmware and writes a conf file the wrapper boots. What that buys and what it costs:

- Nothing to clone or hand-edit (`quickget macos <release>` → `quickemu --vm macos-<release>.conf`). Validate the
  release against the tool's OWN supported list rather than a list copied from memory, and default it to the
  release CI actually runs so VM and runner agree.
- It is **a plain QEMU process under the user, not a libvirt domain**: the lab's `virsh`-based list shows nothing
  and its clean target does not see the guest. Give it its own directory inside the same gitignored cache, prune
  that directory from the clean target (skipping it while a matching QEMU process still runs), and document
  which commands cover it and which do not. Upstream offers no supported import into libvirt — do not generate
  libvirt XML for it.
- The recovery image lives inside the guest directory, so a clean means re-downloading it.
- The wrapper is typically a manual/AUR install and does not belong in a dependency list checked as distro
  packages: die with the install hint instead.
- CPU gates are real and cheap to check in the script: SSE4.1 for every supported release, AVX2 for
  Ventura-and-newer, plus a documented unstable-TSC hang on some AMD mobile parts for the newer releases.

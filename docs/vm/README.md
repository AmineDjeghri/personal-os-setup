# Testing this project in a VM

`make vm-*` targets (backed by `scripts/vm.sh`) spin up local KVM/QEMU/libvirt VMs to try
this project's setup in a disposable environment instead of on your real machine. **Any Linux
host** — `make vm-deps` auto-detects `pacman`/`apt`/`dnf` and checks the right package names for
each. On CachyOS and Ubuntu those packages are also in `packages.yaml`, so you can install them
from the app's own Packages tab instead of manually.

```bash
make vm-deps            # verify qemu/libvirt/virt-manager/virt-viewer/swtpm are installed, enable libvirtd
                         # (install any missing ones from the app's Packages tab first, if available for your distro)

make vm-cachyos          # CachyOS VM -- manual ISO install, GUI console opens automatically
make vm-ubuntu-server    # Ubuntu Server 26.04 -- unattended autoinstall, no clicking needed
make vm-ubuntu-server-manual  # same ISO, manual click-through install
make vm-ubuntu           # Ubuntu Desktop 26.04 -- manual install
WIN_ISO=/path/to/windows.iso make vm-windows  # Windows 11 (UEFI + Secure Boot + emulated TPM) -- manual install, you supply the ISO
make vm-macos            # macOS via Quickemu (NOT libvirt) -- downloads Apple's recovery image; MACOS_VERSION=sonoma to pick another

make vm-list             # list this project's libvirt VMs and their state (does NOT show the Quickemu macOS guest)
make vm-clean            # destroy/undefine all this project's VMs, wipe disks + the Quickemu macOS guest (keeps cached ISOs)
make vm-clean-isos       # delete cached install ISOs too (re-downloaded on next make vm-*)
```

Re-running a `vm-*` target on a VM that already exists just starts it and reopens the GUI
console instead of recreating it. Everything (ISOs, disk images, cloud-init seeds, the macOS guest) is cached
under `.vm/` (gitignored) — repo-local, so deleting the repo also cleans it all up.

## Per-guest walkthroughs

The command list above is shared; each guest's step-by-step flow and gotchas live with its OS docs:

| Guest      | Walkthrough                                                                                          | What's special                                                                                                                                                                                            |
|------------|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| CachyOS    | [Testing the CachyOS flow in a VM](../linux/CachyOS.md#testing-the-cachyos-flow-in-a-vm)             | ISO is downloaded for you (not checksum-verified)                                                                                                                                                         |
| Ubuntu     | [Testing the Ubuntu flow in a VM](../linux/README.md#testing-the-ubuntu-flow-in-a-vm)                | ISO is downloaded for you; Ubuntu Server can autoinstall                                                                                                                                                  |
| Windows 11 | [Testing the Windows flow in a VM](../windows_workflow/README.md#5-testing-the-windows-flow-in-a-vm) | you supply the ISO (`WIN_ISO`); UEFI + Secure Boot + emulated TPM                                                                                                                                         |
| macOS      | [Testing the macOS flow in a VM](../macos_darwin/README.md#6-testing-the-macos-flow-in-a-vm)         | [Quickemu](https://github.com/quickemu-project/quickemu), **not libvirt**: not shown by `make vm-list`, but wiped by `make vm-clean`; install Quickemu from the Packages tab (not part of `make vm-deps`) |

**If a VM has no internet access during install**, it's very likely your host's firewall
blocking NAT'd VM traffic on libvirt's `virbr0` bridge, even though libvirt sets up its own
NAT rules for it. On `ufw`-based hosts (Ubuntu's default), fix it with:

```bash
make vm-ufw-allow   # asks for confirmation, then allows routing for virbr0 specifically
make vm-ufw-revert  # undoes it, same confirm-first prompt
```

This only opens routing for `virbr0` — every other interface keeps `ufw`'s default DROP-forward
policy untouched. If your host uses `firewalld` instead (common on Fedora/RHEL), the equivalent
is adding `virbr0`'s zone to the trusted zone or an explicit forwarding rule — `vm-ufw-allow`
doesn't cover that yet.

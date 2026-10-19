#!/usr/bin/env bash
# KVM/QEMU/libvirt VM helper for `make vm-*` targets. Linux host only.
#
# Usage: scripts/vm.sh {cachyos|ubuntu-server-auto|ubuntu-server-manual|ubuntu-desktop|windows|macos|list|clean}
set -euo pipefail

# A venv on PATH breaks virt-install's python3 shebang (no system PyGObject).
if [ -n "${VIRTUAL_ENV:-}" ]; then
    PATH="$(echo "$PATH" | tr ':' '\n' | grep -vF "$VIRTUAL_ENV/bin" | paste -sd: -)"
    unset VIRTUAL_ENV
fi

# Pin the connection -- otherwise virsh/virt-install may default to qemu:///session,
# which has no networks defined.
export LIBVIRT_DEFAULT_URI="qemu:///system"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_DIR="$ROOT_DIR/.vm"
ISO_DIR="$VM_DIR/isos"
DISK_DIR="$VM_DIR/disks"
SEED_DIR="$VM_DIR/cloud-init"

RAM_MB=6144
VCPUS=4
DISK_GB=40
NAME_PREFIX="pos-"

# Generic throwaway default — the VM is an ephemeral local dev box, never network-exposed.
# Override with: AUTOINSTALL_USER=foo AUTOINSTALL_PASSWORD=bar make vm-ubuntu-server
# (password falls back to the resolved user value when left unset)
AUTOINSTALL_USER="${AUTOINSTALL_USER:-pos-dev}"
AUTOINSTALL_PASSWORD="${AUTOINSTALL_PASSWORD:-$AUTOINSTALL_USER}"

# `make vm-windows` knobs: WIN_ISO (required), WIN_ISO_SHA256 (verified when set), WIN_VERSION 11|10, WIN_DISK_GB.
WIN_ISO="${WIN_ISO:-}"
WIN_ISO_SHA256="${WIN_ISO_SHA256:-}"
WIN_VERSION="${WIN_VERSION:-11}"
WIN_DISK_GB="${WIN_DISK_GB:-80}"

# `make vm-macos`: the default release tracks what `macos-latest` currently runs in CI (macOS 26 = tahoe).
MACOS_VERSION="${MACOS_VERSION:-tahoe}"
MACOS_DIR="$VM_DIR/macos"

YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${YELLOW}==> $*${NC}"; }
ok() { echo -e "${GREEN}$*${NC}"; }
die() {
    echo "error: $*" >&2
    exit 1
}

ensure_dirs() { mkdir -p "$ISO_DIR" "$DISK_DIR" "$SEED_DIR"; }

# The QEMU process user varies by distro (libvirt-qemu on Debian/Ubuntu/Arch, qemu on
# Fedora/RHEL); qemu.conf can also override it explicitly.
hypervisor_user() {
    local configured
    configured="$(grep -E '^[[:space:]]*user[[:space:]]*=' /etc/libvirt/qemu.conf 2>/dev/null |
        sed -E 's/.*=[[:space:]]*"?([^"[:space:]]+)"?.*/\1/' | tail -1)"
    if [ -n "$configured" ] && [ "$configured" != "root" ]; then
        echo "$configured"
    elif id libvirt-qemu >/dev/null 2>&1; then
        echo libvirt-qemu
    elif id qemu >/dev/null 2>&1; then
        echo qemu
    else
        echo nobody
    fi
}

# Grant that user traverse access down to $VM_DIR (home dirs aren't world-traversable
# by default), plus rw + a default ACL so new files (e.g. a fresh qcow2) inherit access.
ensure_hypervisor_access() {
    command -v setfacl >/dev/null 2>&1 || {
        log "setfacl not found (package 'acl') -- skipping ACL setup, VM storage access may fail"
        return 0
    }
    local hv_user
    hv_user="$(hypervisor_user)"
    local dir="$VM_DIR"
    while [ "$dir" != "/" ] && [ "$dir" != "$HOME" ]; do
        setfacl -m "u:$hv_user:x" "$dir" 2>/dev/null || true
        dir="$(dirname "$dir")"
    done
    setfacl -m "u:$hv_user:x" "$HOME" 2>/dev/null || true
    setfacl -R -m "u:$hv_user:rwX" "$VM_DIR" 2>/dev/null || true
    setfacl -R -d -m "u:$hv_user:rwX" "$VM_DIR" 2>/dev/null || true
}

require_bin() {
    command -v "$1" >/dev/null 2>&1 || die "$1 not found -- run 'make vm-deps' first"
}

# Download $1 (url) to $2 (dest) if not already present, resuming partial downloads.
download() {
    local url="$1" dest="$2"
    if [ -s "$dest" ]; then
        ok "cached: $dest"
        return 0
    fi
    log "downloading $url"
    curl -L --fail --retry 3 -C - -o "$dest.part" "$url"
    mv "$dest.part" "$dest"
}

# Verify $1 (file) against a SHA256SUMS-formatted file $2, matching by basename.
verify_sha256sums() {
    local file="$1" sums_file="$2" name
    name="$(basename "$file")"
    local expected
    expected="$(grep -F -m1 "$name" "$sums_file" | awk '{print $1}')"
    [ -n "$expected" ] || die "no checksum entry for $name in $sums_file"
    local actual
    actual="$(sha256sum "$file" | awk '{print $1}')"
    [ "$expected" = "$actual" ] || die "checksum mismatch for $name (expected $expected, got $actual)"
    ok "checksum ok: $name"
}

vm_exists() { virsh dominfo "$1" >/dev/null 2>&1; }
vm_running() { [ "$(virsh domstate "$1" 2>/dev/null || true)" = "running" ]; }

open_viewer() {
    if command -v virt-viewer >/dev/null 2>&1; then
        virt-viewer --connect qemu:///system --wait "$1" &
    elif command -v virt-manager >/dev/null 2>&1; then
        virt-manager --connect qemu:///system --show-domain-console "$1" &
    else
        log "no GUI viewer found; connect manually with: virsh console $1"
    fi
}

# Starts+opens an existing VM and returns success, so callers skip creating it again.
start_if_exists() {
    local name="$1"
    vm_exists "$name" || return 1
    if vm_running "$name"; then
        log "$name already running, opening viewer"
    else
        log "$name exists but is stopped, starting it"
        virsh start "$name"
    fi
    open_viewer "$name"
    return 0
}

fetch_cachyos_iso_url() {
    # No stable "latest" URL for CachyOS -- scrape the SourceForge RSS feed instead.
    local rss
    rss="$(curl -sL --fail "https://sourceforge.net/projects/cachyos-arch/rss?path=/gui-installer/desktop")"
    echo "$rss" | grep -oE -m1 'https://sourceforge\.net/projects/cachyos-arch/files/gui-installer/desktop/[^<"]+\.iso/download'
}

cmd_cachyos() {
    local name="${NAME_PREFIX}cachyos"
    start_if_exists "$name" && return 0
    ensure_dirs
    ensure_hypervisor_access
    require_bin virt-install

    local url iso_name iso_path
    url="$(fetch_cachyos_iso_url)"
    [ -n "$url" ] || die "couldn't find the current CachyOS ISO automatically -- download it yourself from https://cachyos.org/download/ and save it as $ISO_DIR/cachyos-desktop.iso, then re-run"
    iso_name="$(basename "$(dirname "$url")").iso"
    iso_path="$ISO_DIR/$iso_name"
    download "$url" "$iso_path"
    log "CachyOS doesn't publish a reliably scrapable checksum file, so this ISO is not cryptographically verified -- only its presence/size is trusted."

    log "creating $name (manual install -- a GUI console window will open)"
    virt-install \
        --name "$name" \
        --memory "$RAM_MB" --vcpus "$VCPUS" \
        --disk "path=$DISK_DIR/$name.qcow2,size=$DISK_GB,format=qcow2,bus=virtio" \
        --cdrom "$iso_path" \
        --osinfo detect=on,require=off \
        --network network=default,model=virtio \
        --graphics spice --video virtio \
        --boot uefi \
        --noreboot
}

cmd_ubuntu_desktop() {
    local name="${NAME_PREFIX}ubuntu-desktop"
    start_if_exists "$name" && return 0
    ensure_dirs
    ensure_hypervisor_access
    require_bin virt-install

    local base="https://releases.ubuntu.com/26.04"
    local iso_path="$ISO_DIR/ubuntu-26.04-desktop-amd64.iso"
    local sums_path="$ISO_DIR/ubuntu-26.04-desktop.SHA256SUMS"
    download "$base/ubuntu-26.04-desktop-amd64.iso" "$iso_path"
    download "$base/SHA256SUMS" "$sums_path"
    verify_sha256sums "$iso_path" "$sums_path"

    log "creating $name (manual install -- a GUI console window will open)"
    virt-install \
        --name "$name" \
        --memory "$RAM_MB" --vcpus "$VCPUS" \
        --disk "path=$DISK_DIR/$name.qcow2,size=$DISK_GB,format=qcow2,bus=virtio" \
        --cdrom "$iso_path" \
        --osinfo detect=on,require=off \
        --network network=default,model=virtio \
        --graphics spice --video virtio \
        --boot uefi \
        --noreboot
}

cmd_ubuntu_server_manual() {
    local name="${NAME_PREFIX}ubuntu-server-manual"
    start_if_exists "$name" && return 0
    ensure_dirs
    ensure_hypervisor_access
    require_bin virt-install

    local base="https://releases.ubuntu.com/26.04"
    local iso_path="$ISO_DIR/ubuntu-26.04-live-server-amd64.iso"
    local sums_path="$ISO_DIR/ubuntu-26.04-server.SHA256SUMS"
    download "$base/ubuntu-26.04-live-server-amd64.iso" "$iso_path"
    download "$base/SHA256SUMS" "$sums_path"
    verify_sha256sums "$iso_path" "$sums_path"

    log "creating $name (manual install -- a GUI console window will open)"
    virt-install \
        --name "$name" \
        --memory "$RAM_MB" --vcpus "$VCPUS" \
        --disk "path=$DISK_DIR/$name.qcow2,size=$DISK_GB,format=qcow2,bus=virtio" \
        --cdrom "$iso_path" \
        --osinfo detect=on,require=off \
        --network network=default,model=virtio \
        --graphics spice --video virtio \
        --boot uefi \
        --noreboot
}

cmd_ubuntu_server_auto() {
    local name="${NAME_PREFIX}ubuntu-server-auto"
    start_if_exists "$name" && return 0
    ensure_dirs
    ensure_hypervisor_access
    require_bin virt-install
    require_bin cloud-localds

    local base="https://releases.ubuntu.com/26.04"
    local iso_path="$ISO_DIR/ubuntu-26.04-live-server-amd64.iso"
    local sums_path="$ISO_DIR/ubuntu-26.04-server.SHA256SUMS"
    download "$base/ubuntu-26.04-live-server-amd64.iso" "$iso_path"
    download "$base/SHA256SUMS" "$sums_path"
    verify_sha256sums "$iso_path" "$sums_path"

    log "building autoinstall seed for user '$AUTOINSTALL_USER'"
    local seed_dir="$SEED_DIR/$name"
    mkdir -p "$seed_dir"
    local crypted_password
    crypted_password="$(openssl passwd -6 "$AUTOINSTALL_PASSWORD")"

    cat >"$seed_dir/user-data" <<EOF
#cloud-config
autoinstall:
  version: 1
  identity:
    hostname: $name
    username: $AUTOINSTALL_USER
    password: "$crypted_password"
  ssh:
    install-server: true
    allow-pw: true
  storage:
    layout:
      name: direct
EOF
    cat >"$seed_dir/meta-data" <<EOF
instance-id: $name-$(date +%s)
local-hostname: $name
EOF

    local seed_iso="$seed_dir/seed.iso"
    rm -f "$seed_iso"
    cloud-localds "$seed_iso" "$seed_dir/user-data" "$seed_dir/meta-data"

    log "creating $name (unattended autoinstall -- user '$AUTOINSTALL_USER', password '$AUTOINSTALL_PASSWORD')"
    log "if it boots to the installer menu instead of installing automatically, pick 'Autoinstall Ubuntu Server' there"
    virt-install \
        --name "$name" \
        --memory "$RAM_MB" --vcpus "$VCPUS" \
        --disk "path=$DISK_DIR/$name.qcow2,size=$DISK_GB,format=qcow2,bus=virtio" \
        --location "$iso_path" \
        --extra-args "autoinstall ds=nocloud;s=/dev/sr1/" \
        --disk "path=$seed_iso,device=cdrom" \
        --osinfo detect=on,require=off \
        --network network=default,model=virtio \
        --graphics spice --video virtio \
        --boot uefi
}

# Win 11 needs UEFI + Secure Boot + TPM 2.0 (OVMF + swtpm); SATA disk + e1000e NIC use inbox drivers (no virtio-win ISO).
# 80 GB because setup rejects disks < 64 GB; no --noreboot because setup reboots several times.
cmd_windows() {
    local name="${NAME_PREFIX}windows"
    start_if_exists "$name" && return 0
    ensure_dirs
    ensure_hypervisor_access
    require_bin virt-install

    case "$WIN_VERSION" in
    11 | 10) ;;
    *) die "WIN_VERSION must be 11 or 10 (got '$WIN_VERSION')" ;;
    esac
    [ -n "$WIN_ISO" ] || die "WIN_ISO is not set. Windows ISOs can't be downloaded automatically (Microsoft licensing) -- download one from https://www.microsoft.com/software-download/ and re-run with: WIN_ISO=/path/to/windows.iso make vm-windows"
    [ -f "$WIN_ISO" ] || die "WIN_ISO='$WIN_ISO' is not a file -- download a Windows ISO from https://www.microsoft.com/software-download/ and point WIN_ISO at it"

    if [ -n "$WIN_ISO_SHA256" ]; then
        local actual
        actual="$(sha256sum "$WIN_ISO" | awk '{print $1}')"
        [ "${actual,,}" = "${WIN_ISO_SHA256,,}" ] || die "checksum mismatch for $WIN_ISO (expected $WIN_ISO_SHA256, got $actual)"
        ok "checksum ok: $(basename "$WIN_ISO")"
    else
        log "WIN_ISO_SHA256 not set -- the ISO is not verified. Microsoft lists the SHA-256 on its download page."
    fi

    local iso_path
    iso_path="$ISO_DIR/$(basename "$WIN_ISO")"
    if [ -s "$iso_path" ] && [ "$(stat -c %s "$iso_path")" = "$(stat -c %s "$WIN_ISO")" ]; then
        ok "cached: $iso_path"
    else
        log "copying $WIN_ISO into $ISO_DIR (so libvirt can read it)"
        cp --reflink=auto "$WIN_ISO" "$iso_path.part"
        mv "$iso_path.part" "$iso_path"
    fi

    # Arrays are never empty, so they stay safe under `set -u` on older bash.
    local boot_args tpm_args osinfo
    if [ "$WIN_VERSION" = "11" ]; then
        require_bin swtpm
        require_bin swtpm_setup
        boot_args=(--boot "uefi,firmware.secure-boot=yes,firmware.enrolled-keys=yes")
        tpm_args=(--tpm "backend.type=emulator,backend.version=2.0,model=tpm-crb")
        osinfo="detect=on,name=win11,require=off"
    else
        boot_args=(--boot uefi)
        tpm_args=(--tpm none)
        osinfo="detect=on,name=win10,require=off"
    fi

    log "creating $name (Windows $WIN_VERSION, manual install -- a GUI console window will open)"
    log "click into the console and press a key at 'Press any key to boot from CD or DVD' (it times out after a few seconds)"
    virt-install \
        --name "$name" \
        --memory "$RAM_MB" --vcpus "$VCPUS" \
        --disk "path=$DISK_DIR/$name.qcow2,size=$WIN_DISK_GB,format=qcow2,bus=sata" \
        --cdrom "$iso_path" \
        --osinfo "$osinfo" \
        --network network=default,model=e1000e \
        --graphics spice --video vga \
        --clock offset=localtime \
        "${boot_args[@]}" \
        "${tpm_args[@]}"
}

# Quickemu is a QEMU wrapper, not libvirt: the guest lives under .vm/macos/ so `vm-clean` wipes it and `vm-list` never shows it.
# CPU requirements, limits and the Apple EULA note: docs/linux/CachyOS.md#testing-this-project-in-a-vm.
require_quickemu() {
    local bin
    for bin in quickemu quickget; do
        command -v "$bin" >/dev/null 2>&1 && continue
        if command -v pacman >/dev/null 2>&1; then
            die "$bin not found -- Quickemu isn't part of 'make vm-deps'; install it from the AUR with: paru -S quickemu"
        fi
        die "$bin not found -- Quickemu isn't part of 'make vm-deps'; install it for your distro by following the install section of https://github.com/quickemu-project/quickemu"
    done
}

cmd_macos() {
    case "$MACOS_VERSION" in
    mojave | catalina | big-sur | monterey | ventura | sonoma | sequoia | tahoe) ;;
    *) die "MACOS_VERSION must be one of: mojave catalina big-sur monterey ventura sonoma sequoia tahoe (got '$MACOS_VERSION')" ;;
    esac
    require_quickemu

    grep -qw sse4_1 /proc/cpuinfo 2>/dev/null || die "this CPU doesn't report SSE4.1, which macOS guests need"
    case "$MACOS_VERSION" in
    ventura | sonoma | sequoia | tahoe)
        grep -qw avx2 /proc/cpuinfo 2>/dev/null || die "macOS $MACOS_VERSION guests need AVX2 and this CPU doesn't report it -- try MACOS_VERSION=monterey (or older)"
        ;;
    esac

    local conf="macos-$MACOS_VERSION.conf"
    mkdir -p "$MACOS_DIR"
    cd "$MACOS_DIR"

    if [ -f "$conf" ]; then
        ok "cached: $MACOS_DIR/$conf"
    else
        log "fetching macOS $MACOS_VERSION via quickget (Apple's multi-GB recovery image + OpenCore) into $MACOS_DIR"
        quickget macos "$MACOS_VERSION"
        [ -f "$conf" ] || die "quickget finished but $MACOS_DIR/$conf is missing -- check its output above"
        log "first boot lands in macOS Recovery: in Disk Utility (View > Show All Devices) erase the big 'Apple VirtIO Block Media' disk (~137 GB) as APFS, then 'Reinstall macOS' onto it (the ~400 MB QEMU HARDDISK is OpenCore, the ~2.5 GB volume is the Recovery image)"
        log "Ventura+ hangs on some AMD Ryzen mobile CPUs (unstable TSC) -- see the macOS page of the Quickemu wiki"
    fi

    log "starting macOS $MACOS_VERSION with quickemu (a window opens; this is not listed by 'make vm-list')"
    quickemu --vm "$conf"
}

cmd_list() {
    virsh list --all --name 2>/dev/null | grep "^${NAME_PREFIX}" || echo "(no ${NAME_PREFIX}* VMs)"
}

cmd_clean() {
    local name
    for name in $(virsh list --all --name 2>/dev/null | grep "^${NAME_PREFIX}" || true); do
        log "destroying $name"
        virsh destroy "$name" >/dev/null 2>&1 || true
        virsh undefine "$name" --nvram --tpm >/dev/null 2>&1 || virsh undefine "$name" --nvram >/dev/null 2>&1 || virsh undefine "$name" >/dev/null 2>&1 || true
    done
    rm -rf "$DISK_DIR" "$SEED_DIR"
    # The Quickemu macOS guest is plain QEMU, not libvirt, so the loop above never saw it.
    if pgrep -f -- "$MACOS_DIR" >/dev/null 2>&1; then
        log "macOS guest (Quickemu) is still running -- shut it down, then re-run to wipe $MACOS_DIR"
    else
        rm -rf "$MACOS_DIR"
    fi
    ok "VM disks, cloud-init seeds and the Quickemu macOS guest wiped. Cached ISOs kept in $ISO_DIR."
}

cmd_clean_isos() {
    rm -rf "$ISO_DIR"
    ok "Cached ISOs wiped ($ISO_DIR)."
}

confirm() {
    local reply
    read -r -p "$1 [y/N] " reply
    case "$reply" in
    [yY] | [yY][eE][sS]) return 0 ;;
    *) return 1 ;;
    esac
}

# ufw's default forward policy (DROP) blocks NAT'd VM traffic on virbr0; this opens
# routing for virbr0 only, leaving ufw's policy untouched everywhere else.
cmd_ufw_allow() {
    command -v ufw >/dev/null 2>&1 || {
        ok "ufw not found -- nothing to do"
        return 0
    }
    if ! systemctl is-active --quiet ufw; then
        ok "ufw is not active -- nothing to do"
        return 0
    fi
    log "ufw is active. Its default forward policy blocks VM internet access over libvirt's"
    log "NAT bridge (virbr0) unless routing is explicitly allowed for it. This will run:"
    echo "    sudo ufw route allow in on virbr0"
    echo "    sudo ufw route allow out on virbr0"
    echo "    sudo ufw allow in on virbr0"
    echo "    sudo ufw reload"
    confirm "Apply these ufw rules now?" || {
        log "skipped"
        return 0
    }
    sudo ufw route allow in on virbr0
    sudo ufw route allow out on virbr0
    sudo ufw allow in on virbr0
    sudo ufw reload
    ok "Applied. Undo later with: make vm-ufw-revert"
}

cmd_ufw_revert() {
    command -v ufw >/dev/null 2>&1 || {
        ok "ufw not found -- nothing to do"
        return 0
    }
    log "This will run:"
    echo "    sudo ufw route delete allow in on virbr0"
    echo "    sudo ufw route delete allow out on virbr0"
    echo "    sudo ufw delete allow in on virbr0"
    echo "    sudo ufw reload"
    confirm "Revert these ufw rules now?" || {
        log "skipped"
        return 0
    }
    sudo ufw route delete allow in on virbr0 2>/dev/null || true
    sudo ufw route delete allow out on virbr0 2>/dev/null || true
    sudo ufw delete allow in on virbr0 2>/dev/null || true
    sudo ufw reload
    ok "Reverted."
}

case "${1:-}" in
cachyos) cmd_cachyos ;;
ubuntu-desktop) cmd_ubuntu_desktop ;;
ubuntu-server-manual) cmd_ubuntu_server_manual ;;
ubuntu-server-auto) cmd_ubuntu_server_auto ;;
windows) cmd_windows ;;
macos) cmd_macos ;;
list) cmd_list ;;
clean) cmd_clean ;;
clean-isos) cmd_clean_isos ;;
ufw-allow) cmd_ufw_allow ;;
ufw-revert) cmd_ufw_revert ;;
*) die "usage: $0 {cachyos|ubuntu-desktop|ubuntu-server-manual|ubuntu-server-auto|windows|macos|list|clean|clean-isos|ufw-allow|ufw-revert}" ;;
esac

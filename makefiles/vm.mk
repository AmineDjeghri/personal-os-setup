# Virtual machine targets (KVM/QEMU/libvirt) for testing this app in a clean OS.
# Linux host only, any distro -- vm-deps auto-detects pacman/apt/dnf.
# VM disks/ISOs are cached under .vm/ (gitignored); see scripts/vm.sh for the logic.
# vm-macos is Quickemu (plain QEMU, not libvirt) and a manual install, not part of vm-deps.

.PHONY: vm-deps vm-cachyos vm-ubuntu-server vm-ubuntu-server-manual vm-ubuntu vm-windows vm-macos vm-list vm-clean vm-clean-isos vm-ufw-allow vm-ufw-revert

# Package names mirror packages.yaml's Dev_tools VM entries (cachyos/ubuntu/debian) -- keep in sync.
# swtpm is the emulated TPM 2.0 for vm-windows.
vm-deps: ## Verify qemu/libvirt/virt-manager are installed and enable libvirtd
	@printf '%b\n' "${CYAN}=========> checking qemu/libvirt/virt-manager are installed ${NC}" >&2
	@if command -v pacman >/dev/null 2>&1; then \
		pkgs="qemu-full libvirt virt-manager virt-viewer dnsmasq edk2-ovmf cloud-image-utils swtpm"; \
		check() { pacman -Qi "$$1" >/dev/null 2>&1; }; \
	elif command -v apt-get >/dev/null 2>&1; then \
		pkgs="qemu-system qemu-utils libvirt-daemon-system libvirt-clients virtinst virt-manager virt-viewer dnsmasq-base ovmf cloud-image-utils swtpm swtpm-tools"; \
		check() { dpkg -s "$$1" >/dev/null 2>&1; }; \
	elif command -v dnf >/dev/null 2>&1; then \
		pkgs="qemu-kvm libvirt virt-install virt-manager virt-viewer dnsmasq edk2-ovmf cloud-utils swtpm swtpm-tools"; \
		check() { rpm -q "$$1" >/dev/null 2>&1; }; \
	else \
		printf '%b\n' "${RED}Unsupported package manager (no pacman/apt/dnf found).${NC}"; \
		echo "Install qemu/kvm, libvirt, virt-manager, virt-viewer, dnsmasq, OVMF firmware, cloud-image-utils, and swtpm manually for your distro, then re-run 'make vm-deps'."; \
		exit 1; \
	fi; \
	missing=""; \
	for pkg in $$pkgs; do check "$$pkg" || missing="$$missing $$pkg"; done; \
	if [ -n "$$missing" ]; then \
		printf '%b\n' "${RED}Missing packages:$$missing${NC}"; \
		echo "Install them from the app's Packages tab (Dev_tools category) if available for your distro, or manually otherwise, then re-run 'make vm-deps'."; \
		exit 1; \
	fi
	@sudo systemctl enable --now libvirtd.service
	sudo usermod -aG libvirt,kvm "$$USER" 2>/dev/null || sudo usermod -aG libvirt "$$USER"
	sudo virsh net-autostart default 2>/dev/null || true
	sudo virsh net-start default 2>/dev/null || true
	@printf '%b\n' "${GREEN}Done. Log out and back in for the libvirt/kvm group membership to take effect.${NC}"
	@printf '%b\n' "${GREEN}vm-deps complete${NC}" >&2

vm-cachyos: ## Create/start a CachyOS VM (manual ISO install, GUI console)
	@printf '%b\n' "${CYAN}=========> vm-cachyos...${NC}" >&2
	@./scripts/vm.sh cachyos
	@printf '%b\n' "${GREEN}vm-cachyos complete${NC}" >&2

vm-ubuntu-server: ## Create/start an Ubuntu Server 26.04 VM (unattended autoinstall)
	@printf '%b\n' "${CYAN}=========> vm-ubuntu-server...${NC}" >&2
	@./scripts/vm.sh ubuntu-server-auto
	@printf '%b\n' "${GREEN}vm-ubuntu-server complete${NC}" >&2

vm-ubuntu-server-manual: ## Create/start an Ubuntu Server 26.04 VM (manual ISO install, GUI console)
	@printf '%b\n' "${CYAN}=========> vm-ubuntu-server-manual...${NC}" >&2
	@./scripts/vm.sh ubuntu-server-manual
	@printf '%b\n' "${GREEN}vm-ubuntu-server-manual complete${NC}" >&2

vm-ubuntu: ## Create/start an Ubuntu Desktop 26.04 VM (manual ISO install, GUI console)
	@printf '%b\n' "${CYAN}=========> vm-ubuntu...${NC}" >&2
	@./scripts/vm.sh ubuntu-desktop
	@printf '%b\n' "${GREEN}vm-ubuntu complete${NC}" >&2

vm-windows: ## Create/start a Windows VM from YOUR ISO: WIN_ISO=/path/to.iso make vm-windows (UEFI+TPM, GUI console)
	@printf '%b\n' "${CYAN}=========> vm-windows...${NC}" >&2
	@./scripts/vm.sh windows
	@printf '%b\n' "${GREEN}vm-windows complete${NC}" >&2

vm-macos: ## Create/start a macOS guest via Quickemu (not libvirt, not in vm-list): MACOS_VERSION=sonoma make vm-macos (default tahoe = macos-latest)
	@printf '%b\n' "${CYAN}=========> vm-macos...${NC}" >&2
	@./scripts/vm.sh macos
	@printf '%b\n' "${GREEN}vm-macos complete${NC}" >&2

vm-list: ## List this project's libvirt VMs and their state (the Quickemu macOS guest is not shown)
	@printf '%b\n' "${CYAN}=========> vm-list...${NC}" >&2
	@./scripts/vm.sh list
	@printf '%b\n' "${GREEN}vm-list complete${NC}" >&2

vm-clean: ## Destroy and undefine all this project's VMs, wipe disks and the Quickemu macOS guest (keeps cached ISOs)
	@printf '%b\n' "${CYAN}=========> vm-clean...${NC}" >&2
	@./scripts/vm.sh clean
	@printf '%b\n' "${GREEN}vm-clean complete${NC}" >&2

vm-clean-isos: ## Delete cached VM install ISOs (re-downloaded on next make vm-*)
	@printf '%b\n' "${CYAN}=========> vm-clean-isos...${NC}" >&2
	@./scripts/vm.sh clean-isos
	@printf '%b\n' "${GREEN}vm-clean-isos complete${NC}" >&2

vm-ufw-allow: ## Allow VM internet access through ufw's virbr0 bridge (asks first)
	@printf '%b\n' "${CYAN}=========> vm-ufw-allow...${NC}" >&2
	@./scripts/vm.sh ufw-allow
	@printf '%b\n' "${GREEN}vm-ufw-allow complete${NC}" >&2

vm-ufw-revert: ## Undo vm-ufw-allow's ufw rules (asks first)
	@printf '%b\n' "${CYAN}=========> vm-ufw-revert...${NC}" >&2
	@./scripts/vm.sh ufw-revert
	@printf '%b\n' "${GREEN}vm-ufw-revert complete${NC}" >&2

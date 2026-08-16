# Virtual machine targets (KVM/QEMU/libvirt) for testing this app in a clean OS.
# Linux host only, any distro -- vm-deps auto-detects pacman/apt/dnf.
# VM disks/ISOs are cached under .vm/ (gitignored); see scripts/vm.sh for the logic.

.PHONY: vm-deps vm-cachyos vm-ubuntu-server vm-ubuntu-server-manual vm-ubuntu vm-list vm-clean vm-clean-isos vm-ufw-allow vm-ufw-revert

# Package names mirror packages.yaml's Dev_tools VM entries (cachyos/ubuntu) -- keep in sync.
vm-deps: ## Verify qemu/libvirt/virt-manager are installed and enable libvirtd
	@echo "${YELLOW}=========> checking qemu/libvirt/virt-manager are installed ${NC}"
	@if command -v pacman >/dev/null 2>&1; then \
		pkgs="qemu-full libvirt virt-manager virt-viewer dnsmasq edk2-ovmf cloud-image-utils"; \
		check() { pacman -Qi "$$1" >/dev/null 2>&1; }; \
	elif command -v apt-get >/dev/null 2>&1; then \
		pkgs="qemu-system qemu-utils libvirt-daemon-system libvirt-clients virtinst virt-manager virt-viewer dnsmasq-base ovmf cloud-image-utils"; \
		check() { dpkg -s "$$1" >/dev/null 2>&1; }; \
	elif command -v dnf >/dev/null 2>&1; then \
		pkgs="qemu-kvm libvirt virt-install virt-manager virt-viewer dnsmasq edk2-ovmf cloud-utils"; \
		check() { rpm -q "$$1" >/dev/null 2>&1; }; \
	else \
		echo "Unsupported package manager (no pacman/apt/dnf found)."; \
		echo "Install qemu/kvm, libvirt, virt-manager, virt-viewer, dnsmasq, OVMF firmware, and cloud-image-utils manually for your distro, then re-run 'make vm-deps'."; \
		exit 1; \
	fi; \
	missing=""; \
	for pkg in $$pkgs; do check "$$pkg" || missing="$$missing $$pkg"; done; \
	if [ -n "$$missing" ]; then \
		echo "Missing packages:$$missing"; \
		echo "Install them from the app's Packages tab (Dev_tools category) if available for your distro, or manually otherwise, then re-run 'make vm-deps'."; \
		exit 1; \
	fi
	sudo systemctl enable --now libvirtd.service
	sudo usermod -aG libvirt,kvm "$$USER" 2>/dev/null || sudo usermod -aG libvirt "$$USER"
	sudo virsh net-autostart default 2>/dev/null || true
	sudo virsh net-start default 2>/dev/null || true
	@echo "${GREEN}Done. Log out and back in for the libvirt/kvm group membership to take effect.${NC}"

vm-cachyos: ## Create/start a CachyOS VM (manual ISO install, GUI console)
	@./scripts/vm.sh cachyos

vm-ubuntu-server: ## Create/start an Ubuntu Server 26.04 VM (unattended autoinstall)
	@./scripts/vm.sh ubuntu-server-auto

vm-ubuntu-server-manual: ## Create/start an Ubuntu Server 26.04 VM (manual ISO install, GUI console)
	@./scripts/vm.sh ubuntu-server-manual

vm-ubuntu: ## Create/start an Ubuntu Desktop 26.04 VM (manual ISO install, GUI console)
	@./scripts/vm.sh ubuntu-desktop

vm-list: ## List this project's VMs and their state
	@./scripts/vm.sh list

vm-clean: ## Destroy and undefine all this project's VMs, wipe disks (keeps cached ISOs)
	@./scripts/vm.sh clean

vm-clean-isos: ## Delete cached VM install ISOs (re-downloaded on next make vm-*)
	@./scripts/vm.sh clean-isos

vm-ufw-allow: ## Allow VM internet access through ufw's virbr0 bridge (asks first)
	@./scripts/vm.sh ufw-allow

vm-ufw-revert: ## Undo vm-ufw-allow's ufw rules (asks first)
	@./scripts/vm.sh ufw-revert

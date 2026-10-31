# Installation targets
# This file contains all installation-related targets

.PHONY: install-uv update-uv install install-dev install-prod

install-uv: ## Install uv only when missing
	@echo "${YELLOW}=========> installing uv ${NC}"
ifeq ($(OS),Windows_NT)
	@powershell -NoProfile -ExecutionPolicy Bypass -Command "\
		$$ErrorActionPreference = 'Stop'; \
		$$uv = Get-Command uv -ErrorAction SilentlyContinue; \
		if ($$uv) { \
		  Write-Host 'uv exists at' $$uv.Source -ForegroundColor Green; \
		} else { \
		  Write-Host 'Installing uv' -ForegroundColor Yellow; \
		  irm https://astral.sh/uv/install.ps1 | iex; \
		}"
else
	@if [ -x "$(UV)" ]; then \
		echo "${GREEN}uv exists at $(UV) ${NC}"; \
	else \
		echo "${YELLOW}Installing uv${NC}"; \
		curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$$HOME/.local/bin" sh; \
	fi
endif

update-uv: ## Explicitly update an existing uv installation
	@$(UV) self update

install: install-uv ## Install dependencies using uv
	@echo "Installing runtime dependencies..."
	@$(UV) sync
	@echo "${GREEN}Dependencies installed.${NC}"

install-dev: ## Install all dev dependencies
	@echo "${YELLOW}=========> Installing dependencies...\n  \
	 Development dependencies (dev & docs) will be installed by install-dev.${NC}"
	@$(UV) sync --locked --all-groups
	@echo "${GREEN}Dependencies installed.${NC}"

install-prod: ## Install prod dependencies
	@echo "${YELLOW}=========> Installing dependencies (PROD)...${NC}"
	@$(UV) sync
	@echo "${GREEN}Dependencies installed.${NC}"

# Testing targets
# This file contains all testing-related targets

.PHONY: test-installation test test-integration

test-installation: ## Test installation
	@echo "${YELLOW}=========> Testing installation...${NC}"
	@$(UV) run --directory . awesome-os

test: ## Run unit tests with pytest
	@echo "${YELLOW}Running tests...${NC}"
	@set -e; \
	$(UV) run pytest tests/unit || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		echo "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi

test-integration: ## Run integration tests (requires Ubuntu with passwordless sudo)
	@echo "${YELLOW}Running integration tests...${NC}"
	@set -e; \
	$(UV) run pytest tests/integration -v || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		echo "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi

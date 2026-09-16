# Testing targets
# This file contains all testing-related targets

.PHONY: test-installation test test-integration

N ?= 4

test-installation: ## Test installation
	@echo "${YELLOW}=========> Testing installation...${NC}"
	@$(UV) run --directory . awesome-os

test: ## Run unit tests with pytest (parallel via pytest-xdist). Usage: make test [N=<num_workers>] (default: 4)
	@echo "${YELLOW}Running tests with $(N) worker(s)...${NC}"
	@set -e; \
	$(UV) run pytest tests/unit --numprocesses=$(N) || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		echo "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi

# Not parallelized: these tests drive real system package managers
# (pacman/apt/brew) which aren't safe to run concurrently.
test-integration: ## Run integration tests (requires Ubuntu with passwordless sudo)
	@echo "${YELLOW}Running integration tests...${NC}"
	@set -e; \
	$(UV) run pytest tests/integration -v || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		echo "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi

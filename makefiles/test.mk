# Testing targets
# This file contains all testing-related targets

.PHONY: test-installation test test-all test-integration

N ?= 4

test-installation: build-package ## Install the built wheel in a throwaway env and check the personal-os-setup command loads (does not start it)
	@echo "${YELLOW}=========> Testing installation...${NC}"
	@wheel=$$(ls -t dist/*.whl | head -1); \
	$(UV) run --isolated --no-project --with "$$wheel" python -c \
		"from importlib.metadata import entry_points; ep = entry_points(group='console_scripts')['personal-os-setup']; ep.load(); print('OK', ep.name, '->', ep.value)"

test: ## Run unit tests with pytest (parallel via pytest-xdist). Usage: make test [N=<num_workers>] (default: 4)
	@echo "${YELLOW}Running tests with $(N) worker(s)...${NC}"
	@set -e; \
	$(UV) run pytest tests/unit tests/skills --numprocesses=$(N) || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		echo "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi

test-all: ## Run every self-contained suite (unit, skills, built-wheel smoke)
	@$(MAKE) --no-print-directory test
	@$(MAKE) --no-print-directory test-installation
	@echo "${YELLOW}=========> All self-contained suites passed.${NC}"

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

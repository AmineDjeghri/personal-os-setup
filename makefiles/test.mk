# Testing targets
# This file contains all testing-related targets

.PHONY: test-installation test test-integration

N ?= 4

test-installation: build-package ## Install the built wheel in a throwaway env and check the personal-os-setup command loads (does not start it)
	@printf '%b\n' "${CYAN}=========> Testing installation...${NC}" >&2
	@wheel=$$(ls -t dist/*.whl | head -1); \
	$(UV) run --isolated --no-project --with "$$wheel" python -c \
		"from importlib.metadata import entry_points; ep = entry_points(group='console_scripts')['personal-os-setup']; ep.load(); print('OK', ep.name, '->', ep.value)"
	@printf '%b\n' "${GREEN}test-installation complete${NC}" >&2

test: ## Run unit tests with pytest (parallel via pytest-xdist). Usage: make test [N=<num_workers>] (default: 4)
	@printf '%b\n' "${CYAN}Running tests with $(N) worker(s)...${NC}" >&2
	@set -e; \
	$(UV) run pytest tests/unit tests/skills --numprocesses=$(N) || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		printf '%b\n' "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi
	@printf '%b\n' "${GREEN}test complete${NC}" >&2

# Not parallelized: these tests drive real system package managers
# (pacman/apt/brew) which aren't safe to run concurrently.
test-integration: ## Run integration tests (requires Ubuntu with passwordless sudo)
	@printf '%b\n' "${CYAN}Running integration tests...${NC}" >&2
	@set -e; \
	$(UV) run pytest tests/integration -v || rc=$$?; \
	if [ "$${rc:-0}" -eq 5 ]; then \
		printf '%b\n' "${YELLOW}No tests collected (pytest exit code 5) — treating as success.${NC}"; \
	else \
		exit "$${rc:-0}"; \
	fi
	@printf '%b\n' "${GREEN}test-integration complete${NC}" >&2

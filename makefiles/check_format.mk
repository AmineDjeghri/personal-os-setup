# Check Format targets
# This file contains targets for checking code format

.PHONY: pre-commit-install _pre-commit-install-auto pre-commit-status pre-commit lint format docs-build check

pre-commit-install: ## Install the git hooks once after install-dev
	@echo "${YELLOW}=========> Installing pre-commit...${NC}"
	$(UV) run --no-sync pre-commit install --hook-type pre-commit --hook-type commit-msg

_pre-commit-install-auto: # Used by install-dev: install the Git hooks in a real checkout only (not in CI or Docker)
	@if [ -z "$$CI" ] && git rev-parse --git-dir >/dev/null 2>&1; then \
	  $(MAKE) --no-print-directory pre-commit-install || echo "${YELLOW}Git hooks not installed (see the error above); fix it, then run: make pre-commit-install${NC}"; \
	fi

pre-commit-status: ## Warn when the Git hooks are not installed (non-fatal; skipped in CI)
	@if [ -z "$$CI" ] && git rev-parse --git-dir >/dev/null 2>&1; then \
	  hooks=$$(git rev-parse --git-path hooks); \
	  if [ -f "$$hooks/pre-commit" ] && [ -f "$$hooks/commit-msg" ]; then \
	    echo "${GREEN}Git hooks installed.${NC}"; \
	  else \
	    echo "${YELLOW}WARNING: Git hooks are not installed, so commits and commit messages go unchecked. Run: make pre-commit-install${NC}"; \
	  fi; \
	fi

pre-commit: ## Run checks using the prepared development environment
	@echo "${YELLOW}=========> Running pre-commit...${NC}"
	$(UV) run --no-sync pre-commit run $(if $(strip $(FILES)),--files $(FILES),--all-files) $(ARGS)

lint: ## Lint code with Ruff
	@echo "Linting code..."
	@$(UV) run --no-sync ruff check .

format: ## Format code with Ruff
	@echo "Formatting code..."
	@$(UV) run --no-sync ruff format .

docs-build: ## Build strict documentation without starting a server
	@echo "${YELLOW}=========> Building documentation (strict)...${NC}"
	@site=$$(mktemp -d); trap 'rm -rf "$$site"' EXIT; \
	$(UV) run --no-sync properdocs build -f properdocs.yml --strict --site-dir "$$site"

check: ## Run all static/docs hooks and self-contained software checks
	@$(MAKE) --no-print-directory pre-commit-status
	@$(MAKE) --no-print-directory pre-commit
	@$(MAKE) --no-print-directory test-all
	@$(MAKE) --no-print-directory docs-build
	@echo "${YELLOW}=========> All quality gates passed.${NC}"

# Check Format targets
# This file contains targets for checking code format

.PHONY: pre-commit-install pre-commit lint format docs-build check

PRE_COMMIT_ARGS ?= --all-files

pre-commit-install: ## Install the git hooks once after install-dev
	@echo "${YELLOW}=========> Installing pre-commit...${NC}"
	$(UV) run --no-sync pre-commit install --hook-type pre-commit --hook-type commit-msg

pre-commit: ## Run checks using the prepared development environment
	@echo "${YELLOW}=========> Running pre-commit...${NC}"
	$(UV) run --no-sync pre-commit run $(PRE_COMMIT_ARGS)

lint: ## Lint code with Ruff
	@echo "Linting code..."
	@$(UV) run --no-sync ruff check .

format: ## Format code with Ruff
	@echo "Formatting code..."
	@$(UV) run --no-sync ruff format .

docs-build: ## Build strict documentation without starting a server
	@echo "${YELLOW}=========> Building documentation (strict)...${NC}"
	@site=$$(mktemp -d); trap 'rm -rf "$$site"' EXIT; \
	$(UV) run --no-sync properdocs build -f properdocs.yml --strict --quiet --site-dir "$$site"

check: ## Run all static/docs hooks and self-contained software checks
	@$(MAKE) --no-print-directory pre-commit
	@$(MAKE) --no-print-directory test-all
	@echo "${YELLOW}=========> All quality gates passed.${NC}"

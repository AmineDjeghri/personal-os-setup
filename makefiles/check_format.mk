# Check Format targets
# This file contains targets for checking code format

.PHONY: pre-commit-install pre-commit lint format docs-build check

pre-commit-install: install-dev
	@echo "${YELLOW}=========> Installing pre-commit...${NC}"
	$(UV) run pre-commit install --hook-type pre-commit --hook-type commit-msg

pre-commit: pre-commit-install ## Run pre-commit
	@echo "${YELLOW}=========> Running pre-commit...${NC}"
	$(UV) run pre-commit run --all-files

lint: ## Lint code with Ruff
	@echo "Linting code..."
	@$(UV) run ruff check .

format: ## Format code with Ruff
	@echo "Formatting code..."
	@$(UV) run ruff format .

docs-build: ## Build strict documentation without starting a server
	@echo "${YELLOW}=========> Building documentation (strict)...${NC}"
	@$(UV) run properdocs build -f properdocs.yml --strict --quiet --site-dir "$$(mktemp -d)"

check: lint test-all docs-build ## Run static checks, every self-contained suite and strict docs
	@echo "${YELLOW}=========> All quality gates passed.${NC}"

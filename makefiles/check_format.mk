# Check Format targets
# This file contains targets for checking code format

.PHONY: pre-commit-install pre-commit lint format

pre-commit-install: install-dev
	@echo "${YELLOW}=========> Installing pre-commit...${NC}"
	$(UV) run pre-commit install

pre-commit: pre-commit-install ## Run pre-commit
	@echo "${YELLOW}=========> Running pre-commit...${NC}"
	$(UV) run pre-commit run --all-files

lint: ## Lint code with Ruff
	@echo "Linting code..."
	@$(UV) run ruff check .

format: ## Format code with Ruff
	@echo "Formatting code..."
	@$(UV) run ruff format .

# Check Format targets
# This file contains targets for checking code format

.PHONY: pre-commit-install pre-commit lint format

pre-commit-install: install-dev ## Install the pre-commit and commit-msg hooks
	@printf '%b\n' "${CYAN}=========> Installing pre-commit...${NC}" >&2
	@$(UV) run pre-commit install --hook-type pre-commit --hook-type commit-msg
	@printf '%b\n' "${GREEN}pre-commit-install complete${NC}" >&2

pre-commit: pre-commit-install ## Run pre-commit
	@printf '%b\n' "${CYAN}=========> Running pre-commit...${NC}" >&2
	@$(UV) run pre-commit run --all-files
	@printf '%b\n' "${GREEN}pre-commit complete${NC}" >&2

lint: ## Lint code with Ruff
	@printf '%b\n' "${CYAN}Linting code...${NC}" >&2
	@$(UV) run ruff check .
	@printf '%b\n' "${GREEN}lint complete${NC}" >&2

format: ## Format code with Ruff
	@printf '%b\n' "${CYAN}Formatting code...${NC}" >&2
	@$(UV) run ruff format .
	@printf '%b\n' "${GREEN}format complete${NC}" >&2

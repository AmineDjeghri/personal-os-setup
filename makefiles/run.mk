# Run targets
# This file contains targets for running the application

.PHONY: run

run: ## Run the Application
	@printf '%b\n' "${CYAN}Starting server...${NC}" >&2
	@$(UV) run python src/personal_os_setup/frontend/main.py
	@printf '%b\n' "${GREEN}run complete${NC}" >&2

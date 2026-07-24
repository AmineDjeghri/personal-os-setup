# Run targets
# This file contains targets for running the application

.PHONY: run

run: ## Run the Stremio Addon (Dev Mode)
	@echo "Starting server..."
	@$(UV) run python src/personal_os_setup/frontend/main.py

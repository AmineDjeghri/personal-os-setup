# Cleaning targets
# This file contains all cleanup-related targets

.PHONY: prune-uv clean-uv-cache clean

prune-uv: ## Removes all unused cache entries
	@printf '%b\n' "${CYAN}=========> Prune uv cache...${NC}" >&2
	@$(UV) cache prune
	@printf '%b\n' "${GREEN}prune-uv complete${NC}" >&2

clean-uv-cache: ## Removes all cache entries from the cache directory,
	@printf '%b\n' "${CYAN}=========> Cleaning uv cache...${NC}" >&2
	@$(UV) cache clean
	@printf '%b\n' "${GREEN}clean-uv-cache complete${NC}" >&2

clean: clean-uv-cache ## Clean up cache and temp files
	@printf '%b\n' "${CYAN}Cleaning up...${NC}" >&2
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@rm -rf __pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@printf '%b\n' "${GREEN}clean complete${NC}" >&2

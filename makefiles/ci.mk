# CI/CD targets
# This file contains targets for local CI/CD testing with GitHub Actions

.PHONY: install-act act clear_ci_cache

install-act: ## Install GitHub Actions act for local testing
	@printf '%b\n' "${CYAN}=========> Installing github actions act to test locally${NC}" >&2
	@curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/nektos/act/master/install.sh | bash
	@printf '%b\n' "${YELLOW}Github act version is :${NC}"
	@./bin/act --version
	@printf '%b\n' "${GREEN}install-act complete${NC}" >&2

act: install-act ## Run Github Actions locally
	@printf '%b\n' "${CYAN}Running Github Actions locally...${NC}" >&2
	@./bin/act --env-file .env
	@printf '%b\n' "${GREEN}act complete${NC}" >&2

clear_ci_cache: ## Clear GitHub local caches
	@printf '%b\n' "${CYAN}Clearing CI cache...${NC}" >&2
	@printf '%b\n' "${YELLOW}Clearing Github ACT local cache...${NC}"
	@rm -rf ~/.cache/act ~/.cache/actcache
	@printf '%b\n' "${GREEN}clear_ci_cache complete${NC}" >&2

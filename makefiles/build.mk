# Build and deployment targets
# This file contains targets for building packages and deploying documentation

.PHONY: build-package deploy-doc-local deploy-doc-gh

build-package: ## Build package (wheel)
	@printf '%b\n' "${CYAN}=========> Building python package and wheel...${NC}" >&2
	@$(UV) build
	@printf '%b\n' "${GREEN}build-package complete${NC}" >&2

deploy-doc-local: install-dev ## Deploy documentation locally
	@printf '%b\n' "${CYAN}Deploying documentation locally...${NC}" >&2
	@$(UV) run properdocs build && $(UV) run properdocs serve
	@printf '%b\n' "${GREEN}deploy-doc-local complete${NC}" >&2

# Deploy it to the gh-pages branch in your GitHub repository (you need to setup the GitHub Pages in github settings to use the gh-pages branch)
deploy-doc-gh: install-dev ## Deploy documentation to GitHub Pages
	@printf '%b\n' "${CYAN}Deploying documentation in github actions..${NC}" >&2
	@$(UV) run properdocs build && $(UV) run properdocs gh-deploy
	@printf '%b\n' "${GREEN}deploy-doc-gh complete${NC}" >&2

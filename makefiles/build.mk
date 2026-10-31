# Build and deployment targets
# This file contains targets for building packages and deploying documentation

.PHONY: build-package deploy-doc-local deploy-doc-gh

build-package: ## Build and verify a complete wheel/sdist pair for the current version
	@echo "${YELLOW}=========> Building python package and wheel...${NC}"
	@$(UV) build --clear
	@$(UV) run --no-sync python scripts/check_artifacts.py

deploy-doc-local: ## Deploy documentation locally
	@echo "${YELLOW}Deploying documentation locally...${NC}"
	@$(UV) run --no-sync properdocs serve -f properdocs.yml

# Deploy it to the gh-pages branch in your GitHub repository (you need to setup the GitHub Pages in github settings to use the gh-pages branch)
deploy-doc-gh: ## Deploy documentation to GitHub Pages
	@echo "${YELLOW}Deploying documentation in github actions..${NC}"
	@$(UV) run --no-sync properdocs gh-deploy -f properdocs.yml --strict

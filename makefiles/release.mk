# Release targets. A laptop and GitHub Actions (main-release.yml, dev-release.yml) run the same ones.
# The logic is in scripts/release.sh; docs/developer/5.release.md explains the flow.

.PHONY: release-version release-assets release

release-version: ## On a clean main/dev in sync with origin: version, changelog, commit, tag, push, GitHub release
	@printf '%b\n' "${CYAN}=========> release-version...${NC}" >&2
	@UV="$(UV)" scripts/release.sh version
	@printf '%b\n' "${GREEN}release-version complete${NC}" >&2

release-assets: ## Attach dist/ wheel + sdist of the current version to its GitHub release
	@printf '%b\n' "${CYAN}=========> release-assets...${NC}" >&2
	@UV="$(UV)" scripts/release.sh assets
	@printf '%b\n' "${GREEN}release-assets complete${NC}" >&2

release: ## release-version, then build-package and release-assets (docs: make deploy-doc-gh after)
	@printf '%b\n' "${CYAN}=========> release...${NC}" >&2
	@UV="$(UV)" scripts/release.sh release
	@printf '%b\n' "${GREEN}release complete${NC}" >&2

# Release targets. A laptop and GitHub Actions (main-release.yml, dev-release.yml) run the same ones.
# The logic is in scripts/release.sh; docs/developer/5.release.md explains the flow.

.PHONY: release-version release-assets release

release-version: ## On a clean main/dev in sync with origin: version, changelog, commit, tag, push, GitHub release
	@UV="$(UV)" scripts/release.sh version

release-assets: ## Attach dist/ wheel + sdist of the current version to its GitHub release
	@UV="$(UV)" scripts/release.sh assets

release: ## release-version, then build-package and release-assets (docs: make deploy-doc-gh after)
	@UV="$(UV)" scripts/release.sh release

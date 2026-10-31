# Release logic is shared by manual releases and the main workflow.
.PHONY: release-version release-assets release

release-version: ## Version/tag/push from tested main; build and smoke-check before publishing the tag (requires RELEASE_SHA)
	@UV="$(UV)" scripts/release.sh version

release-assets: ## Validate the clean tagged checkout and assets, upload missing files, then publish the draft
	@UV="$(UV)" scripts/release.sh assets

release: ## Version and verify artifacts, then finish or recover GitHub publication (requires RELEASE_SHA)
	@UV="$(UV)" scripts/release.sh release

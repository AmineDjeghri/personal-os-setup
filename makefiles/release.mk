# Release logic is shared by manual releases and the main/dev workflow.
.PHONY: release-version release-assets release release-status

release-status: ## Report whether a release can run: branch, tree, origin sync, tag, GitHub release
	@$(UV) run --no-sync python scripts/release_status.py

release-version: ## Version/tag/push from main/dev; build and smoke-check before publishing the tag
	@UV="$(UV)" scripts/release.sh version

release-assets: ## Validate the clean tagged checkout and assets, upload missing files, then publish the draft
	@UV="$(UV)" scripts/release.sh assets

release: ## Version and verify artifacts, then finish or recover GitHub publication
	@UV="$(UV)" scripts/release.sh release

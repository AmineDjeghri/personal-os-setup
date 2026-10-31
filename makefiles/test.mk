# Self-contained checks are safe locally. OS integration is an explicit, separate target.
.PHONY: test-wheel test-installation test test-local test-all test-coverage test-integration

N ?= 4

# Full gates reject diagnostic options instead of reporting partial execution as validation.
require-full-tests = $(if $(strip $(PYTEST_ARGS) $(PYTEST_ADDOPTS)),$(error $@ requires complete execution; use test-local PYTEST_ARGS="..." for focused or collection-only runs))

test-installation: build-package ## Build and verify artifacts, then smoke-check the installed wheel
	@$(MAKE) --no-print-directory test-wheel

test-wheel: ## Install the existing verified wheel in isolation and load its entry point without starting the app
	@set -e; \
	wheel=$$($(UV) run --no-sync python scripts/check_artifacts.py --wheel); \
	version=$$($(UV) run --no-sync python scripts/check_artifacts.py --version); \
	$(UV) run --isolated --no-project --with "$$wheel" python scripts/check_installation.py "$$version"

test: test-local ## Alias for the safe local suites

test-local: ## Run unit and isolated skills tests (N=4 workers by default; empty collection fails)
	@$(UV) run --no-sync python -m pytest tests/unit tests/skills --numprocesses=$(N) $(PYTEST_ARGS)

test-all: ## Run safe local suites and the built-wheel smoke; OS integration remains separate
	$(require-full-tests)
	@$(MAKE) --no-print-directory test-local $(if $(filter 1,$(TEST_COVERAGE)),PYTEST_ARGS="--cov=personal_os_setup --cov=scripts --cov-report=term-missing --cov-report=xml:reports/coverage.xml")
	@$(MAKE) --no-print-directory test-installation

# Coverage reuses test-all, without running the same suites twice in CI.
test-coverage: ## Run safe checks and report coverage separately from OS integration completeness
	$(require-full-tests)
	@$(MAKE) --no-print-directory test-all TEST_COVERAGE=1

# Serial: real package managers cannot safely share state across parallel tests.
# The reporting plugin allows other platforms' skips, but requires complete execution.
test-integration: ## CI/disposable hosts only: Linux/macOS mutate packages; Windows checks are read-only
	$(require-full-tests)
	@$(UV) run --no-sync python -m pytest -p scripts.integration_results tests/integration -v -ra

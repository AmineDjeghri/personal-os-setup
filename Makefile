# Main Makefile
# This file includes all modular makefiles from the makefiles/ directory
# Each makefile is organized by functionality for better maintainability

# Include common variables and settings
include makefiles/common.mk

# Include all modular makefiles
include makefiles/install.mk
include makefiles/run.mk
include makefiles/check_format.mk
include makefiles/test.mk
include makefiles/clean.mk
include makefiles/ci.mk
include makefiles/build.mk
include makefiles/vm.mk

.PHONY: all help

all: help

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@echo "Installation:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/install.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Checkers & formatters:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/check_format.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Running the Application:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/run.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Testing:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/test.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Cleaning:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/clean.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "CI/CD:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/ci.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Build & Deploy:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/build.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Virtual Machines:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' makefiles/vm.mk | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

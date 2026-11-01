# Common variables and settings
# This file contains shared variables used across all makefiles

PACKAGE_NAME = src
TEST_DIR = tests

ENV_FILE_PATH := .env
-include $(ENV_FILE_PATH) # keep the '-' to ignore this file if it doesn't exist.(Used in gitlab ci)

# Colors
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
CYAN=\033[0;36m
NC=\033[0m

# UV path detection
ifeq ($(OS),Windows_NT)
UV := uv
else
UV := $(shell command -v uv 2>/dev/null || echo "$$HOME/.local/bin/uv")
endif

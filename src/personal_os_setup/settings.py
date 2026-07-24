"""Settings and logging configuration for personal-os-setup."""

from __future__ import annotations

import sys

from loguru import logger as _loguru_logger
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseEnvironmentSettings(BaseSettings):
    """Base settings for environment configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ApplicationSettings(BaseEnvironmentSettings):
    """Configuration for personal-os-setup.

    Values are read from environment variables and optionally
    overridden by a ``.env`` file.
    """

    # --- Runtime ---
    logging_level: str = Field(
        default="CRITICAL",
        validation_alias=AliasChoices("LOGGING_LEVEL", "logging_level"),
        description="Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # Example of a model validator
    # @model_validator(mode="after")
    # def set_os_environ(self) -> Self:
    #     """Sync environment variables after settings load."""
    #     os.environ["DEV_MODE"] = str(self.DEV_MODE)
    #     return self


def _initialize_logger(settings: ApplicationSettings):
    """Initialize the loguru logger with app-specific configuration."""
    level = settings.logging_level

    # Remove the default loguru sink (ID 0) to prevent a duplicate when we add our logger.
    try:
        _loguru_logger.remove(0)
    except ValueError:
        pass  # already removed

    _loguru_logger.add(
        sys.stderr,
        level=level,
        filter=lambda record: record["extra"].get("name") == "personal-os-setup",
    )

    return _loguru_logger.bind(name="personal-os-setup")


settings = ApplicationSettings()
logger = _initialize_logger(settings)

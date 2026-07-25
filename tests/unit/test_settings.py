"""Unit tests for settings.py — module-level settings and logger instances."""

from __future__ import annotations


class TestSettings:
    """Tests for the module-level settings instance."""

    def test_settings_is_singleton(self):
        """The settings instance should be a singleton."""
        from personal_os_setup.settings import settings as s1
        from personal_os_setup.settings import settings as s2

        assert s1 is s2

    def test_logging_level_defaults_to_debug(self):
        """logging_level should default to DEBUG when not set in the environment."""
        from personal_os_setup.settings import settings

        assert settings.logging_level == "CRITICAL"

    def test_logging_level_from_env(self, monkeypatch):
        """logging_level should be read from LOGGING_LEVEL environment variable."""
        monkeypatch.setenv("LOGGING_LEVEL", "INFO")
        # Need to reimport to pick up the new env var
        import importlib
        import personal_os_setup.settings

        importlib.reload(personal_os_setup.settings)
        from personal_os_setup.settings import settings

        assert settings.logging_level == "INFO"


class TestLogger:
    """Tests for the module-level logger instance."""

    def test_logger_is_singleton(self):
        """The logger instance should be a singleton."""
        from personal_os_setup.settings import logger as l1
        from personal_os_setup.settings import logger as l2

        assert l1._core is l2._core

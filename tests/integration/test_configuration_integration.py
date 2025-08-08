# tests/integration/test_configuration_integration.py
"""
Integration tests for configuration management system.

These tests verify that all configuration components work together
correctly across different environments and scenarios.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config.settings import Settings, get_settings, reload_settings
from src.config.environments import (
    EnvironmentDetector,
    ConfigurationLoader,
    initialize_environment,
    get_environment_config
)
from src.core.browser_manager import get_browser_manager, BrowserManager
from src.core.logger import setup_logging, get_logger


class TestConfigurationIntegration:
    """Test configuration system integration."""

    def setup_method(self):
        """Reset configuration state before each test."""
        # Clear any cached settings
        get_settings.cache_clear()

    def test_environment_detection_integration(self):
        """Test environment detection with real environment variables."""
        # Test CI environment detection
        with patch.dict(os.environ, {"CI": "true", "GITHUB_ACTIONS": "true"}):
            detector = EnvironmentDetector()
            env = detector.detect_environment()
            assert env.value in ["testing", "ci"]

        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            env = detector.detect_environment()
            assert env.value == "development"

    def test_configuration_loading_with_env_files(self):
        """Test configuration loading with actual .env files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test .env file
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("""
ENVIRONMENT=testing
DEBUG=true
BROWSER__NAME=chromium
BROWSER__HEADLESS=true
BROWSER__VIEWPORT_WIDTH=1600
BROWSER__TIMEOUT=20000
API__BASE_URL=http://test.local:8080/api
""")

            # Change working directory temporarily
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Reload settings to pick up new .env file
                reload_settings()
                settings = get_settings()

                assert settings.environment.value == "testing"
                assert settings.debug is True
                assert settings.browser.name == "chromium"
                assert settings.browser.headless is True
                assert settings.browser.viewport_width == 1600
                assert settings.browser.timeout == 20000
                assert "test.local" in settings.api.base_url

            finally:
                os.chdir(original_cwd)

    def test_browser_manager_with_configuration(self):
        """Test browser manager integration with configuration."""
        # Test with development configuration
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "BROWSER__NAME": "firefox",
            "BROWSER__HEADLESS": "false",
            "BROWSER__TIMEOUT": "45000"
        }):
            reload_settings()
            manager = BrowserManager()

            # Verify configuration is applied
            assert manager.settings.browser.name == "firefox"
            assert manager.settings.browser.headless is False
            assert manager.settings.browser.timeout == 45000

            # Test launch options generation
            launch_options = manager.factory.create_launch_options()
            assert launch_options["headless"] is False
            assert launch_options["timeout"] == 45000

    def test_logging_configuration_integration(self):
        """Test logging system integration with settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            # Configure logging with settings
            setup_logging(
                log_level="DEBUG",
                enable_file=True,
                log_file_path=log_file,
                enable_json_format=True
            )

            # Test logging functionality
            logger = get_logger("test_integration")
            logger.info("Integration test message", component="configuration")

            # Verify log file was created and contains expected content
            assert log_file.exists()
            log_content = log_file.read_text()
            assert "Integration test message" in log_content
            assert "configuration" in log_content

    def test_cross_environment_configuration(self):
        """Test configuration behavior across different environments."""
        environments = ["development", "testing", "staging", "production"]

        for env in environments:
            with patch.dict(os.environ, {"ENVIRONMENT": env}):
                reload_settings()
                settings = get_settings()

                assert settings.environment.value == env

                # Verify environment-specific adaptations
                if env == "production":
                    assert settings.browser.headless is True
                    assert settings.debug is False
                    assert settings.api.validate_ssl is True

                elif env == "development":
                    # Development can have flexible settings
                    assert settings.logging.level in ["DEBUG", "INFO"]

                elif env == "testing":
                    assert settings.browser.headless is True
                    # Testing should have reasonable timeouts
                    assert settings.browser.timeout <= 30000

    def test_configuration_validation_integration(self):
        """Test configuration validation across components."""
        # Test invalid configuration
        with pytest.raises(ValueError):
            Settings(
                browser__timeout=0,  # Invalid timeout
                api__base_url="invalid-url"  # Invalid URL
            )

        # Test configuration consistency validation
        with pytest.raises(ValueError):
            Settings(
                environment="production",
                debug=True,  # Debug shouldn't be enabled in production
                browser__headless=False  # Non-headless in production
            )

    @pytest.mark.asyncio
    async def test_async_configuration_integration(self):
        """Test configuration with async operations."""
        from src.core.browser_manager import get_browser_manager

        manager = get_browser_manager()

        # Test async browser session creation
        async with manager.async_browser_session("chromium") as session:
            assert session is not None
            assert session.browser_name == "chromium"

            # Verify configuration was applied
            config_summary = manager.get_session_stats()
            assert config_summary["total_sessions"] == 1

    def test_configuration_error_handling(self):
        """Test error handling in configuration system."""
        # Test missing required environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Should use defaults gracefully
            settings = Settings()
            assert settings.environment.value in ["local", "development"]

        # Test malformed environment values
        with patch.dict(os.environ, {
            "BROWSER__TIMEOUT": "invalid_number"
        }):
            # Should raise validation error
            with pytest.raises(ValueError):
                Settings()

    def test_configuration_override_precedence(self):
        """Test configuration override precedence order."""
        # Test that environment variables override .env files
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("BROWSER__HEADLESS=false\n")

            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)

                # Environment variable should override .env file
                with patch.dict(os.environ, {"BROWSER__HEADLESS": "true"}):
                    reload_settings()
                    settings = get_settings()
                    assert settings.browser.headless is True

            finally:
                os.chdir(original_cwd)

    def test_full_framework_integration(self):
        """Test full framework integration with realistic scenario."""
        # Simulate a complete test scenario with configuration
        with patch.dict(os.environ, {
            "ENVIRONMENT": "testing",
            "BROWSER__NAME": "chromium",
            "BROWSER__HEADLESS": "true",
            "API__BASE_URL": "http://localhost:8080/api",
            "TEST__PARALLEL_WORKERS": "2"
        }):
            # Initialize environment
            config = initialize_environment()

            # Setup logging
            setup_logging(
                log_level=config.logging.level,
                enable_console=True,
                enable_file=False
            )

            # Create browser manager
            browser_manager = get_browser_manager(config)

            # Verify everything is configured correctly
            assert config.environment.value == "testing"
            assert browser_manager.settings.browser.name == "chromium"
            assert browser_manager.settings.api.base_url == "http://localhost:8080/api"

            # Test that browser can be launched with this configuration
            with browser_manager.browser_session() as session:
                assert session.browser_name == "chromium"

                # Test that we can get configuration summary
                summary = browser_manager.get_session_stats()
                assert summary["total_sessions"] == 1
                assert summary["browser_counts"]["chromium"] == 1
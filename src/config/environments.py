# src/config/environments.py
"""
Environment-Specific Configuration Module

This module handles environment detection, configuration loading,
and environment-specific overrides. It demonstrates enterprise patterns
for managing multiple deployment environments.

Key Design Patterns:
- Strategy Pattern: Different configuration strategies per environment
- Factory Pattern: Environment-specific configuration creation
- Template Method: Common configuration loading with environment-specific customization

Interview Highlights:
- Sophisticated environment detection and management
- Secure configuration handling across environments
- Production-ready configuration validation
- Flexible override mechanisms for different deployment scenarios
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Type

from settings import (
    Environment,
    Settings,
    create_ci_settings,
    create_development_settings,
    create_production_settings,
    get_settings,
)


class EnvironmentDetector:
    """
    Intelligent environment detection based on multiple signals.

    This class examines various environment indicators to automatically
    determine the current execution environment. It's particularly useful
    in CI/CD pipelines and containerized deployments.
    """

    @staticmethod
    def detect_environment() -> Environment:
        """
        Detect current environment from multiple sources.

        Detection priority:
        1. Explicit ENVIRONMENT variable
        2. CI/CD environment indicators
        3. Container environment signals
        4. Development environment hints
        5. Default to development

        Returns:
            Environment: Detected environment enum value
        """
        # Check explicit environment variable (highest priority)
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var:
            try:
                return Environment(env_var)
            except ValueError:
                pass  # Fall through to other detection methods

        # Check for CI/CD environment indicators
        if EnvironmentDetector._is_ci_environment():
            return Environment.TESTING

        # Check for containerized production environment
        if EnvironmentDetector._is_container_environment():
            return Environment.PRODUCTION

        # Check for development environment indicators
        if EnvironmentDetector._is_development_environment():
            return Environment.DEVELOPMENT

        # Default fallback
        return Environment.DEVELOPMENT

    @staticmethod
    def _is_ci_environment() -> bool:
        """Check if running in a CI/CD environment."""
        ci_indicators = [
            "CI", "CONTINUOUS_INTEGRATION",  # Generic CI
            "GITHUB_ACTIONS",  # GitHub Actions
            "GITLAB_CI",  # GitLab CI
            "JENKINS_URL",  # Jenkins
            "TRAVIS",  # Travis CI
            "CIRCLECI",  # CircleCI
            "BUILDKITE",  # Buildkite
            "AZURE_PIPELINES",  # Azure DevOps
        ]

        return any(os.getenv(indicator) for indicator in ci_indicators)

    @staticmethod
    def _is_container_environment() -> bool:
        """Check if running in a container (Docker/Kubernetes)."""
        container_indicators = [
            # Docker indicators
            lambda: Path("/.dockerenv").exists(),
            lambda: os.getenv("DOCKER_CONTAINER") is not None,

            # Kubernetes indicators
            lambda: os.getenv("KUBERNETES_SERVICE_HOST") is not None,
            lambda: Path("/var/run/secrets/kubernetes.io").exists(),

            # Container runtime indicators
            lambda: "container" in os.getenv("SYSTEMD_EXEC_PID", ""),
        ]

        return any(check() for check in container_indicators)

    @staticmethod
    def _is_development_environment() -> bool:
        """Check if running in a development environment."""
        development_indicators = [
            # Python development indicators
            lambda: hasattr(sys, 'ps1'),  # Interactive session
            lambda: os.getenv("PYTHONPATH") is not None,

            # IDE indicators  
            lambda: any(ide in os.getenv("_", "") for ide in ["pycharm", "vscode", "code"]),

            # Development tools
            lambda: os.getenv("VIRTUAL_ENV") is not None,
            lambda: Path(".git").exists(),  # Git repository
            lambda: Path("pyproject.toml").exists(),  # Python project
        ]

        return any(check() for check in development_indicators)


class ConfigurationLoader:
    """
    Advanced configuration loading with environment-specific overrides.

    This class implements a sophisticated configuration loading strategy
    that supports multiple sources, validation, and environment-specific
    customization.
    """

    def __init__(self, environment: Optional[Environment] = None):
        """
        Initialize configuration loader.

        Args:
            environment: Explicit environment to use, or None for auto-detection
        """
        self.environment = environment or EnvironmentDetector.detect_environment()
        self._config_cache: Optional[Settings] = None

    def load_configuration(self, force_reload: bool = False) -> Settings:
        """
        Load configuration for the current environment.

        Args:
            force_reload: Force reloading configuration even if cached

        Returns:
            Settings: Configured settings instance
        """
        if self._config_cache is None or force_reload:
            self._config_cache = self._create_environment_configuration()
            self._apply_environment_overrides()
            self._validate_configuration()

        return self._config_cache

    def _create_environment_configuration(self) -> Settings:
        """Create base configuration for the detected environment."""
        environment_factories = {
            Environment.DEVELOPMENT: create_development_settings,
            Environment.TESTING: create_ci_settings,
            Environment.STAGING: create_production_settings,  # Use prod settings for staging
            Environment.PRODUCTION: create_production_settings,
        }

        factory = environment_factories.get(self.environment, create_development_settings)
        return factory()

    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides."""
        if not self._config_cache:
            return

        # Load environment-specific override files
        override_files = [
            f".env.{self.environment.value}",
            f"config/{self.environment.value}.env",
            f"configs/{self.environment.value}.json",
        ]

        for override_file in override_files:
            if Path(override_file).exists():
                self._load_override_file(override_file)

    def _load_override_file(self, file_path: str) -> None:
        """Load configuration overrides from a file."""
        # In a full implementation, this would parse JSON/YAML/TOML files
        # For now, we'll handle .env files
        if file_path.endswith('.env'):
            # Environment files are automatically loaded by pydantic-settings
            pass

    def _validate_configuration(self) -> None:
        """Perform comprehensive configuration validation."""
        if not self._config_cache:
            raise ValueError("Configuration not loaded")

        # Environment-specific validation rules
        validation_rules = {
            Environment.PRODUCTION: self._validate_production_config,
            Environment.STAGING: self._validate_staging_config,
            Environment.TESTING: self._validate_testing_config,
            Environment.DEVELOPMENT: self._validate_development_config,
        }

        validator = validation_rules.get(self.environment)
        if validator:
            validator()

    def _validate_production_config(self) -> None:
        """Validate production-specific configuration requirements."""
        config = self._config_cache
        assert config is not None

        # Security requirements
        if config.secret_key == "development-secret-key-change-in-production":
            raise ValueError("Production environment requires secure secret key")

        # Performance requirements
        if not config.browser.headless:
            raise ValueError("Production environment must use headless browser")

        if config.debug:
            raise ValueError("Debug mode must be disabled in production")

        # SSL requirements
        if not config.api.validate_ssl:
            raise ValueError("SSL validation must be enabled in production")

    def _validate_staging_config(self) -> None:
        """Validate staging-specific configuration requirements."""
        # Staging should be similar to production but allow some debugging
        config = self._config_cache
        assert config is not None

        if not config.browser.headless:
            print("Warning: Non-headless browser in staging environment")

    def _validate_testing_config(self) -> None:
        """Validate testing-specific configuration requirements."""
        config = self._config_cache
        assert config is not None

        # Testing optimizations
        if config.browser.slow_mo > 0:
            print("Warning: slow_mo enabled in testing environment may slow down tests")

    def _validate_development_config(self) -> None:
        """Validate development-specific configuration requirements."""
        # Development has the most relaxed validation
        pass


class EnvironmentManager:
    """
    High-level environment management facade.

    This class provides a simple interface for environment-aware
    configuration management and is the main entry point for
    the configuration system.
    """

    def __init__(self):
        """Initialize environment manager."""
        self._loader: Optional[ConfigurationLoader] = None
        self._current_environment: Optional[Environment] = None

    def initialize(self, environment: Optional[Environment] = None) -> Settings:
        """
        Initialize configuration for the specified environment.

        Args:
            environment: Target environment, or None for auto-detection

        Returns:
            Settings: Configured settings instance
        """
        self._current_environment = environment or EnvironmentDetector.detect_environment()
        self._loader = ConfigurationLoader(self._current_environment)

        return self._loader.load_configuration()

    def get_configuration(self) -> Settings:
        """
        Get current configuration instance.

        Returns:
            Settings: Current configuration

        Raises:
            RuntimeError: If environment not initialized
        """
        if not self._loader:
            raise RuntimeError("Environment not initialized. Call initialize() first.")

        return self._loader.load_configuration()

    def reload_configuration(self) -> Settings:
        """
        Force reload of configuration from all sources.

        Returns:
            Settings: Reloaded configuration
        """
        if not self._loader:
            return self.initialize()

        return self._loader.load_configuration(force_reload=True)

    def switch_environment(self, environment: Environment) -> Settings:
        """
        Switch to a different environment configuration.

        Args:
            environment: Target environment

        Returns:
            Settings: Configuration for new environment
        """
        return self.initialize(environment)

    @property
    def current_environment(self) -> Optional[Environment]:
        """Get the current environment."""
        return self._current_environment

    def is_environment(self, environment: Environment) -> bool:
        """Check if currently running in specified environment."""
        return self._current_environment == environment

    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get comprehensive environment information.

        Returns:
            Dict containing environment details for debugging/logging
        """
        return {
            "environment": self._current_environment.value if self._current_environment else "unknown",
            "auto_detected": self._current_environment == EnvironmentDetector.detect_environment(),
            "ci_environment": EnvironmentDetector._is_ci_environment(),
            "container_environment": EnvironmentDetector._is_container_environment(),
            "development_environment": EnvironmentDetector._is_development_environment(),
            "python_version": sys.version,
            "working_directory": str(Path.cwd()),
            "environment_variables": {
                key: value for key, value in os.environ.items()
                if key.startswith(("ENV", "ENVIRONMENT", "CI", "DOCKER", "KUBERNETES"))
            }
        }


# Global environment manager instance
_environment_manager = EnvironmentManager()


def initialize_environment(environment: Optional[Environment] = None) -> Settings:
    """
    Initialize the global environment configuration.

    This is the main entry point for configuration initialization.
    Should be called once at application startup.

    Args:
        environment: Explicit environment to use, or None for auto-detection

    Returns:
        Settings: Initialized configuration

    Example:
        >>> # Auto-detect environment
        >>> config = initialize_environment()
        >>> 
        >>> # Explicit environment
        >>> config = initialize_environment(Environment.TESTING)
    """
    return _environment_manager.initialize(environment)


def get_current_environment() -> Optional[Environment]:
    """Get the current active environment."""
    return _environment_manager.current_environment


def is_environment(environment: Environment) -> bool:
    """Check if currently running in the specified environment."""
    return _environment_manager.is_environment(environment)


def get_environment_config() -> Settings:
    """
    Get the current environment configuration.

    Returns:
        Settings: Current configuration instance

    Raises:
        RuntimeError: If environment not initialized
    """
    return _environment_manager.get_configuration()


def reload_environment_config() -> Settings:
    """Force reload of the environment configuration."""
    return _environment_manager.reload_configuration()


# Convenience functions for common environment checks
def is_production() -> bool:
    """Check if running in production environment."""
    return is_environment(Environment.PRODUCTION)


def is_development() -> bool:
    """Check if running in development environment."""
    return is_environment(Environment.DEVELOPMENT)


def is_testing() -> bool:
    """Check if running in testing/CI environment."""
    return is_environment(Environment.TESTING)


def is_staging() -> bool:
    """Check if running in staging environment."""
    return is_environment(Environment.STAGING)
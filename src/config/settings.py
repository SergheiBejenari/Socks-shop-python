# src/config/settings.py
"""
Environment-Aware Configuration Management with Pydantic v2

This module provides comprehensive configuration management that:
- Loads settings from multiple sources (defaults → .env → environment variables)
- Validates all configuration with Pydantic v2
- Handles sensitive data securely
- Supports different environments (dev, test, staging, prod)
- Integrates with CI/CD systems

Key Design Patterns:
- Settings Pattern: Centralized configuration with validation
- Environment Pattern: Environment-specific overrides
- Security Pattern: Sensitive data handling

Interview Highlights:
- Production-ready configuration management
- Pydantic v2 validation with custom validators
- Hierarchical configuration loading
- Secure sensitive data handling
- CI/CD and cloud integration ready
"""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments with specific behaviors."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class BrowserSettings(BaseModel):
    """
    Browser configuration settings with validation.

    These settings control browser behavior, performance,
    and compatibility across different environments.
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Browser selection and basic settings
    name: str = Field(
        default="chromium",
        description="Browser type (chromium, firefox, webkit)"
    )

    headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )

    # Viewport configuration
    viewport_width: int = Field(
        default=1920,
        ge=320,
        le=3840,
        description="Browser viewport width (320-3840)"
    )

    viewport_height: int = Field(
        default=1080,
        ge=568,
        le=2160,
        description="Browser viewport height (568-2160)"
    )

    # Performance settings
    timeout: int = Field(
        default=30000,
        ge=5000,
        le=300000,
        description="Browser timeout in milliseconds (5s-5min)"
    )

    slow_mo: int = Field(
        default=0,
        ge=0,
        le=5000,
        description="Slow down operations by milliseconds"
    )

    # Resource management
    max_concurrent_browsers: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent browser instances"
    )

    # Browser arguments
    args: List[str] = Field(
        default_factory=lambda: [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu"
        ],
        description="Browser command line arguments"
    )

    # Recording and debugging
    record_video: bool = Field(
        default=False,
        description="Record videos of test execution"
    )

    screenshot_mode: str = Field(
        default="only-on-failure",
        description="Screenshot capture mode (off, on, only-on-failure)"
    )

    @field_validator("name")
    @classmethod
    def validate_browser_name(cls, v: str) -> str:
        """Validate browser name is supported."""
        supported = {"chromium", "firefox", "webkit", "chrome", "safari"}
        if v.lower() not in supported:
            raise ValueError(f"Unsupported browser: {v}. Choose from {supported}")
        return v.lower()

    @field_validator("screenshot_mode")
    @classmethod
    def validate_screenshot_mode(cls, v: str) -> str:
        """Validate screenshot mode."""
        valid_modes = {"off", "on", "only-on-failure"}
        if v not in valid_modes:
            raise ValueError(f"Invalid screenshot mode: {v}. Choose from {valid_modes}")
        return v

    @field_validator("args", mode="before")
    @classmethod
    def parse_args(cls, v) -> List[str]:
        """Parse browser arguments from string or list."""
        if isinstance(v, str):
            return [arg.strip() for arg in v.split(",") if arg.strip()]
        return v or []


class APISettings(BaseModel):
    """API configuration with comprehensive validation."""
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    # Base configuration
    base_url: str = Field(
        default="http://localhost:8080/api",
        description="Base API URL"
    )

    # Timeouts and retries
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="API request timeout in seconds"
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts"
    )

    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Base retry delay in seconds"
    )

    # Security settings
    validate_ssl: bool = Field(
        default=True,
        description="Validate SSL certificates"
    )

    # Headers
    default_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "SockShop-TestFramework/1.0"
        },
        description="Default HTTP headers"
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate base URL format."""
        try:
            result = urlparse(v)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
            return v.rstrip("/")
        except Exception as e:
            raise ValueError(f"Invalid base_url: {e}")


class DatabaseSettings(BaseModel):
    """Database configuration for test data management."""
    model_config = ConfigDict(extra="forbid")

    host: str = Field(default="localhost")
    port: int = Field(default=5432, ge=1, le=65535)
    name: str = Field(default="sockshop_test")
    username: str = Field(default="testuser")
    password: Optional[str] = Field(default=None, repr=False)  # Don't show in repr

    # Connection pool
    max_connections: int = Field(default=10, ge=1, le=100)
    min_connections: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_connection_pool(self) -> "DatabaseSettings":
        """Validate connection pool settings."""
        if self.min_connections > self.max_connections:
            raise ValueError("min_connections cannot exceed max_connections")
        return self

    def get_connection_string(self, include_password: bool = True) -> str:
        """Generate database connection string."""
        if include_password and self.password:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"
        return f"postgresql://{self.username}@{self.host}:{self.port}/{self.name}"


class LoggingSettings(BaseModel):
    """Centralized logging configuration."""
    model_config = ConfigDict(extra="forbid")

    # Basic logging settings
    level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    format_type: str = Field(
        default="structured",
        description="Log format (structured, simple, json)"
    )

    # Output destinations
    console_enabled: bool = Field(default=True)
    file_enabled: bool = Field(default=True)
    file_path: Path = Field(default=Path("logs/automation.log"))

    # File rotation
    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    backup_count: int = Field(default=5, ge=1, le=30)

    # Advanced features
    correlation_id_enabled: bool = Field(default=True)
    performance_logging: bool = Field(default=True)

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v_upper

    @field_validator("format_type")
    @classmethod
    def validate_format_type(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = {"structured", "simple", "json"}
        if v not in valid_formats:
            raise ValueError(f"Invalid format: {v}")
        return v


class TestSettings(BaseModel):
    """Test execution and behavior configuration."""
    model_config = ConfigDict(extra="forbid")

    # Parallel execution
    parallel_workers: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of parallel test workers"
    )

    # Test data management
    cleanup_data: bool = Field(
        default=True,
        description="Clean up test data after execution"
    )

    # Reporting
    generate_report: bool = Field(default=True)
    report_formats: List[str] = Field(
        default=["html", "allure"],
        description="Report formats to generate"
    )

    # Feature flags
    enable_visual_testing: bool = Field(default=False)
    enable_accessibility_testing: bool = Field(default=False)
    enable_performance_testing: bool = Field(default=False)
    enable_api_contract_testing: bool = Field(default=True)

    # Test filtering
    test_tags: List[str] = Field(default_factory=list)
    excluded_tags: List[str] = Field(default_factory=list)

    @field_validator("report_formats")
    @classmethod
    def validate_report_formats(cls, v: List[str]) -> List[str]:
        """Validate report formats."""
        valid_formats = {"html", "json", "xml", "allure", "junit"}
        invalid = set(v) - valid_formats
        if invalid:
            raise ValueError(f"Invalid formats: {invalid}")
        return v


class PerformanceSettings(BaseModel):
    """Performance monitoring and thresholds."""
    model_config = ConfigDict(extra="forbid")

    # Monitoring flags
    enable_monitoring: bool = Field(default=True)

    # Thresholds (in milliseconds)
    page_load_threshold: int = Field(
        default=5000,
        ge=100,
        le=60000,
        description="Page load time threshold in ms"
    )

    api_response_threshold: int = Field(
        default=2000,
        ge=50,
        le=30000,
        description="API response time threshold in ms"
    )

    # Memory thresholds (in MB)
    memory_usage_threshold: int = Field(
        default=512,
        ge=128,
        le=4096,
        description="Memory usage threshold in MB"
    )


class SecuritySettings(BaseModel):
    """Security-related configuration."""
    model_config = ConfigDict(extra="forbid")

    # Secret management
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        min_length=32,
        description="Secret key for encryption and signing"
    )

    # JWT settings
    jwt_secret: Optional[str] = Field(default=None, repr=False)
    jwt_expiry_hours: int = Field(default=24, ge=1, le=168)  # Max 1 week

    # API keys
    api_secret_key: Optional[str] = Field(default=None, repr=False)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key security."""
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        return v


class Settings(BaseSettings):
    """
    Main application settings with environment-aware loading.

    This class loads configuration from multiple sources in priority order:
    1. Environment variables (highest priority)
    2. .env.local file (for sensitive data)
    3. .env file (for regular settings)
    4. Default values (lowest priority)

    The configuration automatically adjusts based on the ENVIRONMENT variable.
    """

    model_config = SettingsConfigDict(
        # Environment file loading
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",

        # Secrets directory for Docker/Kubernetes secrets
        secrets_dir="/var/secrets" if Path("/var/secrets").exists() else None,
    )

    # Core application settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias="ENVIRONMENT",
        description="Application environment"
    )

    debug: bool = Field(
        default=False,
        validation_alias="DEBUG",
        description="Enable debug mode"
    )

    app_name: str = Field(
        default="Sock Shop Test Automation",
        validation_alias="APP_NAME"
    )

    app_version: str = Field(default="1.0.0")

    # Application URLs
    sock_shop_base_url: str = Field(
        default="http://localhost:8080",
        validation_alias="SOCK_SHOP_BASE_URL",
        description="Sock Shop application base URL"
    )

    # Nested configuration sections
    browser: BrowserSettings = Field(
        default_factory=BrowserSettings,
        description="Browser configuration"
    )

    api: APISettings = Field(
        default_factory=APISettings,
        description="API configuration"
    )

    database: DatabaseSettings = Field(
        default_factory=DatabaseSettings,
        description="Database configuration"
    )

    logging: LoggingSettings = Field(
        default_factory=LoggingSettings,
        description="Logging configuration"
    )

    test: TestSettings = Field(
        default_factory=TestSettings,
        description="Test execution configuration"
    )

    performance: PerformanceSettings = Field(
        default_factory=PerformanceSettings,
        description="Performance monitoring settings"
    )

    security: SecuritySettings = Field(
        default_factory=SecuritySettings,
        description="Security settings"
    )

    @model_validator(mode="after")
    def configure_environment_defaults(self) -> "Settings":
        """Apply environment-specific configuration adjustments."""

        if self.environment == Environment.PRODUCTION:
            # Production security hardening
            self.browser.headless = True
            self.browser.record_video = False
            self.api.validate_ssl = True
            self.debug = False
            self.logging.level = "INFO"

        elif self.environment == Environment.DEVELOPMENT:
            # Development conveniences
            if not self.debug:
                self.logging.level = "DEBUG"
            self.browser.slow_mo = 100 if not self.browser.slow_mo else self.browser.slow_mo
            self.test.cleanup_data = False

        elif self.environment == Environment.TESTING:
            # Testing optimizations
            self.browser.headless = True
            self.browser.timeout = min(self.browser.timeout, 15000)
            self.api.timeout = min(self.api.timeout, 15)
            self.test.parallel_workers = min(self.test.parallel_workers, 8)

        return self

    @field_validator("sock_shop_base_url")
    @classmethod
    def validate_sock_shop_url(cls, v: str) -> str:
        """Validate Sock Shop URL."""
        try:
            result = urlparse(v)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
            return v.rstrip("/")
        except Exception as e:
            raise ValueError(f"Invalid sock_shop_base_url: {e}")

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == Environment.DEVELOPMENT

    def get_browser_launch_options(self) -> Dict[str, Any]:
        """Get Playwright browser launch options."""
        return {
            "headless": self.browser.headless,
            "slow_mo": self.browser.slow_mo,
            "timeout": self.browser.timeout,
            "args": self.browser.args,
            "viewport": {
                "width": self.browser.viewport_width,
                "height": self.browser.viewport_height,
            },
            "record_video_dir": "reports/videos" if self.browser.record_video else None,
        }

    def get_api_client_config(self) -> Dict[str, Any]:
        """Get API client configuration."""
        return {
            "base_url": self.api.base_url,
            "timeout": self.api.timeout,
            "headers": self.api.default_headers,
            "verify": self.api.validate_ssl,
        }

    def model_dump_safe(self) -> Dict[str, Any]:
        """Dump configuration excluding sensitive data."""
        data = self.model_dump()

        # Mask sensitive fields
        if "security" in data:
            security = data["security"]
            for key in ["secret_key", "jwt_secret", "api_secret_key"]:
                if key in security and security[key]:
                    security[key] = "*" * 8

        if "database" in data and "password" in data["database"]:
            data["database"]["password"] = "*" * 8

        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached application settings instance.

    This function loads settings once and caches them for performance.
    The cache can be cleared using get_settings.cache_clear()

    Returns:
        Settings: Application settings instance

    Example:
        >>> settings = get_settings()
        >>> print(f"Running on {settings.environment}")
        >>> browser_opts = settings.get_browser_launch_options()
    """
    return Settings()


def reload_settings() -> Settings:
    """Force reload settings by clearing cache."""
    get_settings.cache_clear()
    return get_settings()


# Environment-specific factory functions
def get_development_settings() -> Settings:
    """Get development-optimized settings."""
    return Settings(
        environment=Environment.DEVELOPMENT,
        debug=True,
        browser__headless=False,
        browser__slow_mo=200,
        logging__level="DEBUG",
        test__parallel_workers=2,
        test__cleanup_data=False
    )


def get_testing_settings() -> Settings:
    """Get testing/CI-optimized settings."""
    return Settings(
        environment=Environment.TESTING,
        debug=False,
        browser__headless=True,
        browser__timeout=15000,
        logging__level="INFO",
        test__parallel_workers=8,
        test__cleanup_data=True
    )


def get_production_settings() -> Settings:
    """Get production-hardened settings."""
    return Settings(
        environment=Environment.PRODUCTION,
        debug=False,
        browser__headless=True,
        browser__record_video=False,
        logging__level="WARNING",
        api__validate_ssl=True
    )
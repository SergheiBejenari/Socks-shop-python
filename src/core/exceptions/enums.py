# src/core/exceptions/enums.py
"""
Exception Classification Enums

This module defines enums for categorizing and prioritizing exceptions
throughout the test automation framework. These enums provide consistent
classification for error handling, monitoring, and recovery strategies.

Key Design Benefits:
- Type Safety: Enum values prevent typos and invalid categories
- IDE Support: Autocompletion and validation in IDEs
- Consistent Classification: Standardized error categorization
- Easy Extension: Simple to add new categories or severity levels

Interview Highlights:
- Modern Python 3.9 enum usage with string inheritance
- Clear error classification system for monitoring
- Type-safe error handling approach
- Built-in business logic in enums
"""

from enum import Enum
from typing import Dict, Set


class ErrorSeverity(str, Enum):
    """
    Error severity levels for exception prioritization.

    These severity levels help determine:
    - How urgently the error needs attention
    - Whether automated recovery should be attempted
    - What level of logging/alerting is appropriate
    - Impact on test execution continuation

    Usage:
        >>> error = SomeException(severity=ErrorSeverity.HIGH)
        >>> if error.severity == ErrorSeverity.CRITICAL:
        ...     alert_operations_team(error)
    """

    LOW = "low"
    """
    Low severity errors that don't impact test execution significantly.
    Examples: Minor validation failures, cosmetic issues, warnings
    Actions: Log for analysis, continue test execution
    """

    MEDIUM = "medium"
    """
    Medium severity errors that may impact test reliability.
    Examples: Flaky element interactions, slow responses, retryable failures
    Actions: Log with details, attempt recovery, continue with caution
    """

    HIGH = "high"
    """
    High severity errors that significantly impact test execution.
    Examples: Authentication failures, critical element not found, API errors
    Actions: Detailed logging, attempt recovery, may fail test
    """

    CRITICAL = "critical"
    """
    Critical errors that require immediate attention and stop execution.
    Examples: Browser crashes, environment failures, security issues
    Actions: Alert operations, stop execution, require manual intervention
    """

    def should_retry(self) -> bool:
        """Determine if this severity level supports automatic retry."""
        return self in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]

    def should_alert(self) -> bool:
        """Determine if this severity level requires alerting."""
        return self in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]

    def max_retry_attempts(self) -> int:
        """Get maximum retry attempts for this severity level."""
        retry_mapping: Dict[ErrorSeverity, int] = {
            ErrorSeverity.LOW: 3,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 1,
            ErrorSeverity.CRITICAL: 0,
        }
        return retry_mapping[self]

    def get_timeout_multiplier(self) -> float:
        """Get timeout multiplier based on severity."""
        timeout_mapping: Dict[ErrorSeverity, float] = {
            ErrorSeverity.LOW: 1.0,
            ErrorSeverity.MEDIUM: 1.5,
            ErrorSeverity.HIGH: 2.0,
            ErrorSeverity.CRITICAL: 0.5,  # Quick fail for critical
        }
        return timeout_mapping[self]


class ErrorCategory(str, Enum):
    """
    Error categories for organizing exception types by functional area.

    These categories help with:
    - Error analysis and trending
    - Automated recovery strategy selection
    - Team assignment for issue resolution
    - Monitoring dashboard organization

    Usage:
        >>> error = NetworkException(category=ErrorCategory.NETWORK)
        >>> if error.category == ErrorCategory.BROWSER:
        ...     restart_browser()
    """

    BROWSER = "browser"
    """
    Browser-related errors: launch failures, crashes, version issues.
    Recovery: Restart browser, try different browser, check installation
    Team: Infrastructure/DevOps team
    """

    NETWORK = "network"
    """
    Network and connectivity errors: API failures, timeouts, DNS issues.
    Recovery: Retry request, check connectivity, verify endpoints
    Team: Network/API team
    """

    ELEMENT = "element"
    """
    UI element interaction errors: not found, not clickable, stale elements.
    Recovery: Wait for element, refresh page, try alternative locator
    Team: Frontend/UI team
    """

    DATA = "data"
    """
    Data-related errors: validation failures, format issues, missing data.
    Recovery: Regenerate data, validate schema, check data sources
    Team: Data/Backend team
    """

    CONFIGURATION = "configuration"
    """
    Configuration and setup errors: missing settings, invalid values.
    Recovery: Check config files, validate environment, reset defaults
    Team: DevOps/Configuration team
    """

    TIMEOUT = "timeout"
    """
    Timeout-related errors: page loads, element waits, API responses.
    Recovery: Increase timeout, check performance, verify conditions
    Team: Performance/Infrastructure team
    """

    AUTHENTICATION = "authentication"
    """
    Authentication and authorization errors: login failures, expired tokens.
    Recovery: Refresh credentials, re-authenticate, check permissions
    Team: Security/Auth team
    """

    VALIDATION = "validation"
    """
    Test validation and assertion errors: expectation mismatches, test logic.
    Recovery: Review test logic, update expectations, check requirements
    Team: QA/Test team
    """

    INFRASTRUCTURE = "infrastructure"
    """
    Infrastructure and environment errors: system failures, resource issues.
    Recovery: Check resources, restart services, verify environment health
    Team: Infrastructure/DevOps team
    """

    TEST = "test"
    """
    Test-specific errors: test data issues, test configuration problems.
    Recovery: Fix test setup, update test data, review test logic
    Team: QA/Test team
    """

    def get_responsible_team(self) -> str:
        """Get the team typically responsible for this error category."""
        team_mapping: Dict[ErrorCategory, str] = {
            ErrorCategory.BROWSER: "Infrastructure Team",
            ErrorCategory.NETWORK: "Network/API Team",
            ErrorCategory.ELEMENT: "Frontend Team",
            ErrorCategory.DATA: "Backend/Data Team",
            ErrorCategory.CONFIGURATION: "DevOps Team",
            ErrorCategory.TIMEOUT: "Performance Team",
            ErrorCategory.AUTHENTICATION: "Security Team",
            ErrorCategory.VALIDATION: "QA Team",
            ErrorCategory.INFRASTRUCTURE: "Infrastructure Team",
            ErrorCategory.TEST: "QA Team",
        }
        return team_mapping.get(self, "Unknown Team")

    def get_recovery_priority(self) -> int:
        """Get recovery priority (1=highest, 5=lowest) for this category."""
        priority_mapping: Dict[ErrorCategory, int] = {
            ErrorCategory.AUTHENTICATION: 1,  # Security issues first
            ErrorCategory.INFRASTRUCTURE: 1,  # System issues first
            ErrorCategory.BROWSER: 2,  # Browser issues affect all tests
            ErrorCategory.NETWORK: 2,  # Network issues affect API tests
            ErrorCategory.CONFIGURATION: 3,  # Config issues need attention
            ErrorCategory.TIMEOUT: 3,  # Performance issues matter
            ErrorCategory.ELEMENT: 4,  # UI issues are localized
            ErrorCategory.DATA: 4,  # Data issues are often test-specific
            ErrorCategory.VALIDATION: 5,  # Test logic issues are lowest priority
            ErrorCategory.TEST: 5,  # Test issues are lowest priority
        }
        return priority_mapping[self]

    def get_default_retry_strategy(self) -> 'RetryStrategy':
        """Get default retry strategy for this category."""
        from .enums import RetryStrategy  # Local import to avoid circular dependency

        strategy_mapping: Dict[ErrorCategory, RetryStrategy] = {
            ErrorCategory.BROWSER: RetryStrategy.LINEAR,
            ErrorCategory.NETWORK: RetryStrategy.EXPONENTIAL_JITTER,
            ErrorCategory.ELEMENT: RetryStrategy.LINEAR,
            ErrorCategory.DATA: RetryStrategy.NONE,
            ErrorCategory.CONFIGURATION: RetryStrategy.NONE,
            ErrorCategory.TIMEOUT: RetryStrategy.EXPONENTIAL,
            ErrorCategory.AUTHENTICATION: RetryStrategy.LINEAR,
            ErrorCategory.VALIDATION: RetryStrategy.NONE,
            ErrorCategory.INFRASTRUCTURE: RetryStrategy.EXPONENTIAL,
            ErrorCategory.TEST: RetryStrategy.NONE,
        }
        return strategy_mapping.get(self, RetryStrategy.NONE)

    def get_monitoring_tags(self) -> Set[str]:
        """Get monitoring tags for this category."""
        base_tags = {self.value, "automation_error"}

        tag_mapping: Dict[ErrorCategory, Set[str]] = {
            ErrorCategory.BROWSER: {"browser_issue", "ui_automation"},
            ErrorCategory.NETWORK: {"network_issue", "api_failure", "connectivity"},
            ErrorCategory.ELEMENT: {"element_issue", "ui_failure", "dom_error"},
            ErrorCategory.DATA: {"data_issue", "validation_error"},
            ErrorCategory.CONFIGURATION: {"config_issue", "setup_error"},
            ErrorCategory.TIMEOUT: {"timeout_issue", "performance_problem"},
            ErrorCategory.AUTHENTICATION: {"auth_issue", "security_error"},
            ErrorCategory.VALIDATION: {"assertion_failure", "test_validation"},
            ErrorCategory.INFRASTRUCTURE: {"infra_issue", "system_error"},
            ErrorCategory.TEST: {"test_issue", "test_failure"},
        }

        return base_tags.union(tag_mapping.get(self, set()))


class RetryStrategy(str, Enum):
    """
    Retry strategies for different types of failures.

    These strategies determine how the framework should handle
    retry attempts for different error scenarios.
    """

    NONE = "none"
    """No retry - fail immediately."""

    IMMEDIATE = "immediate"
    """Retry immediately without delay."""

    LINEAR = "linear"
    """Linear backoff - fixed delay between retries."""

    EXPONENTIAL = "exponential"
    """Exponential backoff - increasing delay between retries."""

    EXPONENTIAL_JITTER = "exponential_jitter"
    """Exponential backoff with random jitter to prevent thundering herd."""

    RANDOM = "random"
    """Random delay within a range."""

    FIBONACCI = "fibonacci"
    """Fibonacci sequence based delays (1, 1, 2, 3, 5, 8...)."""

    def get_base_delay(self) -> float:
        """Get base delay in seconds for this strategy."""
        delay_mapping: Dict[RetryStrategy, float] = {
            RetryStrategy.NONE: 0.0,
            RetryStrategy.IMMEDIATE: 0.0,
            RetryStrategy.LINEAR: 1.0,
            RetryStrategy.EXPONENTIAL: 1.0,
            RetryStrategy.EXPONENTIAL_JITTER: 1.0,
            RetryStrategy.RANDOM: 0.5,
            RetryStrategy.FIBONACCI: 1.0,
        }
        return delay_mapping[self]

    def calculate_delay(self, attempt: int, base_delay: float = None) -> float:
        """
        Calculate delay for given attempt number.

        Args:
            attempt: Current retry attempt (1-based)
            base_delay: Override base delay

        Returns:
            Delay in seconds before next retry
        """
        import random

        base = base_delay if base_delay is not None else self.get_base_delay()

        if self == RetryStrategy.NONE:
            return 0.0
        elif self == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self == RetryStrategy.LINEAR:
            return base * attempt
        elif self == RetryStrategy.EXPONENTIAL:
            return base * (2 ** (attempt - 1))
        elif self == RetryStrategy.EXPONENTIAL_JITTER:
            exp_delay = base * (2 ** (attempt - 1))
            jitter = random.uniform(0.8, 1.2)
            return exp_delay * jitter
        elif self == RetryStrategy.RANDOM:
            return random.uniform(base, base * 3)
        elif self == RetryStrategy.FIBONACCI:
            # Calculate fibonacci number for attempt
            a, b = 0, 1
            for _ in range(attempt):
                a, b = b, a + b
            return base * a
        else:
            return base


class LogLevel(str, Enum):
    """
    Logging levels aligned with standard Python logging.

    These levels determine how much detail should be logged
    for different types of exceptions.
    """

    DEBUG = "DEBUG"
    """Detailed debugging information."""

    INFO = "INFO"
    """General information about execution."""

    WARNING = "WARNING"
    """Warning about potential issues."""

    ERROR = "ERROR"
    """Error conditions that don't stop execution."""

    CRITICAL = "CRITICAL"
    """Critical errors that stop execution."""

    def to_numeric(self) -> int:
        """Convert to Python logging numeric level."""
        import logging

        level_mapping: Dict[LogLevel, int] = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return level_mapping[self]

    @classmethod
    def from_severity(cls, severity: ErrorSeverity) -> 'LogLevel':
        """Determine log level from error severity."""
        severity_mapping: Dict[ErrorSeverity, LogLevel] = {
            ErrorSeverity.LOW: LogLevel.INFO,
            ErrorSeverity.MEDIUM: LogLevel.WARNING,
            ErrorSeverity.HIGH: LogLevel.ERROR,
            ErrorSeverity.CRITICAL: LogLevel.CRITICAL,
        }
        return severity_mapping.get(severity, LogLevel.ERROR)
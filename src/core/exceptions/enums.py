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
- Modern Python enum usage with string inheritance
- Clear error classification system for monitoring
- Type-safe error handling approach
"""

from enum import Enum


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
        retry_mapping = {
            ErrorSeverity.LOW: 2,
            ErrorSeverity.MEDIUM: 3,
            ErrorSeverity.HIGH: 1,
            ErrorSeverity.CRITICAL: 0,
        }
        return retry_mapping[self]


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

    def get_responsible_team(self) -> str:
        """Get the team typically responsible for this error category."""
        team_mapping = {
            ErrorCategory.BROWSER: "Infrastructure Team",
            ErrorCategory.NETWORK: "Network/API Team",
            ErrorCategory.ELEMENT: "Frontend Team",
            ErrorCategory.DATA: "Backend/Data Team",
            ErrorCategory.CONFIGURATION: "DevOps Team",
            ErrorCategory.TIMEOUT: "Performance Team",
            ErrorCategory.AUTHENTICATION: "Security Team",
            ErrorCategory.VALIDATION: "QA Team",
            ErrorCategory.INFRASTRUCTURE: "Infrastructure Team",
        }
        return team_mapping[self]

    def get_recovery_priority(self) -> int:
        """Get recovery priority (1=highest, 5=lowest) for this category."""
        priority_mapping = {
            ErrorCategory.AUTHENTICATION: 1,  # Security issues first
            ErrorCategory.INFRASTRUCTURE: 1,  # System issues first
            ErrorCategory.BROWSER: 2,  # Browser issues affect all tests
            ErrorCategory.NETWORK: 2,  # Network issues affect API tests
            ErrorCategory.CONFIGURATION: 3,  # Config issues need attention
            ErrorCategory.TIMEOUT: 3,  # Performance issues matter
            ErrorCategory.ELEMENT: 4,  # UI issues are localized
            ErrorCategory.DATA: 4,  # Data issues are often test-specific
            ErrorCategory.VALIDATION: 5,  # Test logic issues are lowest priority
        }
        return priority_mapping[self]


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
# src/core/exceptions.py
"""
Custom Exception Hierarchy for Test Automation Framework

This module defines a comprehensive exception hierarchy that provides
clear error categorization, debugging information, and recovery hints.
It demonstrates enterprise-level error handling practices.

Key Design Patterns:
- Exception Hierarchy: Organized exception inheritance for specific error types
- Context Pattern: Rich error context with debugging information
- Chain of Responsibility: Exception handling with recovery suggestions

Interview Highlights:
- Sophisticated error classification and handling
- Rich error context for debugging and monitoring
- Recovery-oriented exception design
- Production-ready error reporting
"""

from typing import Any, Dict, List, Optional, Union
import traceback
from datetime import datetime

from src.core.exceptions.enums import ErrorCategory, ErrorSeverity


class AutomationException(Exception):
    """
    Base exception class for all test automation exceptions.

    This base class provides rich error context, debugging information,
    and recovery suggestions. All framework exceptions should inherit from this.

    Attributes:
        message: Human-readable error description
        error_code: Unique error identifier for tracking
        category: Error category for classification
        severity: Error severity level
        context: Additional context information
        recovery_suggestions: List of potential recovery actions
        timestamp: When the error occurred
        stack_trace: Captured stack trace
    """

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            category: ErrorCategory = ErrorCategory.INFRASTRUCTURE,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            context: Optional[Dict[str, Any]] = None,
            recovery_suggestions: Optional[List[str]] = None,
            original_exception: Optional[Exception] = None
    ):
        """
        Initialize automation exception with rich context.

        Args:
            message: Error description
            error_code: Unique identifier for this error type
            category: Error category for classification
            severity: Severity level
            context: Additional debugging context
            recovery_suggestions: Suggested recovery actions
            original_exception: Original exception that caused this error
        """
        super().__init__(message)

        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on exception type."""
        class_name = self.__class__.__name__
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"{class_name.upper()}_{timestamp}"

    def add_context(self, key: str, value: Any) -> None:
        """Add additional context information to the exception."""
        self.context[key] = value

    def add_recovery_suggestion(self, suggestion: str) -> None:
        """Add a recovery suggestion to the exception."""
        self.recovery_suggestions.append(suggestion)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/reporting.

        Returns:
            Dict containing all exception information
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "category": self.category.value,
            "severity": self.severity.value,
            "context": self.context,
            "recovery_suggestions": self.recovery_suggestions,
            "timestamp": self.timestamp.isoformat(),
            "original_exception": str(self.original_exception) if self.original_exception else None,
            "stack_trace": self.stack_trace
        }

    def __str__(self) -> str:
        """Return a comprehensive string representation."""
        return (
            f"{self.__class__.__name__}: {self.message}\n"
            f"Error Code: {self.error_code}\n"
            f"Category: {self.category.value}\n"
            f"Severity: {self.severity.value}\n"
            f"Context: {self.context}\n"
            f"Recovery Suggestions: {self.recovery_suggestions}"
        )


class BrowserException(AutomationException):
    """
    Exceptions related to browser operations and management.

    This exception type covers browser launching, closing, navigation,
    and other browser-level operations.
    """

    def __init__(
            self,
            message: str,
            browser_name: Optional[str] = None,
            browser_version: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser exception.

        Args:
            message: Error description
            browser_name: Name of the browser (chromium, firefox, webkit)
            browser_version: Browser version if available
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.BROWSER,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            **kwargs
        )

        if browser_name:
            self.add_context("browser_name", browser_name)
        if browser_version:
            self.add_context("browser_version", browser_version)

        # Add common recovery suggestions for browser issues
        self.recovery_suggestions.extend([
            "Check if browser is properly installed",
            "Verify browser executable permissions",
            "Try restarting the browser",
            "Check system resources (memory, disk space)"
        ])


class ElementException(AutomationException):
    """
    Exceptions related to UI element interactions.

    This exception type covers element location, interaction,
    and state validation issues.
    """

    def __init__(
            self,
            message: str,
            selector: Optional[str] = None,
            element_type: Optional[str] = None,
            page_url: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize element exception.

        Args:
            message: Error description
            selector: Element selector that failed
            element_type: Type of element (button, input, etc.)
            page_url: URL where the error occurred
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.ELEMENT,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            **kwargs
        )

        if selector:
            self.add_context("selector", selector)
        if element_type:
            self.add_context("element_type", element_type)
        if page_url:
            self.add_context("page_url", page_url)

        # Add common recovery suggestions for element issues
        self.recovery_suggestions.extend([
            "Verify element selector is correct",
            "Check if element is visible on the page",
            "Wait for page to load completely",
            "Verify element is not inside a frame/iframe"
        ])


class NetworkException(AutomationException):
    """
    Exceptions related to network operations and API calls.

    This exception type covers HTTP requests, API responses,
    and network connectivity issues.
    """

    def __init__(
            self,
            message: str,
            url: Optional[str] = None,
            status_code: Optional[int] = None,
            response_body: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize network exception.

        Args:
            message: Error description
            url: URL that caused the error
            status_code: HTTP status code if available
            response_body: Response body for debugging
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            **kwargs
        )

        if url:
            self.add_context("url", url)
        if status_code:
            self.add_context("status_code", status_code)
        if response_body:
            # Truncate long response bodies for logging
            truncated_body = response_body[:1000] + "..." if len(response_body) > 1000 else response_body
            self.add_context("response_body", truncated_body)

        # Add common recovery suggestions for network issues
        self.recovery_suggestions.extend([
            "Check network connectivity",
            "Verify API endpoint is accessible",
            "Check authentication credentials",
            "Retry the request after a delay"
        ])


class TimeoutException(AutomationException):
    """
    Exceptions related to timeout operations.

    This exception type covers element waits, page loads,
    and other time-sensitive operations.
    """

    def __init__(
            self,
            message: str,
            timeout_duration: Optional[float] = None,
            operation_type: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize timeout exception.

        Args:
            message: Error description
            timeout_duration: How long we waited before timing out
            operation_type: Type of operation that timed out
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            **kwargs
        )

        if timeout_duration:
            self.add_context("timeout_duration", timeout_duration)
        if operation_type:
            self.add_context("operation_type", operation_type)

        # Add common recovery suggestions for timeout issues
        self.recovery_suggestions.extend([
            "Increase timeout duration",
            "Check if page/element loads slowly",
            "Verify network conditions",
            "Check if operation is blocked by other elements"
        ])


class DataValidationException(AutomationException):
    """
    Exceptions related to data validation and processing.

    This exception type covers test data validation,
    API response validation, and data transformation errors.
    """

    def __init__(
            self,
            message: str,
            expected_value: Optional[Any] = None,
            actual_value: Optional[Any] = None,
            validation_rule: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize data validation exception.

        Args:
            message: Error description
            expected_value: Expected value that validation failed for
            actual_value: Actual value received
            validation_rule: Validation rule that failed
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.DATA,
            severity=kwargs.get('severity', ErrorSeverity.LOW),
            **kwargs
        )

        if expected_value is not None:
            self.add_context("expected_value", expected_value)
        if actual_value is not None:
            self.add_context("actual_value", actual_value)
        if validation_rule:
            self.add_context("validation_rule", validation_rule)

        # Add common recovery suggestions for validation issues
        self.recovery_suggestions.extend([
            "Verify test data is correct",
            "Check data transformation logic",
            "Update validation rules if requirements changed",
            "Verify API response format"
        ])


class AuthenticationException(AutomationException):
    """
    Exceptions related to authentication and authorization.

    This exception type covers login failures, token expiration,
    and permission-related issues.
    """

    def __init__(
            self,
            message: str,
            username: Optional[str] = None,
            auth_method: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize authentication exception.

        Args:
            message: Error description
            username: Username that failed authentication (without password!)
            auth_method: Authentication method used
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            **kwargs
        )

        if username:
            self.add_context("username", username)
        if auth_method:
            self.add_context("auth_method", auth_method)

        # Add common recovery suggestions for authentication issues
        self.recovery_suggestions.extend([
            "Verify username and password are correct",
            "Check if account is locked or expired",
            "Verify authentication service is available",
            "Check if session/token has expired"
        ])


class ConfigurationException(AutomationException):
    """
    Exceptions related to configuration and setup issues.

    This exception type covers environment setup, configuration validation,
    and dependency issues.
    """

    def __init__(
            self,
            message: str,
            config_file: Optional[str] = None,
            config_key: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize configuration exception.

        Args:
            message: Error description
            config_file: Configuration file that caused the error
            config_key: Specific configuration key that failed
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.CONFIGURATION,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            **kwargs
        )

        if config_file:
            self.add_context("config_file", config_file)
        if config_key:
            self.add_context("config_key", config_key)

        # Add common recovery suggestions for configuration issues
        self.recovery_suggestions.extend([
            "Verify configuration file exists and is readable",
            "Check configuration syntax is valid",
            "Verify all required configuration keys are present",
            "Check environment variables are set correctly"
        ])


class TestAssertionException(AutomationException):
    """
    Exceptions related to test assertions and validation.

    This exception type covers test failures, assertion errors,
    and validation mismatches in test scenarios.
    """

    def __init__(
            self,
            message: str,
            assertion_type: Optional[str] = None,
            test_step: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize test assertion exception.

        Args:
            message: Error description
            assertion_type: Type of assertion that failed
            test_step: Test step where assertion failed
            **kwargs: Additional arguments passed to AutomationException
        """
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=kwargs.get('severity', ErrorSeverity.LOW),
            **kwargs
        )

        if assertion_type:
            self.add_context("assertion_type", assertion_type)
        if test_step:
            self.add_context("test_step", test_step)

        # Add common recovery suggestions for assertion issues
        self.recovery_suggestions.extend([
            "Verify test expectations are correct",
            "Check if application behavior has changed",
            "Update test data if requirements changed",
            "Review test logic and assertions"
        ])


# Utility functions for exception handling
def create_exception_from_playwright_error(
        playwright_error: Exception,
        context: Optional[Dict[str, Any]] = None
) -> AutomationException:
    """
    Convert Playwright exceptions to our custom exception hierarchy.

    This function analyzes Playwright errors and maps them to appropriate
    custom exception types with enhanced context and recovery suggestions.

    Args:
        playwright_error: Original Playwright exception
        context: Additional context information

    Returns:
        AutomationException: Mapped custom exception
    """
    error_message = str(playwright_error)
    error_context = context or {}

    # Analyze error message to determine exception type
    if "timeout" in error_message.lower():
        return TimeoutException(
            message=f"Playwright timeout: {error_message}",
            original_exception=playwright_error,
            context=error_context,
            operation_type="playwright_operation"
        )

    elif "element" in error_message.lower() or "locator" in error_message.lower():
        return ElementException(
            message=f"Element error: {error_message}",
            original_exception=playwright_error,
            context=error_context
        )

    elif "network" in error_message.lower() or "connection" in error_message.lower():
        return NetworkException(
            message=f"Network error: {error_message}",
            original_exception=playwright_error,
            context=error_context
        )

    elif "browser" in error_message.lower():
        return BrowserException(
            message=f"Browser error: {error_message}",
            original_exception=playwright_error,
            context=error_context
        )

    else:
        # Generic automation exception for unknown errors
        return AutomationException(
            message=f"Playwright error: {error_message}",
            original_exception=playwright_error,
            context=error_context,
            category=ErrorCategory.INFRASTRUCTURE
        )


def handle_exception_with_recovery(
        exception: AutomationException,
        recovery_attempts: int = 3
) -> None:
    """
    Handle exceptions with automatic recovery attempts.

    This function demonstrates how to implement automatic recovery
    strategies based on exception types and severity.

    Args:
        exception: Exception to handle
        recovery_attempts: Number of recovery attempts to make
    """
    print(f"Handling exception: {exception.error_code}")
    print(f"Severity: {exception.severity.value}")
    print(f"Recovery suggestions: {exception.recovery_suggestions}")

    # In a full implementation, this would contain actual recovery logic
    # based on exception type and severity

    if exception.severity == ErrorSeverity.CRITICAL:
        print("Critical error - immediate intervention required")
        raise exception

    elif exception.severity == ErrorSeverity.HIGH:
        print(f"High severity error - attempting {recovery_attempts} recovery attempts")
        # Implement recovery logic here

    elif exception.severity == ErrorSeverity.MEDIUM:
        print("Medium severity error - logging and continuing")
        # Log error and continue

    else:  # LOW severity
        print("Low severity error - logging only")
        # Just log the error


def log_exception_for_monitoring(exception: AutomationException) -> Dict[str, Any]:
    """
    Format exception for external monitoring and alerting systems.

    This function creates a standardized exception report suitable
    for logging platforms, monitoring systems, and alerting tools.

    Args:
        exception: Exception to format

    Returns:
        Dict: Formatted exception data for monitoring
    """
    return {
        "event_type": "automation_exception",
        "timestamp": exception.timestamp.isoformat(),
        "error_code": exception.error_code,
        "error_type": exception.__class__.__name__,
        "category": exception.category.value,
        "severity": exception.severity.value,
        "message": exception.message,
        "context": exception.context,
        "recovery_suggestions": exception.recovery_suggestions,
        "stack_trace": exception.stack_trace,
        "tags": {
            "category": exception.category.value,
            "severity": exception.severity.value,
            "framework": "sock-shop-automation",
            "version": "1.0.0"
        }
    }

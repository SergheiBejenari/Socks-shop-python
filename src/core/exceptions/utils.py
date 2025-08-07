# src/core/exceptions/utils.py
"""
Exception Utility Functions
"""

from typing import Any, Dict, Optional

from .base import AutomationException
from .browser import BrowserException
from .element import ElementException
from .network import NetworkException
from .timeout import TimeoutException
from .enums import ErrorCategory, ErrorSeverity


def create_exception_from_playwright_error(
        playwright_error: Exception,
        context: Optional[Dict[str, Any]] = None
) -> AutomationException:
    """
    Convert Playwright exceptions to our custom exception hierarchy.

    This function analyzes Playwright errors and maps them to appropriate
    custom exception types with enhanced context and recovery suggestions.
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
    """
    print(f"Handling exception: {exception.error_code}")
    print(f"Severity: {exception.severity.value}")
    print(f"Recovery suggestions: {exception.recovery_suggestions}")

    if exception.severity == ErrorSeverity.CRITICAL:
        print("Critical error - immediate intervention required")
        raise exception
    elif exception.severity == ErrorSeverity.HIGH:
        print(f"High severity error - attempting {recovery_attempts} recovery attempts")
    elif exception.severity == ErrorSeverity.MEDIUM:
        print("Medium severity error - logging and continuing")
    else:  # LOW severity
        print("Low severity error - logging only")


def log_exception_for_monitoring(exception: AutomationException) -> Dict[str, Any]:
    """
    Format exception for external monitoring and alerting systems.
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
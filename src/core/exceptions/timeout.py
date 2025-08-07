# src/core/exceptions/timeout.py
"""
Timeout Exception Classes
"""

from typing import Optional

from base import AutomationException
from enums import ErrorCategory, ErrorSeverity


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
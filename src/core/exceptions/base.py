# src/core/exceptions/base.py
"""
Base Exception Class for Test Automation Framework

This module provides the foundation exception class that all other
framework exceptions inherit from. It implements rich error context,
debugging information, and recovery suggestions.

Key Design Patterns:
- Template Method: Common exception structure with customizable details
- Builder Pattern: Fluent API for adding context and recovery suggestions
- Observer Pattern: Support for error event listeners

Interview Highlights:
- Enterprise-level exception design with comprehensive context
- Production-ready error tracking and debugging support
- Recovery-oriented exception architecture
- Integration-ready for monitoring and alerting systems
"""

import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from .enums import ErrorCategory, ErrorSeverity, LogLevel, RetryStrategy


class AutomationException(Exception):
    """
    Base exception class for all test automation framework exceptions.

    This class provides a comprehensive foundation for error handling with:
    - Rich error context for debugging
    - Recovery suggestions for automatic and manual resolution
    - Structured data for monitoring and alerting integration
    - Unique error tracking with correlation IDs
    - Severity and category classification

    All framework exceptions should inherit from this class to ensure
    consistent error handling and rich debugging information.

    Attributes:
        message: Human-readable error description
        error_code: Unique error identifier for tracking
        correlation_id: UUID for correlating related errors
        category: Error category for classification
        severity: Error severity level
        retry_strategy: Suggested retry approach
        context: Additional context information
        recovery_suggestions: List of potential recovery actions
        timestamp: When the error occurred
        stack_trace: Captured stack trace
        original_exception: Original exception that caused this error

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     raise AutomationException(
        ...         message="Operation failed",
        ...         category=ErrorCategory.NETWORK,
        ...         severity=ErrorSeverity.HIGH,
        ...         original_exception=e
        ...     ).add_context("operation", "user_login")
    """

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            correlation_id: Optional[str] = None,
            category: ErrorCategory = ErrorCategory.INFRASTRUCTURE,
            severity: ErrorSeverity = ErrorSeverity.MEDIUM,
            retry_strategy: RetryStrategy = RetryStrategy.NONE,
            context: Optional[Dict[str, Any]] = None,
            recovery_suggestions: Optional[List[str]] = None,
            original_exception: Optional[Exception] = None,
            log_level: LogLevel = LogLevel.ERROR
    ):
        """
        Initialize automation exception with comprehensive error details.

        Args:
            message: Clear, actionable error description
            error_code: Unique identifier for this error type (auto-generated if None)
            correlation_id: UUID for tracking related errors (auto-generated if None)
            category: Error category for classification
            severity: Severity level for prioritization
            retry_strategy: Suggested retry approach
            context: Additional debugging context
            recovery_suggestions: List of recovery actions
            original_exception: Original exception that caused this error
            log_level: Logging level for this exception
        """
        super().__init__(message)

        # Core error information
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.correlation_id = correlation_id or str(uuid4())
        self.category = category
        self.severity = severity
        self.retry_strategy = retry_strategy
        self.log_level = log_level

        # Contextual information
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.original_exception = original_exception

        # Timing and debugging
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc()

        # Event tracking
        self._event_listeners: List[callable] = []

    def _generate_error_code(self) -> str:
        """
        Generate a unique error code based on exception type and timestamp.

        Error codes follow the pattern: EXCEPTION_TYPE_TIMESTAMP
        This provides uniqueness while maintaining readability.

        Returns:
            str: Generated error code
        """
        class_name = self.__class__.__name__.replace("Exception", "").upper()
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S_%f")[:19]  # Include microseconds
        return f"{class_name}_{timestamp}"

    def add_context(self, key: str, value: Any) -> "AutomationException":
        """
        Add contextual information to the exception.

        This method supports method chaining for fluent error construction.
        Context information is crucial for debugging and should include
        relevant state at the time of the error.

        Args:
            key: Context key (e.g., "page_url", "element_selector")
            value: Context value (any serializable type)

        Returns:
            AutomationException: Self for method chaining

        Example:
            >>> exception = AutomationException("Login failed") \
            ...     .add_context("username", "test_user") \
            ...     .add_context("page_url", "https://example.com/login")
        """
        self.context[key] = value
        return self

    def add_recovery_suggestion(self, suggestion: str) -> "AutomationException":
        """
        Add a recovery suggestion to help resolve the error.

        Recovery suggestions should be actionable and specific to the error.
        They help both automated recovery systems and human operators.

        Args:
            suggestion: Specific recovery action

        Returns:
            AutomationException: Self for method chaining

        Example:
            >>> exception.add_recovery_suggestion("Verify network connectivity") \
            ...          .add_recovery_suggestion("Check API endpoint status")
        """
        if suggestion not in self.recovery_suggestions:
            self.recovery_suggestions.append(suggestion)
        return self

    def set_severity(self, severity: ErrorSeverity) -> "AutomationException":
        """
        Update the exception severity level.

        This can be useful when the initial severity assessment changes
        based on additional context or recovery attempts.

        Args:
            severity: New severity level

        Returns:
            AutomationException: Self for method chaining
        """
        self.severity = severity
        return self

    def set_retry_strategy(self, strategy: RetryStrategy) -> "AutomationException":
        """
        Set the recommended retry strategy for this exception.

        Args:
            strategy: Retry strategy to use

        Returns:
            AutomationException: Self for method chaining
        """
        self.retry_strategy = strategy
        return self

    def should_retry(self) -> bool:
        """
        Determine if this exception should trigger a retry attempt.

        This decision is based on both the retry strategy and severity level.
        Critical errors typically should not be retried automatically.

        Returns:
            bool: True if retry should be attempted
        """
        if self.retry_strategy == RetryStrategy.NONE:
            return False

        if self.severity == ErrorSeverity.CRITICAL:
            return False

        return True

    def get_retry_delay(self, attempt: int = 1) -> float:
        """
        Calculate retry delay based on the retry strategy and attempt number.

        Args:
            attempt: Current retry attempt number (1-based)

        Returns:
            float: Delay in seconds before retry
        """
        import random

        base_delay = 1.0

        if self.retry_strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self.retry_strategy == RetryStrategy.LINEAR:
            return base_delay * attempt
        elif self.retry_strategy == RetryStrategy.EXPONENTIAL:
            return base_delay * (2 ** (attempt - 1))
        elif self.retry_strategy == RetryStrategy.RANDOM:
            return random.uniform(0.5, 2.0) * attempt
        else:
            return base_delay

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for serialization.

        This format is suitable for:
        - JSON logging and monitoring systems
        - API error responses
        - Database storage
        - Message queue publishing

        Returns:
            Dict: Complete exception data
        """
        return {
            # Core identification
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "correlation_id": self.correlation_id,
            "message": self.message,

            # Classification
            "category": self.category.value,
            "severity": self.severity.value,
            "retry_strategy": self.retry_strategy.value,
            "log_level": self.log_level.value,

            # Context and recovery
            "context": self.context,
            "recovery_suggestions": self.recovery_suggestions,

            # Timing and tracing
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,

            # Original cause
            "original_exception": {
                "type": type(self.original_exception).__name__,
                "message": str(self.original_exception)
            } if self.original_exception else None
        }

    def to_json(self) -> str:
        """
        Convert exception to JSON string for logging/monitoring.

        Returns:
            str: JSON representation of the exception
        """
        import json
        return json.dumps(self.to_dict(), indent=2, default=str)

    def add_event_listener(self, listener: callable) -> "AutomationException":
        """
        Add an event listener for this exception.

        Event listeners can be used for:
        - Custom logging
        - Monitoring system integration
        - Automated recovery actions
        - Alerting and notifications

        Args:
            listener: Callable that takes the exception as parameter

        Returns:
            AutomationException: Self for method chaining
        """
        self._event_listeners.append(listener)
        return self

    def notify_listeners(self) -> None:
        """
        Notify all registered event listeners about this exception.

        This method is typically called when the exception is raised
        or when significant state changes occur.
        """
        for listener in self._event_listeners:
            try:
                listener(self)
            except Exception as e:
                # Don't let listener failures crash the main exception handling
                print(f"Warning: Exception listener failed: {e}")

    def __str__(self) -> str:
        """
        Return a comprehensive string representation for logging.

        This format is optimized for human readability in logs
        while still containing all essential debugging information.

        Returns:
            str: Formatted exception description
        """
        lines = [
            f"🚨 {self.__class__.__name__}: {self.message}",
            f"📋 Error Code: {self.error_code}",
            f"🔗 Correlation ID: {self.correlation_id}",
            f"📂 Category: {self.category.value}",
            f"⚠️  Severity: {self.severity.value}",
            f"🔄 Retry Strategy: {self.retry_strategy.value}",
            f"⏰ Timestamp: {self.timestamp.isoformat()}",
        ]

        if self.context:
            lines.append(f"📝 Context: {self.context}")

        if self.recovery_suggestions:
            lines.append("💡 Recovery Suggestions:")
            for i, suggestion in enumerate(self.recovery_suggestions, 1):
                lines.append(f"   {i}. {suggestion}")

        if self.original_exception:
            lines.append(f"🔗 Original Exception: {self.original_exception}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return a concise representation suitable for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"category={self.category.value}, "
            f"severity={self.severity.value}, "
            f"error_code='{self.error_code}'"
            f")"
        )
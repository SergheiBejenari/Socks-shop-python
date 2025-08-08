# src/core/exceptions/base/automation_exception.py
"""
Base Automation Exception - Foundation for all framework exceptions

This module provides the core exception class that all other framework
exceptions inherit from. It implements comprehensive error context,
debugging information, and recovery strategies.

Key Design Patterns:
- Template Method: Common exception structure with customizable details
- Builder Pattern: Fluent API for adding context and recovery suggestions
- Observer Pattern: Support for error event listeners
- Strategy Pattern: Different recovery strategies per exception type

SOLID Principles Applied:
- SRP: Single responsibility for base exception functionality
- OCP: Open for extension, closed for modification
- LSP: All subclasses are substitutable
- ISP: Clean interface with focused responsibilities
- DIP: Depends on abstractions (enums, protocols)
"""

import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4
from abc import ABC, abstractmethod

from .enums import ErrorCategory, ErrorSeverity, LogLevel, RetryStrategy


class ErrorReporter(Protocol):
    """Protocol for error reporting systems."""

    def report_error(self, exception: "AutomationException") -> None:
        """Report error to external system."""
        ...


class RecoveryStrategy(Protocol):
    """Protocol for recovery strategy implementations."""

    def can_recover(self, exception: "AutomationException") -> bool:
        """Check if this strategy can recover from the exception."""
        ...

    def attempt_recovery(self, exception: "AutomationException") -> bool:
        """Attempt to recover from the exception."""
        ...


class AutomationException(Exception, ABC):
    """
    Base exception class for all test automation framework exceptions.

    This class provides a comprehensive foundation for error handling with:
    - Rich error context for debugging
    - Recovery suggestions for automatic and manual resolution
    - Structured data for monitoring and alerting integration
    - Unique error tracking with correlation IDs
    - Severity and category classification
    - Event system for error reporting

    All framework exceptions should inherit from this class to ensure
    consistent error handling and rich debugging information.
    """

    def __init__(
            self,
            message: str,
            error_code: Optional[str] = None,
            correlation_id: Optional[str] = None,
            category: Optional[ErrorCategory] = None,
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
            category: Error category for classification (auto-detected if None)
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
        self.category = category or self._determine_category()
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

        # Event system
        self._event_listeners: List[ErrorReporter] = []
        self._recovery_strategies: List[RecoveryStrategy] = []

        # Initialize subclass-specific data
        self._initialize_exception()

    @abstractmethod
    def _determine_category(self) -> ErrorCategory:
        """
        Determine the error category for this exception type.

        Each concrete exception class must implement this method
        to provide its specific error category.

        Returns:
            ErrorCategory: Category for this exception type
        """
        pass

    def _initialize_exception(self) -> None:
        """
        Initialize exception-specific data.

        Subclasses can override this method to perform
        additional initialization after base construction.
        """
        pass

    def _generate_error_code(self) -> str:
        """
        Generate a unique error code based on exception type and timestamp.

        Returns:
            str: Generated error code
        """
        class_name = self.__class__.__name__.replace("Exception", "").upper()
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S_%f")[:19]
        return f"{class_name}_{timestamp}"

    def add_context(self, key: str, value: Any) -> "AutomationException":
        """
        Add contextual information to the exception.

        Args:
            key: Context key (e.g., "page_url", "element_selector")
            value: Context value (any serializable type)

        Returns:
            AutomationException: Self for method chaining
        """
        self.context[key] = value
        return self

    def add_recovery_suggestion(self, suggestion: str) -> "AutomationException":
        """
        Add a recovery suggestion to help resolve the error.

        Args:
            suggestion: Specific recovery action

        Returns:
            AutomationException: Self for method chaining
        """
        if suggestion not in self.recovery_suggestions:
            self.recovery_suggestions.append(suggestion)
        return self

    def set_severity(self, severity: ErrorSeverity) -> "AutomationException":
        """
        Update the exception severity level.

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
        elif self.retry_strategy == RetryStrategy.EXPONENTIAL_JITTER:
            base = base_delay * (2 ** (attempt - 1))
            jitter = random.uniform(0.8, 1.2)
            return base * jitter
        elif self.retry_strategy == RetryStrategy.RANDOM:
            return random.uniform(0.5, 2.0) * attempt
        else:
            return base_delay

    def add_event_listener(self, listener: ErrorReporter) -> "AutomationException":
        """
        Add an event listener for this exception.

        Args:
            listener: Error reporter that implements ErrorReporter protocol

        Returns:
            AutomationException: Self for method chaining
        """
        self._event_listeners.append(listener)
        return self

    def add_recovery_strategy(self, strategy: RecoveryStrategy) -> "AutomationException":
        """
        Add a recovery strategy for this exception.

        Args:
            strategy: Recovery strategy that implements RecoveryStrategy protocol

        Returns:
            AutomationException: Self for method chaining
        """
        self._recovery_strategies.append(strategy)
        return self

    def notify_listeners(self) -> None:
        """
        Notify all registered event listeners about this exception.
        """
        for listener in self._event_listeners:
            try:
                listener.report_error(self)
            except Exception as e:
                # Don't let listener failures crash the main exception handling
                print(f"Warning: Exception listener failed: {e}")

    def attempt_recovery(self) -> bool:
        """
        Attempt automated recovery using registered strategies.

        Returns:
            bool: True if recovery was successful
        """
        for strategy in self._recovery_strategies:
            try:
                if strategy.can_recover(self):
                    if strategy.attempt_recovery(self):
                        return True
            except Exception as e:
                # Log recovery failure but continue with next strategy
                print(f"Recovery strategy failed: {e}")

        return False

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for serialization.

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
            } if self.original_exception else None,

            # Recovery information
            "should_retry": self.should_retry(),
            "retry_delay": self.get_retry_delay() if self.should_retry() else None
        }

    def to_json(self) -> str:
        """
        Convert exception to JSON string for logging/monitoring.

        Returns:
            str: JSON representation of the exception
        """
        import json
        return json.dumps(self.to_dict(), indent=2, default=str)

    def __str__(self) -> str:
        """
        Return a comprehensive string representation for logging.

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
            context_summary = {k: (str(v)[:50] + "..." if len(str(v)) > 50 else v)
                               for k, v in self.context.items()}
            lines.append(f"📝 Context: {context_summary}")

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


class ExceptionBuilder:
    """
    Builder class for constructing complex exceptions with fluent API.

    Example:
        >>> exception = ExceptionBuilder(ConcreteException) \
        ...     .with_message("Operation failed") \
        ...     .with_severity(ErrorSeverity.HIGH) \
        ...     .add_context("operation", "login") \
        ...     .build()
    """

    def __init__(self, exception_class: type):
        """Initialize exception builder."""
        self.exception_class = exception_class
        self.message = ""
        self.error_code = None
        self.correlation_id = None
        self.category = None
        self.severity = ErrorSeverity.MEDIUM
        self.retry_strategy = RetryStrategy.NONE
        self.context = {}
        self.recovery_suggestions = []
        self.original_exception = None
        self.log_level = LogLevel.ERROR

    def with_message(self, message: str) -> "ExceptionBuilder":
        """Set exception message."""
        self.message = message
        return self

    def with_severity(self, severity: ErrorSeverity) -> "ExceptionBuilder":
        """Set error severity."""
        self.severity = severity
        return self

    def add_context(self, key: str, value: Any) -> "ExceptionBuilder":
        """Add context information."""
        self.context[key] = value
        return self

    def add_recovery_suggestion(self, suggestion: str) -> "ExceptionBuilder":
        """Add recovery suggestion."""
        self.recovery_suggestions.append(suggestion)
        return self

    def with_original_exception(self, exception: Exception) -> "ExceptionBuilder":
        """Set original exception."""
        self.original_exception = exception
        return self

    def build(self) -> AutomationException:
        """
        Build the exception with all configured parameters.

        Returns:
            AutomationException: Constructed exception instance
        """
        exception = self.exception_class(
            message=self.message,
            error_code=self.error_code,
            correlation_id=self.correlation_id,
            category=self.category,
            severity=self.severity,
            retry_strategy=self.retry_strategy,
            context=self.context,
            recovery_suggestions=self.recovery_suggestions,
            original_exception=self.original_exception,
            log_level=self.log_level
        )
        return exception
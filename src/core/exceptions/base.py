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
- Strategy Pattern: Different recovery strategies per exception type

Interview Highlights:
- Enterprise-level exception design with comprehensive context
- Production-ready error tracking and debugging support
- Recovery-oriented exception architecture
- Integration-ready for monitoring and alerting systems
"""

import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

# Import enums from the same package
from .enums import ErrorCategory, ErrorSeverity, LogLevel, RetryStrategy


@dataclass
class ErrorContext:
    """
    Enhanced error context management.

    Provides structured context information for debugging and monitoring.
    Immutable after creation for thread safety.
    """

    data: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add(self, key: str, value: Any) -> 'ErrorContext':
        """Add context data."""
        self.data[key] = value
        return self

    def add_tag(self, tag: str) -> 'ErrorContext':
        """Add a tag for categorization."""
        self.tags.add(tag)
        return self

    def add_metadata(self, key: str, value: Any) -> 'ErrorContext':
        """Add metadata for monitoring systems."""
        self.metadata[key] = value
        return self

    def merge(self, other: 'ErrorContext') -> 'ErrorContext':
        """Merge with another context."""
        self.data.update(other.data)
        self.tags.update(other.tags)
        self.metadata.update(other.metadata)
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data": self.data.copy(),
            "tags": list(self.tags),
            "metadata": self.metadata.copy()
        }


class AutomationException(Exception):
    """
    Base exception class for all test automation framework exceptions.

    This class provides comprehensive error handling with:
    - Rich error context for debugging
    - Recovery suggestions for automatic and manual resolution
    - Structured data for monitoring and alerting integration
    - Unique error tracking with correlation IDs
    - Severity and category classification
    - Event system for error reporting

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
            retry_strategy: Optional[RetryStrategy] = None,
            context: Optional[Dict[str, Any]] = None,
            recovery_suggestions: Optional[List[str]] = None,
            original_exception: Optional[Exception] = None,
            log_level: Optional[LogLevel] = None
    ):
        """
        Initialize automation exception with comprehensive error details.

        Args:
            message: Clear, actionable error description
            error_code: Unique identifier for this error type (auto-generated if None)
            correlation_id: UUID for tracking related errors (auto-generated if None)
            category: Error category for classification
            severity: Severity level for prioritization
            retry_strategy: Suggested retry approach (auto-determined if None)
            context: Additional debugging context
            recovery_suggestions: List of recovery actions
            original_exception: Original exception that caused this error
            log_level: Logging level for this exception (auto-determined if None)
        """
        super().__init__(message)

        # Core error information
        self.message = message
        self.error_code = error_code or self._generate_error_code()
        self.correlation_id = correlation_id or str(uuid4())
        self.category = category
        self.severity = severity

        # Determine retry strategy if not provided
        self.retry_strategy = retry_strategy or category.get_default_retry_strategy()

        # Determine log level if not provided
        self.log_level = log_level or LogLevel.from_severity(severity)

        # Enhanced context
        self.error_context = ErrorContext()
        if context:
            for key, value in context.items():
                self.error_context.add(key, value)

        # Add category-specific tags
        for tag in category.get_monitoring_tags():
            self.error_context.add_tag(tag)

        # Recovery information
        self.recovery_suggestions = recovery_suggestions or []
        self._recovery_callbacks: List[Callable[['AutomationException'], bool]] = []

        # Original exception tracking
        self.original_exception = original_exception
        if original_exception:
            self.error_context.add("original_type", type(original_exception).__name__)
            self.error_context.add("original_message", str(original_exception))

        # Timing and debugging
        self.timestamp = datetime.now(timezone.utc)
        self.stack_trace = traceback.format_exc()

        # Event system
        self._event_listeners: List[Callable[['AutomationException'], None]] = []

        # Statistics
        self._retry_attempts = 0
        self._recovery_attempted = False

    def _generate_error_code(self) -> str:
        """Generate a unique error code based on exception type and timestamp."""
        class_name = self.__class__.__name__.replace("Exception", "").upper()
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S_%f")[:19]  # Include microseconds
        return f"{class_name}_{timestamp}"

    def add_context(self, key: str, value: Any) -> 'AutomationException':
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
        self.error_context.add(key, value)
        return self

    def add_tag(self, tag: str) -> 'AutomationException':
        """Add a tag for categorization and monitoring."""
        self.error_context.add_tag(tag)
        return self

    def add_metadata(self, key: str, value: Any) -> 'AutomationException':
        """Add metadata for monitoring systems."""
        self.error_context.add_metadata(key, value)
        return self

    def add_recovery_suggestion(self, suggestion: str) -> 'AutomationException':
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
        if suggestion and suggestion not in self.recovery_suggestions:
            self.recovery_suggestions.append(suggestion)
        return self

    def add_recovery_callback(
            self,
            callback: Callable[['AutomationException'], bool]
    ) -> 'AutomationException':
        """
        Add a recovery callback function.

        Args:
            callback: Function that attempts recovery, returns True if successful

        Returns:
            AutomationException: Self for method chaining
        """
        self._recovery_callbacks.append(callback)
        return self

    def add_event_listener(
            self,
            listener: Callable[['AutomationException'], None]
    ) -> 'AutomationException':
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

    def set_severity(self, severity: ErrorSeverity) -> 'AutomationException':
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
        # Update log level accordingly
        self.log_level = LogLevel.from_severity(severity)
        return self

    def set_retry_strategy(self, strategy: RetryStrategy) -> 'AutomationException':
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

        # Check if we've exceeded max retry attempts for this severity
        max_attempts = self.severity.max_retry_attempts()
        if self._retry_attempts >= max_attempts:
            return False

        return True

    def get_retry_delay(self, attempt: Optional[int] = None) -> float:
        """
        Calculate retry delay based on the retry strategy and attempt number.

        Args:
            attempt: Current retry attempt number (1-based), uses internal counter if None

        Returns:
            float: Delay in seconds before retry
        """
        attempt_num = attempt if attempt is not None else self._retry_attempts + 1

        # Apply severity-based timeout multiplier
        base_delay = self.retry_strategy.get_base_delay()
        multiplier = self.severity.get_timeout_multiplier()

        return self.retry_strategy.calculate_delay(attempt_num, base_delay * multiplier)

    def increment_retry_attempts(self) -> None:
        """Increment the internal retry attempt counter."""
        self._retry_attempts += 1
        self.add_metadata("retry_attempts", self._retry_attempts)

    def attempt_recovery(self) -> bool:
        """
        Attempt automated recovery using registered callbacks.

        This method tries each recovery callback in order until
        one succeeds or all callbacks are exhausted.

        Returns:
            bool: True if recovery was successful
        """
        if self._recovery_attempted:
            return False  # Only attempt recovery once

        self._recovery_attempted = True

        for callback in self._recovery_callbacks:
            try:
                if callback(self):
                    self.add_metadata("recovery_successful", True)
                    return True
            except Exception as e:
                # Log recovery failure but continue with next callback
                self.add_context("recovery_error", str(e))
                continue

        self.add_metadata("recovery_successful", False)
        return False

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
                self.add_context("listener_error", str(e))

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
            "context": self.error_context.to_dict(),
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
            "retry_delay": self.get_retry_delay() if self.should_retry() else None,
            "retry_attempts": self._retry_attempts,
            "recovery_attempted": self._recovery_attempted,

            # Metadata
            "responsible_team": self.category.get_responsible_team(),
            "recovery_priority": self.category.get_recovery_priority()
        }

    def to_json(self) -> str:
        """
        Convert exception to JSON string for logging/monitoring.

        Returns:
            str: JSON representation of the exception
        """
        return json.dumps(self.to_dict(), indent=2, default=str)

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
            f"📂 Category: {self.category.value} (Team: {self.category.get_responsible_team()})",
            f"⚠️  Severity: {self.severity.value}",
            f"🔄 Retry Strategy: {self.retry_strategy.value}",
            f"⏰ Timestamp: {self.timestamp.isoformat()}",
        ]

        if self.error_context.data:
            context_str = ', '.join(f"{k}={v}" for k, v in list(self.error_context.data.items())[:5])
            lines.append(f"📝 Context: {context_str}")

        if self.error_context.tags:
            lines.append(f"🏷️  Tags: {', '.join(list(self.error_context.tags)[:5])}")

        if self.recovery_suggestions:
            lines.append("💡 Recovery Suggestions:")
            for i, suggestion in enumerate(self.recovery_suggestions[:3], 1):
                lines.append(f"   {i}. {suggestion}")

        if self.original_exception:
            lines.append(f"🔗 Original: {type(self.original_exception).__name__}: {str(self.original_exception)[:100]}")

        return "\n".join(lines)

    def __repr__(self) -> str:
        """Return a concise representation suitable for debugging."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message[:50]}...', "
            f"category={self.category.value}, "
            f"severity={self.severity.value}, "
            f"error_code='{self.error_code}'"
            f")"
        )
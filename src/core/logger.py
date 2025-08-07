# src/core/logger.py
"""
Structured Logging System for Test Automation Framework

This module provides enterprise-grade logging with:
- Structured JSON logging for machine readability
- Correlation IDs for tracking related operations
- Performance metrics collection
- Multiple output destinations (console, file, external systems)
- Automatic context enrichment

Key Design Patterns:
- Singleton Pattern: Single logger configuration per application
- Context Manager: Automatic context cleanup
- Observer Pattern: Event-driven logging with listeners
- Factory Pattern: Logger creation with different configurations

Interview Highlights:
- Production-ready structured logging with correlation tracking
- Performance monitoring integration
- Multi-destination logging (console, files, external systems)
- Context-aware logging with automatic enrichment
"""

import json
import logging
import logging.handlers
import sys
import time
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import structlog

# Context variables for correlation tracking
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')
test_id_var: ContextVar[str] = ContextVar('test_id', default='')
user_session_var: ContextVar[str] = ContextVar('user_session', default='')


class PerformanceTimer:
    """
    Context manager for measuring operation performance.

    This class automatically logs performance metrics for operations
    and can be used as a decorator or context manager.

    Example:
        >>> with PerformanceTimer("login_operation") as timer:
        ...     perform_login()
        ...     timer.add_metric("steps_completed", 3)
    """

    def __init__(self, operation_name: str, logger: Optional[structlog.BoundLogger] = None):
        """
        Initialize performance timer.

        Args:
            operation_name: Name of the operation being timed
            logger: Logger instance to use (defaults to framework logger)
        """
        self.operation_name = operation_name
        self.logger = logger or get_logger()
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.metrics: Dict[str, Any] = {}

    def __enter__(self) -> "PerformanceTimer":
        """Start timing the operation."""
        self.start_time = time.perf_counter()
        self.logger.debug(
            "Operation started",
            operation=self.operation_name,
            event_type="performance_start"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """End timing and log performance metrics."""
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time if self.start_time else 0

        # Log performance completion
        log_data = {
            "operation": self.operation_name,
            "duration_seconds": round(duration, 3),
            "event_type": "performance_end",
            **self.metrics
        }

        if exc_type is None:
            self.logger.info("Operation completed successfully", **log_data)
        else:
            log_data["exception_type"] = exc_type.__name__ if exc_type else None
            log_data["exception_message"] = str(exc_val) if exc_val else None
            self.logger.error("Operation failed", **log_data)

    def add_metric(self, key: str, value: Any) -> None:
        """Add a custom metric to be logged with performance data."""
        self.metrics[key] = value

    @property
    def duration(self) -> Optional[float]:
        """Get the current or final duration of the operation."""
        if self.start_time is None:
            return None
        end_time = self.end_time or time.perf_counter()
        return end_time - self.start_time


class LoggingManager:
    """
    Central logging management system.

    This class configures and manages the logging system for the entire
    test automation framework. It provides structured logging with
    correlation tracking and multiple output destinations.
    """

    def __init__(self):
        """Initialize the logging manager."""
        self._configured = False
        self._loggers: Dict[str, structlog.BoundLogger] = {}
        self._log_file_handlers: List[logging.Handler] = []

    def configure_logging(
            self,
            log_level: str = "INFO",
            enable_console: bool = True,
            enable_file: bool = True,
            log_file_path: Optional[Path] = None,
            enable_json_format: bool = True,
            enable_correlation_id: bool = True,
            max_file_size_mb: int = 100,
            backup_count: int = 5
    ) -> None:
        """
        Configure the logging system with specified parameters.

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            enable_console: Enable console output
            enable_file: Enable file output
            log_file_path: Path to log file (default: logs/automation.log)
            enable_json_format: Use structured JSON format
            enable_correlation_id: Enable correlation ID tracking
            max_file_size_mb: Maximum log file size in MB
            backup_count: Number of backup log files to keep
        """
        if self._configured:
            return

        # Configure standard library logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format="%(message)s",  # structlog will handle formatting
            handlers=[]
        )

        # Build processor chain for structlog
        processors = []

        # Add correlation ID processor if enabled
        if enable_correlation_id:
            processors.append(self._add_correlation_context)

        # Add standard processors
        processors.extend([
            self._add_timestamp,
            self._add_log_level,
            self._add_framework_context,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
        ])

        # Configure output format
        if enable_json_format:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        # Configure structlog
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Set up output destinations
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        if enable_console:
            self._setup_console_handler(root_logger)

        if enable_file:
            log_path = log_file_path or Path("logs/automation.log")
            self._setup_file_handler(root_logger, log_path, max_file_size_mb, backup_count)

        self._configured = True

        # Log configuration completion
        logger = self.get_logger("logging_manager")
        logger.info(
            "Logging system configured",
            log_level=log_level,
            console_enabled=enable_console,
            file_enabled=enable_file,
            json_format=enable_json_format,
            correlation_tracking=enable_correlation_id
        )

    def _setup_console_handler(self, root_logger: logging.Logger) -> None:
        """Set up console logging handler."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

    def _setup_file_handler(
            self,
            root_logger: logging.Logger,
            log_path: Path,
            max_size_mb: int,
            backup_count: int
    ) -> None:
        """Set up rotating file logging handler."""
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        max_bytes = max_size_mb * 1024 * 1024
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)

        root_logger.addHandler(file_handler)
        self._log_file_handlers.append(file_handler)

    def _add_correlation_context(self, logger, method_name, event_dict):
        """Add correlation context to log entries."""
        correlation_id = correlation_id_var.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id

        test_id = test_id_var.get()
        if test_id:
            event_dict['test_id'] = test_id

        user_session = user_session_var.get()
        if user_session:
            event_dict['user_session'] = user_session

        return event_dict

    def _add_timestamp(self, logger, method_name, event_dict):
        """Add timestamp to log entries."""
        event_dict['timestamp'] = datetime.now().isoformat()
        return event_dict

    def _add_log_level(self, logger, method_name, event_dict):
        """Add log level to event dict if not present."""
        if 'level' not in event_dict:
            event_dict['level'] = method_name.upper()
        return event_dict

    def _add_framework_context(self, logger, method_name, event_dict):
        """Add framework-specific context to log entries."""
        event_dict['framework'] = 'sock-shop-automation'
        event_dict['version'] = '1.0.0'
        return event_dict

    def get_logger(self, name: str = "automation") -> structlog.BoundLogger:
        """
        Get a configured logger instance.

        Args:
            name: Logger name for identification

        Returns:
            structlog.BoundLogger: Configured logger instance
        """
        if not self._configured:
            # Configure with defaults if not already configured
            self.configure_logging()

        if name not in self._loggers:
            self._loggers[name] = structlog.get_logger(name)

        return self._loggers[name]

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for the current context."""
        correlation_id_var.set(correlation_id)

    def set_test_id(self, test_id: str) -> None:
        """Set test ID for the current context."""
        test_id_var.set(test_id)

    def set_user_session(self, user_session: str) -> None:
        """Set user session ID for the current context."""
        user_session_var.set(user_session)

    def clear_context(self) -> None:
        """Clear all context variables."""
        correlation_id_var.set('')
        test_id_var.set('')
        user_session_var.set('')

    def get_log_file_paths(self) -> List[Path]:
        """Get paths to all active log files."""
        paths = []
        for handler in self._log_file_handlers:
            if hasattr(handler, 'baseFilename'):
                paths.append(Path(handler.baseFilename))
        return paths


# Global logging manager instance
_logging_manager = LoggingManager()


def setup_logging(
        log_level: str = "INFO",
        enable_console: bool = True,
        enable_file: bool = True,
        log_file_path: Optional[Path] = None,
        enable_json_format: bool = True,
        enable_correlation_id: bool = True,
        max_file_size_mb: int = 100,
        backup_count: int = 5
) -> None:
    """
    Set up logging for the test automation framework.

    This is the main entry point for configuring logging.
    Should be called once at application startup.

    Args:
        log_level: Logging level
        enable_console: Enable console output
        enable_file: Enable file output
        log_file_path: Path to log file
        enable_json_format: Use structured JSON format
        enable_correlation_id: Enable correlation ID tracking
        max_file_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep

    Example:
        >>> setup_logging(
        ...     log_level="DEBUG",
        ...     enable_json_format=True,
        ...     log_file_path=Path("logs/test_run.log")
        ... )
    """
    _logging_manager.configure_logging(
        log_level=log_level,
        enable_console=enable_console,
        enable_file=enable_file,
        log_file_path=log_file_path,
        enable_json_format=enable_json_format,
        enable_correlation_id=enable_correlation_id,
        max_file_size_mb=max_file_size_mb,
        backup_count=backup_count
    )


def get_logger(name: str = "automation") -> structlog.BoundLogger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name for identification

    Returns:
        structlog.BoundLogger: Configured logger instance

    Example:
        >>> logger = get_logger("page_operations")
        >>> logger.info("Navigating to page", url="https://example.com")
    """
    return _logging_manager.get_logger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID for tracking related operations.

    Args:
        correlation_id: Explicit correlation ID, or None to generate new one

    Returns:
        str: The correlation ID that was set

    Example:
        >>> correlation_id = set_correlation_id()
        >>> logger = get_logger()
        >>> logger.info("Starting operation")  # Will include correlation_id
    """
    if correlation_id is None:
        correlation_id = str(uuid4())
    _logging_manager.set_correlation_id(correlation_id)
    return correlation_id


def set_test_id(test_id: str) -> None:
    """Set test ID for the current test execution."""
    _logging_manager.set_test_id(test_id)


def set_user_session(user_session: str) -> None:
    """Set user session ID for tracking user-specific operations."""
    _logging_manager.set_user_session(user_session)


def clear_logging_context() -> None:
    """Clear all logging context variables."""
    _logging_manager.clear_context()


def get_performance_timer(operation_name: str) -> PerformanceTimer:
    """
    Create a performance timer for measuring operation duration.

    Args:
        operation_name: Name of the operation to time

    Returns:
        PerformanceTimer: Timer instance for use as context manager

    Example:
        >>> with get_performance_timer("page_load") as timer:
        ...     page.goto("https://example.com")
        ...     timer.add_metric("page_size_mb", 2.5)
    """
    return PerformanceTimer(operation_name)


class LoggingContext:
    """
    Context manager for automatic logging context management.

    This class automatically sets up and cleans up logging context
    for operations like test execution or user sessions.

    Example:
        >>> with LoggingContext(test_id="test_login", user_session="session_123"):
        ...     logger = get_logger()
        ...     logger.info("Test step executed")  # Includes context automatically
    """

    def __init__(
            self,
            correlation_id: Optional[str] = None,
            test_id: Optional[str] = None,
            user_session: Optional[str] = None
    ):
        """
        Initialize logging context.

        Args:
            correlation_id: Correlation ID for operation tracking
            test_id: Test identification
            user_session: User session identification
        """
        self.correlation_id = correlation_id
        self.test_id = test_id
        self.user_session = user_session
        self._previous_correlation_id = ''
        self._previous_test_id = ''
        self._previous_user_session = ''

    def __enter__(self) -> "LoggingContext":
        """Set up logging context."""
        # Store previous values
        self._previous_correlation_id = correlation_id_var.get()
        self._previous_test_id = test_id_var.get()
        self._previous_user_session = user_session_var.get()

        # Set new values
        if self.correlation_id is not None:
            set_correlation_id(self.correlation_id)
        elif not self._previous_correlation_id:
            set_correlation_id()  # Generate new correlation ID

        if self.test_id is not None:
            set_test_id(self.test_id)

        if self.user_session is not None:
            set_user_session(self.user_session)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore previous logging context."""
        correlation_id_var.set(self._previous_correlation_id)
        test_id_var.set(self._previous_test_id)
        user_session_var.set(self._previous_user_session)


def log_test_step(step_name: str, **kwargs) -> None:
    """
    Log a test step with standardized format.

    Args:
        step_name: Name of the test step
        **kwargs: Additional context to include

    Example:
        >>> log_test_step("Navigate to login page", url="https://app.com/login")
        >>> log_test_step("Enter credentials", username="test_user")
    """
    logger = get_logger("test_steps")
    logger.info(
        f"Test step: {step_name}",
        step_name=step_name,
        event_type="test_step",
        **kwargs
    )


def log_assertion(assertion_type: str, expected: Any, actual: Any, passed: bool) -> None:
    """
    Log test assertion results with standardized format.

    Args:
        assertion_type: Type of assertion (equals, contains, etc.)
        expected: Expected value
        actual: Actual value
        passed: Whether assertion passed

    Example:
        >>> log_assertion("equals", "Welcome", page_title, page_title == "Welcome")
    """
    logger = get_logger("assertions")
    log_method = logger.info if passed else logger.error

    log_method(
        f"Assertion {assertion_type}: {'PASSED' if passed else 'FAILED'}",
        assertion_type=assertion_type,
        expected=expected,
        actual=actual,
        passed=passed,
        event_type="assertion"
    )
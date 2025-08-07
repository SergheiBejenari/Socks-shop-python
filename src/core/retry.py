# src/core/retry.py
"""
Intelligent Retry System for Test Automation Framework

This module provides sophisticated retry mechanisms with:
- Multiple retry strategies (exponential backoff, linear, fixed, random)
- Exception-aware retry logic
- Circuit breaker pattern for preventing cascade failures
- Retry statistics and monitoring
- Configurable retry policies per operation type

Key Design Patterns:
- Strategy Pattern: Different retry strategies for different scenarios
- Decorator Pattern: Easy application of retry logic to functions
- Circuit Breaker Pattern: Fail-fast when services are down
- Observer Pattern: Retry event monitoring and metrics

Interview Highlights:
- Production-ready retry mechanisms with intelligent backoff
- Circuit breaker pattern for system resilience
- Comprehensive retry statistics and monitoring
- Exception-aware retry decisions based on error types
"""

import asyncio
import functools
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union
from uuid import uuid4

from exceptions.base import AutomationException
from exceptions.enums import ErrorSeverity, ErrorCategory
from logger import get_logger

F = TypeVar('F', bound=Callable[..., Any])


class RetryStrategy(str, Enum):
    """
    Retry strategies for different failure scenarios.

    Each strategy implements a different approach to timing
    retry attempts based on the nature of the failure.
    """

    FIXED = "fixed"
    """Fixed delay between retry attempts."""

    LINEAR = "linear"
    """Linear backoff - delay increases linearly with attempt number."""

    EXPONENTIAL = "exponential"
    """Exponential backoff - delay doubles with each attempt."""

    EXPONENTIAL_JITTER = "exponential_jitter"
    """Exponential backoff with random jitter to prevent thundering herd."""

    RANDOM = "random"
    """Random delay within specified bounds."""


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    This class encapsulates all retry-related settings and provides
    sensible defaults for different types of operations.
    """

    max_attempts: int = 3
    """Maximum number of retry attempts (including initial attempt)."""

    base_delay: float = 1.0
    """Base delay in seconds between attempts."""

    max_delay: float = 60.0
    """Maximum delay in seconds between attempts."""

    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_JITTER
    """Retry strategy to use."""

    backoff_multiplier: float = 2.0
    """Multiplier for exponential backoff strategies."""

    jitter_range: tuple[float, float] = (0.8, 1.2)
    """Range for random jitter (as multipliers of calculated delay)."""

    retryable_exceptions: Set[Type[Exception]] = field(
        default_factory=lambda: {
            AutomationException,
            ConnectionError,
            TimeoutError,
        }
    )
    """Exception types that should trigger retry attempts."""

    non_retryable_exceptions: Set[Type[Exception]] = field(
        default_factory=lambda: {
            KeyboardInterrupt,
            SystemExit,
            MemoryError,
        }
    )
    """Exception types that should never be retried."""

    retry_on_severity: Set[ErrorSeverity] = field(
        default_factory=lambda: {
            ErrorSeverity.LOW,
            ErrorSeverity.MEDIUM
        }
    )
    """AutomationException severity levels that allow retry."""

    retry_on_categories: Set[ErrorCategory] = field(
        default_factory=lambda: {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.BROWSER,
        }
    )
    """AutomationException categories that allow retry."""


@dataclass
class RetryAttempt:
    """Information about a single retry attempt."""

    attempt_number: int
    """Attempt number (1-based)."""

    timestamp: datetime
    """When the attempt was made."""

    exception: Optional[Exception]
    """Exception that caused the retry (None for successful attempts)."""

    delay_before: float
    """Delay in seconds before this attempt."""

    duration: float = 0.0
    """How long the attempt took in seconds."""


@dataclass
class RetryStats:
    """Statistics about retry operations."""

    operation_id: str
    """Unique identifier for the operation."""

    operation_name: str
    """Human-readable operation name."""

    total_attempts: int = 0
    """Total number of attempts made."""

    successful_attempts: int = 0
    """Number of successful attempts."""

    failed_attempts: int = 0
    """Number of failed attempts."""

    total_duration: float = 0.0
    """Total time spent on all attempts."""

    attempts: List[RetryAttempt] = field(default_factory=list)
    """Detailed information about each attempt."""

    final_success: bool = False
    """Whether the operation ultimately succeeded."""

    final_exception: Optional[Exception] = None
    """Final exception if operation failed completely."""

    @property
    def average_attempt_duration(self) -> float:
        """Average duration per attempt."""
        return self.total_duration / max(1, self.total_attempts)

    @property
    def success_rate(self) -> float:
        """Success rate as a percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.successful_attempts / self.total_attempts) * 100


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascade failures.

    The circuit breaker monitors failures and can temporarily stop
    attempts to call a failing service, allowing it time to recover.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
            self,
            failure_threshold: int = 5,
            recovery_timeout: float = 60.0,
            success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failures needed to open circuit
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Successes needed to close circuit from half-open
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

        self.logger = get_logger("circuit_breaker")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker.

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker half-open, testing service")
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout

    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0

        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "CLOSED"
                self.success_count = 0
                self.logger.info("Circuit breaker closed - service recovered")

    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now()

        if (self.state == "CLOSED" and
                self.failure_count >= self.failure_threshold):
            self.state = "OPEN"
            self.logger.warning(
                "Circuit breaker opened - service failing",
                failure_count=self.failure_count,
                threshold=self.failure_threshold
            )
        elif self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.logger.warning("Circuit breaker re-opened - service still failing")


class RetryManager:
    """
    Central manager for retry operations and statistics.

    This class tracks retry operations, collects statistics,
    and manages circuit breakers for different services.
    """

    def __init__(self):
        """Initialize retry manager."""
        self.stats: Dict[str, RetryStats] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = get_logger("retry_manager")

    def get_stats(self, operation_name: Optional[str] = None) -> Union[Dict[str, RetryStats], RetryStats]:
        """
        Get retry statistics.

        Args:
            operation_name: Specific operation name, or None for all stats

        Returns:
            Statistics for specified operation or all operations
        """
        if operation_name:
            return self.stats.get(operation_name)
        return self.stats.copy()

    def get_circuit_breaker(self, service_name: str, **kwargs) -> CircuitBreaker:
        """
        Get or create circuit breaker for a service.

        Args:
            service_name: Name of the service
            **kwargs: Circuit breaker configuration options

        Returns:
            CircuitBreaker instance for the service
        """
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = CircuitBreaker(**kwargs)
        return self.circuit_breakers[service_name]

    def clear_stats(self) -> None:
        """Clear all retry statistics."""
        self.stats.clear()
        self.logger.info("Retry statistics cleared")

    def _record_stats(self, stats: RetryStats) -> None:
        """Record retry statistics."""
        self.stats[stats.operation_name] = stats


# Global retry manager instance
_retry_manager = RetryManager()


def calculate_delay(
        attempt: int,
        config: RetryConfig
) -> float:
    """
    Calculate delay before next retry attempt.

    Args:
        attempt: Current attempt number (1-based)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    if attempt <= 1:
        return 0.0

    if config.strategy == RetryStrategy.FIXED:
        delay = config.base_delay

    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.base_delay * (attempt - 1)

    elif config.strategy == RetryStrategy.EXPONENTIAL:
        delay = config.base_delay * (config.backoff_multiplier ** (attempt - 2))

    elif config.strategy == RetryStrategy.EXPONENTIAL_JITTER:
        base_delay = config.base_delay * (config.backoff_multiplier ** (attempt - 2))
        jitter_min, jitter_max = config.jitter_range
        jitter = random.uniform(jitter_min, jitter_max)
        delay = base_delay * jitter

    elif config.strategy == RetryStrategy.RANDOM:
        delay = random.uniform(config.base_delay, config.max_delay)

    else:
        delay = config.base_delay

    # Cap the delay at max_delay
    return min(delay, config.max_delay)


def should_retry(
        exception: Exception,
        attempt: int,
        config: RetryConfig
) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: Exception that occurred
        attempt: Current attempt number
        config: Retry configuration

    Returns:
        True if should retry, False otherwise
    """
    # Check if we've exceeded max attempts
    if attempt >= config.max_attempts:
        return False

    # Check for non-retryable exceptions first
    for exc_type in config.non_retryable_exceptions:
        if isinstance(exception, exc_type):
            return False

    # Check for AutomationException specific rules
    if isinstance(exception, AutomationException):
        # Check severity level
        if exception.severity not in config.retry_on_severity:
            return False

        # Check error category
        if exception.category not in config.retry_on_categories:
            return False

    # Check for retryable exceptions
    for exc_type in config.retryable_exceptions:
        if isinstance(exception, exc_type):
            return True

    # Default: don't retry unknown exceptions
    return False


def retry_with_backoff(
        config: Optional[RetryConfig] = None,
        operation_name: Optional[str] = None,
        circuit_breaker: Optional[str] = None
) -> Callable[[F], F]:
    """
    Decorator for adding retry logic with intelligent backoff.

    Args:
        config: Retry configuration (uses defaults if None)
        operation_name: Name for logging and stats (uses function name if None)
        circuit_breaker: Circuit breaker service name (optional)

    Returns:
        Decorated function with retry logic

    Example:
        >>> @retry_with_backoff(
        ...     config=RetryConfig(max_attempts=5, strategy=RetryStrategy.EXPONENTIAL),
        ...     operation_name="api_call"
        ... )
        ... def call_api():
        ...     return requests.get("https://api.example.com/data")
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return _execute_with_retry(
                func, args, kwargs, config, operation_name, circuit_breaker
            )

        return wrapper

    return decorator


async def retry_async_with_backoff(
        config: Optional[RetryConfig] = None,
        operation_name: Optional[str] = None,
        circuit_breaker: Optional[str] = None
) -> Callable[[F], F]:
    """
    Async version of retry decorator.

    Args:
        config: Retry configuration
        operation_name: Operation name for logging
        circuit_breaker: Circuit breaker service name

    Returns:
        Decorated async function with retry logic
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await _execute_async_with_retry(
                func, args, kwargs, config, operation_name, circuit_breaker
            )

        return wrapper

    return decorator


def _execute_with_retry(
        func: Callable,
        args: tuple,
        kwargs: dict,
        config: RetryConfig,
        operation_name: Optional[str],
        circuit_breaker_name: Optional[str]
) -> Any:
    """Execute function with retry logic (synchronous)."""
    op_name = operation_name or func.__name__
    operation_id = str(uuid4())

    logger = get_logger("retry")
    stats = RetryStats(
        operation_id=operation_id,
        operation_name=op_name
    )

    # Get circuit breaker if specified
    circuit_breaker = None
    if circuit_breaker_name:
        circuit_breaker = _retry_manager.get_circuit_breaker(circuit_breaker_name)

    logger.info(
        f"Starting operation with retry",
        operation_name=op_name,
        operation_id=operation_id,
        max_attempts=config.max_attempts,
        strategy=config.strategy.value
    )

    for attempt in range(1, config.max_attempts + 1):
        attempt_start = time.perf_counter()
        delay_before = calculate_delay(attempt, config) if attempt > 1 else 0.0

        # Apply delay before attempt (except first attempt)
        if delay_before > 0:
            logger.debug(
                f"Waiting before attempt {attempt}",
                delay_seconds=delay_before,
                attempt=attempt,
                operation_id=operation_id
            )
            time.sleep(delay_before)

        try:
            # Execute through circuit breaker if configured
            if circuit_breaker:
                result = circuit_breaker.call(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record successful attempt
            attempt_duration = time.perf_counter() - attempt_start
            attempt_info = RetryAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                exception=None,
                delay_before=delay_before,
                duration=attempt_duration
            )

            stats.attempts.append(attempt_info)
            stats.total_attempts += 1
            stats.successful_attempts += 1
            stats.total_duration += attempt_duration
            stats.final_success = True

            logger.info(
                f"Operation succeeded on attempt {attempt}",
                attempt=attempt,
                duration=attempt_duration,
                operation_id=operation_id
            )

            # Record stats and return result
            _retry_manager._record_stats(stats)
            return result

        except Exception as e:
            attempt_duration = time.perf_counter() - attempt_start
            attempt_info = RetryAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                exception=e,
                delay_before=delay_before,
                duration=attempt_duration
            )

            stats.attempts.append(attempt_info)
            stats.total_attempts += 1
            stats.failed_attempts += 1
            stats.total_duration += attempt_duration
            stats.final_exception = e

            # Check if we should retry
            if should_retry(e, attempt, config):
                logger.warning(
                    f"Attempt {attempt} failed, will retry",
                    attempt=attempt,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    duration=attempt_duration,
                    operation_id=operation_id
                )
                continue
            else:
                logger.error(
                    f"Attempt {attempt} failed, no more retries",
                    attempt=attempt,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    duration=attempt_duration,
                    operation_id=operation_id
                )
                break

    # All attempts failed
    logger.error(
        f"Operation failed after {stats.total_attempts} attempts",
        operation_name=op_name,
        total_attempts=stats.total_attempts,
        total_duration=stats.total_duration,
        operation_id=operation_id
    )

    _retry_manager._record_stats(stats)
    raise stats.final_exception


async def _execute_async_with_retry(
        func: Callable,
        args: tuple,
        kwargs: dict,
        config: RetryConfig,
        operation_name: Optional[str],
        circuit_breaker_name: Optional[str]
) -> Any:
    """Execute async function with retry logic."""
    op_name = operation_name or func.__name__
    operation_id = str(uuid4())

    logger = get_logger("retry")
    stats = RetryStats(
        operation_id=operation_id,
        operation_name=op_name
    )

    # Get circuit breaker if specified
    circuit_breaker = None
    if circuit_breaker_name:
        circuit_breaker = _retry_manager.get_circuit_breaker(circuit_breaker_name)

    logger.info(
        f"Starting async operation with retry",
        operation_name=op_name,
        operation_id=operation_id,
        max_attempts=config.max_attempts,
        strategy=config.strategy.value
    )

    for attempt in range(1, config.max_attempts + 1):
        attempt_start = time.perf_counter()
        delay_before = calculate_delay(attempt, config) if attempt > 1 else 0.0

        # Apply delay before attempt (except first attempt)
        if delay_before > 0:
            logger.debug(
                f"Waiting before async attempt {attempt}",
                delay_seconds=delay_before,
                attempt=attempt,
                operation_id=operation_id
            )
            await asyncio.sleep(delay_before)

        try:
            # Execute through circuit breaker if configured
            if circuit_breaker:
                result = circuit_breaker.call(func, *args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                result = await func(*args, **kwargs)

            # Record successful attempt
            attempt_duration = time.perf_counter() - attempt_start
            attempt_info = RetryAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                exception=None,
                delay_before=delay_before,
                duration=attempt_duration
            )

            stats.attempts.append(attempt_info)
            stats.total_attempts += 1
            stats.successful_attempts += 1
            stats.total_duration += attempt_duration
            stats.final_success = True

            logger.info(
                f"Async operation succeeded on attempt {attempt}",
                attempt=attempt,
                duration=attempt_duration,
                operation_id=operation_id
            )

            # Record stats and return result
            _retry_manager._record_stats(stats)
            return result

        except Exception as e:
            attempt_duration = time.perf_counter() - attempt_start
            attempt_info = RetryAttempt(
                attempt_number=attempt,
                timestamp=datetime.now(),
                exception=e,
                delay_before=delay_before,
                duration=attempt_duration
            )

            stats.attempts.append(attempt_info)
            stats.total_attempts += 1
            stats.failed_attempts += 1
            stats.total_duration += attempt_duration
            stats.final_exception = e

            # Check if we should retry
            if should_retry(e, attempt, config):
                logger.warning(
                    f"Async attempt {attempt} failed, will retry",
                    attempt=attempt,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    duration=attempt_duration,
                    operation_id=operation_id
                )
                continue
            else:
                logger.error(
                    f"Async attempt {attempt} failed, no more retries",
                    attempt=attempt,
                    exception_type=type(e).__name__,
                    exception_message=str(e),
                    duration=attempt_duration,
                    operation_id=operation_id
                )
                break

    # All attempts failed
    logger.error(
        f"Async operation failed after {stats.total_attempts} attempts",
        operation_name=op_name,
        total_attempts=stats.total_attempts,
        total_duration=stats.total_duration,
        operation_id=operation_id
    )

    _retry_manager._record_stats(stats)
    raise stats.final_exception


# Convenience functions and pre-configured retry configs
def get_retry_manager() -> RetryManager:
    """Get the global retry manager instance."""
    return _retry_manager


def create_network_retry_config() -> RetryConfig:
    """Create retry configuration optimized for network operations."""
    return RetryConfig(
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        backoff_multiplier=2.0,
        retry_on_categories={
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.INFRASTRUCTURE
        }
    )


def create_browser_retry_config() -> RetryConfig:
    """Create retry configuration optimized for browser operations."""
    return RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=10.0,
        strategy=RetryStrategy.LINEAR,
        retry_on_categories={
            ErrorCategory.BROWSER,
            ErrorCategory.ELEMENT,
            ErrorCategory.TIMEOUT
        }
    )


def create_api_retry_config() -> RetryConfig:
    """Create retry configuration optimized for API operations."""
    return RetryConfig(
        max_attempts=4,
        base_delay=0.5,
        max_delay=20.0,
        strategy=RetryStrategy.EXPONENTIAL_JITTER,
        backoff_multiplier=1.5,
        retry_on_categories={
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.AUTHENTICATION
        }
    )
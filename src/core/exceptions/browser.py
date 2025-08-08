# src/core/exceptions/browser.py
"""
Browser-Related Exception Classes

This module defines exceptions specific to browser operations including
launch failures, crashes, navigation issues, and timeout problems.

Key Design Patterns:
- Inheritance from AutomationException for consistent error handling
- Specific recovery strategies for browser-related issues
- Rich context for debugging browser problems
- Integration with browser session management

Interview Highlights:
- Comprehensive browser error classification
- Recovery-oriented design for browser failures
- Performance-aware timeout handling
- Cross-browser compatibility considerations
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import AutomationException
from .enums import ErrorCategory, ErrorSeverity, RetryStrategy


class BrowserException(AutomationException):
    """
    Base class for all browser-related exceptions.

    This exception covers browser operations like launching,
    navigation, and general browser management issues.
    """

    def __init__(
            self,
            message: str,
            browser_name: Optional[str] = None,
            browser_version: Optional[str] = None,
            session_id: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser exception with browser-specific context.

        Args:
            message: Error description
            browser_name: Name of browser (chromium, firefox, webkit)
            browser_version: Browser version if available
            session_id: Browser session ID if available
            **kwargs: Additional arguments for AutomationException
        """
        # Set browser-specific defaults
        kwargs.setdefault('category', ErrorCategory.BROWSER)
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(message=message, **kwargs)

        # Add browser-specific context
        self.browser_name = browser_name
        self.browser_version = browser_version
        self.session_id = session_id

        if browser_name:
            self.add_context("browser_name", browser_name)
            self.add_tag(f"browser_{browser_name.lower()}")

        if browser_version:
            self.add_context("browser_version", browser_version)

        if session_id:
            self.add_context("session_id", session_id)
            self.add_metadata("session_id", session_id)

        # Add common recovery suggestions for browser issues
        self._add_common_browser_suggestions()

    def _add_common_browser_suggestions(self) -> None:
        """Add common recovery suggestions for browser issues."""
        self.add_recovery_suggestion("Check if browser is properly installed")
        self.add_recovery_suggestion("Verify browser executable permissions")
        self.add_recovery_suggestion("Try restarting the browser")
        self.add_recovery_suggestion("Check system resources (memory, disk space)")


class BrowserLaunchException(BrowserException):
    """
    Exception for browser launch failures.

    This exception is raised when the browser cannot be started,
    typically due to missing executables, permission issues,
    or system resource constraints.
    """

    def __init__(
            self,
            message: str,
            browser_name: Optional[str] = None,
            executable_path: Optional[str] = None,
            launch_args: Optional[List[str]] = None,
            launch_timeout: Optional[int] = None,
            **kwargs
    ):
        """
        Initialize browser launch exception.

        Args:
            message: Error description
            browser_name: Browser that failed to launch
            executable_path: Path to browser executable
            launch_args: Arguments used for launch
            launch_timeout: Timeout value used for launch
            **kwargs: Additional exception arguments
        """
        # Launch failures are critical
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Failed to launch browser: {message}",
            browser_name=browser_name,
            **kwargs
        )

        self.executable_path = executable_path
        self.launch_args = launch_args
        self.launch_timeout = launch_timeout

        if executable_path:
            self.add_context("executable_path", executable_path)

        if launch_args:
            self.add_context("launch_args", launch_args)
            self.add_context("launch_args_count", len(launch_args))

        if launch_timeout:
            self.add_context("launch_timeout", launch_timeout)

        # Launch-specific recovery suggestions
        self._add_launch_specific_suggestions()

    def _add_launch_specific_suggestions(self) -> None:
        """Add launch-specific recovery suggestions."""
        self.add_recovery_suggestion("Verify browser executable exists and is accessible")
        self.add_recovery_suggestion("Check browser installation and try reinstalling")
        self.add_recovery_suggestion("Try launching browser manually to test")
        self.add_recovery_suggestion("Check for browser updates or use different version")

        if self.executable_path:
            self.add_recovery_suggestion(f"Verify path exists: {self.executable_path}")

        if self.launch_timeout and self.launch_timeout < 30000:
            self.add_recovery_suggestion("Consider increasing launch timeout")


class BrowserCrashException(BrowserException):
    """
    Exception for browser crashes during execution.

    This exception handles scenarios where the browser unexpectedly
    terminates or becomes unresponsive during test execution.
    """

    def __init__(
            self,
            message: str,
            crash_reason: Optional[str] = None,
            last_url: Optional[str] = None,
            crash_time: Optional[datetime] = None,
            memory_usage_mb: Optional[int] = None,
            open_tabs_count: Optional[int] = None,
            **kwargs
    ):
        """
        Initialize browser crash exception.

        Args:
            message: Error description
            crash_reason: Reason for crash if known
            last_url: Last URL being accessed when crash occurred
            crash_time: When the crash happened
            memory_usage_mb: Memory usage at crash time
            open_tabs_count: Number of open tabs/windows
            **kwargs: Additional exception arguments
        """
        # Crashes are critical and need exponential backoff
        kwargs.setdefault('severity', ErrorSeverity.CRITICAL)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL)

        super().__init__(
            message=f"Browser crashed: {message}",
            **kwargs
        )

        self.crash_reason = crash_reason
        self.last_url = last_url
        self.crash_time = crash_time or datetime.now()
        self.memory_usage_mb = memory_usage_mb
        self.open_tabs_count = open_tabs_count

        if crash_reason:
            self.add_context("crash_reason", crash_reason)
            self.add_tag(f"crash_{crash_reason.lower().replace(' ', '_')}")

        if last_url:
            self.add_context("last_url", last_url)

        if crash_time:
            self.add_context("crash_time", crash_time.isoformat())

        if memory_usage_mb:
            self.add_context("memory_usage_mb", memory_usage_mb)
            self.add_metadata("memory_usage_mb", memory_usage_mb)

        if open_tabs_count:
            self.add_context("open_tabs_count", open_tabs_count)

        # Crash-specific recovery suggestions
        self._add_crash_recovery_suggestions()

    def _add_crash_recovery_suggestions(self) -> None:
        """Add crash-specific recovery suggestions."""
        self.add_recovery_suggestion("Restart browser with fresh session")
        self.add_recovery_suggestion("Check browser logs for crash details")
        self.add_recovery_suggestion("Verify page content didn't cause crash")
        self.add_recovery_suggestion("Try with different browser if crash persists")
        self.add_recovery_suggestion("Check system memory and close other applications")

        if self.memory_usage_mb and self.memory_usage_mb > 1024:
            self.add_recovery_suggestion("High memory usage detected - consider closing tabs")

        if self.open_tabs_count and self.open_tabs_count > 10:
            self.add_recovery_suggestion("Many tabs open - consider reducing concurrent operations")


class BrowserNavigationException(BrowserException):
    """
    Exception for browser navigation failures.

    This exception covers failures in page navigation, including
    timeouts, network issues, DNS problems, and invalid URLs.
    """

    def __init__(
            self,
            message: str,
            target_url: Optional[str] = None,
            current_url: Optional[str] = None,
            navigation_timeout: Optional[int] = None,
            status_code: Optional[int] = None,
            error_type: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser navigation exception.

        Args:
            message: Error description
            target_url: URL that failed to load
            current_url: Current page URL before navigation
            navigation_timeout: Timeout value used for navigation
            status_code: HTTP status code if available
            error_type: Type of navigation error (timeout, dns, connection, etc.)
            **kwargs: Additional exception arguments
        """
        # Navigation failures are medium severity with jitter for network issues
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL_JITTER)

        super().__init__(
            message=f"Navigation failed: {message}",
            **kwargs
        )

        self.target_url = target_url
        self.current_url = current_url
        self.navigation_timeout = navigation_timeout
        self.status_code = status_code
        self.error_type = error_type

        if target_url:
            self.add_context("target_url", target_url)
            # Extract domain for monitoring
            try:
                from urllib.parse import urlparse
                domain = urlparse(target_url).netloc
                self.add_tag(f"domain_{domain.replace('.', '_')}")
            except:
                pass

        if current_url:
            self.add_context("current_url", current_url)

        if navigation_timeout:
            self.add_context("navigation_timeout", navigation_timeout)

        if status_code:
            self.add_context("status_code", status_code)
            self.add_metadata("http_status", status_code)
            self._adjust_severity_by_status_code()

        if error_type:
            self.add_context("error_type", error_type)
            self.add_tag(f"nav_error_{error_type}")

        # Navigation-specific recovery suggestions
        self._add_navigation_recovery_suggestions()

    def _adjust_severity_by_status_code(self) -> None:
        """Adjust severity based on HTTP status code."""
        if self.status_code:
            if 400 <= self.status_code < 500:
                # Client errors are usually not retryable
                self.severity = ErrorSeverity.HIGH
                self.retry_strategy = RetryStrategy.NONE
            elif 500 <= self.status_code < 600:
                # Server errors should be retried
                self.severity = ErrorSeverity.MEDIUM
                self.retry_strategy = RetryStrategy.EXPONENTIAL_JITTER

    def _add_navigation_recovery_suggestions(self) -> None:
        """Add navigation-specific recovery suggestions."""
        self.add_recovery_suggestion("Verify target URL is accessible")
        self.add_recovery_suggestion("Check network connectivity and DNS resolution")

        if self.navigation_timeout and self.navigation_timeout < 30000:
            self.add_recovery_suggestion("Increase navigation timeout if page loads slowly")

        self.add_recovery_suggestion("Try navigating to URL manually in browser first")
        self.add_recovery_suggestion("Check for proxy or firewall blocking access")

        if self.status_code:
            if self.status_code == 404:
                self.add_recovery_suggestion("Page not found - verify URL is correct")
            elif self.status_code == 403:
                self.add_recovery_suggestion("Access forbidden - check authentication")
            elif self.status_code == 500:
                self.add_recovery_suggestion("Server error - wait and retry")
            elif self.status_code == 503:
                self.add_recovery_suggestion("Service unavailable - check server status")

        if self.error_type:
            if "timeout" in self.error_type.lower():
                self.add_recovery_suggestion("Page load timeout - check page performance")
            elif "dns" in self.error_type.lower():
                self.add_recovery_suggestion("DNS resolution failed - check domain name")
            elif "connection" in self.error_type.lower():
                self.add_recovery_suggestion("Connection failed - check network settings")


class BrowserTimeoutException(BrowserException):
    """
    Exception for browser operation timeouts.

    This exception is raised when browser operations exceed
    their configured timeout values.
    """

    def __init__(
            self,
            message: str,
            operation_type: Optional[str] = None,
            timeout_value: Optional[int] = None,
            elapsed_time: Optional[float] = None,
            element_selector: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser timeout exception.

        Args:
            message: Error description
            operation_type: Type of operation that timed out
            timeout_value: Configured timeout value in milliseconds
            elapsed_time: Actual time elapsed before timeout
            element_selector: Element selector if element operation
            **kwargs: Additional exception arguments
        """
        # Timeouts are medium severity with linear retry
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.LINEAR)

        super().__init__(
            message=f"Browser operation timed out: {message}",
            **kwargs
        )

        self.operation_type = operation_type
        self.timeout_value = timeout_value
        self.elapsed_time = elapsed_time
        self.element_selector = element_selector

        if operation_type:
            self.add_context("operation_type", operation_type)
            self.add_tag(f"timeout_{operation_type}")

        if timeout_value:
            self.add_context("timeout_value", timeout_value)
            self.add_metadata("timeout_ms", timeout_value)

        if elapsed_time:
            self.add_context("elapsed_time", elapsed_time)
            # Check if we were close to timeout
            if timeout_value and elapsed_time / (timeout_value / 1000) > 0.9:
                self.add_tag("near_timeout_limit")

        if element_selector:
            self.add_context("element_selector", element_selector)

        # Timeout-specific recovery suggestions
        self._add_timeout_recovery_suggestions()

    def _add_timeout_recovery_suggestions(self) -> None:
        """Add timeout-specific recovery suggestions."""
        self.add_recovery_suggestion("Increase timeout value for this operation")

        if self.timeout_value and self.timeout_value < 10000:
            self.add_recovery_suggestion(f"Current timeout {self.timeout_value}ms may be too short")

        self.add_recovery_suggestion("Check if page or elements load slowly")
        self.add_recovery_suggestion("Verify network conditions and page performance")
        self.add_recovery_suggestion("Consider breaking operation into smaller steps")

        if self.operation_type:
            if "wait" in self.operation_type.lower():
                self.add_recovery_suggestion("Element may not exist - verify selector")
            elif "load" in self.operation_type.lower():
                self.add_recovery_suggestion("Page load slow - check page size and resources")
            elif "script" in self.operation_type.lower():
                self.add_recovery_suggestion("JavaScript execution slow - optimize script")


class BrowserResourceException(BrowserException):
    """
    Exception for browser resource issues.

    This exception handles resource-related problems like
    memory exhaustion, too many open tabs, or disk space issues.
    """

    def __init__(
            self,
            message: str,
            resource_type: str,
            current_usage: Optional[float] = None,
            limit: Optional[float] = None,
            unit: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser resource exception.

        Args:
            message: Error description
            resource_type: Type of resource (memory, disk, handles, etc.)
            current_usage: Current resource usage
            limit: Resource limit
            unit: Unit of measurement (MB, GB, count, etc.)
            **kwargs: Additional exception arguments
        """
        # Resource issues are high severity
        kwargs.setdefault('severity', ErrorSeverity.HIGH)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL)

        super().__init__(
            message=f"Browser resource issue: {message}",
            **kwargs
        )

        self.resource_type = resource_type
        self.current_usage = current_usage
        self.limit = limit
        self.unit = unit

        self.add_context("resource_type", resource_type)
        self.add_tag(f"resource_{resource_type}")

        if current_usage is not None:
            self.add_context("current_usage", current_usage)
            self.add_metadata(f"{resource_type}_usage", current_usage)

        if limit is not None:
            self.add_context("limit", limit)

            # Calculate usage percentage
            if current_usage is not None:
                usage_percent = (current_usage / limit) * 100
                self.add_context("usage_percent", f"{usage_percent:.1f}%")

                if usage_percent > 90:
                    self.add_tag("critical_resource_usage")
                elif usage_percent > 75:
                    self.add_tag("high_resource_usage")

        if unit:
            self.add_context("unit", unit)

        # Resource-specific recovery suggestions
        self._add_resource_recovery_suggestions()

    def _add_resource_recovery_suggestions(self) -> None:
        """Add resource-specific recovery suggestions."""
        if self.resource_type == "memory":
            self.add_recovery_suggestion("Close unnecessary browser tabs and windows")
            self.add_recovery_suggestion("Clear browser cache and cookies")
            self.add_recovery_suggestion("Restart browser to free memory")
            self.add_recovery_suggestion("Check for memory leaks in test code")

        elif self.resource_type == "disk":
            self.add_recovery_suggestion("Clear browser download folder")
            self.add_recovery_suggestion("Remove old screenshots and videos")
            self.add_recovery_suggestion("Check available disk space")

        elif self.resource_type == "handles":
            self.add_recovery_suggestion("Close unused browser contexts")
            self.add_recovery_suggestion("Reduce concurrent browser operations")

        else:
            self.add_recovery_suggestion(f"Check {self.resource_type} usage and limits")
            self.add_recovery_suggestion("Restart browser to reset resources")
# src/core/exceptions/browser.py
"""
Browser-Related Exception Classes

Fixed version with proper imports and enhanced functionality.
"""

from typing import Optional

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
        super().__init__(
            message=message,
            category=ErrorCategory.BROWSER,
            severity=kwargs.get('severity', ErrorSeverity.HIGH),
            retry_strategy=kwargs.get('retry_strategy', RetryStrategy.LINEAR),
            **kwargs
        )

        # Add browser-specific context
        if browser_name:
            self.add_context("browser_name", browser_name)
        if browser_version:
            self.add_context("browser_version", browser_version)
        if session_id:
            self.add_context("session_id", session_id)

        # Add common recovery suggestions for browser issues
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
            launch_args: Optional[list] = None,
            **kwargs
    ):
        """
        Initialize browser launch exception.

        Args:
            message: Error description
            browser_name: Browser that failed to launch
            executable_path: Path to browser executable
            launch_args: Arguments used for launch
            **kwargs: Additional exception arguments
        """
        super().__init__(
            message=f"Failed to launch browser: {message}",
            browser_name=browser_name,
            severity=ErrorSeverity.CRITICAL,
            retry_strategy=RetryStrategy.LINEAR,  # Linear retry for launch issues
            **kwargs
        )

        if executable_path:
            self.add_context("executable_path", executable_path)
        if launch_args:
            self.add_context("launch_args", launch_args)

        # Launch-specific recovery suggestions
        self.add_recovery_suggestion("Verify browser executable exists and is accessible")
        self.add_recovery_suggestion("Check browser installation and try reinstalling")
        self.add_recovery_suggestion("Try launching browser manually to test")
        self.add_recovery_suggestion("Check for browser updates or use different version")


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
            crash_time: Optional[str] = None,
            **kwargs
    ):
        """
        Initialize browser crash exception.

        Args:
            message: Error description
            crash_reason: Reason for crash if known
            last_url: Last URL being accessed when crash occurred
            crash_time: When the crash happened
            **kwargs: Additional exception arguments
        """
        super().__init__(
            message=f"Browser crashed: {message}",
            severity=ErrorSeverity.CRITICAL,
            retry_strategy=RetryStrategy.EXPONENTIAL,  # Exponential backoff for crashes
            **kwargs
        )

        if crash_reason:
            self.add_context("crash_reason", crash_reason)
        if last_url:
            self.add_context("last_url", last_url)
        if crash_time:
            self.add_context("crash_time", crash_time)

        # Crash-specific recovery suggestions
        self.add_recovery_suggestion("Restart browser with fresh session")
        self.add_recovery_suggestion("Check browser logs for crash details")
        self.add_recovery_suggestion("Verify page content didn't cause crash")
        self.add_recovery_suggestion("Try with different browser if crash persists")
        self.add_recovery_suggestion("Check system memory and close other applications")


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
            **kwargs: Additional exception arguments
        """
        super().__init__(
            message=f"Navigation failed: {message}",
            severity=ErrorSeverity.MEDIUM,
            retry_strategy=RetryStrategy.EXPONENTIAL_JITTER,  # Jitter for network issues
            **kwargs
        )

        if target_url:
            self.add_context("target_url", target_url)
        if current_url:
            self.add_context("current_url", current_url)
        if navigation_timeout:
            self.add_context("navigation_timeout", navigation_timeout)
        if status_code:
            self.add_context("status_code", status_code)

        # Navigation-specific recovery suggestions
        self.add_recovery_suggestion("Verify target URL is accessible")
        self.add_recovery_suggestion("Check network connectivity and DNS resolution")
        self.add_recovery_suggestion("Increase navigation timeout if page loads slowly")
        self.add_recovery_suggestion("Try navigating to URL manually in browser first")
        self.add_recovery_suggestion("Check for proxy or firewall blocking access")


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
            **kwargs
    ):
        """
        Initialize browser timeout exception.

        Args:
            message: Error description
            operation_type: Type of operation that timed out
            timeout_value: Configured timeout value in milliseconds
            elapsed_time: Actual time elapsed before timeout
            **kwargs: Additional exception arguments
        """
        super().__init__(
            message=f"Browser operation timed out: {message}",
            severity=ErrorSeverity.MEDIUM,
            retry_strategy=RetryStrategy.LINEAR,  # Linear retry for timeouts
            **kwargs
        )

        if operation_type:
            self.add_context("operation_type", operation_type)
        if timeout_value:
            self.add_context("timeout_value", timeout_value)
        if elapsed_time:
            self.add_context("elapsed_time", elapsed_time)

        # Timeout-specific recovery suggestions
        self.add_recovery_suggestion("Increase timeout value for this operation")
        self.add_recovery_suggestion("Check if page or elements load slowly")
        self.add_recovery_suggestion("Verify network conditions and page performance")
        self.add_recovery_suggestion("Consider breaking operation into smaller steps")
# src/core/exceptions/browser.py
"""
Browser-Related Exception Classes
"""

from typing import Optional

from base import AutomationException
from enums import ErrorCategory, ErrorSeverity


class BrowserException(AutomationException):
    """
    Exceptions related to browser operations and management.
    """

    def __init__(
            self,
            message: str,
            browser_name: Optional[str] = None,
            browser_version: Optional[str] = None,
            **kwargs
    ):
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


class BrowserLaunchException(BrowserException):
    """Exception for browser launch failures."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=f"Failed to launch browser: {message}",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


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
            **kwargs
    ):
        super().__init__(
            message=f"Browser crashed: {message}",
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )

        if crash_reason:
            self.add_context("crash_reason", crash_reason)
        if last_url:
            self.add_context("last_url", last_url)

        # Add crash-specific recovery suggestions
        self.add_recovery_suggestion("Restart browser with fresh session")
        self.add_recovery_suggestion("Check browser logs for crash details")
        self.add_recovery_suggestion("Verify page content didn't cause crash")
        self.add_recovery_suggestion("Try with different browser if crash persists")


class BrowserNavigationException(BrowserException):
    """
    Exception for browser navigation failures.

    This exception covers failures in page navigation, including
    timeouts, network issues, and invalid URLs.
    """

    def __init__(
            self,
            message: str,
            target_url: Optional[str] = None,
            current_url: Optional[str] = None,
            navigation_timeout: Optional[int] = None,
            **kwargs
    ):
        super().__init__(
            message=f"Navigation failed: {message}",
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )

        if target_url:
            self.add_context("target_url", target_url)
        if current_url:
            self.add_context("current_url", current_url)
        if navigation_timeout:
            self.add_context("navigation_timeout", navigation_timeout)

        # Add navigation-specific recovery suggestions
        self.add_recovery_suggestion("Verify target URL is accessible")
        self.add_recovery_suggestion("Check network connectivity")
        self.add_recovery_suggestion("Increase navigation timeout")
        self.add_recovery_suggestion("Try navigating to URL manually first")
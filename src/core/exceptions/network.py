# src/core/exceptions/network.py
"""
Network and API Exception Classes
"""

from typing import Optional

from base import AutomationException
from enums import ErrorCategory, ErrorSeverity


class NetworkException(AutomationException):
    """
    Exceptions related to network operations and API calls.

    This exception type covers HTTP requests, API responses,
    and network connectivity issues.
    """

    def __init__(
            self,
            message: str,
            url: Optional[str] = None,
            status_code: Optional[int] = None,
            response_body: Optional[str] = None,
            **kwargs
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            **kwargs
        )

        if url:
            self.add_context("url", url)
        if status_code:
            self.add_context("status_code", status_code)
        if response_body:
            # Truncate long response bodies for logging
            truncated_body = response_body[:1000] + "..." if len(response_body) > 1000 else response_body
            self.add_context("response_body", truncated_body)

        # Add common recovery suggestions for network issues
        self.recovery_suggestions.extend([
            "Check network connectivity",
            "Verify API endpoint is accessible",
            "Check authentication credentials",
            "Retry the request after a delay"
        ])
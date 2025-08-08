# src/core/exceptions/network/__init__.py
"""
Network Exception Package
"""

from .network_exception import NetworkException
from .api_exception import APIException
from .connectivity_exception import ConnectivityException
from .http_exception import HTTPException

__all__ = [
    "NetworkException",
    "APIException",
    "ConnectivityException",
    "HTTPException"
]

# ========================================================================================
# src/core/exceptions/network/network_exception.py
"""
Base Network Exception Class - SOLID Implementation
"""

from typing import Optional, Dict, Any

from .base import AutomationException
from .enums import ErrorCategory, ErrorSeverity, RetryStrategy


class NetworkException(AutomationException):
    """
    Base class for all network-related exceptions.

    This exception covers HTTP requests, API responses,
    and network connectivity issues.
    """

    def __init__(
            self,
            message: str,
            url: Optional[str] = None,
            method: Optional[str] = None,
            status_code: Optional[int] = None,
            **kwargs
    ):
        # Set network-specific defaults
        kwargs.setdefault('severity', ErrorSeverity.MEDIUM)
        kwargs.setdefault('retry_strategy', RetryStrategy.EXPONENTIAL_JITTER)

        super().__init__(message=message, **kwargs)

        self.url = url
        self.method = method
        self.status_code = status_code

        if url:
            self.add_context("url", url)
        if method:
            self.add_context("method", method)
        if status_code:
            self.add_context("status_code", status_code)

    def _determine_category(self) -> ErrorCategory:
        """Return network error category."""
        return ErrorCategory.NETWORK

    def _initialize_exception(self) -> None:
        """Initialize network-specific recovery suggestions."""
        self.add_recovery_suggestion("Check network connectivity")
        self.add_recovery_suggestion("Verify API endpoint is accessible")
        self.add_recovery_suggestion("Check authentication credentials")
        self.add_recovery_suggestion("Retry the request after a delay")


# ========================================================================================
# src/core/exceptions/network/api_exception.py
"""
API Exception - SRP Implementation
"""

from typing import Optional, Dict, Any

from .network_exception import NetworkException
from ..enums import ErrorSeverity, RetryStrategy


class APIException(NetworkException):
    """
    Exception for API-related failures.

    This exception handles REST API errors, including
    HTTP status errors, malformed responses, and API-specific issues.
    """

    def __init__(
            self,
            message: str,
            api_endpoint: Optional[str] = None,
            response_body: Optional[str] = None,
            request_headers: Optional[Dict[str, str]] = None,
            response_headers: Optional[Dict[str, str]] = None,
            **kwargs
    ):
        super().__init__(message=f"API error: {message}", **kwargs)

        self.api_endpoint = api_endpoint
        self.response_body = response_body
        self.request_headers = request_headers or {}
        self.response_headers = response_headers or {}

        if api_endpoint:
            self.add_context("api_endpoint", api_endpoint)
        if response_body:
            # Truncate long response bodies for logging
            truncated_body = response_body[:1000] + "..." if len(response_body) > 1000 else response_body
            self.add_context("response_body", truncated_body)
        if request_headers:
            # Don't log sensitive headers
            safe_headers = {k: v for k, v in request_headers.items()
                            if k.lower() not in ['authorization', 'cookie', 'x-api-key']}
            self.add_context("request_headers", safe_headers)
        if response_headers:
            self.add_context("response_headers", response_headers)

    def _initialize_exception(self) -> None:
        """Initialize API-specific recovery suggestions."""
        super()._initialize_exception()

        self.add_recovery_suggestion("Check API documentation for correct usage")
        self.add_recovery_suggestion("Verify request format matches API expectations")
        self.add_recovery_suggestion("Check API rate limits and quotas")
        self.add_recovery_suggestion("Validate authentication tokens are not expired")

        # Status-code specific suggestions
        if self.status_code:
            if 400 <= self.status_code < 500:
                self.add_recovery_suggestion("Check request parameters and body format")
                if self.status_code == 401:
                    self.add_recovery_suggestion("Refresh authentication credentials")
                elif self.status_code == 403:
                    self.add_recovery_suggestion("Verify user permissions for this endpoint")
                elif self.status_code == 404:
                    self.add_recovery_suggestion("Check if API endpoint URL is correct")
                elif self.status_code == 429:
                    self.add_recovery_suggestion("Implement exponential backoff for rate limiting")
            elif 500 <= self.status_code < 600:
                self.add_recovery_suggestion("API server error - try again later")
                self.add_recovery_suggestion("Check API
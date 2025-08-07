# src/core/exceptions/element.py
"""
UI Element Exception Classes
"""

from typing import Optional

from base import AutomationException
from enums import ErrorCategory, ErrorSeverity


class ElementException(AutomationException):
    """
    Exceptions related to UI element interactions.

    This exception type covers element location, interaction,
    and state validation issues.
    """

    def __init__(
            self,
            message: str,
            selector: Optional[str] = None,
            element_type: Optional[str] = None,
            page_url: Optional[str] = None,
            **kwargs
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.ELEMENT,
            severity=kwargs.get('severity', ErrorSeverity.MEDIUM),
            **kwargs
        )

        if selector:
            self.add_context("selector", selector)
        if element_type:
            self.add_context("element_type", element_type)
        if page_url:
            self.add_context("page_url", page_url)

        # Add common recovery suggestions for element issues
        self.recovery_suggestions.extend([
            "Verify element selector is correct",
            "Check if element is visible on the page",
            "Wait for page to load completely",
            "Verify element is not inside a frame/iframe"
        ])